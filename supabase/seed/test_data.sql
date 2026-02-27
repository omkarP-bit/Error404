-- Seed Data for Testing
-- This file contains sample data for development and testing

BEGIN;

-- Sample user
INSERT INTO users (auth_uid, name, email, phone, monthly_income, income_type, risk_profile, kyc_status)
VALUES 
('550e8400-e29b-41d4-a716-446655440000', 'Test User', 'test@example.com', 9876543210, 50000, 'salary', 'moderate', 'verified')
ON CONFLICT (email) DO NOTHING;

-- Get user_id
DO $$
DECLARE
    test_user_id INT;
BEGIN
    SELECT user_id INTO test_user_id FROM users WHERE email = 'test@example.com';

    -- Sample account
    INSERT INTO accounts (user_id, institution_name, account_type, current_balance)
    VALUES (test_user_id, 'HDFC Bank', 'savings', 25000);

    -- Sample budget profile
    INSERT INTO budget_profiles (user_id, needs_ratio, wants_ratio, savings_ratio, baseline_expense, avg_monthly_surplus, safe_investable_amount)
    VALUES (test_user_id, 0.50, 0.30, 0.20, 25000, 10000, 7000)
    ON CONFLICT (user_id) DO NOTHING;

    -- Sample budgets
    INSERT INTO budgets (user_id, category, limit_amount, spent_amount, period, is_active)
    VALUES 
    (test_user_id, 'Food & Dining', 8000, 3500, 'monthly', true),
    (test_user_id, 'Transportation', 3000, 1200, 'monthly', true),
    (test_user_id, 'Shopping', 5000, 2000, 'monthly', true);

    -- Sample goals
    INSERT INTO goals (user_id, goal_name, target_amount, current_amount, deadline, status, feasibility_score)
    VALUES 
    (test_user_id, 'Emergency Fund', 150000, 50000, '2024-12-31', 'active', 0.85),
    (test_user_id, 'Vacation', 50000, 10000, '2024-06-30', 'active', 0.75);

END $$;

-- Sample merchants
INSERT INTO merchants (raw_name, clean_name, default_category, txn_count)
VALUES 
('SWIGGY*ORDER', 'Swiggy', 'Food & Dining', 0),
('UBER*TRIP', 'Uber', 'Transportation', 0),
('AMAZON*IN', 'Amazon', 'Shopping', 0),
('NETFLIX.COM', 'Netflix', 'Entertainment', 0);

-- Sample mutual funds
INSERT INTO mf_instruments (fund_category_id, name, isin, risk_level, cagr_3y, sip_minimum, nav)
VALUES 
(1, 'HDFC Equity Fund', 'INF179K01234', 'high', 12.5, 500, 450.25),
(2, 'ICICI Debt Fund', 'INF109K01567', 'low', 7.2, 1000, 25.80),
(3, 'SBI Hybrid Fund', 'INF200K01890', 'medium', 9.8, 500, 180.50);

COMMIT;
