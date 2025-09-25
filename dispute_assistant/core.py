"""
Hybrid dispute classification module for the AI Dispute Assistant.

This version implements a hybrid pipeline:
1. High-confidence metadata rules (duplicate check).
2. Per-phrase fuzzy matching (thefuzz/process.extractOne).
3. Semantic embedding similarity (SentenceTransformers) as a fallback/booster.
4. A priority/resolver that resolves conflicts (e.g., REFUND_PENDING > FAILED_TRANSACTION).

Drop-in replacement for your previous core module. No external orchestration changes required.
"""

import logging
from datetime import timedelta
from typing import Tuple, Dict, List

import pandas as pd
from thefuzz import fuzz, process

# Try to import sentence-transformers for embeddings. If not available, fall back to fuzz-only mode.
try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_EMBEDDINGS = True
except Exception:
    _HAS_EMBEDDINGS = False

# Import settings from our configuration file
from dispute_assistant import config

logger = logging.getLogger(__name__)


def _find_duplicate_transactions(dispute_txn: pd.Series, all_txns_df: pd.DataFrame, window_minutes: int = 3) -> bool:
    """
    (Internal) Checks for duplicate transactions in the transaction log within a short time window.
    """
    time_window = timedelta(minutes=window_minutes)
    dispute_time = dispute_txn['timestamp']

    potential_duplicates = all_txns_df[
        (all_txns_df['customer_id'] == dispute_txn['customer_id']) &
        (all_txns_df['amount'] == dispute_txn['amount']) &
        (all_txns_df['txn_id'] != dispute_txn['txn_id'])
    ]

    for _, row in potential_duplicates.iterrows():
        if abs(dispute_time - row['timestamp']) <= time_window:
            return True
    return False


class HybridMatcher:
    """Encapsulates fuzzy and embedding based matching against keyword maps."""

    def __init__(self, keyword_map: Dict[str, List[str]]):
        self.keyword_map = keyword_map
        # Pre-flattened lists for quick access
        self.categories = list(keyword_map.keys())

        # Precompute embeddings for each phrase, grouped by category, if embeddings available
        self.embed_model = None
        self.phrase_embeddings = {}

        if _HAS_EMBEDDINGS:
            try:
                # lightweight model suitable for sentence similarity
                self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
                for cat, phrases in keyword_map.items():
                    # store phrases as-is and their embeddings
                    self.phrase_embeddings[cat] = {
                        "phrases": phrases,
                        "embs": self.embed_model.encode(phrases, convert_to_tensor=True)
                    }
            except Exception as e:
                logger.warning("Embedding model failed to load: %s. Falling back to fuzz-only mode.", e)
                self.embed_model = None
                self.phrase_embeddings = {}

    def best_fuzzy_match(self, text: str, category: str) -> Tuple[str, int]:
        """Return best phrase and fuzz score for a given category."""
        phrases = self.keyword_map.get(category, [])
        if not phrases:
            return ("", 0)
        best = process.extractOne(text, phrases, scorer=fuzz.token_set_ratio)
        if best is None:
            return ("", 0)
        return best  # tuple (phrase, score)

    def best_embedding_score(self, text: str, category: str) -> float:
        """Return the max cosine similarity between text and any phrase in the category (0.0 - 1.0).
        If embedding model isn't available, returns 0.0.
        """
        if not self.embed_model or category not in self.phrase_embeddings:
            return 0.0
        try:
            text_emb = self.embed_model.encode(text, convert_to_tensor=True)
            phrase_embs = self.phrase_embeddings[category]["embs"]
            cos_scores = util.cos_sim(text_emb, phrase_embs)
            # cos_scores is a 1 x N tensor; take the max
            max_score = float(cos_scores.max())
            return max_score
        except Exception as e:
            logger.debug("Embedding scoring failed for category %s: %s", category, e)
            return 0.0

    def score_all_categories(self, text: str) -> Dict[str, Dict[str, float]]:
        """Return a dict with both fuzzy and embedding scores for all categories.
        Example: { 'FAILED_TRANSACTION': { 'fuzzy': 82, 'embed': 0.71 }, ... }
        """
        results = {}
        for cat in self.categories:
            best_phrase, fuzz_score = self.best_fuzzy_match(text, cat)
            emb_score = self.best_embedding_score(text, cat)
            results[cat] = {"best_phrase": best_phrase, "fuzzy": fuzz_score, "embed": emb_score}
        return results


