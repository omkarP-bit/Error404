# 💰 FinAI — Personal Finance Manager with AI Insights

A modular, production-style prototype of a Personal Finance Manager with four integrated ML models, a FastAPI backend, and a Jinja2 web UI.

---

## ✨ Features

| Feature | Technology |
|---|---|
| Transaction Categorization | TF-IDF + LinearSVC + SentenceTransformer |
| Anomaly Detection | IsolationForest (scikit-learn) |
| Goal Feasibility Prediction | Ridge Regression |
| Investment Readiness Assessment | Logistic Regression + Rule Overrides |
| OCR Receipt Ingestion | pytesseract + Pillow |
| PDF Bank Statement Parsing | pdfplumber |
| Database ORM | SQLAlchemy 2.0 (SQLite WAL) |
| Migrations | Alembic 1.13 |
| Web Framework | FastAPI 0.109 + Jinja2 |

---

## 🗂️ Project Structure

```
e:\Morpheus\
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic-Settings config
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models/                  # ORM models (10 tables)
│   ├── routers/                 # FastAPI routers (5 domains)
│   ├── schemas/                 # Pydantic schemas
│   ├── services/                # Analytics engine, OCR, PDF
│   ├── templates/               # Jinja2 HTML templates
│   └── static/                  # CSS + JS assets
├── ml_models/
│   ├── categorization_model/    # TF-IDF + SVC pipeline
│   ├── anomaly_detection_model/ # IsolationForest pipeline
│   ├── goal_feasibility_model/  # Ridge Regression pipeline
│   └── investment_readiness_model/ # LogReg + Rules pipeline
├── data/
│   ├── generate_dataset.py      # CSV dataset generator (2200 rows)
│   └── seed_data.py             # DB seeder (10 users, 2200+ txns)
├── migrations/                  # Alembic migration scripts
├── requirements.txt
├── .env
└── alembic.ini
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Tesseract OCR** (optional, for receipt scanning):
> Download and install from https://github.com/UB-Mannheim/tesseract/wiki
> Then set `TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe` in `.env`

### 2. Generate Dataset

```bash
python data/generate_dataset.py
```

Generates `data/finance_ml_dataset.csv` with 2200 rows and 22 feature columns.

### 3. Seed Database

```bash
python data/seed_data.py
```

Populates the SQLite database with 10 users, 5 accounts/user, 20 merchants, 2200+ transactions, goals, budgets, and alerts.

### 4. Train ML Models

Each model can be trained independently:

```bash
python ml_models/categorization_model/model.py
python ml_models/anomaly_detection_model/model.py
python ml_models/goal_feasibility_model/model.py
python ml_models/investment_readiness_model/model.py
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

---

## 🌐 Routes

### Pages (Jinja2 UI)

| Route | Description |
|---|---|
| `GET /dashboard?user_id=1` | Main financial dashboard |
| `GET /categorization-test` | Categorization model test UI |
| `GET /anomaly-test` | Anomaly detection test UI |
| `GET /goal-test` | Goal feasibility test UI |
| `GET /investment-test` | Investment readiness test UI |

### API Endpoints

#### Categorization
| Method | Route | Description |
|---|---|---|
| `POST` | `/api/categorize` | Categorize a transaction (form data) |
| `POST` | `/api/categorize/confirm` | Submit user category feedback |
| `POST` | `/api/categorize/ocr` | Upload receipt image for OCR |
| `POST` | `/api/categorize/pdf` | Upload PDF bank statement |
| `POST` | `/api/retrain/categorize` | Retrain categorization model |

#### Anomaly Detection
| Method | Route | Description |
|---|---|---|
| `POST` | `/api/anomaly/single` | Check single transaction |
| `POST` | `/api/anomaly/scan` | Bulk scan all user transactions |
| `POST` | `/api/retrain/anomaly` | Retrain anomaly model |

#### Goal Feasibility
| Method | Route | Description |
|---|---|---|
| `POST` | `/api/goal/assess` | Assess single goal |
| `POST` | `/api/goal/assess-bulk` | Assess all goals for a user |
| `POST` | `/api/retrain/goal` | Retrain goal model |

#### Investment Readiness
| Method | Route | Description |
|---|---|---|
| `POST` | `/api/investment/assess` | Manual feature assessment |
| `POST` | `/api/investment/assess-user` | Auto-compute from user DB profile |
| `POST` | `/api/retrain/investment` | Retrain investment model |

#### Transactions
| Method | Route | Description |
|---|---|---|
| `GET` | `/api/transactions/` | List transactions (filterable) |
| `POST` | `/api/transactions/` | Ingest a new transaction |
| `GET` | `/api/transactions/{txn_id}` | Get transaction detail |
| `POST` | `/api/transactions/confirm-category` | Confirm/correct a category |

