"""
ml_models/goal_feasibility_engine/allocation_optimizer.py
==========================================================
Priority-aware multi-goal allocation optimizer.

Distributes the user's total feasible saving capacity across all active
goals using priority weights and per-goal caps (no over-saving for a goal).

Priority weight mapping:
  Rank 1  →  1.00  (High priority)
  Rank 2  →  0.70  (Medium)
  Rank 3  →  0.40  (Low)
  Rank 4  →  0.25
  Rank 5+ →  0.15

Emergency fund override:
  Any goal with goal_type in EMERGENCY_TYPES receives weight 1.50, regardless
  of priority rank, until it is fully funded.

Returns: dict of {goal_id: allocation_fraction}
  where allocation_fraction = this_goal_allocation / max_feasible_saving
"""
from __future__ import annotations

PRIORITY_WEIGHTS: dict[int, float] = {
    1: 1.00,
    2: 0.70,
    3: 0.40,
    4: 0.25,
    5: 0.15,
}

EMERGENCY_TYPES = {
    "emergency", "emergency_fund", "emergency fund",
    "contingency", "rainy day", "rainy_day",
}


def allocate_goals(all_goals: list, max_feasible: float) -> dict:
    """
    Parameters
    ----------
    all_goals
        List of goal summary dicts from feature_builder.all_active_goals.
        Each dict must have: goal_id, priority, required_monthly, goal_type.
    max_feasible
        Total monthly saving capacity to distribute (from behavioral_constraint_model).

    Returns
    -------
    dict
        {goal_id: fraction_of_max_feasible}
        Fractions sum to <= 1.0.
    """
    if not all_goals or max_feasible <= 0:
        return {}

    # ── Build per-goal weights and caps ──────────────────────────────────────
    meta: dict[int, dict] = {}
    for g in all_goals:
        rank = max(min(int(g.get("priority", 2)), 5), 1)
        w    = PRIORITY_WEIGHTS.get(rank, 0.15)

        # Emergency fund override
        if g.get("goal_type", "").strip() in EMERGENCY_TYPES:
            w = 1.50

        req = float(g.get("required_monthly", 0.0))
        meta[g["goal_id"]] = {"weight": w, "req": req}

    total_weight = sum(v["weight"] for v in meta.values())
    if total_weight == 0:
        n = max(len(all_goals), 1)
        return {g["goal_id"]: 1.0 / n for g in all_goals}

    # ── First pass: proportional allocation, capped at required ──────────────
    allocations: dict[int, float] = {}
    for gid, m in meta.items():
        raw   = (m["weight"] / total_weight) * max_feasible
        capped = min(raw, m["req"]) if m["req"] > 0 else raw
        allocations[gid] = capped

    # ── Redistribute any surplus created by capping ───────────────────────────
    remainder = max_feasible - sum(allocations.values())

    if remainder > 1.0:
        under = [
            (gid, meta[gid]["weight"])
            for gid in allocations
            if meta[gid]["req"] == 0 or allocations[gid] < meta[gid]["req"]
        ]
        if under:
            uw_sum = sum(w for _, w in under)
            for gid, w in under:
                extra = (w / uw_sum) * remainder
                req   = meta[gid]["req"]
                if req > 0:
                    allocations[gid] = min(allocations[gid] + extra, req)
                else:
                    allocations[gid] += extra

    # ── Convert absolute amounts to fractions ─────────────────────────────────
    return {
        gid: alloc / max(max_feasible, 1.0)
        for gid, alloc in allocations.items()
    }
