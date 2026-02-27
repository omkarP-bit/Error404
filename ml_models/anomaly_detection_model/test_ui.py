"""
ml_models/anomaly_detection_model/test_ui.py
=============================================
Console test harness for Anomaly Detection model.
Run: python ml_models/anomaly_detection_model/test_ui.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_models.anomaly_detection_model.inference import (
    detect_anomaly,
    scan_dataset_anomalies,
    retrain_model,
)


TEST_CASES = [
    # Normal transaction
    {"amount": 350.0,  "amount_z_score": 0.2,  "daily_txn_freq": 2, "category_variance": 5,
     "is_odd_hour": 0, "avg_spend_per_category": 400.0, "spend_std_dev": 120.0, "expense_volatility": 3000.0},
    # Suspicious: huge amount at odd hour
    {"amount": 85000.0,"amount_z_score": 8.5,  "daily_txn_freq": 1, "category_variance": 1,
     "is_odd_hour": 1, "avg_spend_per_category": 400.0, "spend_std_dev": 120.0, "expense_volatility": 3000.0},
    # Frequency spike (20 transactions in one day)
    {"amount": 300.0,  "amount_z_score": 0.1,  "daily_txn_freq":20, "category_variance": 2,
     "is_odd_hour": 0, "avg_spend_per_category": 300.0, "spend_std_dev": 50.0,  "expense_volatility": 2000.0},
    # Large single transaction
    {"amount": 45000.0,"amount_z_score": 5.2,  "daily_txn_freq": 1, "category_variance": 3,
     "is_odd_hour": 0, "avg_spend_per_category": 1200.0,"spend_std_dev": 800.0, "expense_volatility": 5000.0},
]


def run_console_test():
    print("=" * 60)
    print("  ANOMALY DETECTION MODEL — Console Test")
    print("=" * 60)

    from ml_models.anomaly_detection_model.model import AnomalyDetectionModel
    m = AnomalyDetectionModel()
    if not m.is_trained():
        print("\n🔄  Training model …")
        retrain_model()
    else:
        print("\n✅  Pre-trained model found")

    print("\n📋  Single-record test cases:\n")
    for i, tc in enumerate(TEST_CASES, 1):
        result = detect_anomaly(tc)
        flag = "🚨 ANOMALY" if result["is_anomaly"] else "✅ Normal"
        print(f"  [{i}] Amount: ₹{tc['amount']:<10} z-score: {tc['amount_z_score']}")
        print(f"       → {flag}  |  Score: {result['anomaly_score']:.4f}  |  {result['severity'].upper()}")
        print(f"       → {result['explanation']}")
        print()

    print("\n📊  Full dataset anomaly scan:")
    result_df = scan_dataset_anomalies()
    n_total    = len(result_df)
    n_anomaly  = int(result_df["is_anomaly"].sum())
    print(f"   Total transactions : {n_total:,}")
    print(f"   Anomalies detected : {n_anomaly} ({n_anomaly/n_total:.1%})")
    print("\n   Severity breakdown:")
    for sev in ["critical", "high", "medium", "low"]:
        cnt = int((result_df[result_df["is_anomaly"]==1]["severity"] == sev).sum())
        print(f"     {sev:<10}: {cnt}")

    print("\n✅  Test complete.")


if __name__ == "__main__":
    run_console_test()
