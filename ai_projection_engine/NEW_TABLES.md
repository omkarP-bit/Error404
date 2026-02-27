# New Database Tables — Adaptive Financial Projection Engine

> **Important:** This microservice is read-only with respect to all existing
> Morpheus tables (`users`, `transactions`, `accounts`, `goals`, etc.).
> The four tables documented below are **created only if they do not already exist**
> (`CREATE TABLE IF NOT EXISTS`) and are **completely additive** — no existing column,
> index, or row is ever modified or deleted by this service.

---

## Table 1: `forecast_snapshots`

**Purpose:** Caches the latest Monte Carlo forecast result per user per calendar month.
Avoids re-running 1 000 simulations on every API call.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER PK | ✗ | Auto-increment primary key |
| `user_id` | INTEGER | ✗ | FK reference (logical) to `users.user_id` |
| `month_year` | VARCHAR(7) | ✗ | Calendar month, e.g. `"2026-02"` |
| `computed_at` | DATETIME | ✗ | UTC timestamp of last computation |
| `band_lower_25` | FLOAT | ✓ | P25 projected month-end spend (₹) |
| `band_median_50` | FLOAT | ✓ | P50 projected month-end spend (₹) |
| `band_upper_90` | FLOAT | ✓ | P90 projected month-end spend (₹) |
| `balance_lower` | FLOAT | ✓ | P25 projected month-end account balance (₹) |
| `balance_median` | FLOAT | ✓ | P50 projected month-end account balance (₹) |
| `balance_upper` | FLOAT | ✓ | P90 projected month-end account balance (₹) |
| `depletion_risk_flag` | BOOLEAN | ✓ | `True` if projected balance < safety threshold |
| `depletion_risk_date` | VARCHAR(20) | ✓ | ISO date when balance may run out (if applicable) |
| `category_breakdown` | TEXT (JSON) | ✓ | Per-category P25/P50/P90 spend breakdown |

**Unique constraint:** `(user_id, month_year)` — one snapshot per user per month.

**Cache TTL:** Controlled by `FORECAST_CACHE_TTL_MINUTES` (default: 60 minutes).

---

## Table 2: `adaptive_budgets`

**Purpose:** Stores computed adaptive spending budgets per user, per category, per month.
The budget auto-adjusts to actual behaviour using the formula:

```
AdaptiveBudget = 0.50 × Median(last 3 months spend)
               + 0.30 × EMA(last 30 days spend)
               + 0.20 × Current month pace adjustment
```

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER PK | ✗ | Auto-increment primary key |
| `user_id` | INTEGER | ✗ | Logical FK to `users.user_id` |
| `category` | VARCHAR(100) | ✗ | Spending category name |
| `month_year` | VARCHAR(7) | ✗ | Calendar month, e.g. `"2026-02"` |
| `median_spend_3m` | FLOAT | ✓ | Median monthly spend over last 3 months (₹) |
| `ema_30d` | FLOAT | ✓ | Exponential moving average of last 30 days (₹) |
| `current_month_pace` | FLOAT | ✓ | Projected full-month spend at current pace (₹) |
| `adaptive_budget` | FLOAT | ✗ | Final computed adaptive budget for the category (₹) |
| `actual_spend_so_far` | FLOAT | ✓ | Actual spend in the current month so far (₹) |
| `created_at` | DATETIME | ✗ | Row creation timestamp |
| `updated_at` | DATETIME | ✗ | Last update timestamp |

**Unique constraint:** `(user_id, category, month_year)`.

**Update frequency:** On every `POST /recompute/{user_id}` call and nightly job.

---

## Table 3: `savings_opportunities`

**Purpose:** Stores counterfactual savings simulations for discretionary spending categories.
Pre-computed to ensure sub-2-second API response times.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER PK | ✗ | Auto-increment primary key |
| `user_id` | INTEGER | ✗ | Logical FK to `users.user_id` |
| `category` | VARCHAR(100) | ✗ | Spending category name |
| `month_year` | VARCHAR(7) | ✗ | Calendar month |
| `is_discretionary` | BOOLEAN | ✓ | Whether this is a discretionary category |
| `current_spend` | FLOAT | ✗ | Actual spend so far this month (₹) |
| `saving_5pct` | FLOAT | ✓ | ₹ saved at 5% reduction |
| `saving_10pct` | FLOAT | ✓ | ₹ saved at 10% reduction |
| `saving_15pct` | FLOAT | ✓ | ₹ saved at 15% reduction |
| `saving_20pct` | FLOAT | ✓ | ₹ saved at 20% reduction |
| `balance_impact_5pct` | FLOAT | ✓ | Projected balance improvement at 5% cut (₹) |
| `balance_impact_10pct` | FLOAT | ✓ | Projected balance improvement at 10% cut (₹) |
| `balance_impact_15pct` | FLOAT | ✓ | Projected balance improvement at 15% cut (₹) |
| `balance_impact_20pct` | FLOAT | ✓ | Projected balance improvement at 20% cut (₹) |
| `created_at` | DATETIME | ✗ | Row creation timestamp |

**Unique constraint:** `(user_id, category, month_year)`.

**Rules:**
- Fixed expense categories (Rent, EMI, Insurance, etc.) are **never** included.
- Reductions are capped at 25% (configurable via `MAX_REDUCTION_PCT`).

---

## Table 4: `behavior_profiles`

**Purpose:** Aggregated behavioural metrics per user. One row per user, overwritten on
every recompute. Drives the feature engineering pipeline and enables quick lookups
without re-scanning all transactions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER PK | ✗ | Auto-increment primary key |
| `user_id` | INTEGER | ✗ | Logical FK to `users.user_id` (UNIQUE) |
| `avg_daily_spend` | FLOAT | ✓ | Mean daily spend across all categories (₹) |
| `mid_month_burn_rate` | FLOAT | ✓ | Ratio of first-half vs second-half monthly spend |
| `spend_volatility` | FLOAT | ✓ | Std-dev of monthly totals (₹) |
| `discretionary_ratio` | FLOAT | ✓ | Fraction of spend on discretionary categories |
| `fixed_ratio` | FLOAT | ✓ | Fraction of spend on fixed expense categories |
| `weekend_spending_multiplier` | FLOAT | ✓ | Avg weekend spend ÷ avg weekday spend |
| `recurring_expense_count` | INTEGER | ✓ | Number of recurring transaction rows |
| `data_days_available` | INTEGER | ✓ | Total days of transaction history available |
| `computed_at` | DATETIME | ✗ | UTC timestamp of last computation |

**Unique constraint:** `user_id` — one profile row per user.

---

## Safety Guarantees

| Guarantee | How enforced |
|-----------|-------------|
| Existing tables never modified | `Base.metadata.create_all()` only creates **new** tables |
| No foreign-key constraints on existing tables | All cross-table references are logical (app-level) |
| Read-only access to core tables | All `SELECT` queries use SQLAlchemy `text()` with no `UPDATE`/`DELETE` |
| Additive-only schema changes | These 4 tables can be dropped at any time with no impact on the main app |
