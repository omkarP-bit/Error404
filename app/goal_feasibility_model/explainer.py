"""
ml_models/goal_feasibility_model/explainer.py
==============================================
Local Explainability Engine — SHAP-style feature attribution.

Approach: Occlusion / Marginal Sensitivity Analysis
  For each feature i, measure how much the predicted probability drops
  when feature i is replaced with its training-set mean value.
  SHAP_i ≈ P(all features) − P(feature_i = population_mean)

This is a first-order Shapley approximation that:
  ✓ Is directionally correct for monotone features
  ✓ Requires no external dependency (no shap package)
  ✓ Runs in O(n_features × forward_pass) time
  ✓ Produces human-readable positive/negative drivers

Feature population means are stored in the preprocessor's scaler.mean_
attribute (inverse-transformed back to original space).

Output:
  {
    "top_negative": [
      {"feature": "expense_volatility_ratio",
       "human_label": "High expense volatility",
       "shap_value": -0.134, "current_value": 0.62},
      ...
    ],
    "top_positive": [
      {"feature": "avg_monthly_surplus",
       "human_label": "Strong monthly surplus",
       "shap_value": +0.112, "current_value": 42000},
      ...
    ],
    "all_contributions": {"feature_name": float, ...}
  }
"""
from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ml_models.goal_feasibility_model.model import GoalProbabilityModel

# ── Human-readable labels for each feature ───────────────────────────────────
FEATURE_LABELS: dict[str, str] = {
    "log_target_amount":        "Goal target size",
    "log_remaining_amount":     "Remaining amount to save",
    "months_left":              "Time remaining to deadline",
    "monthly_required":         "Required monthly savings rate",
    "progress_pct":             "Progress made so far",
    "monthly_income":           "Monthly income",
    "avg_monthly_surplus":      "Average monthly surplus",
    "expense_volatility":       "Expense variability (absolute)",
    "current_balance":          "Current account balance",
    "safe_surplus":             "Safe investable surplus",
    "savings_rate":             "Savings rate (% of income)",
    "feasibility_ratio":        "Surplus-to-requirement ratio",
    "avg_monthly_expenses":     "Average monthly expenses",
    "expense_volatility_ratio": "Expense volatility (relative)",
    "anomaly_count_3m":         "Unusual high-value transactions",
    "recurring_expense_ratio":  "Recurring expense burden",
    "discretionary_ratio":      "Discretionary spending share",
    "txn_frequency":            "Transaction frequency",
    "high_value_txn_count":     "High-value transaction count",
    "dining_slope":             "Rising dining expenses trend",
    "shopping_slope":           "Rising shopping expenses trend",
    "entertainment_slope":      "Rising entertainment expenses trend",
    "contribution_streak":      "Consistent saving streak (months)",
    "missed_saving_months":     "Months with insufficient savings",
    "behavioral_consistency":   "Spending behaviour consistency",
    "health_score":             "Financial health score",
    "debit_ratio_3m_6m":        "Recent spend acceleration",
    "income_stability":         "Income source stability",
}

# Features where a HIGHER value is BAD for the probability
NEGATIVE_DIRECTION: set[str] = {
    "log_remaining_amount",
    "monthly_required",
    "expense_volatility",
    "avg_monthly_expenses",
    "expense_volatility_ratio",
    "anomaly_count_3m",
    "recurring_expense_ratio",
    "discretionary_ratio",
    "high_value_txn_count",
    "dining_slope",
    "shopping_slope",
    "entertainment_slope",
    "missed_saving_months",
    "debit_ratio_3m_6m",
}


class LocalExplainer:
    """
    Computes per-feature probability contributions for one prediction.
    Must be called after the model is fitted.
    """

    def __init__(self, model: "GoalProbabilityModel"):
        self.model = model
        # Compute population means from scaler (training distribution)
        try:
            self._pop_means: np.ndarray = model.preprocessor.scaler.mean_
        except Exception:
            self._pop_means = None

    def explain(
        self,
        feature_dict: dict,
        base_probability: float,
        top_k_negative: int = 3,
        top_k_positive: int = 2,
    ) -> dict:
        """
        Run occlusion analysis over all 28 features.

        Parameters
        ----------
        feature_dict     : raw (unscaled) feature dict
        base_probability : model output for the unmodified feature vector
        top_k_negative   : how many negative drivers to return
        top_k_positive   : how many positive drivers to return
        """
        from ml_models.goal_feasibility_model.feature_builder import FEATURE_NAMES

        if self._pop_means is None:
            return _empty_explanation()

        contributions: dict[str, float] = {}

        for i, fname in enumerate(FEATURE_NAMES):
            # Replace this feature with its population mean (occlude it)
            occluded = dict(feature_dict)
            # Pop mean is in scaled space; inverse-transform back to raw space
            scaler = self.model.preprocessor.scaler
            # Build a scaled vector with only this feature at mean (=0 in scaled space)
            try:
                X_base     = self.model.preprocessor.transform_dict(feature_dict).flatten()
                X_occluded = X_base.copy()
                X_occluded[i] = 0.0   # mean of a StandardScaler feature = 0 in scaled space

                gb = self.model.gb_model or self.model.lr_fallback
                if gb is None:
                    contributions[fname] = 0.0
                    continue

                p_occluded = float(gb.predict_proba(X_occluded.reshape(1, -1))[0, 1])
                contributions[fname] = round(base_probability - p_occluded, 5)
            except Exception:
                contributions[fname] = 0.0

        # Sort into positive / negative drivers
        sorted_contribs = sorted(contributions.items(), key=lambda x: x[1])

        # Negative drivers: features whose occlusion INCREASES probability
        # (meaning their current value was hurting us)
        negatives = [
            {
                "feature":       fname,
                "human_label":   FEATURE_LABELS.get(fname, fname),
                "shap_value":    round(val, 5),
                "current_value": round(feature_dict.get(fname, 0.0), 4),
            }
            for fname, val in sorted_contribs
            if val < 0
        ][:top_k_negative]

        # Positive drivers: features whose occlusion DECREASES probability
        # (meaning their current value was helping us)
        positives = [
            {
                "feature":       fname,
                "human_label":   FEATURE_LABELS.get(fname, fname),
                "shap_value":    round(val, 5),
                "current_value": round(feature_dict.get(fname, 0.0), 4),
            }
            for fname, val in reversed(sorted_contribs)
            if val > 0
        ][:top_k_positive]

        return {
            "top_negative":      negatives,
            "top_positive":      positives,
            "all_contributions": {k: round(v, 5) for k, v in contributions.items()},
        }


def _empty_explanation() -> dict:
    return {"top_negative": [], "top_positive": [], "all_contributions": {}}
