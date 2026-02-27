-- ============================================
-- QUICKSIGHT ANONYMIZED VIEWS
-- ============================================
-- These views provide aggregated, anonymized data for admin dashboards
-- NO PII (names, emails, phone numbers) is exposed

-- ============================================
-- 1. Transaction Analytics View
-- ============================================
CREATE OR REPLACE VIEW vw_transaction_analytics AS
SELECT 
    MD5(user_id::text) as user_hash,
    DATE_TRUNC('day', txn_timestamp) as txn_date,
    DATE_TRUNC('month', txn_timestamp) as txn_month,
    EXTRACT(HOUR FROM txn_timestamp) as txn_hour,
    EXTRACT(DOW FROM txn_timestamp) as day_of_week,
    txn_type,
    category,
    subcategory,
    payment_mode,
    COUNT(*) as transaction_count,
    AVG(amount) as avg_amount,
    SUM(amount) as total_amount,
    MIN(amount) as min_amount,
    MAX(amount) as max_amount,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN is_anomalous THEN 1 ELSE 0 END) as anomaly_count,
    SUM(CASE WHEN user_verified_category THEN 1 ELSE 0 END) as user_corrected_count
FROM transactions
WHERE txn_timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 
    MD5(user_id::text),
    DATE_TRUNC('day', txn_timestamp),
    DATE_TRUNC('month', txn_timestamp),
    EXTRACT(HOUR FROM txn_timestamp),
    EXTRACT(DOW FROM txn_timestamp),
    txn_type,
    category,
    subcategory,
    payment_mode;

-- ============================================
-- 2. User Financial Health (Anonymized)
-- ============================================
CREATE OR REPLACE VIEW vw_user_financial_health AS
SELECT 
    MD5(u.user_id::text) as user_hash,
    u.risk_profile,
    u.kyc_status,
    DATE_TRUNC('month', u.created_at) as cohort_month,
    bp.needs_ratio,
    bp.wants_ratio,
    bp.savings_ratio,
    bp.baseline_expense,
    bp.expense_volatility,
    bp.avg_monthly_surplus,
    bp.safe_investable_amount,
    COUNT(DISTINCT g.goal_id) as active_goals,
    AVG(g.feasibility_score) as avg_goal_feasibility,
    COUNT(DISTINCT b.budget_id) as active_budgets,
    AVG(b.spent_amount / NULLIF(b.limit_amount, 0)) as avg_budget_utilization
FROM users u
LEFT JOIN budget_profiles bp ON u.user_id = bp.user_id
LEFT JOIN goals g ON u.user_id = g.user_id AND g.status = 'active'
LEFT JOIN budgets b ON u.user_id = b.user_id AND b.is_active = true
GROUP BY 
    MD5(u.user_id::text),
    u.risk_profile,
    u.kyc_status,
    DATE_TRUNC('month', u.created_at),
    bp.needs_ratio,
    bp.wants_ratio,
    bp.savings_ratio,
    bp.baseline_expense,
    bp.expense_volatility,
    bp.avg_monthly_surplus,
    bp.safe_investable_amount;

-- ============================================
-- 3. ML Model Performance Metrics
-- ============================================
CREATE OR REPLACE VIEW vw_ml_model_performance AS
SELECT 
    DATE_TRUNC('day', created_at) as metric_date,
    model_name,
    model_version,
    COUNT(*) as total_predictions,
    AVG(confidence) as avg_confidence,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as median_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency_ms,
    SUM(CASE WHEN confidence >= 0.85 THEN 1 ELSE 0 END) as high_confidence_count,
    SUM(CASE WHEN confidence < 0.85 THEN 1 ELSE 0 END) as low_confidence_count
FROM ml_model_runs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    DATE_TRUNC('day', created_at),
    model_name,
    model_version;

-- ============================================
-- 4. Category Distribution
-- ============================================
CREATE OR REPLACE VIEW vw_category_distribution AS
SELECT 
    DATE_TRUNC('month', txn_timestamp) as month,
    category,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(confidence_score) as avg_confidence
FROM transactions
WHERE txn_timestamp >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY 
    DATE_TRUNC('month', txn_timestamp),
    category;

