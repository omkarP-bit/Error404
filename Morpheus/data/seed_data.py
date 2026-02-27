"""
data/seed_data.py
=================
Seeds the SQLite database with:
  • 10  Users  (varied income bands)
  • 5   Accounts per user  (50 total)
  • 20  Merchants  (Indian realistic)
  • 2000+ Transactions
  • 200  UserFeedback corrections
  • 50   Alerts
  • 5    Goals per user
  • 3    Budgets per user

Also calls generate_dataset.py to produce finance_ml_dataset.csv
if it does not already exist.

Run:  python data/seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import random
import numpy as np
from datetime import datetime, timedelta, date
from pathlib import Path

# ── Imports after sys.path fix ────────────────────────────────────────────────
from app.database import Base, engine, SessionLocal
from app.models import (
    User, Account, Merchant, Transaction, UserFeedback,
    CategoryMapping, Alert, AuditLog, Goal, Budget,
    IncomeType, RiskProfile, KYCStatus, AccountType, TxnType,
    FeedbackSource, MappingSource, AlertType, AlertSeverity,
    AlertStatus, ActorType, GoalStatus, BudgetPeriod,
)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Dataset generation ────────────────────────────────────────────────────────
DATASET_PATH = Path(__file__).parent / "finance_ml_dataset.csv"


def ensure_dataset():
    if not DATASET_PATH.exists():
        print("📊  Dataset not found — generating …")
        from data.generate_dataset import main as gen_main
        gen_main()
    else:
        print(f"📊  Dataset already exists at {DATASET_PATH}")


# ── Indian Merchants (20 exactly) ─────────────────────────────────────────────
MERCHANTS_DATA = [
    ("SWIGGY ORDER* 1234",     "Swiggy",         "Food & Dining"),
    ("ZOMATO* 5678",           "Zomato",          "Food & Dining"),
    ("BigBasket Online",       "BigBasket",       "Groceries"),
    ("BLINKIT APP*",           "Blinkit",         "Groceries"),
    ("Jio Prepaid Recharge",   "Jio",             "Utilities"),
    ("Airtel Broadband",       "Airtel",          "Utilities"),
    ("NETFLIX INDIA PVT LTD",  "Netflix",         "Entertainment"),
    ("AMAZON PAY* SELLER",     "Amazon",          "Shopping"),
    ("FLIPKART INTERNET PVT",  "Flipkart",        "Shopping"),
    ("UBER INDIA TECH*",       "Uber",            "Transport"),
    ("OLA CABS PVT LTD",       "Ola",             "Transport"),
    ("HPCL PETROL PUMP",       "HPCL",            "Transport"),
    ("APOLLO PHARMACY LTD",    "Apollo Pharmacy", "Healthcare"),
    ("PRACTO ONLINE CONSULT",  "Practo",          "Healthcare"),
    ("HDFC BANK LOAN EMI",     "HDFC EMI",        "Finance"),
    ("SBI MUTUAL FUND SIP",    "SBI MF",          "Investments"),
    ("ZERODHA BROKING LTD",    "Zerodha",         "Investments"),
    ("IRCTC E-TICKET PNR",     "IRCTC",           "Travel"),
    ("MAKEMYTRIP ONLINE*",     "MakeMyTrip",      "Travel"),
    ("RELIANCE FRESH STORE",   "Reliance Fresh",  "Groceries"),
]

# ── Spend config per merchant ─────────────────────────────────────────────────
MERCHANT_SPEND = {
    "Swiggy":         (80,   800),
    "Zomato":         (60,   700),
    "BigBasket":      (200,  3000),
    "Blinkit":        (150,  1500),
    "Jio":            (199,  999),
    "Airtel":         (299,  1199),
    "Netflix":        (149,  649),
    "Amazon":         (100,  8000),
    "Flipkart":       (100,  6000),
    "Uber":           (50,   600),
    "Ola":            (40,   500),
    "HPCL":           (500,  3000),
    "Apollo Pharmacy":(100,  2000),
    "Practo":         (200,  1200),
    "HDFC EMI":       (2000, 25000),
    "SBI MF":         (500,  10000),
    "Zerodha":        (1000, 50000),
    "IRCTC":          (200,  3000),
    "MakeMyTrip":     (1500, 25000),
    "Reliance Fresh": (200,  2500),
}

SUBCATEGORY_MAP = {
    "Food & Dining":  ["Food Delivery", "Restaurant", "Cafe"],
    "Groceries":      ["Online Grocery", "Quick Commerce", "Supermarket"],
    "Utilities":      ["Mobile Recharge", "Broadband", "Electricity", "Gas"],
    "Entertainment":  ["Streaming", "Movies", "Gaming"],
    "Shopping":       ["E-commerce", "Clothes", "Electronics"],
    "Transport":      ["Cab", "Fuel", "Metro", "Auto"],
    "Healthcare":     ["Medicines", "Consultation", "Insurance"],
    "Finance":        ["Loan EMI", "Credit Card", "Wallet Top-up"],
    "Investments":    ["Mutual Fund", "Stock Trading", "FD"],
    "Travel":         ["Train Tickets", "Flight/Hotel", "Bus"],
    "Education":      ["Online Learning", "Books", "Tuition"],
    "Income":         ["Salary", "Freelance", "Interest"],
}

INSTITUTIONS = [
    "HDFC Bank", "SBI", "ICICI Bank", "Axis Bank",
    "Kotak Bank", "Yes Bank", "Bank of Baroda", "PNB",
]

PAYMENT_MODES = ["UPI", "Net Banking", "Debit Card", "Credit Card", "Wallet", "NEFT"]

GOAL_NAMES = [
    "Emergency Fund", "Home Down Payment", "Vacation to Europe",
    "New Car Purchase", "Retirement Corpus", "Child's Education",
    "Laptop Upgrade", "Wedding Fund", "Gold Investment",
    "Side Business Capital",
]

BUDGET_CATEGORIES = [
    "Food & Dining", "Groceries", "Shopping", "Transport",
    "Entertainment", "Utilities", "Healthcare", "Travel",
]


# ── Helper ────────────────────────────────────────────────────────────────────

def rand_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def create_tables():
    """Create all tables via SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)
    print("✅  Tables created (or already exist)")


