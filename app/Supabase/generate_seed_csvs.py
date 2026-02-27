"""
Supabase/generate_seed_csvs.py
===============================
Generates production-grade, schema-constrained, ML-compatible CSV seed data
for the Morpheus FinTech PostgreSQL schema.

Single user (user_id=1), all FK/ENUM constraints respected, ML metadata complete.
Run: python Supabase/generate_seed_csvs.py
"""

import csv
import json
import math
import os
import random
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

OUTPUT_DIR = Path(__file__).parent / "seed_data_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime(2026, 2, 26, 12, 0, 0)  # current date reference
SIX_MONTHS_AGO = NOW - timedelta(days=182)

# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

def ds(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def rand_between(lo: float, hi: float, decimals: int = 2) -> float:
    return round(random.uniform(lo, hi), decimals)

def rand_ts(start: datetime, end: datetime) -> datetime:
    delta = end - start
    secs = int(delta.total_seconds())
    return start + timedelta(seconds=random.randint(0, secs))

def write_csv(filename: str, rows: list[dict], fieldnames: list[str]):
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # Ensure all fields are present
            clean = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(clean)
    print(f"  ✅ {filename:45s} {len(rows):>4} rows")

# ─────────────────────────────────────────────────────────────────────────────
# 1. USERS
# ─────────────────────────────────────────────────────────────────────────────
USER_ID = 1
USER_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
MONTHLY_INCOME = 120000.0

users = [{
    "user_id": USER_ID,
    "auth_uid": USER_UUID,
    "name": "Arjun Sharma",
    "email": "arjun.sharma@example.com",
    "phone": "+919876543210",
    "monthly_income": MONTHLY_INCOME,
    "income_type": "salaried",
    "risk_profile": "moderate",
    "kyc_status": "verified",
    "created_at": ts(NOW - timedelta(days=365)),
    "updated_at": ts(NOW - timedelta(days=5)),
}]

write_csv("users.csv", users, [
    "user_id", "auth_uid", "name", "email", "phone",
    "monthly_income", "income_type", "risk_profile", "kyc_status",
    "created_at", "updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 2. ACCOUNTS
# ─────────────────────────────────────────────────────────────────────────────
accounts = [
    {
        "account_id": 1, "user_id": USER_ID,
        "institution_name": "HDFC Bank",
        "account_type": "savings",
        "current_balance": 0.0,  # will be updated after transactions
        "created_at": ts(NOW - timedelta(days=360)),
    },
    {
        "account_id": 2, "user_id": USER_ID,
        "institution_name": "ICICI Bank",
        "account_type": "credit",
        "current_balance": 0.0,
        "created_at": ts(NOW - timedelta(days=350)),
    },
    {
        "account_id": 3, "user_id": USER_ID,
        "institution_name": "Zerodha Demat",
        "account_type": "current",
        "current_balance": 0.0,
        "created_at": ts(NOW - timedelta(days=340)),
    },
    {
        "account_id": 4, "user_id": USER_ID,
        "institution_name": "Axis Bank",
        "account_type": "savings",
        "current_balance": 0.0,
        "created_at": ts(NOW - timedelta(days=330)),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. MERCHANTS  (25 realistic Indian merchants)
# ─────────────────────────────────────────────────────────────────────────────
MERCHANT_DEFS = [
    # (merchant_id, raw_name, clean_name, default_category)
    (1,  "SWIGGY ORDER* 1234567",          "Swiggy",            "Food & Dining"),
    (2,  "ZOMATO* ORDER 9876543",          "Zomato",            "Food & Dining"),
    (3,  "BIGBASKET ONLINE GRC",           "BigBasket",         "Groceries"),
    (4,  "BLINKIT APP INSTANT DELIVER",    "Blinkit",           "Groceries"),
    (5,  "JIO PREPAID RECHARGE",           "Jio",               "Utilities"),
    (6,  "AIRTEL BROADBAND MONTHLY",       "Airtel",            "Utilities"),
    (7,  "NETFLIX INDIA PVT LTD",          "Netflix",           "Entertainment"),
    (8,  "AMAZON PAY SELLER SERVICES",     "Amazon",            "Shopping"),
    (9,  "FLIPKART INTERNET PVT LTD",      "Flipkart",          "Shopping"),
    (10, "UBER INDIA TECH PVT LTD",        "Uber",              "Transport"),
    (11, "OLA CABS PVT LTD BANGALORE",     "Ola Cabs",          "Transport"),
    (12, "HPCL PETROL PUMP 4567",          "HPCL",              "Transport"),
    (13, "APOLLO PHARMACY LTD",            "Apollo Pharmacy",   "Healthcare"),
    (14, "PRACTO ONLINE CONSULTATION",     "Practo",            "Healthcare"),
    (15, "HDFC BANK HOME LOAN EMI",        "HDFC Loan EMI",     "Finance"),
    (16, "SBI MUTUAL FUND SIP AUTO",       "SBI MF SIP",        "Investments"),
    (17, "ZERODHA BROKING LIMITED",        "Zerodha",           "Investments"),
    (18, "IRCTC E-TICKET BOOKING",         "IRCTC",             "Travel"),
    (19, "MAKEMYTRIP ONLINE TRAVEL",       "MakeMyTrip",        "Travel"),
    (20, "RELIANCE FRESH STORE 12",        "Reliance Fresh",    "Groceries"),
    (21, "PAYTM WALLET MERCHANT",          "Paytm",             "Finance"),
    (22, "MYNTRA FASHION STORE",           "Myntra",            "Shopping"),
    (23, "SPOTIFY INDIA MUSIC",            "Spotify",           "Entertainment"),
    (24, "DOMINOS PIZZA ORDER",            "Domino's Pizza",    "Food & Dining"),
    (25, "BOOKMYSHOW TICKETS",             "BookMyShow",        "Entertainment"),
]

merchants = []
for mid, raw, clean, cat in MERCHANT_DEFS:
    merchants.append({
        "merchant_id": mid,
        "raw_name": raw,
        "clean_name": clean,
        "default_category": cat,
        "created_at": ts(NOW - timedelta(days=400)),
    })

# txn_count will be derived from transactions below — init to 0 for import
# (actual count validated at end of script and noted in comment)

# ─────────────────────────────────────────────────────────────────────────────
# 4. TRANSACTIONS  (300 transactions over 6 months)
# ─────────────────────────────────────────────────────────────────────────────

def make_ml_metadata(txn_ts: datetime, amount: float, category: str,
                     rolling_avg: float, cat_volatility: float,
                     balance_after: float, surplus: float) -> str:
    return json.dumps({
        "month": txn_ts.month,
        "day_of_week": txn_ts.weekday(),
        "hour": txn_ts.hour,
        "rolling_avg_spend": round(rolling_avg, 2),
        "category_volatility": round(cat_volatility, 4),
        "balance_after_txn": round(balance_after, 2),
        "monthly_surplus_estimate": round(surplus, 2),
        "amount_z_score": round((amount - rolling_avg) / max(rolling_avg * 0.3, 1), 4),
        "daily_txn_freq": round(random.uniform(1.0, 4.5), 2),
        "avg_spend_per_category": round(rolling_avg * random.uniform(0.8, 1.2), 2),
        "spend_std_dev": round(rolling_avg * 0.28, 2),
        "expense_volatility": round(cat_volatility * 100, 4),
        "is_odd_hour": 1 if (txn_ts.hour < 7 or txn_ts.hour > 22) else 0,
    })

# Build transactions with realistic patterns
transactions = []
txn_id = 1

# Account balances (track running balance for savings account 1)
savings_balance = 45000.0   # starting balance
credit_balance  = 0.0
invest_balance  = 85000.0
axis_balance    = 22000.0

# Category rolling averages (for ML metadata)
cat_rolling = {
    "Food & Dining": 350.0, "Groceries": 1200.0, "Utilities": 600.0,
    "Entertainment": 300.0, "Shopping": 1500.0, "Transport": 400.0,
    "Healthcare": 500.0, "Finance": 18000.0, "Investments": 5000.0,
    "Travel": 3000.0, "Salary": 120000.0, "Rent": 22000.0,
}
cat_volatility = {
    "Food & Dining": 0.42, "Groceries": 0.21, "Utilities": 0.08,
    "Entertainment": 0.35, "Shopping": 0.55, "Transport": 0.38,
    "Healthcare": 0.60, "Finance": 0.05, "Investments": 0.04,
    "Travel": 0.72, "Salary": 0.01, "Rent": 0.00,
}

# Recurring group IDs
RG_SALARY   = "RG-SALARY-001"
RG_RENT     = "RG-RENT-001"
RG_SIP      = "RG-SIP-001"
RG_JIO      = "RG-JIO-001"
RG_AIRTEL   = "RG-AIRTEL-001"
RG_NETFLIX  = "RG-NETFLIX-001"
RG_SPOTIFY  = "RG-SPOTIFY-001"

# Used txn_ids for feedback uniqueness
feedback_txn_ids = set()
anomalous_txn_ids = []

# Map category → merchant pool
CAT_TO_MERCHANTS = {
    "Food & Dining":  [1, 2, 24],
    "Groceries":      [3, 4, 20],
    "Utilities":      [5, 6],
    "Entertainment":  [7, 23, 25],
    "Shopping":       [8, 9, 22],
    "Transport":      [10, 11, 12],
    "Healthcare":     [13, 14],
    "Finance":        [15, 21],
    "Investments":    [16, 17],
    "Travel":         [18, 19],
}

PAYMENT_MODES = ["UPI", "NEFT", "IMPS", "Card", "NetBanking", "Auto-Debit", "Cheque"]
CAT_METHODS   = ["sentence_transformer", "rule_based", "ml_model", "tfidf_classifier"]

def pick_hour_for_category(cat: str) -> int:
    if cat in ("Food & Dining",):
        return random.choice([8, 9, 13, 14, 19, 20, 21])
    if cat == "Utilities":
        return random.choice([10, 11, 14, 15])
    if cat == "Shopping":
        return random.choice([11, 12, 15, 16, 20, 21])
    return random.randint(8, 22)

# ── Month-by-month generation ─────────────────────────────────────────────────
month_starts = []
for delta_months in range(6, 0, -1):
    y = NOW.year
    m = NOW.month - delta_months
    while m <= 0:
        m += 12; y -= 1
    month_starts.append(datetime(y, m, 1))

# Also include current partial month
month_starts.append(datetime(NOW.year, NOW.month, 1))

txn_counter_per_merchant = {mid: 0 for mid in range(1, 26)}

for month_dt in month_starts:
    # Determine month end
    next_month = month_dt.replace(day=28) + timedelta(days=4)
    month_end = min(
        datetime(next_month.year, next_month.month, 1) - timedelta(seconds=1),
        NOW
    )

    # ── Salary credit (1st of month) ──────────────────────────────────────
    salary_ts = month_dt.replace(hour=9, minute=15)
    if salary_ts <= NOW:
        savings_balance += MONTHLY_INCOME
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": "",
            "amount": MONTHLY_INCOME,
            "txn_type": "credit",
            "category": "Salary",
            "subcategory": "Monthly Salary",
            "raw_description": f"SALARY CREDIT NEFT - TECHCORP INDIA - {salary_ts.strftime('%b%Y').upper()} - REF{random.randint(100000,999999)}",
            "payment_mode": "NEFT",
            "user_verified": "true",
            "is_recurring": "true",
            "confidence_score": 0.98,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(salary_ts),
            "clean_description": "salary credit techcorp india monthly",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.02,
            "user_verified_category": "true",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_SALARY,
            "ml_metadata": make_ml_metadata(salary_ts, MONTHLY_INCOME, "Salary",
                                             cat_rolling["Salary"], cat_volatility["Salary"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Rent debit (2nd of month) ──────────────────────────────────────────
    rent_ts = month_dt.replace(day=2, hour=10, minute=0)
    if rent_ts <= NOW:
        rent_amount = 22000.0
        savings_balance -= rent_amount
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": "",
            "amount": rent_amount,
            "txn_type": "debit",
            "category": "Rent",
            "subcategory": "Monthly Rent",
            "raw_description": f"NEFT TO LANDLORD RAJESH KUMAR - RENT {rent_ts.strftime('%b%Y').upper()} - REF{random.randint(100000,999999)}",
            "payment_mode": "NEFT",
            "user_verified": "true",
            "is_recurring": "true",
            "confidence_score": 0.97,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(rent_ts),
            "clean_description": "rent payment landlord monthly",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.03,
            "user_verified_category": "true",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_RENT,
            "ml_metadata": make_ml_metadata(rent_ts, rent_amount, "Rent",
                                             cat_rolling["Rent"], cat_volatility["Rent"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── SIP (5th of month) ─────────────────────────────────────────────────
    sip_ts = month_dt.replace(day=5, hour=10, minute=30)
    if sip_ts <= NOW:
        sip_amount = 10000.0
        savings_balance -= sip_amount
        invest_balance  += sip_amount
        mid = 16  # SBI MF SIP
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": sip_amount,
            "txn_type": "debit",
            "category": "Investments",
            "subcategory": "Mutual Fund SIP",
            "raw_description": f"SBI MUTUAL FUND SIP AUTO DEBIT - {sip_ts.strftime('%b%Y').upper()} - FOLIO12345",
            "payment_mode": "Auto-Debit",
            "user_verified": "true",
            "is_recurring": "true",
            "confidence_score": 0.97,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(sip_ts),
            "clean_description": "sbi mutual fund sip auto debit monthly",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.02,
            "user_verified_category": "true",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_SIP,
            "ml_metadata": make_ml_metadata(sip_ts, sip_amount, "Investments",
                                             cat_rolling["Investments"], cat_volatility["Investments"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Jio recharge (6th of month) ───────────────────────────────────────
    jio_ts = month_dt.replace(day=6, hour=11, minute=0)
    if jio_ts <= NOW:
        jio_amount = 599.0
        savings_balance -= jio_amount
        mid = 5
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": jio_amount,
            "txn_type": "debit",
            "category": "Utilities",
            "subcategory": "Mobile Recharge",
            "raw_description": f"JIO PREPAID RECHARGE UPI {jio_ts.strftime('%d%m%Y')} REF{random.randint(1000000,9999999)}",
            "payment_mode": "UPI",
            "user_verified": "false",
            "is_recurring": "true",
            "confidence_score": 0.95,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(jio_ts),
            "clean_description": "jio prepaid recharge monthly",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.04,
            "user_verified_category": "false",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_JIO,
            "ml_metadata": make_ml_metadata(jio_ts, jio_amount, "Utilities",
                                             cat_rolling["Utilities"], cat_volatility["Utilities"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Netflix (8th) ─────────────────────────────────────────────────────
    nf_ts = month_dt.replace(day=8, hour=14, minute=0)
    if nf_ts <= NOW:
        nf_amount = 649.0
        savings_balance -= nf_amount
        mid = 7
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": nf_amount,
            "txn_type": "debit",
            "category": "Entertainment",
            "subcategory": "Streaming",
            "raw_description": f"NETFLIX INDIA PVT LTD AUTO DEBIT {nf_ts.strftime('%d%m%Y')}",
            "payment_mode": "Auto-Debit",
            "user_verified": "false",
            "is_recurring": "true",
            "confidence_score": 0.96,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(nf_ts),
            "clean_description": "netflix india subscription monthly",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.03,
            "user_verified_category": "false",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_NETFLIX,
            "ml_metadata": make_ml_metadata(nf_ts, nf_amount, "Entertainment",
                                             cat_rolling["Entertainment"], cat_volatility["Entertainment"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Airtel broadband (10th) ───────────────────────────────────────────
    airtel_ts = month_dt.replace(day=10, hour=9, minute=30)
    if airtel_ts <= NOW:
        airtel_amount = 999.0
        savings_balance -= airtel_amount
        mid = 6
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": airtel_amount,
            "txn_type": "debit",
            "category": "Utilities",
            "subcategory": "Broadband",
            "raw_description": f"AIRTEL BROADBAND MONTHLY BILL {airtel_ts.strftime('%b%Y').upper()} REF{random.randint(100000,999999)}",
            "payment_mode": "Auto-Debit",
            "user_verified": "false",
            "is_recurring": "true",
            "confidence_score": 0.95,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(airtel_ts),
            "clean_description": "airtel broadband monthly bill",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.03,
            "user_verified_category": "false",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_AIRTEL,
            "ml_metadata": make_ml_metadata(airtel_ts, airtel_amount, "Utilities",
                                             cat_rolling["Utilities"], cat_volatility["Utilities"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Spotify (12th) ────────────────────────────────────────────────────
    spot_ts = month_dt.replace(day=12, hour=10, minute=0)
    if spot_ts <= NOW:
        spot_amount = 119.0
        savings_balance -= spot_amount
        mid = 23
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": spot_amount,
            "txn_type": "debit",
            "category": "Entertainment",
            "subcategory": "Music Streaming",
            "raw_description": f"SPOTIFY INDIA MUSIC SUBSCRIPTION {spot_ts.strftime('%d%m%Y')}",
            "payment_mode": "Auto-Debit",
            "user_verified": "false",
            "is_recurring": "true",
            "confidence_score": 0.95,
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(spot_ts),
            "clean_description": "spotify india music subscription",
            "cat_method": "rule_based",
            "source_type": "csv_import",
            "is_anomalous": "false",
            "anomaly_score": 0.03,
            "user_verified_category": "false",
            "location": "Mumbai, MH",
            "recurring_group_id": RG_SPOTIFY,
            "ml_metadata": make_ml_metadata(spot_ts, spot_amount, "Entertainment",
                                             cat_rolling["Entertainment"], cat_volatility["Entertainment"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Variable food & dining (8–12 per month) ───────────────────────────
    food_count = random.randint(8, 12)
    for _ in range(food_count):
        day = random.randint(1, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day,
                               pick_hour_for_category("Food & Dining"),
                               random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([1, 2, 24])
        amount = round(random.uniform(80, 750), 2)
        savings_balance -= amount
        is_anom = amount > 600 and random.random() < 0.15
        anom_score = round(random.uniform(0.65, 0.88), 4) if is_anom else round(random.uniform(0.02, 0.18), 4)
        txn_counter_per_merchant[mid] += 1
        row = {
            "txn_id": txn_id,
            "user_id": USER_ID,
            "account_id": 1,
            "merchant_id": mid,
            "amount": amount,
            "txn_type": "debit",
            "category": "Food & Dining",
            "subcategory": random.choice(["Online Food Order", "Restaurant", "Cafe"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["UPI", "Card"]),
            "user_verified": "false",
            "is_recurring": "false",
            "confidence_score": round(random.uniform(0.80, 0.95), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} food order",
            "cat_method": random.choice(CAT_METHODS),
            "source_type": "csv_import",
            "is_anomalous": "true" if is_anom else "false",
            "anomaly_score": anom_score,
            "user_verified_category": "false",
            "location": random.choice(["Mumbai, MH", "Mumbai, MH", "Thane, MH", "Navi Mumbai, MH"]),
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Food & Dining",
                                             cat_rolling["Food & Dining"], cat_volatility["Food & Dining"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        }
        if is_anom:
            anomalous_txn_ids.append(txn_id)
        transactions.append(row)
        txn_id += 1

    # ── Groceries (3–5 per month) ──────────────────────────────────────────
    for _ in range(random.randint(3, 5)):
        day = random.randint(1, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(10, 20), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([3, 4, 20])
        amount = round(random.uniform(200, 3000), 2)
        savings_balance -= amount
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": "Groceries", "subcategory": random.choice(["Vegetables", "Household", "Dairy"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["UPI", "Card", "NetBanking"]),
            "user_verified": "false", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.82, 0.96), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} grocery purchase",
            "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
            "is_anomalous": "false", "anomaly_score": round(random.uniform(0.02, 0.12), 4),
            "user_verified_category": "false",
            "location": random.choice(["Mumbai, MH", "Thane, MH"]),
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Groceries",
                                             cat_rolling["Groceries"], cat_volatility["Groceries"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Shopping (2–4 per month) ───────────────────────────────────────────
    for _ in range(random.randint(2, 4)):
        day = random.randint(1, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(11, 22), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([8, 9, 22])
        amount = round(random.uniform(199, 5500), 2)
        savings_balance -= amount
        is_anom = amount > 4000 and random.random() < 0.2
        anom_score = round(random.uniform(0.68, 0.92), 4) if is_anom else round(random.uniform(0.03, 0.15), 4)
        txn_counter_per_merchant[mid] += 1
        row = {
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": "Shopping", "subcategory": random.choice(["Electronics", "Clothing", "Home Decor"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["Card", "UPI", "NetBanking"]),
            "user_verified": "false", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.79, 0.94), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} online shopping",
            "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
            "is_anomalous": "true" if is_anom else "false", "anomaly_score": anom_score,
            "user_verified_category": "false",
            "location": random.choice(["Mumbai, MH", "Navi Mumbai, MH"]),
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Shopping",
                                             cat_rolling["Shopping"], cat_volatility["Shopping"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        }
        if is_anom:
            anomalous_txn_ids.append(txn_id)
        transactions.append(row)
        txn_id += 1

    # ── Transport (4–7 per month) ──────────────────────────────────────────
    for _ in range(random.randint(4, 7)):
        day = random.randint(1, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.choice([8, 9, 18, 19, 20]), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([10, 11, 12])
        amount = round(random.uniform(50, 800), 2)
        savings_balance -= amount
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": "Transport", "subcategory": random.choice(["Cab", "Petrol", "Metro"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["UPI", "Card"]),
            "user_verified": "false", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.82, 0.95), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} transport",
            "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
            "is_anomalous": "false", "anomaly_score": round(random.uniform(0.02, 0.14), 4),
            "user_verified_category": "false",
            "location": random.choice(["Mumbai, MH", "Thane, MH", "Dadar, MH"]),
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Transport",
                                             cat_rolling["Transport"], cat_volatility["Transport"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Healthcare (0–2 per month) ────────────────────────────────────────
    for _ in range(random.randint(0, 2)):
        day = random.randint(1, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(10, 18), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([13, 14])
        amount = round(random.uniform(150, 2000), 2)
        savings_balance -= amount
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": "Healthcare", "subcategory": random.choice(["Pharmacy", "Consultation", "Lab Test"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["UPI", "Card", "NetBanking"]),
            "user_verified": "false", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.80, 0.93), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} healthcare",
            "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
            "is_anomalous": "false", "anomaly_score": round(random.uniform(0.03, 0.18), 4),
            "user_verified_category": "false",
            "location": "Mumbai, MH",
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Healthcare",
                                             cat_rolling["Healthcare"], cat_volatility["Healthcare"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Travel (0–1 per month) ────────────────────────────────────────────
    if random.random() < 0.5:
        day = random.randint(10, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(9, 17), random.randint(0, 59))
        except ValueError:
            pass
        else:
            if txn_ts <= NOW:
                mid = random.choice([18, 19])
                amount = round(random.uniform(800, 8000), 2)
                savings_balance -= amount
                is_anom = amount > 6000 and random.random() < 0.25
                anom_score = round(random.uniform(0.70, 0.90), 4) if is_anom else round(random.uniform(0.04, 0.20), 4)
                txn_counter_per_merchant[mid] += 1
                row = {
                    "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
                    "merchant_id": mid, "amount": amount, "txn_type": "debit",
                    "category": "Travel", "subcategory": random.choice(["Train Ticket", "Flight", "Hotel"]),
                    "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} PNR{random.randint(1000000000,9999999999)}",
                    "payment_mode": random.choice(["NetBanking", "Card", "UPI"]),
                    "user_verified": "false", "is_recurring": "false",
                    "confidence_score": round(random.uniform(0.81, 0.94), 4),
                    "balance_after_txn": round(savings_balance, 2),
                    "txn_timestamp": ts(txn_ts),
                    "clean_description": f"{merchants[mid-1]['clean_name'].lower()} travel booking",
                    "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
                    "is_anomalous": "true" if is_anom else "false", "anomaly_score": anom_score,
                    "user_verified_category": "false",
                    "location": random.choice(["Mumbai, MH", "Pune, MH", "Delhi, DL"]),
                    "recurring_group_id": "",
                    "ml_metadata": make_ml_metadata(txn_ts, amount, "Travel",
                                                     cat_rolling["Travel"], cat_volatility["Travel"],
                                                     savings_balance, MONTHLY_INCOME * 0.3),
                }
                if is_anom:
                    anomalous_txn_ids.append(txn_id)
                transactions.append(row)
                txn_id += 1

    # ── Zerodha investments (occasional, 0–2 per month) ───────────────────
    for _ in range(random.randint(0, 2)):
        day = random.randint(3, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(9, 15), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = 17  # Zerodha
        amount = round(random.uniform(2000, 25000), 2)
        savings_balance -= amount
        invest_balance  += amount
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": "Investments", "subcategory": "Stock Purchase",
            "raw_description": f"ZERODHA BROKING LIMITED UPI {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": "UPI",
            "user_verified": "true", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.88, 0.97), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": "zerodha broking stock purchase",
            "cat_method": "sentence_transformer", "source_type": "csv_import",
            "is_anomalous": "false", "anomaly_score": round(random.uniform(0.03, 0.14), 4),
            "user_verified_category": "true",
            "location": "Mumbai, MH",
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Investments",
                                             cat_rolling["Investments"], cat_volatility["Investments"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

    # ── Credit card bill payment (25th of month) ──────────────────────────
    cc_ts = month_dt.replace(day=25, hour=11, minute=30)
    try:
        cc_ts = datetime(month_dt.year, month_dt.month, 25, 11, 30)
    except ValueError:
        pass
    else:
        if cc_ts <= NOW:
            cc_amount = round(random.uniform(8000, 25000), 2)
            savings_balance -= cc_amount
            mid = 21  # Paytm / bank gateway
            txn_counter_per_merchant[mid] += 1
            transactions.append({
                "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
                "merchant_id": mid, "amount": cc_amount, "txn_type": "debit",
                "category": "Finance", "subcategory": "Credit Card Bill",
                "raw_description": f"ICICI CREDIT CARD BILL PAYMENT {cc_ts.strftime('%b%Y').upper()} REF{random.randint(100000,999999)}",
                "payment_mode": "NEFT",
                "user_verified": "true", "is_recurring": "true",
                "confidence_score": 0.96,
                "balance_after_txn": round(savings_balance, 2),
                "txn_timestamp": ts(cc_ts),
                "clean_description": "icici credit card bill payment monthly",
                "cat_method": "rule_based", "source_type": "csv_import",
                "is_anomalous": "false", "anomaly_score": round(random.uniform(0.02, 0.08), 4),
                "user_verified_category": "true",
                "location": "Mumbai, MH",
                "recurring_group_id": "RG-CCBILL-001",
                "ml_metadata": make_ml_metadata(cc_ts, cc_amount, "Finance",
                                                 cat_rolling["Finance"], cat_volatility["Finance"],
                                                 savings_balance, MONTHLY_INCOME * 0.3),
            })
            txn_id += 1

    # ── Month-end spike: extra shopping/entertainment (last 3 days) ────────
    for _ in range(random.randint(2, 4)):
        day = random.randint(26, 28)
        try:
            txn_ts = datetime(month_dt.year, month_dt.month, day, random.randint(17, 22), random.randint(0, 59))
        except ValueError:
            continue
        if txn_ts > NOW:
            continue
        mid = random.choice([8, 9, 24, 25])
        amount = round(random.uniform(150, 2500), 2)
        savings_balance -= amount
        txn_counter_per_merchant[mid] += 1
        transactions.append({
            "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
            "merchant_id": mid, "amount": amount, "txn_type": "debit",
            "category": random.choice(["Shopping", "Entertainment"]),
            "subcategory": random.choice(["Movie Tickets", "Online Shopping", "Weekend Outing"]),
            "raw_description": f"{merchants[mid-1]['raw_name']} {txn_ts.strftime('%d%m%Y')} TXN{random.randint(100000,999999)}",
            "payment_mode": random.choice(["UPI", "Card"]),
            "user_verified": "false", "is_recurring": "false",
            "confidence_score": round(random.uniform(0.78, 0.93), 4),
            "balance_after_txn": round(savings_balance, 2),
            "txn_timestamp": ts(txn_ts),
            "clean_description": f"{merchants[mid-1]['clean_name'].lower()} weekend purchase",
            "cat_method": random.choice(CAT_METHODS), "source_type": "csv_import",
            "is_anomalous": "false", "anomaly_score": round(random.uniform(0.03, 0.16), 4),
            "user_verified_category": "false",
            "location": random.choice(["Mumbai, MH", "Bandra, MH", "Juhu, MH"]),
            "recurring_group_id": "",
            "ml_metadata": make_ml_metadata(txn_ts, amount, "Shopping",
                                             cat_rolling["Shopping"], cat_volatility["Shopping"],
                                             savings_balance, MONTHLY_INCOME * 0.3),
        })
        txn_id += 1

# ── Add one large anomalous transaction (odd hour, unusual location) ──────────
anomaly_ts = datetime(2025, 11, 17, 2, 33, 0)
savings_balance -= 18500.0
anomalous_txn_ids.append(txn_id)
transactions.append({
    "txn_id": txn_id, "user_id": USER_ID, "account_id": 1,
    "merchant_id": 8,  # Amazon
    "amount": 18500.0, "txn_type": "debit",
    "category": "Shopping", "subcategory": "Electronics",
    "raw_description": "AMAZON PAY SELLER SERVICES 17112025 TXN998877 APPLE IPHONE",
    "payment_mode": "NetBanking",
    "user_verified": "false", "is_recurring": "false",
    "confidence_score": 0.88,
    "balance_after_txn": round(savings_balance, 2),
    "txn_timestamp": ts(anomaly_ts),
    "clean_description": "amazon electronics large purchase midnight",
    "cat_method": "sentence_transformer", "source_type": "csv_import",
    "is_anomalous": "true", "anomaly_score": 0.9312,
    "user_verified_category": "false",
    "location": "Kolkata, WB",
    "recurring_group_id": "",
    "ml_metadata": make_ml_metadata(anomaly_ts, 18500.0, "Shopping",
                                     cat_rolling["Shopping"], 0.85, savings_balance, 12000.0),
})
txn_counter_per_merchant[8] += 1
txn_id += 1

# ── Update merchant txn_count ─────────────────────────────────────────────────
for m in merchants:
    mid = m["merchant_id"]
    m["txn_count"] = txn_counter_per_merchant.get(mid, 0)

# ── Update account balances ───────────────────────────────────────────────────
accounts[0]["current_balance"] = round(max(savings_balance, 0), 2)
accounts[1]["current_balance"] = round(credit_balance, 2)
accounts[2]["current_balance"] = round(invest_balance, 2)
accounts[3]["current_balance"] = round(axis_balance, 2)

# Write transactions CSV
TXN_FIELDS = [
    "txn_id", "user_id", "account_id", "merchant_id", "amount", "txn_type",
    "category", "subcategory", "raw_description", "clean_description",
    "payment_mode", "user_verified", "is_recurring", "confidence_score",
    "balance_after_txn", "txn_timestamp", "cat_method", "source_type",
    "is_anomalous", "anomaly_score", "user_verified_category", "location",
    "recurring_group_id", "ml_metadata",
]
write_csv("transactions.csv", transactions, TXN_FIELDS)

# Write accounts
write_csv("accounts.csv", accounts, [
    "account_id", "user_id", "institution_name", "account_type",
    "current_balance", "created_at",
])

# Write merchants
write_csv("merchants.csv", merchants, [
    "merchant_id", "raw_name", "clean_name", "default_category",
    "txn_count", "created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 5. USER FEEDBACK  (20 rows)
# ─────────────────────────────────────────────────────────────────────────────
# Pick unique txn_ids that are debit transactions
debit_txn_ids = [t["txn_id"] for t in transactions if t["txn_type"] == "debit"]
random.shuffle(debit_txn_ids)
feedback_source_opts = ["user_ui", "user_ui", "user_ui", "ocr", "pdf", "auto_correction"]

feedbacks = []
used_fb_txn = set()
for i in range(20):
    if i >= len(debit_txn_ids):
        break
    tid = debit_txn_ids[i]
    used_fb_txn.add(tid)
    txn = next(t for t in transactions if t["txn_id"] == tid)
    orig_cat = txn["category"]
    corrections = {
        "Food & Dining": ("Food & Dining", "Restaurant"),
        "Groceries": ("Groceries", "Supermarket"),
        "Shopping": ("Shopping", "Clothing"),
        "Transport": ("Transport", "Cab"),
        "Utilities": ("Utilities", "Mobile Recharge"),
        "Entertainment": ("Entertainment", "OTT"),
        "Healthcare": ("Healthcare", "Pharmacy"),
        "Finance": ("Finance", "Credit Card Bill"),
        "Investments": ("Investments", "Mutual Fund"),
        "Travel": ("Travel", "Train Ticket"),
        "Rent": ("Housing", "Rent"),
        "Salary": ("Income", "Salary"),
    }
    corrected_cat, corrected_sub = corrections.get(orig_cat, (orig_cat, "General"))
    fb_ts = datetime.strptime(txn["txn_timestamp"].replace("Z",""), "%Y-%m-%dT%H:%M:%S") + timedelta(hours=random.randint(1, 48))
    if fb_ts > NOW:
        fb_ts = NOW - timedelta(hours=1)
    feedbacks.append({
        "feedback_id": i + 1,
        "txn_id": tid,
        "corrected_category": corrected_cat,
        "corrected_subcategory": corrected_sub,
        "source": random.choice(feedback_source_opts),
        "created_at": ts(fb_ts),
    })

write_csv("user_feedback.csv", feedbacks, [
    "feedback_id", "txn_id", "corrected_category", "corrected_subcategory",
    "source", "created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 6. CATEGORY MAPPINGS  (20 rows)
# ─────────────────────────────────────────────────────────────────────────────
mapping_source_opts = ["user", "ml_model", "system", "ocr"]
cat_mappings = []
for i, (mid, raw, clean, cat) in enumerate(MERCHANT_DEFS[:20]):
    cat_mappings.append({
        "mapping_id": i + 1,
        "user_id": USER_ID,
        "merchant_id": mid,
        "category": cat,
        "subcategory": "General",
        "confidence": round(random.uniform(0.85, 1.0), 4),
        "source": random.choice(mapping_source_opts),
        "created_at": ts(NOW - timedelta(days=random.randint(30, 300))),
        "updated_at": ts(NOW - timedelta(days=random.randint(1, 30))),
    })

write_csv("category_mappings.csv", cat_mappings, [
    "mapping_id", "user_id", "merchant_id", "category", "subcategory",
    "confidence", "source", "created_at", "updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 7. GOALS  (5 goals)
# ─────────────────────────────────────────────────────────────────────────────
goals = [
    {
        "goal_id": 1, "user_id": USER_ID,
        "goal_name": "Emergency Fund",
        "target_amount": 360000.0, "current_amount": 145000.0,
        "deadline": "2026-12-31", "status": "active",
        "feasibility_score": 0.82,
        "created_at": ts(NOW - timedelta(days=180)),
        "updated_at": ts(NOW - timedelta(days=5)),
    },
    {
        "goal_id": 2, "user_id": USER_ID,
        "goal_name": "Retirement Corpus",
        "target_amount": 10000000.0, "current_amount": 285000.0,
        "deadline": "2050-01-01", "status": "active",
        "feasibility_score": 0.74,
        "created_at": ts(NOW - timedelta(days=365)),
        "updated_at": ts(NOW - timedelta(days=10)),
    },
    {
        "goal_id": 3, "user_id": USER_ID,
        "goal_name": "New Laptop",
        "target_amount": 120000.0, "current_amount": 48000.0,
        "deadline": "2026-08-31", "status": "active",
        "feasibility_score": 0.88,
        "created_at": ts(NOW - timedelta(days=90)),
        "updated_at": ts(NOW - timedelta(days=3)),
    },
    {
        "goal_id": 4, "user_id": USER_ID,
        "goal_name": "Goa Vacation",
        "target_amount": 80000.0, "current_amount": 32000.0,
        "deadline": "2026-06-15", "status": "active",
        "feasibility_score": 0.79,
        "created_at": ts(NOW - timedelta(days=60)),
        "updated_at": ts(NOW - timedelta(days=2)),
    },
    {
        "goal_id": 5, "user_id": USER_ID,
        "goal_name": "Home Down Payment",
        "target_amount": 2000000.0, "current_amount": 125000.0,
        "deadline": "2030-03-31", "status": "active",
        "feasibility_score": 0.61,
        "created_at": ts(NOW - timedelta(days=270)),
        "updated_at": ts(NOW - timedelta(days=7)),
    },
]

write_csv("goals.csv", goals, [
    "goal_id", "user_id", "goal_name", "target_amount", "current_amount",
    "deadline", "status", "feasibility_score", "created_at", "updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 8. BUDGETS  (one row per category, 10 categories)
# ─────────────────────────────────────────────────────────────────────────────
budget_defs = [
    ("Food & Dining",  8000.0,  6200.0),
    ("Groceries",      10000.0, 8500.0),
    ("Utilities",      2500.0,  1598.0),
    ("Entertainment",  2000.0,  1536.0),
    ("Shopping",       10000.0, 11200.0),  # intentional breach
    ("Transport",      5000.0,  3800.0),
    ("Healthcare",     3000.0,  1200.0),
    ("Finance",        30000.0, 27400.0),
    ("Investments",    15000.0, 14880.0),
    ("Travel",         8000.0,  3400.0),
]

budgets = []
for i, (cat, limit, spent) in enumerate(budget_defs):
    budgets.append({
        "budget_id": i + 1,
        "user_id": USER_ID,
        "category": cat,
        "limit_amount": limit,
        "spent_amount": spent,
        "period": "monthly",
        "is_active": "true",
        "created_at": ts(NOW - timedelta(days=180)),
        "updated_at": ts(NOW - timedelta(days=2)),
    })

write_csv("budgets.csv", budgets, [
    "budget_id", "user_id", "category", "limit_amount", "spent_amount",
    "period", "is_active", "created_at", "updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 9. ALERTS  (15 alerts)
# ─────────────────────────────────────────────────────────────────────────────
# Ensure we have enough anomalous txn_ids
while len(anomalous_txn_ids) < 5:
    anomalous_txn_ids.append(random.choice([t["txn_id"] for t in transactions if t["txn_type"] == "debit"]))

alert_defs = [
    # (alert_type, severity, status, message, use_txn)
    ("anomaly",           "critical", "open",         "Unusual large transaction detected at midnight in Kolkata", True),
    ("anomaly",           "high",     "acknowledged",  "High-value shopping transaction outside home city", True),
    ("anomaly",           "high",     "resolved",      "Multiple transactions in quick succession detected", True),
    ("budget_breach",     "high",     "open",          "Shopping budget exceeded by ₹1,200 this month", False),
    ("budget_breach",     "medium",   "open",          "Finance spend at 91% of monthly budget limit", False),
    ("budget_breach",     "medium",   "acknowledged",  "Food & Dining spend at 77% of monthly limit", False),
    ("large_transaction", "high",     "resolved",      "Transaction of ₹18,500 on Amazon flagged as large", True),
    ("large_transaction", "medium",   "open",          "Travel booking ₹7,800 detected — verify if intended", True),
    ("unusual_pattern",   "medium",   "open",          "Weekend spending 3x higher than weekday average", False),
    ("unusual_pattern",   "low",      "dismissed",     "Category mix shift detected in last 30 days", False),
    ("goal_at_risk",      "medium",   "open",          "Home Down Payment goal progress is below schedule", False),
    ("goal_at_risk",      "low",      "open",          "Goa Vacation goal needs ₹2,400/week to stay on track", False),
    ("duplicate_charge",  "high",     "resolved",      "Possible duplicate charge detected from Swiggy", True),
    ("anomaly",           "medium",   "open",          "Groceries spend 2.4x higher than rolling average", False),
    ("budget_breach",     "low",      "dismissed",     "Investment SIP completed — monthly surplus below ₹5,000", False),
]

# Severity → AlertSeverity enum
SEV_VALID = {"low", "medium", "high", "critical"}
TYPE_VALID = {"anomaly", "budget_breach", "large_transaction", "unusual_pattern", "goal_at_risk", "duplicate_charge"}
STATUS_VALID = {"open", "acknowledged", "resolved", "dismissed"}

alerts = []
anom_idx = 0
high_debit_txns = [t["txn_id"] for t in transactions if t["txn_type"] == "debit" and t["amount"] > 5000]

for i, (atype, sev, status, msg, use_txn) in enumerate(alert_defs):
    alert_ts = NOW - timedelta(days=random.randint(1, 60), hours=random.randint(0, 23))
    resolved_at = ""
    if status == "resolved":
        resolved_at = ts(alert_ts + timedelta(hours=random.randint(2, 48)))

    txn_ref = ""
    if use_txn and anom_idx < len(anomalous_txn_ids):
        txn_ref = anomalous_txn_ids[anom_idx]
        anom_idx += 1
    elif use_txn and high_debit_txns:
        txn_ref = random.choice(high_debit_txns)

    alerts.append({
        "alert_id": i + 1,
        "user_id": USER_ID,
        "txn_id": txn_ref,
        "alert_type": atype,
        "severity": sev,
        "status": status,
        "message": msg,
        "created_at": ts(alert_ts),
        "resolved_at": resolved_at,
    })

write_csv("alerts.csv", alerts, [
    "alert_id", "user_id", "txn_id", "alert_type", "severity", "status",
    "message", "created_at", "resolved_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 10. AUDIT LOGS  (20 rows)
# ─────────────────────────────────────────────────────────────────────────────
actor_types = ["user", "system", "ml_model", "admin"]
audit_defs = [
    # (action, resource_type, actor_type, resource_id_offset)
    ("INSERT",  "transactions",     "system",   1),
    ("INSERT",  "transactions",     "system",   2),
    ("INSERT",  "transactions",     "system",   3),
    ("UPDATE",  "transactions",     "user",     5),
    ("UPDATE",  "transactions",     "user",     8),
    ("UPDATE",  "category_mappings","user",     1),
    ("UPDATE",  "category_mappings","ml_model", 2),
    ("INSERT",  "goals",            "user",     1),
    ("UPDATE",  "goals",            "user",     3),
    ("INSERT",  "alerts",           "system",   1),
    ("UPDATE",  "alerts",           "user",     4),
    ("INSERT",  "user_feedback",    "user",     1),
    ("INSERT",  "user_feedback",    "user",     2),
    ("UPDATE",  "users",            "user",     1),
    ("INSERT",  "category_mappings","system",   3),
    ("INSERT",  "transactions",     "system",   50),
    ("UPDATE",  "transactions",     "ml_model", 22),
    ("UPDATE",  "goals",            "system",   2),
    ("INSERT",  "alerts",           "ml_model", 5),
    ("UPDATE",  "transactions",     "user",     15),
]

audit_logs = []
for i, (action, res_type, actor_t, res_id) in enumerate(audit_defs):
    log_ts = NOW - timedelta(days=random.randint(1, 150), hours=random.randint(0, 23))
    old_v = json.dumps({"status": "pending", "category": "uncategorized"}) if action == "UPDATE" else None
    new_v = json.dumps({"status": "active",  "category": "Food & Dining", "updated_by": actor_t})
    audit_logs.append({
        "log_id": i + 1,
        "actor_id": USER_ID if actor_t == "user" else "",
        "actor_type": actor_t,
        "action": action,
        "resource_type": res_type,
        "resource_id": res_id,
        "old_value": old_v if old_v else "",
        "new_value": new_v,
        "ip_address": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
        "created_at": ts(log_ts),
    })

write_csv("audit_logs.csv", audit_logs, [
    "log_id", "actor_id", "actor_type", "action", "resource_type",
    "resource_id", "old_value", "new_value", "ip_address", "created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 11. CURRENCIES
# ─────────────────────────────────────────────────────────────────────────────
currencies = [
    {"currency_id": 1, "code": "INR", "name": "Indian Rupee",   "symbol": "₹", "created_at": ts(NOW - timedelta(days=400))},
    {"currency_id": 2, "code": "USD", "name": "US Dollar",      "symbol": "$", "created_at": ts(NOW - timedelta(days=400))},
    {"currency_id": 3, "code": "EUR", "name": "Euro",           "symbol": "€", "created_at": ts(NOW - timedelta(days=400))},
    {"currency_id": 4, "code": "GBP", "name": "British Pound",  "symbol": "£", "created_at": ts(NOW - timedelta(days=400))},
    {"currency_id": 5, "code": "JPY", "name": "Japanese Yen",   "symbol": "¥", "created_at": ts(NOW - timedelta(days=400))},
]
write_csv("currencies.csv", currencies, ["currency_id", "code", "name", "symbol", "created_at"])

# ─────────────────────────────────────────────────────────────────────────────
# 12. FUND CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
fund_categories = [
    {"fund_category_id": 1, "name": "Equity - Large Cap",   "description": "Large cap equity mutual funds with stable returns", "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 2, "name": "Equity - Mid Cap",     "description": "Mid cap equity funds with higher growth potential", "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 3, "name": "Equity - Small Cap",   "description": "Small cap funds with high risk and high reward",    "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 4, "name": "Debt - Short Term",    "description": "Short duration debt funds for capital preservation","created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 5, "name": "Debt - Long Term",     "description": "Long duration government and corporate bonds",      "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 6, "name": "Hybrid - Balanced",    "description": "Balanced mix of equity and debt instruments",       "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 7, "name": "Index Fund",           "description": "Passive funds tracking Nifty 50 / Sensex",          "created_at": ts(NOW - timedelta(days=400))},
    {"fund_category_id": 8, "name": "ELSS",                 "description": "Tax-saving equity linked savings scheme (80C)",     "created_at": ts(NOW - timedelta(days=400))},
]
write_csv("fund_categories.csv", fund_categories, ["fund_category_id", "name", "description", "created_at"])

# ─────────────────────────────────────────────────────────────────────────────
# 13. MF INSTRUMENTS  (12 instruments)
# ─────────────────────────────────────────────────────────────────────────────
mf_instruments = [
    {"instrument_id":1,  "fund_category_id":7, "name":"Nifty 50 Index Fund - Direct",      "isin":"INF846K01EW2", "risk_level":"moderate",     "cagr_1y":14.2, "cagr_3y":13.8, "cagr_5y":15.1, "sip_minimum":500,  "nav":185.42, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":2,  "fund_category_id":1, "name":"HDFC Top 100 Fund - Direct",        "isin":"INF179K01VR5", "risk_level":"moderate",     "cagr_1y":16.5, "cagr_3y":14.9, "cagr_5y":16.2, "sip_minimum":500,  "nav":952.18, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":3,  "fund_category_id":2, "name":"Axis Midcap Fund - Direct",         "isin":"INF846K01DP1", "risk_level":"moderate",     "cagr_1y":18.3, "cagr_3y":16.4, "cagr_5y":18.7, "sip_minimum":500,  "nav":112.65, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":4,  "fund_category_id":3, "name":"SBI Small Cap Fund - Direct",       "isin":"INF200K01RO2", "risk_level":"aggressive",   "cagr_1y":22.1, "cagr_3y":20.5, "cagr_5y":24.3, "sip_minimum":500,  "nav":145.32, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":5,  "fund_category_id":8, "name":"Mirae Asset ELSS Tax Saver - Direct","isin":"INF769K01DM2","risk_level":"moderate",     "cagr_1y":17.8, "cagr_3y":15.6, "cagr_5y":17.9, "sip_minimum":500,  "nav":38.74,  "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":6,  "fund_category_id":6, "name":"ICICI Pru Balanced Advantage - Direct","isin":"INF109K01Z95","risk_level":"moderate",   "cagr_1y":13.4, "cagr_3y":12.8, "cagr_5y":14.2, "sip_minimum":1000, "nav":72.18,  "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":7,  "fund_category_id":4, "name":"HDFC Short Term Debt Fund - Direct","isin":"INF179K01XD2", "risk_level":"conservative", "cagr_1y":7.2,  "cagr_3y":6.9,  "cagr_5y":7.1,  "sip_minimum":1000, "nav":28.94,  "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":8,  "fund_category_id":5, "name":"SBI Gilt Fund - Direct",            "isin":"INF200K01WE3", "risk_level":"conservative", "cagr_1y":8.1,  "cagr_3y":7.8,  "cagr_5y":8.4,  "sip_minimum":5000, "nav":58.62,  "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":9,  "fund_category_id":1, "name":"Kotak Bluechip Fund - Direct",      "isin":"INF174K01LS4", "risk_level":"moderate",     "cagr_1y":15.9, "cagr_3y":14.2, "cagr_5y":15.8, "sip_minimum":500,  "nav":623.45, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":10, "fund_category_id":2, "name":"Nippon India Growth Fund - Direct", "isin":"INF204K01U66", "risk_level":"aggressive",   "cagr_1y":19.4, "cagr_3y":17.9, "cagr_5y":19.2, "sip_minimum":500,  "nav":3842.10,"nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":11, "fund_category_id":7, "name":"UTI Nifty Next 50 Index - Direct",  "isin":"INF789F1AND9", "risk_level":"moderate",     "cagr_1y":12.8, "cagr_3y":11.9, "cagr_5y":13.5, "sip_minimum":500,  "nav":24.18,  "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
    {"instrument_id":12, "fund_category_id":8, "name":"Quant ELSS Tax Saver - Direct",     "isin":"INF966L01AX5", "risk_level":"aggressive",   "cagr_1y":25.3, "cagr_3y":22.1, "cagr_5y":26.4, "sip_minimum":500,  "nav":418.92, "nav_date":"2026-02-25", "created_at": ts(NOW - timedelta(days=300))},
]
write_csv("mf_instruments.csv", mf_instruments, [
    "instrument_id","fund_category_id","name","isin","risk_level",
    "cagr_1y","cagr_3y","cagr_5y","sip_minimum","nav","nav_date","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 14. FINANCIAL HEALTH RATINGS  (3 historical snapshots)
# ─────────────────────────────────────────────────────────────────────────────
fhr = [
    {
        "rating_id":1, "user_id":USER_ID, "score":62.5, "rating_label":"Fair",
        "prev_rating_id":"", "rating_delta":"",
        "improvement_tips": json.dumps([
            "Reduce discretionary shopping spend by 15%",
            "Build emergency fund to 3x monthly expense",
            "Start SIP of ₹5,000 in index fund",
        ]),
        "window_months":3, "created_at": ts(NOW - timedelta(days=180)),
    },
    {
        "rating_id":2, "user_id":USER_ID, "score":68.0, "rating_label":"Good",
        "prev_rating_id":1, "rating_delta":5.5,
        "improvement_tips": json.dumps([
            "Increase SIP amount by ₹2,000",
            "Clear credit card outstanding by month end",
            "Add term insurance coverage",
        ]),
        "window_months":3, "created_at": ts(NOW - timedelta(days=90)),
    },
    {
        "rating_id":3, "user_id":USER_ID, "score":72.4, "rating_label":"Good",
        "prev_rating_id":2, "rating_delta":4.4,
        "improvement_tips": json.dumps([
            "Diversify into debt funds for stability",
            "Automate emergency fund top-up",
            "Review and cancel unused subscriptions",
        ]),
        "window_months":3, "created_at": ts(NOW - timedelta(days=10)),
    },
]
write_csv("financial_health_ratings.csv", fhr, [
    "rating_id","user_id","score","rating_label","prev_rating_id",
    "rating_delta","improvement_tips","window_months","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 15. MF RECOMMENDATIONS  (5 rows)
# ─────────────────────────────────────────────────────────────────────────────
mf_recs = [
    {"recommendation_id":1,"user_id":USER_ID,"instrument_id":1,"rating_id":3,
     "expected_cagr_low":12.0,"expected_cagr_high":16.0,
     "reason":"Passive index fund ideal for beginner with moderate risk profile",
     "hard_gates_snapshot": json.dumps({"min_age":18,"kyc_required":True,"min_investment":500}),
     "created_at": ts(NOW - timedelta(days=9))},
    {"recommendation_id":2,"user_id":USER_ID,"instrument_id":5,"rating_id":3,
     "expected_cagr_low":14.0,"expected_cagr_high":19.0,
     "reason":"ELSS saves ₹46,800 tax under 80C and builds long-term wealth",
     "hard_gates_snapshot": json.dumps({"min_age":18,"kyc_required":True,"lock_in_years":3}),
     "created_at": ts(NOW - timedelta(days=9))},
    {"recommendation_id":3,"user_id":USER_ID,"instrument_id":6,"rating_id":3,
     "expected_cagr_low":11.0,"expected_cagr_high":15.0,
     "reason":"Balanced advantage fund reduces volatility for medium-term goals",
     "hard_gates_snapshot": json.dumps({"min_age":18,"kyc_required":True,"min_investment":1000}),
     "created_at": ts(NOW - timedelta(days=9))},
    {"recommendation_id":4,"user_id":USER_ID,"instrument_id":7,"rating_id":2,
     "expected_cagr_low":6.5,"expected_cagr_high":8.0,
     "reason":"Short-term debt fund for emergency fund parking — low risk",
     "hard_gates_snapshot": json.dumps({"min_age":18,"kyc_required":True,"min_investment":1000}),
     "created_at": ts(NOW - timedelta(days=88))},
    {"recommendation_id":5,"user_id":USER_ID,"instrument_id":3,"rating_id":3,
     "expected_cagr_low":15.0,"expected_cagr_high":21.0,
     "reason":"Mid cap exposure recommended given 5+ year investment horizon",
     "hard_gates_snapshot": json.dumps({"min_age":18,"kyc_required":True,"min_investment":500}),
     "created_at": ts(NOW - timedelta(days=9))},
]
write_csv("mf_recommendations.csv", mf_recs, [
    "recommendation_id","user_id","instrument_id","rating_id",
    "expected_cagr_low","expected_cagr_high","reason","hard_gates_snapshot","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 16. MF WATCHLIST  (5 unique entries)
# ─────────────────────────────────────────────────────────────────────────────
mf_watchlist = [
    {"watchlist_id":1,"user_id":USER_ID,"instrument_id":1,"added_at": ts(NOW - timedelta(days=45))},
    {"watchlist_id":2,"user_id":USER_ID,"instrument_id":2,"added_at": ts(NOW - timedelta(days=40))},
    {"watchlist_id":3,"user_id":USER_ID,"instrument_id":4,"added_at": ts(NOW - timedelta(days=30))},
    {"watchlist_id":4,"user_id":USER_ID,"instrument_id":5,"added_at": ts(NOW - timedelta(days=20))},
    {"watchlist_id":5,"user_id":USER_ID,"instrument_id":12,"added_at": ts(NOW - timedelta(days=10))},
]
write_csv("mf_watchlist.csv", mf_watchlist, ["watchlist_id","user_id","instrument_id","added_at"])

# ─────────────────────────────────────────────────────────────────────────────
# 17. RECEIPTS  (15 rows — unique txn_ids)
# ─────────────────────────────────────────────────────────────────────────────
receipt_eligible = [t for t in transactions if t["txn_type"] == "debit" and float(t["amount"]) > 200]
random.shuffle(receipt_eligible)
receipt_eligible = receipt_eligible[:15]

receipts_rows = []
for i, txn in enumerate(receipt_eligible):
    amt = float(txn["amount"])
    matched = random.random() > 0.15
    items = [
        {"name": txn["subcategory"], "qty": 1, "price": round(amt * 0.85, 2)},
        {"name": "GST 18%",          "qty": 1, "price": round(amt * 0.15, 2)},
    ]
    receipts_rows.append({
        "receipt_id":     i + 1,
        "txn_id":         txn["txn_id"],
        "extracted_items": json.dumps(items),
        "total_amount":   amt,
        "amount_matched": "true" if matched else "false",
        "ocr_confidence": round(random.uniform(0.78, 0.97), 4),
        "created_at":     ts(datetime.strptime(txn["txn_timestamp"].replace("Z",""), "%Y-%m-%dT%H:%M:%S") + timedelta(minutes=random.randint(5,60))),
    })
write_csv("receipts.csv", receipts_rows, [
    "receipt_id","txn_id","extracted_items","total_amount","amount_matched","ocr_confidence","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 18. BUDGET PROFILE  (1 row)
# ─────────────────────────────────────────────────────────────────────────────
total_debit = sum(float(t["amount"]) for t in transactions if t["txn_type"] == "debit")
months_covered = 7
baseline_expense = round(total_debit / months_covered, 2)
avg_surplus = round(MONTHLY_INCOME - baseline_expense, 2)
budget_profiles = [{
    "profile_id":             1,
    "user_id":                USER_ID,
    "needs_ratio":            0.52,
    "wants_ratio":            0.28,
    "savings_ratio":          0.20,
    "baseline_expense":       baseline_expense,
    "expense_volatility":     0.18,
    "avg_monthly_surplus":    avg_surplus,
    "safe_investable_amount": round(avg_surplus * 0.6, 2),
    "created_at":             ts(NOW - timedelta(days=180)),
    "updated_at":             ts(NOW - timedelta(days=3)),
}]
write_csv("budget_profiles.csv", budget_profiles, [
    "profile_id","user_id","needs_ratio","wants_ratio","savings_ratio",
    "baseline_expense","expense_volatility","avg_monthly_surplus",
    "safe_investable_amount","created_at","updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 19. SAVINGS POTS  (5 pots linked to goals)
# ─────────────────────────────────────────────────────────────────────────────
savings_pots = [
    {"pot_id":1,"user_id":USER_ID,"goal_id":1,"name":"Emergency Fund Pot",   "target_amount":360000.0,"current_amount":145000.0,"created_at":ts(NOW-timedelta(days=180)),"updated_at":ts(NOW-timedelta(days=5))},
    {"pot_id":2,"user_id":USER_ID,"goal_id":2,"name":"Retirement Savings",   "target_amount":500000.0,"current_amount":285000.0,"created_at":ts(NOW-timedelta(days=365)),"updated_at":ts(NOW-timedelta(days=10))},
    {"pot_id":3,"user_id":USER_ID,"goal_id":3,"name":"Laptop Fund",          "target_amount":120000.0,"current_amount":48000.0, "created_at":ts(NOW-timedelta(days=90)), "updated_at":ts(NOW-timedelta(days=3))},
    {"pot_id":4,"user_id":USER_ID,"goal_id":4,"name":"Goa Trip Savings",     "target_amount":80000.0, "current_amount":32000.0, "created_at":ts(NOW-timedelta(days=60)), "updated_at":ts(NOW-timedelta(days=2))},
    {"pot_id":5,"user_id":USER_ID,"goal_id":5,"name":"Home Down Payment Pot","target_amount":500000.0,"current_amount":125000.0,"created_at":ts(NOW-timedelta(days=270)),"updated_at":ts(NOW-timedelta(days=7))},
]
write_csv("savings_pots.csv", savings_pots, [
    "pot_id","user_id","goal_id","name","target_amount","current_amount","created_at","updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 20. TRANSACTION PATTERNS  (one per category)
# ─────────────────────────────────────────────────────────────────────────────
from collections import defaultdict
import statistics

cat_txns = defaultdict(list)
for t in transactions:
    if t["txn_type"] == "debit":
        cat_txns[t["category"]].append(t)

txn_patterns = []
for pid, (cat, txn_list) in enumerate(cat_txns.items(), start=1):
    amounts   = [float(t["amount"]) for t in txn_list]
    weekdays  = list(set(datetime.strptime(t["txn_timestamp"].replace("Z",""), "%Y-%m-%dT%H:%M:%S").weekday() for t in txn_list))
    merch_ids = list(set(int(t["merchant_id"]) for t in txn_list if t.get("merchant_id")))
    txn_patterns.append({
        "pattern_id":           pid,
        "user_id":              USER_ID,
        "category":             cat,
        "avg_amount":           round(statistics.mean(amounts), 2),
        "std_amount":           round(statistics.stdev(amounts) if len(amounts) > 1 else 0.0, 2),
        "typical_weekdays":     json.dumps(sorted(weekdays)),
        "typical_merchant_ids": json.dumps(sorted(merch_ids[:5])),
        "txn_count":            len(txn_list),
        "created_at":           ts(NOW - timedelta(days=7)),
        "updated_at":           ts(NOW - timedelta(days=1)),
    })
write_csv("transaction_patterns.csv", txn_patterns, [
    "pattern_id","user_id","category","avg_amount","std_amount",
    "typical_weekdays","typical_merchant_ids","txn_count","created_at","updated_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 21. ML MODEL RUNS  (60 rows — categorization + anomaly models)
# ─────────────────────────────────────────────────────────────────────────────
sample_txns = random.sample([t for t in transactions if t["txn_type"] == "debit"], min(60, len([t for t in transactions if t["txn_type"] == "debit"])))
ml_runs = []
cat_labels = ["Food & Dining","Groceries","Shopping","Transport","Healthcare","Utilities","Entertainment","Finance","Investments","Travel"]

for i, txn in enumerate(sample_txns):
    model_type = "categorization_v1" if i % 2 == 0 else "anomaly_v1"
    top5 = random.sample(cat_labels, 5)
    top5_with_scores = {c: round(random.uniform(0.02, 0.35), 4) for c in top5}
    # Ensure output category has highest score
    top5_with_scores[txn["category"]] = round(random.uniform(0.70, 0.97), 4)
    ml_runs.append({
        "run_id":          i + 1,
        "txn_id":          txn["txn_id"],
        "model_name":      model_type,
        "model_version":   "1.2.0" if model_type == "categorization_v1" else "1.1.0",
        "input_text":      txn["clean_description"][:200],
        "output_category": txn["category"],
        "confidence":      txn["confidence_score"],
        "top5_categories": json.dumps(top5_with_scores),
        "latency_ms":      random.randint(8, 95),
        "created_at":      ts(datetime.strptime(txn["txn_timestamp"].replace("Z",""), "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=random.randint(1, 5))),
    })
write_csv("ml_model_runs.csv", ml_runs, [
    "run_id","txn_id","model_name","model_version","input_text",
    "output_category","confidence","top5_categories","latency_ms","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# 22. NOTIFICATION LOG  (one per alert)
# ─────────────────────────────────────────────────────────────────────────────
channels = ["push", "in_app", "email", "sms"]
notif_logs = []
for i, alert in enumerate(alerts):
    sent_dt = datetime.strptime(alert["created_at"].replace("Z",""), "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=random.randint(5, 30))
    delivered_dt = sent_dt + timedelta(seconds=random.randint(1, 10))
    notif_logs.append({
        "notification_id": i + 1,
        "alert_id":        alert["alert_id"],
        "user_id":         USER_ID,
        "channel":         random.choice(channels),
        "sent_at":         ts(sent_dt),
        "delivered_at":    ts(delivered_dt),
        "created_at":      ts(sent_dt),
    })
write_csv("notification_log.csv", notif_logs, [
    "notification_id","alert_id","user_id","channel","sent_at","delivered_at","created_at",
])

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ML FEATURE COMPLETENESS VALIDATION")
print("="*60)
ml_required = ["raw_description", "clean_description", "category", "subcategory",
               "confidence_score", "cat_method", "payment_mode", "is_recurring",
               "anomaly_score", "is_anomalous", "ml_metadata", "balance_after_txn"]
all_ok = True
for col in ml_required:
    missing = sum(1 for t in transactions if not t.get(col) and t.get(col) != 0 and t.get(col) != "false")
    status = "✅" if missing == 0 else f"⚠️  {missing} missing"
    print(f"  {col:35s} {status}")
    if missing > 0:
        all_ok = False

anom_count = sum(1 for t in transactions if t.get("is_anomalous") == "true")
anom_pct   = anom_count / len(transactions) * 100
print(f"\n  Anomaly distribution: {anom_count}/{len(transactions)} = {anom_pct:.1f}%  (target 5–10%)")
print(f"  Anomaly pct ok:       {'✅' if 4 <= anom_pct <= 12 else '⚠️'}")

recurring_count = sum(1 for t in transactions if t.get("is_recurring") == "true")
print(f"  Recurring txns:       {recurring_count} ({recurring_count/len(transactions)*100:.1f}%)")

print(f"\n  Total transactions:        {len(transactions)}")
print(f"  Total merchants:           {len(merchants)}")
print(f"  Total alerts:              {len(alerts)}")
print(f"  Total goals:               {len(goals)}")
print(f"  Total budgets:             {len(budgets)}")
print(f"  Total feedback rows:       {len(feedbacks)}")
print(f"  Total audit logs:          {len(audit_logs)}")
print(f"  Total cat mappings:        {len(cat_mappings)}")
print(f"  Total currencies:          {len(currencies)}")
print(f"  Total fund_categories:     {len(fund_categories)}")
print(f"  Total mf_instruments:      {len(mf_instruments)}")
print(f"  Total mf_recommendations:  {len(mf_recs)}")
print(f"  Total mf_watchlist:        {len(mf_watchlist)}")
print(f"  Total receipts:            {len(receipts_rows)}")
print(f"  Total budget_profiles:     {len(budget_profiles)}")
print(f"  Total savings_pots:        {len(savings_pots)}")
print(f"  Total txn_patterns:        {len(txn_patterns)}")
print(f"  Total ml_model_runs:       {len(ml_runs)}")
print(f"  Total financial_ratings:   {len(fhr)}")
print(f"  Total notification_log:    {len(notif_logs)}")
print(f"\n  CSV files total:           22 / 22 tables")

print(f"\n  All ML checks passed: {'✅  YES' if all_ok else '❌  NO — see above'}")
print("="*60)
print(f"\n📁  CSVs written to: {OUTPUT_DIR.resolve()}")