-- ============================================
-- 5. Anomaly Detection Metrics
-- ============================================
CREATE OR REPLACE VIEW vw_anomaly_metrics AS
SELECT 
    DATE_TRUNC('day', t.created_at) as detection_date,
    a.severity,
    a.alert_type,
    COUNT(DISTINCT t.txn_id) as anomaly_count,
    AVG(t.anomaly_score) as avg_anomaly_score,
    COUNT(DISTINCT a.alert_id) as alerts_generated,
    SUM(CASE WHEN a.status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
    AVG(EXTRACT(EPOCH FROM (a.resolved_at - a.created_at))/3600) as avg_resolution_hours
FROM transactions t
LEFT JOIN alerts a ON t.txn_id = a.txn_id
WHERE t.is_anomalous = true
  AND t.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    DATE_TRUNC('day', t.created_at),
    a.severity,
    a.alert_type;

-- ============================================
-- 6. Budget Performance
-- ============================================
CREATE OR REPLACE VIEW vw_budget_performance AS
SELECT 
    DATE_TRUNC('month', b.created_at) as budget_month,
    b.category,
    b.period,
    COUNT(DISTINCT b.user_id) as users_with_budget,
    AVG(b.limit_amount) as avg_limit,
    AVG(b.spent_amount) as avg_spent,
    AVG(b.spent_amount / NULLIF(b.limit_amount, 0)) as avg_utilization,
    SUM(CASE WHEN b.spent_amount > b.limit_amount THEN 1 ELSE 0 END) as over_budget_count,
    SUM(CASE WHEN b.spent_amount <= b.limit_amount * 0.8 THEN 1 ELSE 0 END) as under_budget_count
FROM budgets b
WHERE b.created_at >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY 
    DATE_TRUNC('month', b.created_at),
    b.category,
    b.period;

-- ============================================
-- 7. Goal Achievement Metrics
-- ============================================
CREATE OR REPLACE VIEW vw_goal_metrics AS
SELECT 
    DATE_TRUNC('month', g.created_at) as goal_month,
    g.status,
    COUNT(*) as goal_count,
    AVG(g.target_amount) as avg_target,
    AVG(g.current_amount) as avg_current,
    AVG(g.current_amount / NULLIF(g.target_amount, 0)) as avg_progress,
    AVG(g.feasibility_score) as avg_feasibility,
    AVG(EXTRACT(EPOCH FROM (g.deadline - g.created_at))/86400) as avg_duration_days,
    SUM(CASE WHEN g.status = 'completed' THEN 1 ELSE 0 END) as completed_count
FROM goals g
WHERE g.created_at >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY 
    DATE_TRUNC('month', g.created_at),
    g.status;

-- ============================================
-- 8. System Health Metrics
-- ============================================
CREATE OR REPLACE VIEW vw_system_metrics AS
SELECT 
    DATE_TRUNC('hour', created_at) as metric_hour,
    'transactions' as metric_type,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (created_at - txn_timestamp))) as avg_processing_delay_seconds
FROM transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)

UNION ALL

SELECT 
    DATE_TRUNC('hour', created_at) as metric_hour,
    'alerts' as metric_type,
    COUNT(*) as count,
    NULL as avg_processing_delay_seconds
FROM alerts
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)

UNION ALL

SELECT 
    DATE_TRUNC('hour', created_at) as metric_hour,
    'ml_predictions' as metric_type,
    COUNT(*) as count,
    AVG(latency_ms)/1000 as avg_processing_delay_seconds
FROM ml_model_runs
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at);

-- ============================================
-- 9. User Feedback Analysis
-- ============================================
CREATE OR REPLACE VIEW vw_user_feedback_analysis AS
SELECT 
    DATE_TRUNC('day', uf.created_at) as feedback_date,
    uf.corrected_category,
    t.category as original_category,
    COUNT(*) as correction_count,
    AVG(t.confidence_score) as avg_original_confidence
FROM user_feedback uf
JOIN transactions t ON uf.txn_id = t.txn_id
WHERE uf.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    DATE_TRUNC('day', uf.created_at),
    uf.corrected_category,
    t.category;

-- ============================================
-- 10. Investment Readiness Overview
-- ============================================
CREATE OR REPLACE VIEW vw_investment_readiness AS
SELECT 
    DATE_TRUNC('month', u.created_at) as cohort_month,
    u.risk_profile,
    COUNT(DISTINCT u.user_id) as total_users,
    COUNT(DISTINCT CASE WHEN bp.safe_investable_amount > 0 THEN u.user_id END) as investment_ready_users,
    AVG(bp.safe_investable_amount) as avg_investable_amount,
    COUNT(DISTINCT mw.user_id) as users_with_watchlist,
    COUNT(DISTINCT mr.user_id) as users_with_recommendations
FROM users u
LEFT JOIN budget_profiles bp ON u.user_id = bp.user_id
LEFT JOIN mf_watchlist mw ON u.user_id = mw.user_id
LEFT JOIN mf_recommendations mr ON u.user_id = mr.user_id
GROUP BY 
    DATE_TRUNC('month', u.created_at),
    u.risk_profile;

-- ============================================
-- Grant read-only access to QuickSight role
-- ============================================
-- Run this after creating QuickSight database user
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO quicksight_user;
-- GRANT SELECT ON vw_transaction_analytics TO quicksight_user;
-- GRANT SELECT ON vw_user_financial_health TO quicksight_user;
-- GRANT SELECT ON vw_ml_model_performance TO quicksight_user;
-- GRANT SELECT ON vw_category_distribution TO quicksight_user;
-- GRANT SELECT ON vw_anomaly_metrics TO quicksight_user;
-- GRANT SELECT ON vw_budget_performance TO quicksight_user;
-- GRANT SELECT ON vw_goal_metrics TO quicksight_user;
-- GRANT SELECT ON vw_system_metrics TO quicksight_user;
-- GRANT SELECT ON vw_user_feedback_analysis TO quicksight_user;
-- GRANT SELECT ON vw_investment_readiness TO quicksight_user;
