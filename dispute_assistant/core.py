"""
Core data processing module for the AI Dispute Assistant.

This module contains the primary business logic for:
1. Classifying disputes using a rule-based, fuzzy-matching engine.
2. Suggesting resolutions based on the assigned category.
3. A main processing function to orchestrate the entire pipeline.
"""

import pandas as pd
from thefuzz import fuzz,process
from datetime import timedelta

# Import settings from our configuration file
from dispute_assistant import config


def _find_duplicate_transactions(dispute_txn, all_txns_df):
    """
    (Internal Helper) Checks for duplicate transactions in the transaction log.
    This implements the data-driven check for the bonus task.

    Args:
        dispute_txn (pd.Series): A row from the transactions dataframe related to the dispute.
        all_txns_df (pd.DataFrame): The complete dataframe of all transactions.

    Returns:
        bool: True if a likely duplicate is found, False otherwise.
    """
    time_window = timedelta(minutes=3)
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


def classify_dispute(dispute, txns_df):
    """
    Classifies a single dispute using the rule-based "waterfall" engine.

    Args:
        dispute (pd.Series): A row from the disputes dataframe.
        txns_df (pd.DataFrame): The complete dataframe of all transactions.

    Returns:
        tuple: A tuple containing (predicted_category, confidence, explanation).
    """
    description = dispute['description'].lower()
    dispute_txn = txns_df.loc[txns_df['txn_id'] == dispute['txn_id']].iloc[0]
    print("Classifying Dispute ID:", dispute['dispute_id'])

    # Rule 0: High-confidence data-driven duplicate check (Bonus)
    if _find_duplicate_transactions(dispute_txn, txns_df):
        return ("DUPLICATE_CHARGE", 0.95, "Data analysis found a transaction with the same amount and customer within 3 minutes.")

    # Rule 1: Check for FRAUD (High-risk first)
    best_fraud_match, fraud_score = process.extractOne(description, config.KEYWORD_MAP["FRAUD"], scorer=fuzz.token_set_ratio)
    print("Fraud Score", fraud_score)
    if fraud_score >= config.FUZZY_MATCH_THRESHOLD:
        return ("FRAUD", 0.9, f"Description matched fraud keywords with a score of {fraud_score}.")

    # Rule 2: Check for DUPLICATE_CHARGE (Text-based)
    best_duplicate_match, duplicate_score = process.extractOne(description, config.KEYWORD_MAP["DUPLICATE_CHARGE"], scorer=fuzz.token_set_ratio)
    print("Duplicate Score", duplicate_score)
    if duplicate_score >= config.FUZZY_MATCH_THRESHOLD:
        return ("DUPLICATE_CHARGE", 0.9, f"Description matched duplicate charge keywords with score {duplicate_score}.")

    # Rule 3: Check for FAILED_TRANSACTION
    best_failed_match, failed_score = process.extractOne(description, config.KEYWORD_MAP["FAILED_TRANSACTION"], scorer=fuzz.token_set_ratio)
    print("Failed Score", failed_score)
    if failed_score >= config.FUZZY_MATCH_THRESHOLD:
        status = dispute_txn['status'].upper()
        explanation = f"Description matched failed keywords and txn status is '{status}'."
        confidence = 0.9 if status in ['FAILED', 'CANCELLED'] else 0.7
        return ("FAILED_TRANSACTION", confidence, explanation)

    # Rule 4: Check for REFUND_PENDING
    best_refund_match, refund_score = process.extractOne(description, config.KEYWORD_MAP["REFUND_PENDING"], scorer=fuzz.token_set_ratio)
    print("Refund Score", refund_score)
    if refund_score >= config.FUZZY_MATCH_THRESHOLD:
        return ("REFUND_PENDING", 0.85, f"Description matched refund keywords with score {refund_score}.")

    # Rule 5: Fallback
    return ("OTHERS", 0.5, "No specific keywords or rules matched. Requires manual investigation.")


def suggest_resolution(category, explanation):
    """
    Suggests a next action and a dynamic justification based on the dispute category.

    Args:
        category (str): The predicted category of the dispute.
        explanation (str): The explanation from the classification step.

    Returns:
        tuple: A tuple containing (suggested_action, justification).
    """
    resolution_info = config.RESOLUTION_MAP.get(category)
    action = resolution_info["action"]
    justification = f"{resolution_info['justification']} Reason: {explanation}"
    return (action, justification)


def process_files(disputes_file, transactions_file):
    """
    The main orchestration function for the processing pipeline.

    Args:
        disputes_file: A file-like object for the disputes CSV.
        transactions_file: A file-like object for the transactions CSV.

    Returns:
        tuple: A tuple of two DataFrames (classified_disputes_df, resolutions_df).
    """
    try:
        disputes_df = pd.read_csv(disputes_file, parse_dates=['created_at'])
        txns_df = pd.read_csv(transactions_file, parse_dates=['timestamp'])
    except Exception as e:
        # In a real app, you'd want more specific error handling
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
            "status": "New"  # Bonus Point: Add case history tracking from the start
        })

        resolution_results.append({
            "dispute_id": dispute["dispute_id"],
            "suggested_action": action,
            "justification": justification
        })

    classified_df = pd.DataFrame(classified_results)
    resolutions_df = pd.DataFrame(resolution_results)

    return classified_df, resolutions_df