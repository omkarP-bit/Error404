# Personal Finance Management System

An AI-powered, secure, and scalable Personal Finance Management platform designed to help users track spending, manage budgets, detect anomalies, plan financial goals, and determine investment readiness — all with enterprise-grade security.

This system combines:

* **Supabase (PostgreSQL + Authentication)**
* **AWS API Gateway**
* **AWS KMS (Encryption)**
* **Flutter (User Dashboard)**
* **AWS QuickSight (Admin Analytics)**
* A modular, asynchronous **Machine Learning architecture**

---

# 🚀 Vision

To build a secure, intelligent, and scalable financial intelligence ecosystem that:

* Automatically categorizes transactions
* Learns user financial behavior
* Detects anomalies in real time
* Forecasts cash flow
* Optimizes goal achievement
* Determines safe investment readiness
* Maintains strict financial-grade security

---

# 🏗️ System Architecture Overview

## Core Infrastructure

* **Database:** Supabase PostgreSQL
* **Authentication:** Supabase JWT-based Auth
* **API Layer:** AWS API Gateway
* **Encryption:** AWS KMS
* **Frontend:** Flutter (Mobile & Web)
* **Admin Analytics:** AWS QuickSight
* **ML Layer:** Asynchronous AI services

---

# 📁 Application Structure

```
client/
 └── flutter_app/
      ├── dashboard/
      ├── transactions/
      ├── goals/
      ├── alerts/
      └── auth/

backend/
 ├── api/
 │    ├── transaction_service/
 │    ├── budget_service/
 │    ├── alert_service/
 │    ├── goal_service/
 │    └── admin_api/
 │
 ├── ml/
 │    ├── categorization_model/
 │    ├── pattern_model/
 │    ├── anomaly_model/
 │    ├── forecasting_model/
 │    ├── goal_model/
 │    └── feasibility_model/
 │
 ├── ingestion/
 ├── feature_store/
 ├── rbac/
 └── utils/

infrastructure/
 ├── api_gateway/
 ├── kms/
 └── quicksight_embedding/
```

---

# 🔐 Security Architecture

Security is implemented end-to-end.

### Authentication & Authorization

* Supabase JWT authentication
* Role-Based Access Control (User / Staff / Admin)
* Row-Level Security (PostgreSQL)

### Data Protection

* AWS KMS encryption at rest
* TLS encryption in transit
* Strict access boundaries
* Zero-trust internal architecture
* Audit logging for sensitive actions

No raw financial data is exposed to analytics dashboards.

---

# 🧠 Machine Learning Architecture

The ML system is modular, asynchronous, and explainable.
All model outputs are stored — not computed live during user requests.

---

## 1️⃣ Transaction Categorization Model

Automatically classifies transactions using:

* Sentence Transformer (~120–200ms inference)
* Context validation (NER + amount + timing)
* Confidence scoring
* LLM fallback (low-confidence cases)
* User feedback loop for continuous improvement

### Output:

* Category
* Confidence score
* Short explanation

---

## 2️⃣ User Pattern Learning Model

Builds personalized financial baselines:

* Monthly averages
* Category distributions
* Frequency trends
* Expense volatility
* Seasonal patterns

Feeds downstream models.

---

## 3️⃣ Anomaly Detection Model

Detects suspicious activity using multi-factor scoring:

* Amount deviation (Z-score)
* Frequency anomaly
* Category violations
* Temporal irregularity

### Risk Levels:

* High → SMS + In-app alert
* Medium → In-app alert
* Low → Silent logging

---

## 4️⃣ Forecasting & Cash Flow Model

Predicts near-term financial state:

* Monthly expense forecasting
* Income stability detection
* Surplus calculation
* Budget deviation analysis

### Output:

* Expected month-end balance
* Confidence range
* Stability score

---

## 5️⃣ Goal Planning Model

Optimizes and dynamically adjusts financial goals.

