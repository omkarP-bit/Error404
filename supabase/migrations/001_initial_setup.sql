-- Migration: Initial Schema Setup
-- Version: 001
-- Date: 2024-01-01

BEGIN;

-- Load the main schema
\i schema.sql

-- Insert default currencies
INSERT INTO currencies (code, name, symbol) VALUES
('INR', 'Indian Rupee', '₹'),
('USD', 'US Dollar', '$'),
('EUR', 'Euro', '€')
ON CONFLICT (code) DO NOTHING;

-- Insert default fund categories
INSERT INTO fund_categories (name, description) VALUES
('Equity', 'High risk, high return equity funds'),
('Debt', 'Low risk, stable return debt funds'),
('Hybrid', 'Balanced mix of equity and debt'),
('Liquid', 'Very low risk, highly liquid funds')
ON CONFLICT (name) DO NOTHING;

COMMIT;
