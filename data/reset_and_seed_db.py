"""
data/reset_and_seed_db.py
=========================
1. Deletes existing finance.db
2. Recreates all tables via SQLAlchemy models
3. Seeds the DB from Supabase/seed_data_v2 CSVs (single-user dataset)

Run: python data/reset_and_seed_db.py
"""

import sys
import os
import csv
import json
from pathlib import Path
from datetime import datetime

# ── Fix import path ───────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal
from app.models import (
    User, Account, Merchant, Transaction, UserFeedback,
    CategoryMapping, Alert, AuditLog, Goal, Budget,
    Currency, FundCategory, Receipt, BudgetProfile,
    SavingsPot, TransactionPattern, MLModelRun,
    FinancialHealthRating, MFInstrument, MFRecommendation,
    MFWatchlist, NotificationLog,
)

CSV_DIR = Path(__file__).resolve().parent.parent / "Supabase" / "seed_data_v2"
DB_PATH = Path(__file__).resolve().parent / "finance.db"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_csv(filename: str) -> list[dict]:
    path = CSV_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    s = s.replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def parse_float(s) -> float | None:
    try:
        return float(s) if s not in ("", None) else None
    except (ValueError, TypeError):
        return None

def parse_int(s) -> int | None:
    try:
        return int(s) if s not in ("", None) else None
    except (ValueError, TypeError):
        return None

def parse_bool(s) -> bool:
    return str(s).strip().lower() in ("true", "1", "yes")

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Drop and recreate DB
# ─────────────────────────────────────────────────────────────────────────────
print("\n🗑️   Dropping existing database …")
if DB_PATH.exists():
    DB_PATH.unlink()
    print(f"    Deleted: {DB_PATH}")
else:
    print(f"    No existing DB found at {DB_PATH}")

print("\n🏗️   Creating tables …")
Base.metadata.create_all(bind=engine)
print("    All tables created ✅")

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Seed
# ─────────────────────────────────────────────────────────────────────────────
session = SessionLocal()

