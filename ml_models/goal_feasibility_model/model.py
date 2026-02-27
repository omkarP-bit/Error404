"""
ml_models/goal_feasibility_model/model.py
==========================================
Goal Probability Classifier — v2.0

Primary  : HistGradientBoostingClassifier  (sklearn, XGBoost-equivalent algorithm)
            — handles non-linear financial behaviour, native NaN support,
              feature importances via permutation.
Fallback : LogisticRegression (< 30 training samples or when primary not fitted)

Output   : probability ∈ [0, 1]  (goal achieved before deadline)
Artifacts saved to ml_models/goal_feasibility_model/artifacts/
  ▸ gb_classifier.pkl
  ▸ lr_fallback.pkl
  ▸ preprocessor.pkl
  ▸ feature_names.json
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.inspection import permutation_importance

from ml_models.goal_feasibility_model.feature_builder import FEATURE_NAMES
from ml_models.goal_feasibility_model.preprocessing import GoalPreprocessor
from ml_models.goal_feasibility_model.dataset_loader import load_for_goal_feasibility

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


class GoalProbabilityModel:
    """Binary classifier: P(goal achieved before deadline)."""

    VERSION = "2.0"

    def __init__(self):
        self.preprocessor : Optional[GoalPreprocessor]              = None
        self.gb_model     : Optional[HistGradientBoostingClassifier] = None
        self.lr_fallback  : Optional[LogisticRegression]            = None
        self.feature_importances_: dict[str, float] = {}
        self._fitted = False

    # ────────────────────────────────────────────────────────────────────────
    # Training
    # ────────────────────────────────────────────────────────────────────────
    def train(self, verbose: bool = True) -> dict:
        if verbose:
            print("📚  Generating synthetic goal-feasibility dataset …")
        X_df, y = load_for_goal_feasibility()

        self.preprocessor = GoalPreprocessor()
        X_scaled = self.preprocessor.fit_transform(X_df)

        X_tr, X_te, y_tr, y_te = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        # Primary: HistGradientBoosting
        if verbose:
            print("🌲  Training HistGradientBoostingClassifier …")
        self.gb_model = HistGradientBoostingClassifier(
            max_iter      = 200,
            max_depth     = 6,
            learning_rate = 0.07,
            min_samples_leaf = 20,
            l2_regularization = 0.1,
            random_state  = 42,
        )
        self.gb_model.fit(X_tr, y_tr)

        # Fallback: LogReg
        self.lr_fallback = LogisticRegression(max_iter=1000, random_state=42)
        self.lr_fallback.fit(X_tr, y_tr)

        # Evaluation
        y_pred_proba = self.gb_model.predict_proba(X_te)[:, 1]
        auc   = roc_auc_score(y_te, y_pred_proba)
        cv_auc = cross_val_score(
            self.gb_model, X_scaled, y, cv=5, scoring="roc_auc"
        ).mean()
        report = classification_report(y_te, (y_pred_proba > 0.5).astype(int),
                                       output_dict=True)

        # Feature importance via permutation
        perm = permutation_importance(self.gb_model, X_te, y_te,
                                      n_repeats=5, random_state=42)
        self.feature_importances_ = {
            name: round(float(imp), 5)
            for name, imp in sorted(
                zip(FEATURE_NAMES, perm.importances_mean),
                key=lambda x: -x[1]
            )
        }

        self._fitted = True
        self._save()

        result = {
            "auc":         round(float(auc), 4),
            "cv_auc":      round(float(cv_auc), 4),
            "accuracy":    round(float(report["accuracy"]), 4),
            "n_train":     len(X_tr),
            "n_test":      len(X_te),
            "top_features": list(self.feature_importances_.keys())[:5],
        }
        if verbose:
            print(f"   AUC    : {auc:.4f}")
            print(f"   CV-AUC : {cv_auc:.4f}")
            print(f"   Top-3  : {result['top_features'][:3]}")
            print("✅  Goal probability model saved")
        return result

    # ────────────────────────────────────────────────────────────────────────
    # Prediction
    # ────────────────────────────────────────────────────────────────────────
    def predict_proba(self, feature_dict: dict) -> tuple[float, str]:
        """
        Returns:
          probability  ∈ [0, 1]
          model_source — 'gradient_boost' | 'logistic_regression'
        """
        if not self._fitted:
            self.load()

        X = self.preprocessor.transform_dict(feature_dict)

        # Use primary if available
        if self.gb_model is not None:
            prob = float(self.gb_model.predict_proba(X)[0, 1])
            return round(prob, 4), "gradient_boost"

        prob = float(self.lr_fallback.predict_proba(X)[0, 1])
        return round(prob, 4), "logistic_regression"

    def get_feature_importances(self) -> dict[str, float]:
        return self.feature_importances_

    # ────────────────────────────────────────────────────────────────────────
    # Persistence
    # ────────────────────────────────────────────────────────────────────────
    def _save(self):
        joblib.dump(self.gb_model,    ARTIFACT_DIR / "gb_classifier.pkl")
        joblib.dump(self.lr_fallback, ARTIFACT_DIR / "lr_fallback.pkl")
        self.preprocessor.save()
        with open(ARTIFACT_DIR / "feature_names.json", "w") as f:
            json.dump({"features": FEATURE_NAMES,
                       "importances": self.feature_importances_}, f, indent=2)

    def load(self):
        self.preprocessor = GoalPreprocessor.load()
        self.gb_model     = joblib.load(ARTIFACT_DIR / "gb_classifier.pkl")
        self.lr_fallback  = joblib.load(ARTIFACT_DIR / "lr_fallback.pkl")
        fi_path = ARTIFACT_DIR / "feature_names.json"
        if fi_path.exists():
            with open(fi_path) as f:
                d = json.load(f)
            self.feature_importances_ = d.get("importances", {})
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "gb_classifier.pkl").exists()


# ── Backward-compat alias (old code uses GoalFeasibilityModel) ───────────────
GoalFeasibilityModel = GoalProbabilityModel


if __name__ == "__main__":
    m      = GoalProbabilityModel()
    report = m.train(verbose=True)
    print(f"\nReport: {report}")
    sample_feat = {k: 0.5 for k in FEATURE_NAMES}
    sample_feat.update({"feasibility_ratio": 1.3, "months_left": 12.0,
                        "avg_monthly_surplus": 25000, "expense_volatility_ratio": 0.2})
    prob, src = m.predict_proba(sample_feat)
    print(f"Sample prediction: {prob:.2%}  ({src})")