def seed_users(session) -> list[User]:
    income_configs = [
        (25_000,  IncomeType.SALARIED,      RiskProfile.CONSERVATIVE, KYCStatus.VERIFIED),
        (45_000,  IncomeType.SALARIED,      RiskProfile.CONSERVATIVE, KYCStatus.VERIFIED),
        (60_000,  IncomeType.SALARIED,      RiskProfile.MODERATE,     KYCStatus.VERIFIED),
        (75_000,  IncomeType.FREELANCE,     RiskProfile.MODERATE,     KYCStatus.VERIFIED),
        (90_000,  IncomeType.SELF_EMPLOYED, RiskProfile.MODERATE,     KYCStatus.VERIFIED),
        (120_000, IncomeType.BUSINESS,      RiskProfile.AGGRESSIVE,   KYCStatus.VERIFIED),
        (150_000, IncomeType.SALARIED,      RiskProfile.AGGRESSIVE,   KYCStatus.VERIFIED),
        (200_000, IncomeType.BUSINESS,      RiskProfile.AGGRESSIVE,   KYCStatus.VERIFIED),
        (35_000,  IncomeType.SALARIED,      RiskProfile.CONSERVATIVE, KYCStatus.PENDING),
        (55_000,  IncomeType.FREELANCE,     RiskProfile.MODERATE,     KYCStatus.VERIFIED),
    ]
    names  = ["Aarav Sharma","Priya Nair","Rohit Verma","Anita Patel",
              "Suresh Kumar","Deepika Rao","Vikram Mehta","Kavya Reddy",
              "Arjun Singh","Sneha Joshi"]
    phones = [f"+91 9{random.randint(100000000,999999999)}" for _ in range(10)]

    users = []
    for i, (income, itype, risk, kyc) in enumerate(income_configs):
        u = User(
            auth_uid=str(uuid.uuid4()),
            name=names[i],
            email=f"user{i+1}@finapp.demo",
            phone=phones[i],
            monthly_income=income,
            income_type=itype,
            risk_profile=risk,
            kyc_status=kyc,
            created_at=datetime(2024, 1, 1) + timedelta(days=i * 10),
        )
        session.add(u)
    session.flush()
    users = session.query(User).order_by(User.user_id).all()
    print(f"✅  Seeded {len(users)} users")
    return users


def seed_accounts(session, users: list[User]) -> list[Account]:
    account_types = [
        AccountType.SALARY,
        AccountType.SAVINGS,
        AccountType.CURRENT,
        AccountType.CREDIT,
        AccountType.WALLET,
    ]
    accounts = []
    for user in users:
        for atype in account_types:
            balance = round(random.uniform(5_000, 200_000), 2)
            a = Account(
                user_id=user.user_id,
                institution_name=random.choice(INSTITUTIONS),
                account_type=atype,
                current_balance=balance,
                created_at=user.created_at + timedelta(days=1),
            )
            session.add(a)
    session.flush()
    accounts = session.query(Account).all()
    print(f"✅  Seeded {len(accounts)} accounts")
    return accounts


