# dispute_assistant/config.py

"""
Central configuration file for the AI Dispute Assistant.

This file contains all the constants, rules, and settings used by the core processing engine.
By centralizing the configuration, we can easily update the logic (e.g., add a new keyword)
without modifying the main application code.
"""

# --- Fuzzy Matching Configuration ---
FUZZY_MATCH_THRESHOLD = 85
"""
The similarity score threshold (out of 100) for fuzzy matching.
A lower value makes matching more lenient, a higher value makes it stricter.
"""

# --- Keyword and Phrase Dictionaries for Classification ---
KEYWORD_MAP = {
    "FRAUD": [
        # Single, high-confidence keywords
        "fraud", "unauthorized", "suspicious", "chargeback",
        # Common descriptive phrases
        "i didn't make this payment",
        "not my transaction",
        "do not recognize this charge",
        "someone else used my card",
        "hacked",
    ],
    "REFUND_PENDING": [
        "refund", "waiting for money back", "reversed", "pending refund",
        "refund not received", "amount not reversed"
    ],
    "FAILED_TRANSACTION": [
        "failed", "money debited but not processed", "payment failed",
        "transaction declined", "gateway failed"
    ]
}
"""
A dictionary mapping dispute categories to a list of "evidence patterns".
The fuzzy matching logic will compare dispute descriptions against these patterns.
"""

# --- Resolution Suggestion Mapping ---
RESOLUTION_MAP = {
    "DUPLICATE_CHARGE": {
        "action": "Auto-refund",
        "justification": "High confidence duplicate transaction pattern detected."
    },
    "FRAUD": {
        "action": "Mark as potential fraud & Escalate to bank",
        "justification": "Transaction shows strong indicators of potential fraud."
    },
   "FAILED_TRANSACTION": {
        "action": "Manual review",
        "justification": "Customer claims debit despite failed status. Verify and process manual refund."
    },
    "REFUND_PENDING": {
        "action": "Escalate to bank",
        "justification": "Customer is waiting for a refund. Trace status with payment gateway or bank."
    },
    "OTHERS": {
        "action": "Ask for more info",
        "justification": "The nature of the dispute is unclear and requires more details from the customer."
    }
}

"""
A dictionary mapping a predicted category to a suggested action and a base justification template.
The final justification will be a combination of this template and the dynamic explanation from the classifier.
"""