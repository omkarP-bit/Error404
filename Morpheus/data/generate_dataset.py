"""
data/generate_dataset.py
========================
Generates finance_ml_dataset.csv with 2000+ rows.

All required columns are computed programmatically:
  txn_id, user_id, raw_description, cleaned_description,
  merchant_name, amount, txn_type, payment_mode, category,
  subcategory, confidence_score, txn_timestamp, month,
  day_of_week, hour, is_recurring, avg_spend_per_category,
  spend_std_dev, monthly_surplus, expense_volatility,
  balance_after_txn, user_corrected_label

Run:  python data/generate_dataset.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Output path ───────────────────────────────────────────────────────────────
OUTPUT_PATH = Path(__file__).parent / "finance_ml_dataset.csv"

# ── Constants ─────────────────────────────────────────────────────────────────
NUM_USERS = 10
NUM_TRANSACTIONS = 2200  # ≥ 2000

# ── Indian Merchants & Categories ─────────────────────────────────────────────
MERCHANT_CATALOG = [
    # (raw_name, clean_name, category, subcategory, typical_amount_range)
    ("SWIGGY ORDER*",          "Swiggy",          "Food & Dining",  "Food Delivery",   (80,  800)),
    ("ZOMATO*",                "Zomato",           "Food & Dining",  "Food Delivery",   (60,  700)),
    ("BigBasket",              "BigBasket",        "Groceries",      "Online Grocery",  (200, 3000)),
    ("GROFERS/BLINKIT",        "Blinkit",          "Groceries",      "Quick Commerce",  (150, 1500)),
    ("Jio Recharge",           "Jio",              "Utilities",      "Mobile Recharge", (199, 999)),
    ("Airtel Xstream",         "Airtel",           "Utilities",      "Broadband",       (299, 1199)),
    ("NETFLIX INDIA",          "Netflix",          "Entertainment",  "Streaming",       (149, 649)),
    ("AMAZON PAY*",            "Amazon",           "Shopping",       "E-commerce",      (100, 8000)),
    ("FLIPKART INTERNET",      "Flipkart",         "Shopping",       "E-commerce",      (100, 6000)),
    ("UBER INDIA",             "Uber",             "Transport",      "Cab",             (50,  600)),
    ("OLA CABS*",              "Ola",              "Transport",      "Cab",             (40,  500)),
    ("PETROL PUMP HPCL",       "HPCL",             "Transport",      "Fuel",            (500, 3000)),
    ("APOLLO PHARMACY",        "Apollo Pharmacy",  "Healthcare",     "Medicines",       (100, 2000)),
    ("PRACTO CONSULT",         "Practo",           "Healthcare",     "Consultation",    (200, 1200)),
    ("HDFC BANK EMI",          "HDFC EMI",         "Finance",        "Loan EMI",        (2000,25000)),
    ("SBI MUTUAL FUND SIP",    "SBI MF",           "Investments",    "Mutual Fund",     (500, 10000)),
    ("ZERODHA*",               "Zerodha",          "Investments",    "Stock Trading",   (1000,50000)),
    ("DUNZO DELIVERY",         "Dunzo",            "Groceries",      "Quick Commerce",  (80,  600)),
    ("PAYTM WALLET*",          "Paytm",            "Finance",        "Wallet Top-up",   (100, 5000)),
    ("IRCTC E-TICKET",         "IRCTC",            "Travel",         "Train Tickets",   (200, 3000)),
    ("MAKEMYTRIP",             "MakeMyTrip",       "Travel",         "Flight/Hotel",    (1500,25000)),
    ("RELIANCE FRESH*",        "Reliance Fresh",   "Groceries",      "Supermarket",     (200, 2500)),
    ("D-MART AVENUE",          "DMart",            "Groceries",      "Supermarket",     (300, 4000)),
    ("SPOTIFY INDIA",          "Spotify",          "Entertainment",  "Music Streaming", (59,  189)),
    ("HOTSTAR PREMIUM",        "Hotstar",          "Entertainment",  "Streaming",       (299, 1499)),
    ("BYJU'S SUBSCRIPTION",    "Byjus",            "Education",      "Online Learning", (1000,5000)),
    ("UNACADEMY*",             "Unacademy",        "Education",      "Online Learning", (500, 3000)),
    ("SALARY CREDIT",          "Employer",         "Income",         "Salary",          (30000,150000)),
    ("FREELANCE PAYMENT",      "Freelance",        "Income",         "Freelance",       (5000, 80000)),
    ("BANK INTEREST",          "Bank",             "Income",         "Interest",        (50,  2000)),
]

PAYMENT_MODES = ["UPI", "Net Banking", "Debit Card", "Credit Card", "Wallet", "NEFT", "IMPS", "Cash"]

# ── User profiles ─────────────────────────────────────────────────────────────
USER_PROFILES = [
    {"user_id": i + 1, "monthly_income": inc, "risk": risk}
    for i, (inc, risk) in enumerate([
        (25000,  "conservative"),
        (45000,  "conservative"),
        (60000,  "moderate"),
        (75000,  "moderate"),
        (90000,  "moderate"),
        (120000, "aggressive"),
        (150000, "aggressive"),
        (200000, "aggressive"),
        (35000,  "conservative"),
        (55000,  "moderate"),
    ])
]


def _clean_description(raw: str) -> str:
    """Minimal normalisation of raw merchant description."""
    clean = raw.strip().lower()
    for ch in ["*", "/", "_", "-"]:
        clean = clean.replace(ch, " ")
    return " ".join(clean.split())


def _jitter_amount(base_range: tuple, is_income: bool = False) -> float:
    lo, hi = base_range
    amount = random.uniform(lo, hi)
    # Add slight noise
    noise = random.gauss(0, (hi - lo) * 0.05)
    amount = max(1.0, amount + noise)
    return round(amount, 2)


def generate_transactions() -> pd.DataFrame:
    rows = []
    start_date = datetime(2024, 1, 1)
    end_date   = datetime(2025, 12, 31)
    date_range_days = (end_date - start_date).days

    txn_id = 1
    for _ in range(NUM_TRANSACTIONS):
        user  = random.choice(USER_PROFILES)
        mcat  = random.choice(MERCHANT_CATALOG)

        raw_name, clean_name, category, subcategory, amt_range = mcat
        is_income = category == "Income"

        txn_type    = "credit" if is_income else random.choices(
            ["debit", "debit", "debit", "transfer", "refund"],
            weights=[70, 70, 70, 15, 5]
        )[0]

        amount      = _jitter_amount(amt_range, is_income)
        timestamp   = start_date + timedelta(days=random.randint(0, date_range_days),
                                             hours=random.randint(6, 23),
                                             minutes=random.randint(0, 59))
        payment_mode = random.choice(PAYMENT_MODES)
        is_recurring = clean_name in ["Netflix", "Spotify", "Hotstar", "Jio",
                                       "Airtel", "SBI MF", "HDFC EMI", "Unacademy"]
        confidence   = round(random.uniform(0.70, 1.0), 4)
        # Some transactions intentionally below threshold
        if random.random() < 0.08:
            confidence = round(random.uniform(0.50, 0.84), 4)

        rows.append({
            "txn_id":          txn_id,
            "user_id":         user["user_id"],
            "raw_description": raw_name + " " + str(random.randint(1000, 9999)),
            "merchant_name":   clean_name,
            "amount":          amount,
            "txn_type":        txn_type,
            "payment_mode":    payment_mode,
            "category":        category,
            "subcategory":     subcategory,
            "confidence_score": confidence,
            "txn_timestamp":   timestamp,
            "is_recurring":    int(is_recurring),
            "monthly_income":  user["monthly_income"],
        })
        txn_id += 1

    df = pd.DataFrame(rows)
    df = df.sort_values(["user_id", "txn_timestamp"]).reset_index(drop=True)
    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all programmatically derived features as required by spec."""
    df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    df["month"]         = df["txn_timestamp"].dt.month
    df["day_of_week"]   = df["txn_timestamp"].dt.dayofweek   # 0=Mon
    df["hour"]          = df["txn_timestamp"].dt.hour

    # ── cleaned_description ───────────────────────────────────────────────
    df["cleaned_description"] = df["raw_description"].apply(_clean_description)

    # ── avg_spend_per_category (per user×category) ────────────────────────
    avg_cat = (
        df[df["txn_type"] == "debit"]
        .groupby(["user_id", "category"])["amount"]
        .transform("mean")
    )
    df["avg_spend_per_category"] = avg_cat.fillna(0).round(2)

    # ── spend_std_dev (per user×category) ─────────────────────────────────
    std_cat = (
        df[df["txn_type"] == "debit"]
        .groupby(["user_id", "category"])["amount"]
        .transform("std")
    )
    df["spend_std_dev"] = std_cat.fillna(0).round(2)

    # ── monthly_surplus (income - debit per user per month) ───────────────
    df["year_month"] = df["txn_timestamp"].dt.to_period("M")
    monthly_income   = df[df["txn_type"] == "credit"].groupby(
        ["user_id", "year_month"])["amount"].sum().reset_index()
    monthly_income.columns = ["user_id", "year_month", "month_income"]
    monthly_expense  = df[df["txn_type"] == "debit"].groupby(
        ["user_id", "year_month"])["amount"].sum().reset_index()
    monthly_expense.columns = ["user_id", "year_month", "month_expense"]

    monthly = pd.merge(monthly_income, monthly_expense, on=["user_id","year_month"], how="outer").fillna(0)
    monthly["monthly_surplus"] = monthly["month_income"] - monthly["month_expense"]

    df = df.merge(monthly[["user_id","year_month","monthly_surplus"]],
                  on=["user_id","year_month"], how="left")
    df["monthly_surplus"] = df["monthly_surplus"].fillna(0).round(2)

    # ── expense_volatility (std dev of monthly expense per user) ──────────
    exp_vol = monthly_expense.groupby("user_id")["month_expense"].std().reset_index()
    exp_vol.columns = ["user_id", "expense_volatility"]
    df = df.merge(exp_vol, on="user_id", how="left")
    df["expense_volatility"] = df["expense_volatility"].fillna(0).round(2)

    # ── balance_after_txn (running balance per user) ──────────────────────
    df = df.sort_values(["user_id", "txn_timestamp"]).reset_index(drop=True)
    df["signed_amount"] = df.apply(
        lambda r: r["amount"] if r["txn_type"] == "credit" else -r["amount"], axis=1
    )
    df["balance_after_txn"] = df.groupby("user_id")["signed_amount"].cumsum().round(2)

    # ── user_corrected_label (20% are user-corrected) ─────────────────────
    rng = np.random.default_rng(SEED)
    mask = rng.random(len(df)) < 0.20
    df["user_corrected_label"] = df["category"].where(~mask, other="")
    # Fill corrected with an alternate category for flagged rows
    alt_cats = ["Shopping", "Food & Dining", "Utilities", "Transport", "Groceries"]
    corrected = df[mask]["category"].apply(
        lambda c: random.choice([x for x in alt_cats if x != c] or alt_cats)
    )
    df.loc[mask, "user_corrected_label"] = corrected.values

    # ── Drop intermediate columns ──────────────────────────────────────────
    df = df.drop(columns=["year_month", "signed_amount", "monthly_income"], errors="ignore")

    return df


def main():
    print("🔄  Generating finance_ml_dataset.csv …")
    df = generate_transactions()
    df = add_derived_features(df)

    # ── Reorder columns to spec ────────────────────────────────────────────
    ordered_cols = [
        "txn_id", "user_id", "raw_description", "cleaned_description",
        "merchant_name", "amount", "txn_type", "payment_mode",
        "category", "subcategory", "confidence_score", "txn_timestamp",
        "month", "day_of_week", "hour", "is_recurring",
        "avg_spend_per_category", "spend_std_dev", "monthly_surplus",
        "expense_volatility", "balance_after_txn", "user_corrected_label",
    ]
    df = df[ordered_cols]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅  Saved {len(df):,} rows → {OUTPUT_PATH}")
    print(f"    Columns : {list(df.columns)}")
    print(f"    Date range: {df['txn_timestamp'].min()} → {df['txn_timestamp'].max()}")
    print(f"    Users  : {df['user_id'].nunique()}")
    print(f"    Categories: {df['category'].unique().tolist()}")


if __name__ == "__main__":
    main()
