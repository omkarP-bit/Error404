# Adaptive Financial Projection & Savings Insight Engine

> **Standalone microservice** — runs on its own server, reads the existing
> Morpheus `finance.db`, and exposes REST APIs consumed by a Flutter mobile app.
> Zero changes to any existing table or module.

---

## Architecture Overview

```
ai_projection_engine/
│
├── server/                      ← FastAPI application
│   ├── main.py                  ← App entry point (port 8001)
│   ├── core/
│   │   ├── config.py            ← Pydantic-settings (env vars / .env)
│   │   ├── database.py          ← Engine, new table ORM models, init
│   │   └── constants.py         ← Category lists, formula weights
│   ├── utils/
│   │   ├── feature_engineering.py  ← Raw feature computation from transactions
│   │   ├── anomaly_filter.py       ← IQR outlier detection & down-weighting
│   │   └── simulation_utils.py     ← Gamma distribution fit + Monte Carlo
│   ├── services/
│   │   ├── adaptive_budgeting_service.py     ← Budget formula + DB upsert
│   │   ├── probabilistic_forecast_service.py ← Monte Carlo engine + heuristic fallback
│   │   ├── confidence_band_service.py        ← P25/P50/P90 caching layer
│   │   ├── savings_opportunity_service.py    ← Counterfactual savings + goal impact
│   │   └── llm_insight_service.py            ← Context assembly + Mistral call
│   └── routes/
│       ├── forecast_routes.py   ← GET /forecast/{user_id}
│       ├── savings_routes.py    ← GET /savings-opportunities/{user_id}
│       └── insights_routes.py   ← GET /insights/{user_id}
│
├── llm/
│   ├── mistral_client.py        ← Cloud API + Ollama + template fallback
│   └── prompt_templates.py      ← ₹-only, jargon-free prompts
│
├── jobs/
│   └── nightly_recompute.py     ← Batch job for all users (cron / Task Scheduler)
│
├── models/
│   └── scalers/                 ← Reserved for future scaler persistence
│
├── requirements.txt
├── Dockerfile
├── NEW_TABLES.md                ← Documents all new DB tables
└── README.md                    ← This file
```

---

## Quick Start (Local Development)

### 1. Create a dedicated virtual environment

```bash
cd ai_projection_engine
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

Create `ai_projection_engine/.env`:

```env
# Database — defaults to main project's finance.db (relative path auto-resolved)
DATABASE_URL=sqlite:///E:/Morpheus/data/finance.db

# Mistral Cloud API (leave blank to use template fallback)
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest

# OR use local Ollama
MISTRAL_USE_LOCAL=True
MISTRAL_LOCAL_URL=http://localhost:11434
MISTRAL_LOCAL_MODEL=mistral

# Performance tuning
FORECAST_CACHE_TTL_MINUTES=60
MC_SIMULATIONS=1000
```

### 4. Start the server

```bash
# From ai_projection_engine/ directory
python -m uvicorn server.main:app --host 0.0.0.0 --port 8001 --reload
```

Or use the built-in entrypoint:

```bash
python server/main.py
```

**Server starts at:** `http://localhost:8001`
**Swagger UI:** `http://localhost:8001/docs`
**ReDoc:** `http://localhost:8001/redoc`

---

## API Reference

### `GET /forecast/{user_id}`
Returns cached (TTL-based) Monte Carlo forecast with P25 / P50 / P90 confidence bands.

```json
{
  "status": "success",
  "data": {
    "user_id": 1,
    "month_year": "2026-02",
    "from_cache": true,
    "projected_month_spend": {
      "lower_p25": 18500.0,
      "median_p50": 22300.0,
      "upper_p90": 28100.0
    },
    "projected_balance_at_month_end": {
      "lower": 4200.0,
      "median": 8100.0,
      "upper": 14000.0
    },
    "depletion_risk_flag": false,
    "depletion_risk_date": null,
    "category_breakdown": {
      "Dining": { "spent_so_far": 3200.0, "projected_p25": 4100.0, "projected_p50": 5200.0, "projected_p90": 7100.0 }
    }
  }
}
```

---

### `GET /forecast/{user_id}/fresh`
Force-recomputes without using cache. Use after bulk transaction imports.

---

