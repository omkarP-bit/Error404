"""
app/models/__init__.py
======================
Central model registry — import all models here so that:
  1. SQLAlchemy mapper sees every table before create_all / Alembic.
  2. Application code can import from a single location.
"""

from app.models.enums import (          # noqa: F401
    IncomeType, RiskProfile, KYCStatus, AccountType, TxnType,
    FeedbackSource, MappingSource, AlertType, AlertSeverity,
    AlertStatus, ActorType, GoalStatus, BudgetPeriod,
)

# ── Core tables (10) ─────────────────────────────────────────────────────────
from app.models.user import User                        # noqa: F401
from app.models.account import Account                  # noqa: F401
from app.models.merchant import Merchant                # noqa: F401
from app.models.transaction import Transaction          # noqa: F401
from app.models.feedback import UserFeedback            # noqa: F401
from app.models.category_mapping import CategoryMapping # noqa: F401
from app.models.alert import Alert                      # noqa: F401
from app.models.audit_log import AuditLog               # noqa: F401
from app.models.goal import Goal                        # noqa: F401
from app.models.budget import Budget                    # noqa: F401

# ── Extended v2.0 tables (12) ────────────────────────────────────────────────
from app.models.currency import Currency                                    # noqa: F401
from app.models.fund_category import FundCategory                          # noqa: F401
from app.models.receipt import Receipt                                      # noqa: F401
from app.models.budget_profile import BudgetProfile                        # noqa: F401
from app.models.savings_pot import SavingsPot                              # noqa: F401
from app.models.transaction_pattern import TransactionPattern              # noqa: F401
from app.models.ml_model_run import MLModelRun                             # noqa: F401
from app.models.financial_health_rating import FinancialHealthRating       # noqa: F401
from app.models.mf_instrument import MFInstrument                         # noqa: F401
from app.models.mf_recommendation import MFRecommendation                 # noqa: F401
from app.models.mf_watchlist import MFWatchlist                           # noqa: F401
from app.models.notification_log import NotificationLog                    # noqa: F401
from app.models.savings_activity import SavingsActivity                    # noqa: F401

__all__ = [
    # Core
    "User", "Account", "Merchant", "Transaction",
    "UserFeedback", "CategoryMapping", "Alert", "AuditLog",
    "Goal", "Budget",
    # Extended v2.0
    "Currency", "FundCategory", "Receipt", "BudgetProfile",
    "SavingsPot", "TransactionPattern", "MLModelRun",
    "FinancialHealthRating", "MFInstrument", "MFRecommendation",
    "MFWatchlist", "NotificationLog", "SavingsActivity",
    # Enums
    "IncomeType", "RiskProfile", "KYCStatus", "AccountType",
    "TxnType", "FeedbackSource", "MappingSource",
    "AlertType", "AlertSeverity", "AlertStatus",
    "ActorType", "GoalStatus", "BudgetPeriod",
]