# Initialize a global matcher instance at import time
_GLOBAL_MATCHER = HybridMatcher(config.KEYWORD_MAP)


def _combine_scores(fuzzy_score: float, embed_score: float, fuzz_weight: float = 0.6) -> float:
    """Combine fuzzy (0-100) and embed (0-1) into a unified 0-1 score.

    - fuzzy_score is scaled to 0-1 by /100
    - embed_score assumed to be 0-1
    - fuzz_weight controls relative importance of lexical overlap.
    """
    f = fuzzy_score / 100.0
    e = embed_score
    return fuzz_weight * f + (1 - fuzz_weight) * e


def classify_dispute(dispute: pd.Series, txns_df: pd.DataFrame) -> Tuple[str, float, str]:
    """
    Classify a single dispute using the hybrid waterfall engine.

    Returns (predicted_category, confidence, explanation)
    """
    description = (dispute.get('description') or "").lower()
    dispute_txn = txns_df.loc[txns_df['txn_id'] == dispute['txn_id']].iloc[0]
    logger.info("Classifying Dispute ID: %s", dispute['dispute_id'])

    # 1) High-confidence metadata-driven rule: duplicate transaction
    if _find_duplicate_transactions(dispute_txn, txns_df):
        return ("DUPLICATE_CHARGE", 0.95, "Data analysis found a transaction with the same amount and customer within 3 minutes.")

    # 2) Compute all fuzzy + embedding scores
    scores = _GLOBAL_MATCHER.score_all_categories(description)

    # Log intermediate scores for debugging/explainability
    logger.debug("Match scores for dispute %s: %s", dispute['dispute_id'], scores)

    # 3) Convert to combined scores
    combined = {}
    for cat, vals in scores.items():
        combined_score = _combine_scores(vals['fuzzy'], vals['embed'])
        combined[cat] = {"combined": combined_score, "fuzzy": vals['fuzzy'], "embed": vals['embed'], "best_phrase": vals['best_phrase']}

    # Helper to map combined score to confidence level
    def _combined_to_confidence(score: float) -> float:
        # score in 0-1; map to a 0.5-0.95 range for output confidence
        return round(0.5 + 0.45 * min(max(score, 0.0), 1.0), 2)

    # 4) Priority and conflict resolution logic
    # Business priority: FRAUD > DUPLICATE_CHARGE (handled above) > REFUND_PENDING > FAILED_TRANSACTION > OTHERS

    # Quick check for FRAUD (high priority)
    fraud_combined = combined.get('FRAUD', {}).get('combined', 0.0)
    if fraud_combined >= 0.7:
        conf = _combined_to_confidence(fraud_combined)
        explanation = f"Description matched FRAUD keywords. phrase='{combined['FRAUD']['best_phrase']}', fuzzy={combined['FRAUD']['fuzzy']}, embed={combined['FRAUD']['embed']:.2f}"
        return ("FRAUD", conf, explanation)

    # Check REFUND_PENDING vs FAILED_TRANSACTION conflict: prefer REFUND_PENDING when both are present
    refund_combined = combined.get('REFUND_PENDING', {}).get('combined', 0.0)
    failed_combined = combined.get('FAILED_TRANSACTION', {}).get('combined', 0.0)

    # If refund appears clearly
    if refund_combined >= 0.6:
        conf = _combined_to_confidence(refund_combined)
        explanation = f"Description matched REFUND_PENDING. phrase='{combined['REFUND_PENDING']['best_phrase']}', fuzzy={combined['REFUND_PENDING']['fuzzy']}, embed={combined['REFUND_PENDING']['embed']:.2f}"
        return ("REFUND_PENDING", conf, explanation)

    # If refund not strong but failed is strong, choose failed
    if failed_combined >= 0.6:
        # Further bump confidence if transaction metadata status is FAILED or CANCELLED
        status = dispute_txn.get('status', '').upper()
        conf = _combined_to_confidence(failed_combined)
        if status in ['FAILED', 'CANCELLED']:
            conf = min(conf + 0.15, 0.95)
        explanation = f"Description matched FAILED_TRANSACTION. phrase='{combined['FAILED_TRANSACTION']['best_phrase']}', fuzzy={combined['FAILED_TRANSACTION']['fuzzy']}, embed={combined['FAILED_TRANSACTION']['embed']:.2f}. Txn status={status}"
        return ("FAILED_TRANSACTION", conf, explanation)

    # Check DUPLICATE_CHARGE by text (less priority than metadata duplicate which we handled earlier)
    dup_combined = combined.get('DUPLICATE_CHARGE', {}).get('combined', 0.0)
    if dup_combined >= 0.7:
        conf = _combined_to_confidence(dup_combined)
        explanation = f"Description matched DUPLICATE_CHARGE keywords. phrase='{combined['DUPLICATE_CHARGE']['best_phrase']}', fuzzy={combined['DUPLICATE_CHARGE']['fuzzy']}, embed={combined['DUPLICATE_CHARGE']['embed']:.2f}"
        return ("DUPLICATE_CHARGE", conf, explanation)

    # If nothing strong matched, but some category has a mild score, pick the max with conservative confidence
    best_cat = max(combined.items(), key=lambda kv: kv[1]['combined'])[0]
    best_score = combined[best_cat]['combined']

    if best_score >= 0.45:
        conf = _combined_to_confidence(best_score)
        explanation = f"Low-confidence automatic match: chosen '{best_cat}' by combined score. phrase='{combined[best_cat]['best_phrase']}', fuzzy={combined[best_cat]['fuzzy']}, embed={combined[best_cat]['embed']:.2f}"
        return (best_cat, conf, explanation)

    # Fallback to OTHERS
    return ("OTHERS", 0.5, "No strong rule or semantic/fuzzy match. Requires manual investigation.")