### `GET /forecast/{user_id}/adaptive-budgets`
Returns per-category adaptive budgets for the current month.

```json
{
  "data": [
    {
      "category": "Dining",
      "adaptive_budget": 5200.0,
      "actual_spend_so_far": 3200.0,
      "budget_remaining": 2000.0,
      "is_over_budget": false,
      "is_discretionary": true
    }
  ]
}
```

---

### `GET /savings-opportunities/{user_id}`
Returns counterfactual ₹ savings simulations + goal impact.

```json
{
  "data": {
    "opportunities": [
      {
        "category": "Dining",
        "current_spend_this_month": 3200.0,
        "best_scenario": {
          "reduction_pct": 10.0,
          "amount_saved": 320.0,
          "balance_improvement": 320.0
        },
        "insight": "If Dining reduced by ₹320, month-end balance improves by ₹320"
      }
    ],
    "goal_impact": {
      "goal_feasibility_flag": true,
      "total_monthly_goal_requirement": 8000.0,
      "achievable_savings_this_month": 9400.0,
      "shortfall_for_goals": 0.0
    }
  }
}
```

---

### `GET /insights/{user_id}`
Returns 3-4 sentence Mistral LLM insight in plain English using only ₹ amounts.

```json
{
  "data": {
    "insight": "You spent around ₹4,200 more than your usual pattern, mainly on dining and shopping. If this continues, your balance may fall between ₹3,000 and ₹8,000 by month end. Reducing dining expenses by about ₹1,500 can help maintain your planned savings.",
    "supporting_data": {
      "top_spending_categories": ["Dining", "Shopping", "Travel"],
      "over_budget_categories": ["Dining"],
      "saving_potential": 1820.0,
      "depletion_risk": false
    }
  }
}
```

---

### `POST /recompute/{user_id}`
Invalidates snapshot cache and runs full recompute.
Call this after any transaction update in the main app.

---

### `GET /health`
Health check endpoint.

```json
{ "status": "ok", "service": "Adaptive Financial Projection & Savings Insight Engine", "version": "1.0.0" }
```

---

## Nightly Job

Run manually or via scheduler:

```bash
python jobs/nightly_recompute.py
```

**Windows Task Scheduler** — recommended schedule: `00:05` daily.

**Linux cron:**
```cron
5 0 * * * /path/to/ai_projection_engine/.venv/bin/python /path/to/ai_projection_engine/jobs/nightly_recompute.py >> /var/log/projection_nightly.log 2>&1
```

---

## Docker Deployment

```bash
# Build
docker build -t projection-engine:latest .

# Run (mount main DB volume)
docker run -d \
  -p 8001:8001 \
  -v E:/Morpheus/data:/data \
  -e DATABASE_URL=sqlite:////data/finance.db \
  -e MISTRAL_API_KEY=your_key \
  --name projection-engine \
  projection-engine:latest
```

---

## Engine Design Decisions

| Decision | Detail |
|----------|--------|
| **Monte Carlo distribution** | Gamma (right-skewed, non-negative) — better fit for spending than Normal |
| **Simulations** | 1 000 paths (configurable) for P25/P50/P90 stability |
| **Outlier handling** | IQR fencing with 2× multiplier; outliers down-weighted by 0.25× (not removed) |
| **Adaptive budget formula** | 50% median + 30% EMA + 20% pace — balances history and recency |
| **Heuristic fallback** | Active when < 30 days of data; uses 70% of income as spend proxy |
| **LLM rules** | Only ₹ amounts · no percentages · 3-4 sentences · plain language |
| **Cache TTL** | 60 minutes per month-year snapshot (configurable) |
| **Max savings suggestion** | 25% reduction cap — realistic for actual user behaviour |

---

## New Database Tables

See [NEW_TABLES.md](NEW_TABLES.md) for the complete schema of all 4 new tables:
`forecast_snapshots`, `adaptive_budgets`, `savings_opportunities`, `behavior_profiles`.

These tables are **additive only** and do not modify any existing Morpheus table.

---

## Integration with Main Morpheus App

The main app only needs to:

1. Call `POST /recompute/{user_id}` after saving new transactions.
2. Call `GET /forecast/{user_id}` to display confidence band charts.
3. Call `GET /insights/{user_id}` to display the LLM insight card.

No shared code, no shared imports, no internal coupling.