try:
    # ── Users ──────────────────────────────────────────────────────────────
    print("\n📥  Seeding users …")
    for row in read_csv("users.csv"):
        session.add(User(
            user_id=int(row["user_id"]),
            auth_uid=row["auth_uid"],
            name=row["name"],
            email=row["email"],
            phone=row.get("phone") or None,
            monthly_income=float(row["monthly_income"]),
            income_type=row["income_type"],
            risk_profile=row["risk_profile"],
            kyc_status=row["kyc_status"],
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  users")

    # ── Accounts ───────────────────────────────────────────────────────────
    print("📥  Seeding accounts …")
    for row in read_csv("accounts.csv"):
        session.add(Account(
            account_id=int(row["account_id"]),
            user_id=int(row["user_id"]),
            institution_name=row["institution_name"],
            account_type=row["account_type"],
            current_balance=float(row["current_balance"]),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  accounts")

    # ── Merchants ──────────────────────────────────────────────────────────
    print("📥  Seeding merchants …")
    for row in read_csv("merchants.csv"):
        session.add(Merchant(
            merchant_id=int(row["merchant_id"]),
            raw_name=row["raw_name"],
            clean_name=row["clean_name"],
            default_category=row.get("default_category") or None,
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  merchants")

    # ── Transactions ───────────────────────────────────────────────────────
    print("📥  Seeding transactions …")
    for row in read_csv("transactions.csv"):
        session.add(Transaction(
            txn_id=int(row["txn_id"]),
            user_id=int(row["user_id"]),
            account_id=int(row["account_id"]),
            merchant_id=parse_int(row.get("merchant_id")),
            amount=float(row["amount"]),
            txn_type=row["txn_type"],
            category=row.get("category") or None,
            subcategory=row.get("subcategory") or None,
            raw_description=row.get("raw_description") or None,
            payment_mode=row.get("payment_mode") or None,
            user_verified=parse_bool(row.get("user_verified", "false")),
            is_recurring=parse_bool(row.get("is_recurring", "false")),
            confidence_score=parse_float(row.get("confidence_score")),
            balance_after_txn=parse_float(row.get("balance_after_txn")),
            txn_timestamp=parse_dt(row["txn_timestamp"]),
        ))
    session.commit()
    print("    ✅  transactions")

    # ── User Feedback ──────────────────────────────────────────────────────
    print("📥  Seeding user_feedback …")
    for row in read_csv("user_feedback.csv"):
        session.add(UserFeedback(
            feedback_id=int(row["feedback_id"]),
            txn_id=int(row["txn_id"]),
            corrected_category=row["corrected_category"],
            corrected_subcategory=row.get("corrected_subcategory") or None,
            source=row.get("source", "user_ui"),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  user_feedback")

    # ── Category Mappings ──────────────────────────────────────────────────
    print("📥  Seeding category_mappings …")
    for row in read_csv("category_mappings.csv"):
        session.add(CategoryMapping(
            mapping_id=int(row["mapping_id"]),
            user_id=int(row["user_id"]),
            merchant_id=parse_int(row.get("merchant_id")),
            category=row["category"],
            subcategory=row.get("subcategory") or None,
            confidence=float(row.get("confidence", 1.0)),
            source=row.get("source", "user"),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  category_mappings")

    # ── Alerts ─────────────────────────────────────────────────────────────
    print("📥  Seeding alerts …")
    for row in read_csv("alerts.csv"):
        session.add(Alert(
            alert_id=int(row["alert_id"]),
            user_id=int(row["user_id"]),
            txn_id=parse_int(row.get("txn_id")),
            alert_type=row["alert_type"],
            severity=row.get("severity", "medium"),
            status=row.get("status", "open"),
            message=row.get("message") or None,
            created_at=parse_dt(row["created_at"]),
            resolved_at=parse_dt(row.get("resolved_at")),
        ))
    session.commit()
    print("    ✅  alerts")

    # ── Audit Logs ─────────────────────────────────────────────────────────
    print("📥  Seeding audit_logs …")
    for row in read_csv("audit_logs.csv"):
        def _parse_json(s):
            if not s:
                return None
            try:
                return json.loads(s)
            except Exception:
                return None

        session.add(AuditLog(
            log_id=int(row["log_id"]),
            actor_id=parse_int(row.get("actor_id")),
            actor_type=row.get("actor_type", "system"),
            action=row["action"],
            resource_type=row["resource_type"],
            resource_id=parse_int(row.get("resource_id")),
            old_value=_parse_json(row.get("old_value")),
            new_value=_parse_json(row.get("new_value")),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  audit_logs")

    # ── Goals ──────────────────────────────────────────────────────────────
    print("📥  Seeding goals …")
    for row in read_csv("goals.csv"):
        deadline = None
        if row.get("deadline"):
            try:
                deadline = datetime.strptime(row["deadline"], "%Y-%m-%d").date()
            except ValueError:
                pass
        session.add(Goal(
            goal_id=int(row["goal_id"]),
            user_id=int(row["user_id"]),
            goal_name=row["goal_name"],
            target_amount=float(row["target_amount"]),
            current_amount=float(row.get("current_amount", 0)),
            deadline=deadline,
            status=row.get("status", "active"),
            feasibility_score=parse_float(row.get("feasibility_score")),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  goals")

    # ── Budgets ────────────────────────────────────────────────────────────
    print("📥  Seeding budgets …")
    for row in read_csv("budgets.csv"):
        session.add(Budget(
            budget_id=int(row["budget_id"]),
            user_id=int(row["user_id"]),
            category=row["category"],
            limit_amount=float(row["limit_amount"]),
            spent_amount=float(row.get("spent_amount", 0)),
            period=row.get("period", "monthly"),
            is_active=parse_bool(row.get("is_active", "true")),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  budgets")

    # ── Currencies ─────────────────────────────────────────────────────────
    print("📥  Seeding currencies …")
    for row in read_csv("currencies.csv"):
        session.add(Currency(
            currency_id=int(row["currency_id"]),
            code=row["code"],
            name=row["name"],
            symbol=row["symbol"],
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  currencies")

    # ── Fund Categories ────────────────────────────────────────────────────
    print("📥  Seeding fund_categories …")
    for row in read_csv("fund_categories.csv"):
        session.add(FundCategory(
            fund_category_id=int(row["fund_category_id"]),
            name=row["name"],
            description=row.get("description") or None,
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  fund_categories")

    # ── MF Instruments ─────────────────────────────────────────────────────
    print("📥  Seeding mf_instruments …")
    for row in read_csv("mf_instruments.csv"):
        nav_date = None
        if row.get("nav_date"):
            try:
                nav_date = datetime.strptime(row["nav_date"], "%Y-%m-%d").date()
            except ValueError:
                pass
        session.add(MFInstrument(
            instrument_id=int(row["instrument_id"]),
            fund_category_id=int(row["fund_category_id"]),
            name=row["name"],
            isin=row["isin"],
            risk_level=row["risk_level"],
            cagr_1y=parse_float(row.get("cagr_1y")),
            cagr_3y=parse_float(row.get("cagr_3y")),
            cagr_5y=parse_float(row.get("cagr_5y")),
            sip_minimum=float(row.get("sip_minimum", 500)),
            nav=parse_float(row.get("nav")),
            nav_date=nav_date,
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  mf_instruments")

    # ── Financial Health Ratings ───────────────────────────────────────────
    print("📥  Seeding financial_health_ratings …")
    for row in read_csv("financial_health_ratings.csv"):
        session.add(FinancialHealthRating(
            rating_id=int(row["rating_id"]),
            user_id=int(row["user_id"]),
            score=float(row["score"]),
            rating_label=row["rating_label"],
            prev_rating_id=parse_int(row.get("prev_rating_id")),
            rating_delta=parse_float(row.get("rating_delta")),
            improvement_tips=json.loads(row["improvement_tips"]) if row.get("improvement_tips") else None,
            window_months=int(row.get("window_months", 3)),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  financial_health_ratings")

    # ── MF Recommendations ─────────────────────────────────────────────────
    print("📥  Seeding mf_recommendations …")
    for row in read_csv("mf_recommendations.csv"):
        session.add(MFRecommendation(
            recommendation_id=int(row["recommendation_id"]),
            user_id=int(row["user_id"]),
            instrument_id=int(row["instrument_id"]),
            rating_id=parse_int(row.get("rating_id")),
            expected_cagr_low=float(row["expected_cagr_low"]),
            expected_cagr_high=float(row["expected_cagr_high"]),
            reason=row.get("reason") or None,
            hard_gates_snapshot=json.loads(row["hard_gates_snapshot"]) if row.get("hard_gates_snapshot") else None,
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  mf_recommendations")

    # ── MF Watchlist ───────────────────────────────────────────────────────
    print("📥  Seeding mf_watchlist …")
    for row in read_csv("mf_watchlist.csv"):
        session.add(MFWatchlist(
            watchlist_id=int(row["watchlist_id"]),
            user_id=int(row["user_id"]),
            instrument_id=int(row["instrument_id"]),
            added_at=parse_dt(row["added_at"]),
        ))
    session.commit()
    print("    ✅  mf_watchlist")

    # ── Receipts ───────────────────────────────────────────────────────────
    print("📥  Seeding receipts …")
    for row in read_csv("receipts.csv"):
        session.add(Receipt(
            receipt_id=int(row["receipt_id"]),
            txn_id=int(row["txn_id"]),
            extracted_items=json.loads(row["extracted_items"]) if row.get("extracted_items") else None,
            total_amount=parse_float(row.get("total_amount")),
            amount_matched=parse_bool(row.get("amount_matched", "false")),
            ocr_confidence=parse_float(row.get("ocr_confidence")),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  receipts")

    # ── Budget Profile ─────────────────────────────────────────────────────
    print("📥  Seeding budget_profiles …")
    for row in read_csv("budget_profiles.csv"):
        session.add(BudgetProfile(
            profile_id=int(row["profile_id"]),
            user_id=int(row["user_id"]),
            needs_ratio=float(row["needs_ratio"]),
            wants_ratio=float(row["wants_ratio"]),
            savings_ratio=float(row["savings_ratio"]),
            baseline_expense=float(row["baseline_expense"]),
            expense_volatility=float(row["expense_volatility"]),
            avg_monthly_surplus=float(row["avg_monthly_surplus"]),
            safe_investable_amount=float(row["safe_investable_amount"]),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  budget_profiles")

    # ── Savings Pots ───────────────────────────────────────────────────────
    print("📥  Seeding savings_pots …")
    for row in read_csv("savings_pots.csv"):
        session.add(SavingsPot(
            pot_id=int(row["pot_id"]),
            user_id=int(row["user_id"]),
            goal_id=parse_int(row.get("goal_id")),
            name=row["name"],
            target_amount=float(row["target_amount"]),
            current_amount=float(row["current_amount"]),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  savings_pots")

    # ── Transaction Patterns ───────────────────────────────────────────────
    print("📥  Seeding transaction_patterns …")
    for row in read_csv("transaction_patterns.csv"):
        session.add(TransactionPattern(
            pattern_id=int(row["pattern_id"]),
            user_id=int(row["user_id"]),
            category=row["category"],
            avg_amount=float(row["avg_amount"]),
            std_amount=float(row["std_amount"]),
            typical_weekdays=json.loads(row["typical_weekdays"]) if row.get("typical_weekdays") else None,
            typical_merchant_ids=json.loads(row["typical_merchant_ids"]) if row.get("typical_merchant_ids") else None,
            txn_count=int(row.get("txn_count", 0)),
            created_at=parse_dt(row["created_at"]),
            updated_at=parse_dt(row["updated_at"]),
        ))
    session.commit()
    print("    ✅  transaction_patterns")

    # ── ML Model Runs ──────────────────────────────────────────────────────
    print("📥  Seeding ml_model_runs …")
    for row in read_csv("ml_model_runs.csv"):
        session.add(MLModelRun(
            run_id=int(row["run_id"]),
            txn_id=parse_int(row.get("txn_id")),
            model_name=row["model_name"],
            model_version=row["model_version"],
            input_text=row.get("input_text") or None,
            output_category=row.get("output_category") or None,
            confidence=parse_float(row.get("confidence")),
            top5_categories=json.loads(row["top5_categories"]) if row.get("top5_categories") else None,
            latency_ms=parse_int(row.get("latency_ms")),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  ml_model_runs")

    # ── Notification Log ───────────────────────────────────────────────────
    print("📥  Seeding notification_log …")
    for row in read_csv("notification_log.csv"):
        session.add(NotificationLog(
            notification_id=int(row["notification_id"]),
            alert_id=int(row["alert_id"]),
            user_id=int(row["user_id"]),
            channel=row["channel"],
            sent_at=parse_dt(row["sent_at"]),
            delivered_at=parse_dt(row.get("delivered_at")),
            created_at=parse_dt(row["created_at"]),
        ))
    session.commit()
    print("    ✅  notification_log")

    # ─────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "="*55)
    print("  DATABASE RESET & SEED COMPLETE  (22 tables)")
    print("="*55)
    print(f"  Users                  : {session.query(User).count()}")
    print(f"  Accounts               : {session.query(Account).count()}")
    print(f"  Merchants              : {session.query(Merchant).count()}")
    print(f"  Transactions           : {session.query(Transaction).count()}")
    print(f"  User Feedback          : {session.query(UserFeedback).count()}")
    print(f"  Category Mappings      : {session.query(CategoryMapping).count()}")
    print(f"  Alerts                 : {session.query(Alert).count()}")
    print(f"  Audit Logs             : {session.query(AuditLog).count()}")
    print(f"  Goals                  : {session.query(Goal).count()}")
    print(f"  Budgets                : {session.query(Budget).count()}")
    print(f"  Currencies             : {session.query(Currency).count()}")
    print(f"  Fund Categories        : {session.query(FundCategory).count()}")
    print(f"  MF Instruments         : {session.query(MFInstrument).count()}")
    print(f"  Financial Health Ratings: {session.query(FinancialHealthRating).count()}")
    print(f"  MF Recommendations     : {session.query(MFRecommendation).count()}")
    print(f"  MF Watchlist           : {session.query(MFWatchlist).count()}")
    print(f"  Receipts               : {session.query(Receipt).count()}")
    print(f"  Budget Profiles        : {session.query(BudgetProfile).count()}")
    print(f"  Savings Pots           : {session.query(SavingsPot).count()}")
    print(f"  Transaction Patterns   : {session.query(TransactionPattern).count()}")
    print(f"  ML Model Runs          : {session.query(MLModelRun).count()}")
    print(f"  Notification Log       : {session.query(NotificationLog).count()}")
    print(f"\n  DB path: {DB_PATH}")
    print("="*55)

except Exception as e:
    session.rollback()
    print(f"\n❌  ERROR: {e}")
    raise
finally:
    session.close()