Supports:

* Emergency funds
* Short-term goals (<2 years)
* Long-term goals (>2 years)

### Logic:

* Calculates safe allocation from surplus
* Applies constraint-based prioritization
* Recalculates monthly
* Adjusts based on volatility & obligations

### Output:

* Monthly allocation plan
* Time-to-goal estimate
* Goal confidence score

---

## 6️⃣ Financial Feasibility & Investment Readiness Model

Determines whether a user is financially ready to invest.

### Hard Gate Checks:

* Emergency fund ≥ 3–6 months
* Positive and stable surplus
* Low expense volatility
* No active high-risk anomalies
* Goals sufficiently funded

### If eligible:

* Calculates safe investable amount
* Determines time horizon
* Maps to instrument category (Debt / Hybrid / Equity)
* Applies 3-month stability filter

### Output:

* Readiness score (0–100)
* Investment eligibility
* Safe investment amount
* Explanation layer

This model ensures responsible automation.

---

# 🔄 Backend Flow

1. User request → AWS API Gateway
2. JWT validation (Supabase)
3. RBAC authorization
4. Transaction stored in PostgreSQL
5. Feature store updated
6. ML pipeline triggered asynchronously
7. Insights, alerts, and projections generated
8. Flutter dashboard updated
9. Aggregated metrics sent to AWS QuickSight

---

# 📱 User Dashboard (Flutter)

Provides:

* Unified financial overview
* Auto-categorized transactions
* Budget tracking
* Goal progress
* Forecast projections
* Anomaly alerts
* Editable category corrections
* Investment readiness status

Designed for clarity and explainability.

---

# 📊 Admin & Analytics Layer

## Admin Access

* Private Admin API
* RBAC-protected
* Aggregated & anonymized data only

## AWS QuickSight

Used for:

* Model performance metrics
* System health monitoring
* Spend trend analysis
* Operational analytics
* Log aggregation dashboards

Heavy analytics queries are offloaded to QuickSight.

---

# 🎯 Project Goals

### Primary Goals

* Intelligent automated categorization
* Secure financial data handling
* Real-time anomaly detection
* Financial forecasting
* Goal optimization
* Safe investment readiness scoring
* Scalable cloud-native architecture

### Secondary Goals

* Explainable AI outputs
* Cost-efficient infrastructure
* Low-latency inference
* Enterprise-grade monitoring
* Modular extensibility

---

# 📈 Feasibility Analysis

## Technical Feasibility

* Supabase provides managed PostgreSQL + authentication.
* AWS API Gateway ensures scalable request routing.
* KMS ensures encryption compliance.
* Asynchronous ML prevents compute bottlenecks.
* QuickSight offloads dashboard complexity.

All components are production-ready and cloud-native.

---

## Operational Feasibility

* Stateless services → Horizontal scaling
* Asynchronous AI → Compute control
* Embedded analytics → Reduced frontend complexity
* Modular ML → Maintainable & extensible system

---

## Cost Feasibility

* API Gateway minimizes idle server costs
* Supabase reduces database management overhead
* QuickSight avoids building custom BI infrastructure
* ML runs asynchronously to prevent unnecessary compute usage

---

# 🗄️ Data Layer

* Supabase PostgreSQL
* KMS-encrypted storage
* Feature store for derived metrics
* Row-level access enforcement
* Strict audit logging

---

# 🔮 Future Enhancements

* Continuous model retraining pipelines
* Reinforcement learning from user corrections
* Multi-bank integrations
* Advanced behavioral financial modeling
* Automated compliance monitoring
* Portfolio optimization module

---

# 🧩 Design Principles

* Security-first architecture
* Explainable AI decisions
* Modular backend services
* Asynchronous compute strategy
* Enterprise-grade observability
* Responsible financial automation

---

# 📜 License

Currently under internal development.
License will be defined before public release.

---

**Built with ❤️ by Team Error404**
