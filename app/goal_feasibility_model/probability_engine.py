"""
ml_models/goal_feasibility_model/probability_engine.py
=======================================================
Goal Probability Engine — 10-Step Pipeline Orchestrator.

Architecture:
  Step 1  Fetch user + goal data from DB
  Step 2  Build 28-feature vector  (feature_builder)
  Step 3  Data sufficiency check   (< 30 txns OR < 2 months → heuristic mode)
  Step 4  Run ML prediction        (HistGBT or LogReg fallback)
  Step 5  Generate SHAP-style explanations  (explainer)
  Step 6  Map negative drivers to spending categories
  Step 7  Extract top impacting transactions  (transaction_attribution)
  Step 8  Run counterfactual simulations  (counterfactual)
  Step 9  Generate human-readable feasibility_note
  Step 10 Persist results:
           goals.feasibility_score
           goals.feasibility_note
           goals.health_tag
           ml_model_runs (audit log)

Health Tag Logic (Rule + ML Hybrid):
  feasibility_ratio = safe_surplus / monthly_required
  ≥ 1.50  →  On Track
  1.00–1.49 → Tight
  < 1.00  →  Behind
  < 0.70 + high_volatility → At Risk

Low-Data Heuristic:
  ratio = safe_surplus / monthly_required
  prob  = clamp(0.15 + 0.55 × ratio, 0.05, 0.95)
  Returns with data_sufficiency = "limited" + note header "Estimated …"

Structured API Response:
  {
    "goal_id":                  int,
    "goal_name":                str,
    "probability":              float,       # 0.0 – 1.0
    "probability_pct":          str,         # "78%"
    "health_tag":               str,         # On Track / Tight / Behind / At Risk
    "feasibility_note":         str,         # human-readable summary
    "top_negative_drivers":     list[dict],
    "top_positive_drivers":     list[dict],
    "top_impact_transactions":  list[dict],
    "category_impact_summary":  dict,
    "counterfactuals":          list[dict],
    "feature_snapshot":         dict,        # key metrics only (not all 28)
    "model_source":             str,
    "data_sufficiency":         str,         # "full" | "limited"
    "model_version":            str,
  }
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ml_models.goal_feasibility_model.feature_builder import build_feature_vector, FEATURE_NAMES
from ml_models.goal_feasibility_model.model import GoalProbabilityModel
from ml_models.goal_feasibility_model.explainer import LocalExplainer
from ml_models.goal_feasibility_model.transaction_attribution import attribute_transactions
from ml_models.goal_feasibility_model.counterfactual import simulate_counterfactuals

# ── Lazy model singleton ──────────────────────────────────────────────────────
_model: Optional[GoalProbabilityModel] = None


def _get_model() -> GoalProbabilityModel:
    global _model
    if _model is None:
        _model = GoalProbabilityModel()
        if _model.is_trained():
            _model.load()
        else:
            print("⚙️  Training goal probability model on first run …")
            _model.train(verbose=False)
    return _model


# ── Health tag helper ─────────────────────────────────────────────────────────
def _health_tag(feasibility_ratio: float, exp_vol_ratio: float) -> str:
    if feasibility_ratio >= 1.50:
        return "On Track"
    if feasibility_ratio >= 1.00:
        return "Tight"
    if feasibility_ratio < 0.70 and exp_vol_ratio > 0.40:
        return "At Risk"
    return "Behind"


# ── Heuristic probability (low-data fallback) ─────────────────────────────────
def _heuristic_probability(safe_surplus: float, monthly_required: float) -> float:
    ratio = safe_surplus / max(monthly_required, 1.0)
    return float(max(0.05, min(0.95, 0.15 + 0.55 * ratio)))


# ── Feasibility note generator ────────────────────────────────────────────────
def _build_note(
    goal_name: str,
    deadline: Optional[date],
    probability: float,
    health_tag: str,
    negative_drivers: list[dict],
    positive_drivers: list[dict],
    data_sufficiency: str,
) -> str:
    pct      = f"{probability * 100:.0f}%"
    dl_str   = deadline.strftime("%b %Y") if deadline else "your deadline"
    header   = f"Estimated " if data_sufficiency == "limited" else ""
    note     = f"{header}{pct} chance to achieve '{goal_name}' by {dl_str}  [{health_tag}]\n\n"

    if positive_drivers:
        note += "✅ What's working:\n"
        for d in positive_drivers:
            note += f"  • {d['human_label']}\n"
        note += "\n"

    if negative_drivers:
        note += "⚠️  What's hurting your goal:\n"
        for d in negative_drivers:
            note += f"  • {d['human_label']}\n"
        note += "\n"

    if data_sufficiency == "limited":
        note += "ℹ️  Based on limited transaction history. "
        note += "Accuracy will improve after 2+ months of activity.\n"

    return note.strip()


# ── Main Engine ───────────────────────────────────────────────────────────────
class GoalProbabilityEngine:
    """
    Stateless pipeline engine.
    Create once (or use the module-level singleton); call run() per goal.
    """

    def run(self, db: Session, user_id: int, goal_id: int) -> dict:
        """
        Execute the full 10-step pipeline for one user × goal.
        Updates goals.feasibility_score, goals.feasibility_note, goals.health_tag.
        Logs to ml_model_runs.
        """
        from sqlalchemy import func as F
        from app.models import Transaction
        from app.models.goal import Goal
        from app.models.ml_model_run import MLModelRun
        from app.models.enums import TxnType

        t_start = time.monotonic()

        # ── Step 1: Fetch goal ────────────────────────────────────────────────
        goal = db.query(Goal).filter(
            Goal.goal_id == goal_id, Goal.user_id == user_id
        ).first()
        if not goal:
            return {"error": f"Goal {goal_id} not found for user {user_id}"}

        # ── Step 3: Data sufficiency check ───────────────────────────────────
        now       = datetime.utcnow()
        c2m       = now - timedelta(days=60)
        txn_count = int(
            db.query(F.count(Transaction.txn_id))
            .filter(Transaction.user_id == user_id,
                    Transaction.txn_type == TxnType.DEBIT)
            .scalar() or 0
        )
        months_of_data = 0
        if txn_count > 0:
            oldest = (
                db.query(F.min(Transaction.txn_timestamp))
                .filter(Transaction.user_id == user_id)
                .scalar()
            )
            if oldest:
                months_of_data = (now - oldest).days / 30.44

        low_data = txn_count < 30 or months_of_data < 2
        data_sufficiency = "limited" if low_data else "full"

        # ── Step 2: Build feature vector ─────────────────────────────────────
        feat = build_feature_vector(db, user_id, goal)

        # ── Step 4: ML prediction or heuristic ───────────────────────────────
        if low_data:
            probability  = _heuristic_probability(
                feat["safe_surplus"], feat["monthly_required"]
            )
            model_source = "heuristic"
            explanation  = {"top_negative": [], "top_positive": [], "all_contributions": {}}
        else:
            model        = _get_model()
            probability, model_source = model.predict_proba(feat)

            # ── Step 5: SHAP-style explanations ──────────────────────────────
            explainer   = LocalExplainer(model)
            explanation = explainer.explain(feat, probability)

        # ── Health tag (rule-based, always computed) ──────────────────────────
        health = _health_tag(feat["feasibility_ratio"], feat["expense_volatility_ratio"])

        # ── Step 6+7: Transaction attribution ────────────────────────────────
        attribution = attribute_transactions(
            db, user_id,
            explanation.get("top_negative", []),
            feat,
            top_n=5,
        )

        # ── Step 8: Counterfactual simulations ────────────────────────────────
        if not low_data:
            counterfactuals = simulate_counterfactuals(
                _get_model(), feat, probability
            )
        else:
            # Lightweight heuristic counterfactuals
            counterfactuals = _heuristic_counterfactuals(feat, probability)

        # ── Step 9: Feasibility note ──────────────────────────────────────────
        note = _build_note(
            goal.goal_name,
            goal.deadline,
            probability,
            health,
            explanation.get("top_negative", []),
            explanation.get("top_positive", []),
            data_sufficiency,
        )

        # ── Step 10: Persist ──────────────────────────────────────────────────
        goal.feasibility_score = probability
        goal.feasibility_note  = note
        goal.health_tag        = health

        latency_ms = int((time.monotonic() - t_start) * 1000)

        db.add(MLModelRun(
            model_name      = "goal_probability_engine",
            model_version   = GoalProbabilityModel.VERSION,
            input_text      = f"goal_id={goal_id} user_id={user_id}",
            output_category = health,
            confidence      = probability,
            top5_categories = {
                "health_tag":        health,
                "data_sufficiency":  data_sufficiency,
                "model_source":      model_source,
                "feasibility_ratio": round(feat["feasibility_ratio"], 4),
            },
            latency_ms = latency_ms,
        ))
        db.commit()

        # ── Compose response ──────────────────────────────────────────────────
        return {
            "goal_id":           goal_id,
            "goal_name":         goal.goal_name,
            "goal_type":         goal.goal_type,
            "target_amount":     goal.target_amount,
            "current_amount":    goal.current_amount,
            "progress_pct":      round(goal.progress_pct, 2),
            "deadline":          str(goal.deadline) if goal.deadline else None,
            "probability":       probability,
            "probability_pct":   f"{probability * 100:.0f}%",
            "health_tag":        health,
            "feasibility_note":  note,
            "top_negative_drivers":    explanation.get("top_negative", []),
            "top_positive_drivers":    explanation.get("top_positive", []),
            "top_impact_transactions": attribution["top_impact_transactions"],
            "category_impact_summary": attribution["category_impact_summary"],
            "counterfactuals":         counterfactuals,
            "feature_snapshot": _key_metrics(feat),
            "model_source":      model_source,
            "data_sufficiency":  data_sufficiency,
            "model_version":     GoalProbabilityModel.VERSION,
            "latency_ms":        latency_ms,
        }

    def run_bulk(self, db: Session, user_id: int) -> list[dict]:
        """Assess all active goals for a user."""
        from app.models.goal import Goal
        from app.models.enums import GoalStatus
        goals = (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE)
            .all()
        )
        results = []
        for g in goals:
            try:
                results.append(self.run(db, user_id, g.goal_id))
            except Exception as exc:
                results.append({"goal_id": g.goal_id, "error": str(exc)})
        return results


# ── Helpers ───────────────────────────────────────────────────────────────────
def _key_metrics(feat: dict) -> dict:
    """Return a compact snapshot of the most decision-relevant features."""
    return {
        "monthly_income":        round(feat.get("monthly_income", 0), 2),
        "avg_monthly_surplus":   round(feat.get("avg_monthly_surplus", 0), 2),
        "safe_surplus":          round(feat.get("safe_surplus", 0), 2),
        "monthly_required":      round(feat.get("monthly_required", 0), 2),
        "feasibility_ratio":     round(feat.get("feasibility_ratio", 0), 3),
        "months_left":           round(feat.get("months_left", 0), 1),
        "discretionary_ratio":   round(feat.get("discretionary_ratio", 0), 3),
        "expense_volatility_ratio": round(feat.get("expense_volatility_ratio", 0), 3),
        "contribution_streak":   int(feat.get("contribution_streak", 0)),
        "missed_saving_months":  int(feat.get("missed_saving_months", 0)),
        "health_score":          round(feat.get("health_score", 0.5), 3),
        "behavioral_consistency": round(feat.get("behavioral_consistency", 0.5), 3),
    }


def _heuristic_counterfactuals(feat: dict, base_prob: float) -> list[dict]:
    """Simple rule-based counterfactuals when model isn't available."""
    results = []
    for reduction, cat in [(0.20, "Food & Dining"), (0.15, "Shopping")]:
        avg_exp  = feat.get("avg_monthly_expenses", 1)
        disc_cat = avg_exp * feat.get("discretionary_ratio", 0.25) / 3
        gain     = disc_cat * reduction
        new_surplus  = feat.get("safe_surplus", 0) + gain
        new_req      = feat.get("monthly_required", 1)
        new_ratio    = new_surplus / max(new_req, 1)
        new_prob     = _heuristic_probability(new_surplus, new_req)
        results.append({
            "scenario":              f"Reduce {cat} by {int(reduction*100)}%",
            "new_probability":       round(new_prob, 4),
            "prob_delta":            round(new_prob - base_prob, 4),
            "new_feasibility_ratio": round(new_ratio, 3),
            "months_earlier":        0.0,
            "monthly_savings_gain":  round(gain, 2),
            "actionable_tip":        f"Save ₹{gain:,.0f}/month by reducing {cat} spending",
        })
    return [r for r in results if r["prob_delta"] > 0]


# Module-level singleton for direct import
goal_probability_engine = GoalProbabilityEngine()
