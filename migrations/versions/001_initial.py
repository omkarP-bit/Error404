"""Initial schema — all tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-25
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("auth_uid", sa.String(36), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("monthly_income", sa.Float, nullable=False, server_default="0"),
        sa.Column("income_type", sa.String(20), nullable=False, server_default="salaried"),
        sa.Column("risk_profile", sa.String(20), nullable=False, server_default="moderate"),
        sa.Column("kyc_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── accounts ────────────────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_name", sa.String(255), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False, server_default="savings"),
        sa.Column("current_balance", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    # ── merchants ───────────────────────────────────────────────────────────
    op.create_table(
        "merchants",
        sa.Column("merchant_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("raw_name", sa.String(500), nullable=False),
        sa.Column("clean_name", sa.String(255), nullable=False),
        sa.Column("default_category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_merchants_clean_name", "merchants", ["clean_name"])

    # ── transactions ────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("txn_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_id", sa.Integer, sa.ForeignKey("merchants.merchant_id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("txn_type", sa.String(20), nullable=False, server_default="debit"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("raw_description", sa.String(500), nullable=True),
        sa.Column("payment_mode", sa.String(50), nullable=True),
        sa.Column("user_verified", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("balance_after_txn", sa.Float, nullable=True),
        sa.Column("txn_timestamp", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_txn_user_id", "transactions", ["user_id"])
    op.create_index("ix_txn_timestamp", "transactions", ["txn_timestamp"])
    op.create_index("ix_txn_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_txn_category", "transactions", ["category"])
    op.create_index("ix_txn_amount", "transactions", ["amount"])

    # ── user_feedback ───────────────────────────────────────────────────────
    op.create_table(
        "user_feedback",
        sa.Column("feedback_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("txn_id", sa.Integer, sa.ForeignKey("transactions.txn_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("corrected_category", sa.String(100), nullable=False),
        sa.Column("corrected_subcategory", sa.String(100), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="user_ui"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── category_mappings ───────────────────────────────────────────────────
    op.create_table(
        "category_mappings",
        sa.Column("mapping_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_id", sa.Integer, sa.ForeignKey("merchants.merchant_id", ondelete="CASCADE"), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(20), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── alerts ──────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("txn_id", sa.Integer, sa.ForeignKey("transactions.txn_id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )

    # ── audit_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="user"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.Integer, nullable=True),
        sa.Column("old_value", sa.JSON, nullable=True),
        sa.Column("new_value", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── goals ───────────────────────────────────────────────────────────────
    op.create_table(
        "goals",
        sa.Column("goal_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_name", sa.String(255), nullable=False),
        sa.Column("target_amount", sa.Float, nullable=False),
        sa.Column("current_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("deadline", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("feasibility_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── budgets ─────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column("budget_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("limit_amount", sa.Float, nullable=False),
        sa.Column("spent_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("period", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("budgets")
    op.drop_table("goals")
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("category_mappings")
    op.drop_table("user_feedback")
    op.drop_table("transactions")
    op.drop_table("merchants")
    op.drop_table("accounts")
    op.drop_table("users")
