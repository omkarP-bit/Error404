"""
app/models/enums.py
===================
All shared Python Enums used across ORM models.
Centralised here to avoid circular imports.
"""

import enum


class IncomeType(str, enum.Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    FREELANCE = "freelance"
    BUSINESS = "business"
    RETIRED = "retired"


class RiskProfile(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class AccountType(str, enum.Enum):
    SAVINGS = "savings"
    CURRENT = "current"
    SALARY = "salary"
    CREDIT = "credit"
    WALLET = "wallet"


class TxnType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    REFUND = "refund"


class FeedbackSource(str, enum.Enum):
    USER_UI = "user_ui"
    OCR = "ocr"
    PDF = "pdf"
    AUTO_CORRECTION = "auto_correction"


class MappingSource(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ML_MODEL = "ml_model"
    OCR = "ocr"


class AlertType(str, enum.Enum):
    ANOMALY = "anomaly"
    BUDGET_BREACH = "budget_breach"
    LARGE_TRANSACTION = "large_transaction"
    UNUSUAL_PATTERN = "unusual_pattern"
    GOAL_AT_RISK = "goal_at_risk"
    DUPLICATE_CHARGE = "duplicate_charge"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ActorType(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    ML_MODEL = "ml_model"
    ADMIN = "admin"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class BudgetPeriod(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