def suggest_resolution(category: str, explanation: str) -> Tuple[str, str]:
    resolution_info = config.RESOLUTION_MAP.get(category, config.RESOLUTION_MAP['OTHERS'])
    action = resolution_info["action"]
    justification = f"{resolution_info['justification']} Reason: {explanation}"
    return (action, justification)


def process_files(disputes_file, transactions_file):
    """Main orchestration for processing CSVs (unchanged except using the hybrid classifier)."""
    try:
        disputes_df = pd.read_csv(disputes_file, parse_dates=['created_at'])
        txns_df = pd.read_csv(transactions_file, parse_dates=['timestamp'])
    except Exception as e:
        raise ValueError(f"Error parsing CSV files: {e}")

    classified_results = []
    resolution_results = []

    for _, dispute in disputes_df.iterrows():
        category, confidence, explanation = classify_dispute(dispute, txns_df)
        action, justification = suggest_resolution(category, explanation)

        classified_results.append({
            "dispute_id": dispute["dispute_id"],
            "predicted_category": category,
            "confidence": confidence,
            "explanation": explanation,
            "status": "New"
        })

        resolution_results.append({
            "dispute_id": dispute["dispute_id"],
            "suggested_action": action,
            "justification": justification
        })

    classified_df = pd.DataFrame(classified_results)
    resolutions_df = pd.DataFrame(resolution_results)

    return classified_df, resolutions_df