---

## 🧠 ML Models

### 1. Categorization Model (`ml_models/categorization_model/`)

**Pipeline** (4-step waterfall):
1. User-specific mapping override
2. Merchant name cache lookup
3. TF-IDF (3000 features, 1-2 ngrams) + CalibratedLinearSVC
4. SentenceTransformer (`all-MiniLM-L6-v2`) semantic fallback

**Confidence threshold**: 0.85 (below this, `needs_confirmation=True` is returned and user is prompted to confirm)

### 2. Anomaly Detection Model (`ml_models/anomaly_detection_model/`)

**Algorithm**: IsolationForest (`n_estimators=200`, `contamination=0.05`)

**Features**: `amount`, `amount_z_score`, `daily_txn_freq`, `category_variance`, `is_odd_hour`, `avg_spend_per_category`, `spend_std_dev`, `expense_volatility`

**Severity thresholds**:
- 🔴 Critical: score < -0.15
- 🟠 High: score < -0.08
- 🟡 Medium: score < -0.03
- 🟢 Low: otherwise

### 3. Goal Feasibility Model (`ml_models/goal_feasibility_model/`)

**Algorithm**: Ridge Regression (`alpha=1.0`)

**Features**: `monthly_surplus`, `expense_volatility`, `target_amount`, `deadline_months`, + engineered: `months_to_target`, `buffer_ratio`, `volatility_ratio`, `log_target`

**Output**: Feasibility score 0–100, with 5-tier interpretation text

### 4. Investment Readiness Model (`ml_models/investment_readiness_model/`)

**Algorithm**: Multinomial Logistic Regression + hard rule override layer

**Features**: `savings_ratio`, `surplus_consistency`, `emergency_fund_coverage`, `income_stability`, `risk_profile_encoded`

**Rule overrides**:
- EF coverage < 0.5 → override to "Not Ready"
- Savings ratio < 5% → override to "Not Ready"
- Savings ≥ 30% + EF ≥ 2 + stability ≥ 0.7 → override to "Ready"

---

## 🗄️ Database Schema (10 Tables)

| Table | Description |
|---|---|
| `users` | User profile, financial data, KYC status, risk profile |
| `accounts` | Bank/investment accounts (linked to users) |
| `merchants` | Merchant registry with default categories |
| `transactions` | Core transaction table (6 indexes) |
| `user_feedback` | User category corrections (1 per transaction) |
| `category_mappings` | User-specific merchant→category overrides |
| `alerts` | Anomaly and system alerts with severity |
| `audit_logs` | All changes with old/new JSON values |
| `goals` | Financial goals with progress tracking |
| `budgets` | Budget limits with utilisation tracking |

---

## ⚙️ Configuration (`.env`)

```env
DATABASE_URL=sqlite:///./data/finance.db
CONFIDENCE_THRESHOLD=0.85
TESSERACT_CMD=tesseract
SECRET_KEY=your-secret-key-here
```

---

## 📊 Dataset (`data/finance_ml_dataset.csv`)

2200 rows × 22 columns:

`user_id`, `account_id`, `merchant_name`, `raw_description`, `amount`, `txn_type`, `payment_mode`, `category`, `subcategory`, `timestamp`, `balance_after_txn`, `is_recurring`, `confidence_score`, `rolling_3m_avg`, `rolling_3m_std`, `amount_z_score`, `monthly_income`, `monthly_expense`, `monthly_surplus`, `expense_volatility`, `avg_spend_per_category`, `user_corrected_label`

---

## 📦 Requirements

Key packages (see `requirements.txt` for full list):

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
alembic>=1.13.1
pydantic-settings>=2.1.0
scikit-learn>=1.4.0
sentence-transformers>=2.3.1
pytesseract>=0.3.10
pdfplumber>=0.10.3
Pillow>=10.2.0
python-multipart>=0.0.9
jinja2>=3.1.3
```

---

## 🧪 Running Model Tests

```bash
python ml_models/categorization_model/test_ui.py
python ml_models/anomaly_detection_model/test_ui.py
python ml_models/goal_feasibility_model/test_ui.py
python ml_models/investment_readiness_model/test_ui.py
```

---

## 📝 Notes

- Models are **lazy-loaded** on first inference and cached in memory
- All ML artifacts are saved to `ml_models/*/artifacts/` as `.pkl` files
- SentenceTransformer is loaded only when TF-IDF confidence < 0.85 (lazy)
- The database is auto-created on startup via `Base.metadata.create_all()`
- Seeder is **idempotent** — safe to run multiple times
- Alembic migrations are configured but the app also supports direct `create_all`

---

*Built with FastAPI · SQLAlchemy · scikit-learn · Jinja2*