def seed_merchants(session) -> list[Merchant]:
    merchants = []
    for raw, clean, cat in MERCHANTS_DATA:
        m = Merchant(
            raw_name=raw,
            clean_name=clean,
            default_category=cat,
            created_at=datetime(2023, 12, 1),
        )
        session.add(m)
    session.flush()
    merchants = session.query(Merchant).all()
    print(f"✅  Seeded {len(merchants)} merchants")
    return merchants


def seed_transactions(
    session, users: list[User], accounts: list[Account], merchants: list[Merchant]
) -> list[Transaction]:
    """Generate 2000+ transactions with realistic Indian patterns."""
    start = datetime(2024, 1, 1, 8, 0, 0)
    end   = datetime(2025, 12, 31, 23, 59, 0)

    # Build user→accounts lookup
    user_accounts: dict[int, list[Account]] = {}
    for a in accounts:
        user_accounts.setdefault(a.user_id, []).append(a)

    # Running balance per account
    balances: dict[int, float] = {a.account_id: a.current_balance for a in accounts}

    transactions = []
    target_count = 2200

    for _ in range(target_count):
        user    = random.choice(users)
        user_accs = user_accounts[user.user_id]
        account = random.choice(user_accs)
        merchant = random.choice(merchants)

        cat     = merchant.default_category
        subs    = SUBCATEGORY_MAP.get(cat, ["General"])
        subcat  = random.choice(subs)

        lo, hi  = MERCHANT_SPEND.get(merchant.clean_name, (100, 2000))
        amount  = round(random.uniform(lo, hi), 2)

        is_income = cat == "Income"
        if is_income:
            txn_type = TxnType.CREDIT
        else:
            txn_type = random.choices(
                [TxnType.DEBIT, TxnType.TRANSFER, TxnType.REFUND],
                weights=[85, 10, 5]
            )[0]

        # Update running balance
        if txn_type == TxnType.CREDIT:
            balances[account.account_id] = round(
                balances[account.account_id] + amount, 2
            )
        else:
            balances[account.account_id] = round(
                balances[account.account_id] - amount, 2
            )

        is_recurring = merchant.clean_name in [
            "Netflix", "Spotify", "Hotstar", "Jio", "Airtel",
            "SBI MF", "HDFC EMI",
        ]
        confidence = round(random.uniform(0.72, 1.0), 4)
        if random.random() < 0.07:
            confidence = round(random.uniform(0.50, 0.84), 4)

        t = Transaction(
            user_id=user.user_id,
            account_id=account.account_id,
            merchant_id=merchant.merchant_id,
            amount=amount,
            txn_type=txn_type,
            category=cat,
            subcategory=subcat,
            raw_description=f"{merchant.raw_name} {random.randint(1000,9999)}",
            payment_mode=random.choice(PAYMENT_MODES),
            user_verified=False,
            is_recurring=is_recurring,
            confidence_score=confidence,
            balance_after_txn=balances[account.account_id],
            txn_timestamp=rand_date(start, end),
        )
        session.add(t)
        transactions.append(t)

    session.flush()
    all_txns = session.query(Transaction).all()
    print(f"✅  Seeded {len(all_txns)} transactions")
    return all_txns


def seed_feedback(session, transactions: list[Transaction]) -> None:
    """200 user-feedback corrections targeting low-confidence transactions."""
    low_conf = [t for t in transactions if t.confidence_score and t.confidence_score < 0.85]
    sample   = random.sample(low_conf, min(200, len(low_conf)))

    for txn in sample:
        cats = list(SUBCATEGORY_MAP.keys())
        new_cat  = random.choice([c for c in cats if c != txn.category])
        new_sub  = random.choice(SUBCATEGORY_MAP.get(new_cat, ["General"]))
        fb = UserFeedback(
            txn_id=txn.txn_id,
            corrected_category=new_cat,
            corrected_subcategory=new_sub,
            source=FeedbackSource.USER_UI,
            created_at=txn.txn_timestamp + timedelta(hours=random.randint(1, 48)),
        )
        session.add(fb)
    session.flush()
    print(f"✅  Seeded 200 user feedback records")


def seed_category_mappings(
    session, users: list[User], merchants: list[Merchant]
) -> None:
    for user in users:
        for merchant in random.sample(merchants, k=min(8, len(merchants))):
            cat  = merchant.default_category
            sub  = random.choice(SUBCATEGORY_MAP.get(cat, ["General"]))
            cm = CategoryMapping(
                user_id=user.user_id,
                merchant_id=merchant.merchant_id,
                category=cat,
                subcategory=sub,
                confidence=round(random.uniform(0.85, 1.0), 4),
                source=MappingSource.USER,
            )
            session.add(cm)
    session.flush()
    print("✅  Seeded category mappings")


