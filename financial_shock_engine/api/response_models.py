"""
financial_shock_engine/api/response_models.py
=============================================
Pydantic response models for all API endpoints.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class ShockCapacityResponse(BaseModel):
    user_id:                int
    user_name:              str
    computed_at:            str
    elapsed_ms:             float

    shock_capacity:         float = Field(description="₹ amount safely absorbable this month")
    safe_shock_limit:       float = Field(description="₹ — 95% scenarios stay solvent")
    risk_threshold:         float = Field(description="₹ — 50% scenarios start breaking")
    failure_threshold:      float = Field(description="₹ — 10% scenarios fail")
    resilience_label:       str   = Field(description="Safe / Moderate / Fragile / Critical")
    resilience_score:       int   = Field(description="0–100 composite resilience score")
    depletion_risk:         bool

    current_balance:        float
    projected_end_balance:  float
    confidence_band_low:    float
    confidence_band_high:   float

    current_month_spend:    float
    projected_month_spend:  float
    monthly_income:         float
    monthly_surplus:        float
    burn_rate_daily:        float
    days_to_depletion:      float

    expense_volatility:     float
    top_categories:         list[str]
    discretionary_ratio:    float
    trend_slope:            float

    has_sufficient_data:    bool
    data_months:            int
    projection_method:      str
    simulation_count:       int


class GoalImpact(BaseModel):
    goal_id:               int
    goal_name:             str
    target:                float
    saved:                 float
    remaining:             float
    months_left:           int
    monthly_need:          float
    priority:              int
    impact_level:          str
    delay_in_months:       int
    reduced_contribution:  float
    contribution_gap:      float
    new_completion_date:   str
    suggestion:            Optional[str]


class ShockScenario(BaseModel):
    shock_amount:          float
    balance_after_shock:   float
    resilience_after:      str
    depletion_risk:        bool
    goal_impacts:          list[GoalImpact]
    total_delay_risk:      int


class GoalImpactResponse(BaseModel):
    user_id:         int
    computed_at:     str
    monthly_income:  float
    current_balance: float
    goals_count:     int
    shock_scenarios: list[ShockScenario]


class SavingsOpportunity(BaseModel):
    category:       str
    current_spend:  float
    baseline_spend: float
    save_amount:    float
    confidence:     str
    reason:         str
    insight:        str


class SavingsInsightResponse(BaseModel):
    user_id:                   int
    computed_at:               str
    total_monthly_saveable:    float
    opportunities:             list[SavingsOpportunity]
    top_risk_categories:       list[str]
    resilience_boost:          str
    current_balance:           float
    monthly_income:            float


class InsightResponse(BaseModel):
    user_id:         int
    computed_at:     str
    insight:         str
    insight_source:  str
    shock_summary:   dict[str, Any]
    savings_summary: dict[str, Any]


class HealthResponse(BaseModel):
    status:   str
    db_ok:    bool
    version:  str
    port:     int
