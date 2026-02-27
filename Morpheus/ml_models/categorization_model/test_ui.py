"""
ml_models/categorization_model/test_ui.py
==========================================
Standalone Gradio / console test harness for the Categorisation model.
Run:  python ml_models/categorization_model/test_ui.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_models.categorization_model.inference import (
    categorize_transaction,
    categorize_dataframe,
    retrain_model,
)
from ml_models.categorization_model.dataset_loader import load_raw
import json


TEST_CASES = [
    {"raw_description": "SWIGGY ORDER 8823",  "amount": 450.0,  "merchant_name": "Swiggy",    "txn_type": "debit",  "payment_mode": "UPI"},
    {"raw_description": "AMAZON PAY SELLER",  "amount": 2999.0, "merchant_name": "Amazon",    "txn_type": "debit",  "payment_mode": "Credit Card"},
    {"raw_description": "HDFC BANK EMI 1234", "amount": 12500.0,"merchant_name": "HDFC EMI",  "txn_type": "debit",  "payment_mode": "Net Banking"},
    {"raw_description": "SALARY CREDIT INFOSYS","amount":80000.0,"merchant_name": "Employer", "txn_type": "credit", "payment_mode": "NEFT"},
    {"raw_description": "UBER TRIP BANGALORE","amount": 185.0,  "merchant_name": "Uber",      "txn_type": "debit",  "payment_mode": "UPI"},
    {"raw_description": "RANDOM TRANSACTION",  "amount": 999.0,  "merchant_name": "Unknown",   "txn_type": "debit",  "payment_mode": "Cash"},
]


def run_console_test():
    print("=" * 60)
    print("  CATEGORISATION MODEL — Console Test")
    print("=" * 60)

    print("\n🔄  Ensuring model is trained …")
    from ml_models.categorization_model.model import CategorizationModel
    m = CategorizationModel()
    if not m.is_trained():
        print("   Training model …")
        retrain_model()
    else:
        print("   ✅ Pre-trained model found")

    print("\n📋  Running test cases:\n")
    for i, tc in enumerate(TEST_CASES, 1):
        result = categorize_transaction(**tc, month=6, day_of_week=3, hour=14)
        flag   = "⚠️  NEEDS REVIEW" if result.get("needs_confirmation") else "✅"
        print(f"  [{i}] {tc['merchant_name']:<18} ₹{tc['amount']:<8}")
        print(f"       → Category  : {result['category']}")
        print(f"       → Confidence: {result['confidence']:.2%}  {flag}")
        print(f"       → Step      : {result['pipeline_step']}")
        print()

    print("\n📊  Batch prediction on first 20 rows of dataset:")
    df = load_raw().head(20)
    preds = categorize_dataframe(df)
    for _, row in preds.iterrows():
        flag = "⚠️" if row.get("needs_confirmation") else "✅"
        print(f"   {flag} {row['category']:<25} ({row['confidence']:.2%}) [{row['pipeline_step']}]")

    print("\n✅  Test complete.")


if __name__ == "__main__":
    run_console_test()