def seed_alerts(session, users: list[User], transactions: list[Transaction]) -> None:
    """Seed 50 alerts across all users."""
    txn_sample = random.sample(transactions, min(50, len(transactions)))
    alert_types = list(AlertType)
    severities  = list(AlertSeverity)

    for txn in txn_sample:
        atype = random.choice(alert_types)
        sev   = random.choice(severities)
        alert = Alert(
            user_id=txn.user_id,
            txn_id=txn.txn_id,
            alert_type=atype,
            severity=sev,
            status=random.choice([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            message=(
                f"Detected {atype.value} on ₹{txn.amount:.0f} "
                f"transaction at {txn.category}"
            ),
            created_at=txn.txn_timestamp + timedelta(minutes=random.randint(1, 60)),
        )
        session.add(alert)
    session.flush()
    print("✅  Seeded 50 alerts")


def seed_goals(session, users: list[User]) -> None:
    """5 goals per user."""
    for user in users:
        goals_for_user = random.sample(GOAL_NAMES, 5)
        for gname in goals_for_user:
            target  = round(random.uniform(50_000, 1_000_000), 2)
            current = round(random.uniform(0, target * 0.6), 2)
            months  = random.randint(6, 60)
            deadline_dt = date.today() + timedelta(days=months * 30)
            g = Goal(
                user_id=user.user_id,
                goal_name=gname,
                target_amount=target,
                current_amount=current,
                deadline=deadline_dt,
                status=GoalStatus.ACTIVE,
                feasibility_score=round(random.uniform(20, 95), 1),
                created_at=datetime(2024, 1, 1) + timedelta(days=random.randint(0, 30)),
            )
            session.add(g)
    session.flush()
    print("✅  Seeded 5 goals × 10 users = 50 goals")


def seed_budgets(session, users: list[User]) -> None:
    """3 budget profiles per user."""
    for user in users:
        cats = random.sample(BUDGET_CATEGORIES, 3)
        for cat in cats:
            limit   = round(random.uniform(3_000, 25_000), 2)
            spent   = round(random.uniform(0, limit * 1.1), 2)
            b = Budget(
                user_id=user.user_id,
                category=cat,
                limit_amount=limit,
                spent_amount=spent,
                period=BudgetPeriod.MONTHLY,
                is_active=True,
            )
            session.add(b)
    session.flush()
    print("✅  Seeded 3 budgets × 10 users = 30 budgets")


def seed_audit_logs(session, users: list[User]) -> None:
    actions = [
        "CREATE_TRANSACTION", "UPDATE_CATEGORY", "ADD_FEEDBACK",
        "LOGIN", "CREATE_GOAL", "UPDATE_BUDGET",
    ]
    for user in users:
        for _ in range(random.randint(5, 15)):
            log = AuditLog(
                actor_id=user.user_id,
                actor_type=ActorType.USER,
                action=random.choice(actions),
                resource_type="transaction",
                resource_id=random.randint(1, 2200),
                old_value={"category": "Shopping"},
                new_value={"category": "Groceries"},
                created_at=datetime(2024, random.randint(1, 12), random.randint(1, 28)),
            )
            session.add(log)
    session.flush()
    print("✅  Seeded audit logs")


def main():
    print("\n🚀  Personal Finance Manager — DB Seed Script")
    print("=" * 55)

    # Ensure CSV dataset exists
    ensure_dataset()

    # Create tables
    create_tables()

    with SessionLocal() as session:
        # Check if already seeded
        if session.query(User).count() > 0:
            print("⚠️   Database already seeded. Skipping.")
            return

        try:
            users       = seed_users(session)
            accounts    = seed_accounts(session, users)
            merchants   = seed_merchants(session)
            transactions = seed_transactions(session, users, accounts, merchants)
            seed_feedback(session, transactions)
            seed_category_mappings(session, users, merchants)
            seed_alerts(session, users, transactions)
            seed_goals(session, users)
            seed_budgets(session, users)
            seed_audit_logs(session, users)

            session.commit()
            print("\n🎉  Seed complete!")
            print(f"    Users        : {session.query(User).count()}")
            print(f"    Accounts     : {session.query(Account).count()}")
            print(f"    Merchants    : {session.query(Merchant).count()}")
            print(f"    Transactions : {session.query(Transaction).count()}")
            print(f"    Alerts       : {session.query(Alert).count()}")
            print(f"    Goals        : {session.query(Goal).count()}")
            print(f"    Budgets      : {session.query(Budget).count()}")

        except Exception as exc:
            session.rollback()
            print(f"❌  Seed failed: {exc}")
            raise


if __name__ == "__main__":
    main()
