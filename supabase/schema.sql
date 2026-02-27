-- ============================================
-- PERSONAL FINANCE PLATFORM - DATABASE SCHEMA
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CORE USER & AUTH
-- ============================================

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    auth_uid UUID UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone BIGINT UNIQUE,
    monthly_income NUMERIC(15,2),
    income_type VARCHAR(50),
    risk_profile VARCHAR(50),
    kyc_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_auth_uid ON users(auth_uid);
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- ACCOUNTS & CURRENCIES
-- ============================================

CREATE TABLE currencies (
    currency_id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    institution_name VARCHAR(255),
    account_type VARCHAR(50),
    current_balance NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_accounts_user_id ON accounts(user_id);

-- ============================================
-- MERCHANTS & CATEGORIES
-- ============================================

CREATE TABLE merchants (
    merchant_id SERIAL PRIMARY KEY,
    raw_name TEXT NOT NULL,
    clean_name VARCHAR(255),
    default_category VARCHAR(100),
    txn_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_merchants_clean_name ON merchants(clean_name);

CREATE TABLE fund_categories (
    fund_category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TRANSACTIONS
-- ============================================

CREATE TABLE transactions (
    txn_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    account_id INT REFERENCES accounts(account_id) ON DELETE SET NULL,
    merchant_id INT REFERENCES merchants(merchant_id) ON DELETE SET NULL,
    amount NUMERIC(15,2) NOT NULL,
    txn_type VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    raw_description TEXT,
    clean_description TEXT,
    payment_mode VARCHAR(50),
    user_verified BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC(5,4),
    balance_after_txn NUMERIC(15,2),
    txn_timestamp TIMESTAMPTZ NOT NULL,
    cat_method VARCHAR(50),
    source_type VARCHAR(50),
    is_anomalous BOOLEAN DEFAULT FALSE,
    anomaly_score NUMERIC(5,4),
    user_verified_category BOOLEAN DEFAULT FALSE,
    location VARCHAR(255),
    recurring_group_id VARCHAR(100),
    ml_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_timestamp ON transactions(txn_timestamp);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_merchant_id ON transactions(merchant_id);
CREATE INDEX idx_transactions_is_anomalous ON transactions(is_anomalous);

-- ============================================
-- TRANSACTION PATTERNS & MAPPINGS
-- ============================================

CREATE TABLE transaction_patterns (
    pattern_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    avg_amount NUMERIC(15,2),
    std_amount NUMERIC(15,2),
    typical_weekdays JSONB,
    typical_merchant_ids JSONB,
    txn_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_user_category ON transaction_patterns(user_id, category);

CREATE TABLE category_mappings (
    mapping_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    merchant_id INT NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    confidence NUMERIC(5,4),
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, merchant_id)
);

CREATE INDEX idx_mappings_user_merchant ON category_mappings(user_id, merchant_id);

-- ============================================
-- BUDGETS & PROFILES
-- ============================================

CREATE TABLE budget_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    needs_ratio NUMERIC(5,4) DEFAULT 0.50,
    wants_ratio NUMERIC(5,4) DEFAULT 0.30,
    savings_ratio NUMERIC(5,4) DEFAULT 0.20,
    baseline_expense NUMERIC(15,2),
    expense_volatility NUMERIC(15,2),
    avg_monthly_surplus NUMERIC(15,2),
    safe_investable_amount NUMERIC(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE budgets (
    budget_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    limit_amount NUMERIC(15,2) NOT NULL,
    spent_amount NUMERIC(15,2) DEFAULT 0,
    period VARCHAR(20) DEFAULT 'monthly',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_budgets_user_id ON budgets(user_id);
CREATE INDEX idx_budgets_active ON budgets(is_active);

-- ============================================
-- GOALS & SAVINGS
-- ============================================

CREATE TABLE goals (
    goal_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_name VARCHAR(255) NOT NULL,
    target_amount NUMERIC(15,2) NOT NULL,
    current_amount NUMERIC(15,2) DEFAULT 0,
    deadline DATE,
    status VARCHAR(50) DEFAULT 'active',
    feasibility_score NUMERIC(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_goals_user_id ON goals(user_id);
CREATE INDEX idx_goals_status ON goals(status);

CREATE TABLE savings_pots (
    pot_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_id INT REFERENCES goals(goal_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    target_amount NUMERIC(15,2),
    current_amount NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_savings_pots_user_id ON savings_pots(user_id);

-- ============================================
-- FINANCIAL HEALTH & RATINGS
-- ============================================

CREATE TABLE financial_health_ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    score NUMERIC(5,2) NOT NULL,
    rating_label VARCHAR(50),
    prev_rating_id INT REFERENCES financial_health_ratings(rating_id) ON DELETE SET NULL,
    rating_delta NUMERIC(5,2),
    improvement_tips JSONB,
    window_months INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ratings_user_id ON financial_health_ratings(user_id);
CREATE INDEX idx_ratings_created_at ON financial_health_ratings(created_at);

-- ============================================
-- MUTUAL FUNDS & INVESTMENTS
-- ============================================

CREATE TABLE mf_instruments (
    instrument_id SERIAL PRIMARY KEY,
    fund_category_id INT REFERENCES fund_categories(fund_category_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    isin VARCHAR(20) UNIQUE,
    risk_level VARCHAR(50),
    cagr_1y NUMERIC(5,2),
    cagr_3y NUMERIC(5,2),
    cagr_5y NUMERIC(5,2),
    sip_minimum INT,
    nav NUMERIC(10,4),
    nav_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_instruments_isin ON mf_instruments(isin);
CREATE INDEX idx_instruments_risk_level ON mf_instruments(risk_level);

CREATE TABLE mf_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    instrument_id INT NOT NULL REFERENCES mf_instruments(instrument_id) ON DELETE CASCADE,
    rating_id INT REFERENCES financial_health_ratings(rating_id) ON DELETE SET NULL,
    expected_cagr_low NUMERIC(5,2),
    expected_cagr_high NUMERIC(5,2),
    reason TEXT,
    hard_gates_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recommendations_user_id ON mf_recommendations(user_id);

CREATE TABLE mf_watchlist (
    watchlist_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    instrument_id INT NOT NULL REFERENCES mf_instruments(instrument_id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, instrument_id)
);

CREATE INDEX idx_watchlist_user_id ON mf_watchlist(user_id);

-- ============================================
-- ALERTS & NOTIFICATIONS
-- ============================================

CREATE TABLE alerts (
    alert_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    txn_id INT REFERENCES transactions(txn_id) ON DELETE SET NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_created_at ON alerts(created_at);

CREATE TABLE notification_log (
    notification_id SERIAL PRIMARY KEY,
    alert_id INT REFERENCES alerts(alert_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notification_log(user_id);
CREATE INDEX idx_notifications_alert_id ON notification_log(alert_id);

-- ============================================
-- RECEIPTS & OCR
-- ============================================

CREATE TABLE receipts (
    receipt_id SERIAL PRIMARY KEY,
    txn_id INT UNIQUE NOT NULL REFERENCES transactions(txn_id) ON DELETE CASCADE,
    extracted_items JSONB,
    total_amount NUMERIC(15,2),
    amount_matched BOOLEAN DEFAULT FALSE,
    ocr_confidence NUMERIC(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_receipts_txn_id ON receipts(txn_id);

-- ============================================
-- ML & FEEDBACK
-- ============================================

CREATE TABLE ml_model_runs (
    run_id SERIAL PRIMARY KEY,
    txn_id INT REFERENCES transactions(txn_id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    input_text TEXT,
    output_category VARCHAR(100),
    confidence NUMERIC(5,4),
    top5_categories JSONB,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ml_runs_txn_id ON ml_model_runs(txn_id);
CREATE INDEX idx_ml_runs_model ON ml_model_runs(model_name, model_version);

CREATE TABLE user_feedback (
    feedback_id SERIAL PRIMARY KEY,
    txn_id INT NOT NULL REFERENCES transactions(txn_id) ON DELETE CASCADE,
    corrected_category VARCHAR(100),
    corrected_subcategory VARCHAR(100),
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_txn_id ON user_feedback(txn_id);

-- ============================================
-- AUDIT & COMPLIANCE
-- ============================================

CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    actor_id INT,
    actor_type VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INT,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_actor ON audit_logs(actor_id, actor_type);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transaction_patterns_updated_at BEFORE UPDATE ON transaction_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_category_mappings_updated_at BEFORE UPDATE ON category_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budget_profiles_updated_at BEFORE UPDATE ON budget_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budgets_updated_at BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_savings_pots_updated_at BEFORE UPDATE ON savings_pots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
