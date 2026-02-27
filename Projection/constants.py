"""
ai_projection_engine/server/core/constants.py
=============================================
Shared constants: category lists, formula weights, simulation thresholds.
Edit this file to tune engine behaviour without touching service logic.
"""

# ── Category Classification ────────────────────────────────────────────────────
# Categories treated as FIXED (never suggest reducing these).
FIXED_EXPENSE_CATEGORIES: frozenset = frozenset({
    # ── Standard names ──────────────────────────────────────────────────────
    "Rent",
    "Housing",
    "EMI",
    "Loan Repayment",
    "Insurance",
    "Utilities",
    "Electricity",
    "Internet",
    "Mobile Recharge",
    "Water",
    "Gas",
    "Subscriptions",
    "Education",
    "Medical",
    "Healthcare",
    "Tax",
    "Investment",
    "Savings",
    "SIP",
    "Mutual Fund",
    "Fixed Deposit",
    # ── Actual DB category names ─────────────────────────────────────────────
    "Investments",       # DB: 'Investments'
    "Finance",           # DB: 'Finance' (loans, banking fees)
    "Salary",            # income — exclude from budget analysis
})

# Categories treated as DISCRETIONARY (primary targets for savings).
DISCRETIONARY_EXPENSE_CATEGORIES: frozenset = frozenset({
    # ── Standard names ──────────────────────────────────────────────────────
    "Dining",
    "Food",
    "Restaurants",
    "Shopping",
    "Clothing",
    "Entertainment",
    "Travel",
    "Leisure",
    "Sports",
    "Personal Care",
    "Beauty",
    "Gifts",
    "Hobbies",
    "Electronics",
    "Accessories",
    "Alcohol",
    "Groceries",
    "Snacks",
    "Coffee",
    "Online Shopping",
    "Cab",
    "Transport",
    "Movies",
    "Gaming",
    "Pets",
    # ── Actual DB category names ─────────────────────────────────────────────
    "Food & Dining",     # DB: 'Food & Dining'
})

# ── Adaptive Budget Formula Weights ───────────────────────────────────────────
# AdaptiveBudget = 0.5 * Median(3m) + 0.3 * EMA(30d) + 0.2 * CurrentPaceAdj
ADAPTIVE_BUDGET_WEIGHTS: dict = {
    "median_3m": 0.50,
    "ema_30d": 0.30,
    "pace_adj": 0.20,
}

# ── EMA Smoothing Factor ──────────────────────────────────────────────────────
EMA_ALPHA: float = 0.3   # Higher = more weight on recent observations

# ── Confidence Band Percentiles ────────────────────────────────────────────────
BAND_LOWER_PCT: int = 25    # Optimistic scenario
BAND_MEDIAN_PCT: int = 50   # Central estimate
BAND_UPPER_PCT: int = 90    # Pessimistic scenario

# ── Savings Reduction Scenarios (%) ───────────────────────────────────────────
SAVINGS_REDUCTION_SCENARIOS: list = [5.0, 10.0, 15.0, 20.0]

# ── Depletion Risk Thresholds ─────────────────────────────────────────────────
DEPLETION_RISK_BALANCE_THRESHOLD: float = 2000.0  # Flag if projected balance < ₹2 000
DEPLETION_RISK_DAYS_AHEAD: int = 10              # Look this many days forward

# ── Safe Month-End Buffer ─────────────────────────────────────────────────────
SAFE_BUFFER_RATIO: float = 0.10   # Reserve 10% of income as minimum buffer

# ── Monte Carlo Distribution ──────────────────────────────────────────────────
MC_DISTRIBUTION: str = "gamma"   # "gamma" fits right-skewed spending better

# ── Minimum Spend for Savings Suggestions (₹) ─────────────────────────────────
MIN_CATEGORY_SPEND_FOR_SAVINGS: float = 100.0

# ── API Response Cache Key Template ───────────────────────────────────────────
FORECAST_CACHE_KEY_TPL: str = "forecast:{user_id}:{month_year}"
