"""
Goal Probability Classifier — v2.0

Primary  : HistGradientBoostingClassifier
Fallback : LogisticRegression
Output   : probability ∈ [0, 1] (goal achieved before deadline)
"""

import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


class GoalProbabilityModel:
    """Binary classifier: P(goal achieved before deadline)."""

    VERSION = "2.0"

    def __init__(self):
        self.scaler = StandardScaler()
        self.gb_model = None
        self.lr_fallback = None
        self.feature_importances_ = {}
        self._fitted = False

    def train(self, X_df: pd.DataFrame, y: pd.Series):
        """Train on goal feasibility features."""
        X_scaled = self.scaler.fit_transform(X_df.fillna(0))

        # Primary: HistGradientBoosting
        self.gb_model = HistGradientBoostingClassifier(
            max_iter=200,
            max_depth=6,
            learning_rate=0.07,
            min_samples_leaf=20,
            l2_regularization=0.1,
            random_state=42,
        )
        self.gb_model.fit(X_scaled, y)

        # Fallback: LogReg
        self.lr_fallback = LogisticRegression(max_iter=1000, random_state=42)
        self.lr_fallback.fit(X_scaled, y)

        self._fitted = True
        self._save()

        # Evaluation
        y_pred_proba = self.gb_model.predict_proba(X_scaled)[:, 1]
        auc = roc_auc_score(y, y_pred_proba)

        return {
            "auc": round(float(auc), 4),
            "n_samples": len(X_scaled),
        }

    def predict_proba(self, feature_dict: dict) -> tuple[float, str]:
        """Returns probability and model source."""
        if not self._fitted:
            self.load()

        # Expected features: feasibility_ratio, months_left, avg_monthly_surplus, etc.
        features = [
            feature_dict.get('feasibility_ratio', 0),
            feature_dict.get('months_left', 0),
            feature_dict.get('avg_monthly_surplus', 0),
            feature_dict.get('expense_volatility_ratio', 0),
            feature_dict.get('current_progress', 0),
        ]

        X_scaled = self.scaler.transform([features])

        if self.gb_model is not None:
            prob = float(self.gb_model.predict_proba(X_scaled)[0, 1])
            return round(prob, 4), "gradient_boost"

        prob = float(self.lr_fallback.predict_proba(X_scaled)[0, 1])
        return round(prob, 4), "logistic_regression"

    def calculate(self, user_id: int, goal: dict, user_profile: dict, user_history: list) -> dict:
        """Calculate goal feasibility with recommendations."""
        from datetime import datetime

        target_amount = float(goal['target_amount'])
        current_amount = float(goal.get('current_amount', 0))
        deadline = datetime.fromisoformat(goal['deadline']) if isinstance(goal['deadline'], str) else goal['deadline']
        
        remaining_amount = target_amount - current_amount
        days_left = (deadline - datetime.now()).days
        months_left = max(days_left / 30, 1)
        
        if months_left <= 0:
            return {
                'feasibility_score': 0,
                'monthly_required': 0,
                'recommendations': ['Goal deadline has passed']
            }
        
        monthly_required = remaining_amount / months_left
        
        if not user_profile:
            return {
                'feasibility_score': 0.5,
                'monthly_required': round(monthly_required, 2),
                'recommendations': ['Complete your financial profile']
            }
        
        safe_investable = float(user_profile.get('safe_investable_amount', 0))
        
        # Build features for ML prediction
        features = {
            'feasibility_ratio': safe_investable / monthly_required if monthly_required > 0 else 1,
            'months_left': months_left,
            'avg_monthly_surplus': float(user_profile.get('avg_monthly_surplus', 0)),
            'expense_volatility_ratio': float(user_profile.get('expense_volatility', 0)) / float(user_profile.get('baseline_expense', 1)),
            'current_progress': current_amount / target_amount if target_amount > 0 else 0,
        }
        
        feasibility_score, model_source = self.predict_proba(features)
        
        # Generate recommendations
        recommendations = []
        if feasibility_score >= 0.8:
            recommendations.append('Goal is highly achievable with current savings')
        elif feasibility_score >= 0.5:
            recommendations.append('Goal is achievable but requires discipline')
            recommendations.append(f'Try to save ₹{monthly_required:.0f} per month')
        else:
            recommendations.append('Goal may be challenging with current finances')
            recommendations.append(f'Consider extending deadline or reducing target')
        
        return {
            'feasibility_score': round(feasibility_score, 4),
            'monthly_required': round(monthly_required, 2),
            'months_left': round(months_left, 1),
            'recommendations': recommendations,
            'model_source': model_source,
        }

    def _save(self):
        joblib.dump(self.scaler, ARTIFACT_DIR / "scaler.pkl")
        joblib.dump(self.gb_model, ARTIFACT_DIR / "gb_classifier.pkl")
        joblib.dump(self.lr_fallback, ARTIFACT_DIR / "lr_fallback.pkl")

    def load(self):
        self.scaler = joblib.load(ARTIFACT_DIR / "scaler.pkl")
        self.gb_model = joblib.load(ARTIFACT_DIR / "gb_classifier.pkl")
        self.lr_fallback = joblib.load(ARTIFACT_DIR / "lr_fallback.pkl")
        self._fitted = True

    def is_trained(self) -> bool:
        return (ARTIFACT_DIR / "gb_classifier.pkl").exists()


# Backward-compat alias
GoalFeasibilityModel = GoalProbabilityModel
