"""
app/services/analytics_engine.py
==================================
Central Analytics Update Engine.

Triggered whenever:
  • Transaction is added
  • PDF uploaded
  • Receipt scanned
  • User confirms category

Responsibilities:
  1. Insert/update transaction
  2. Update merchant cache
  3. Update CATEGORY_MAPPINGS
  4. Recompute aggregates
  5. Refresh alerts (run anomaly detection)
  6. Log action in AUDIT_LOGS
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Transaction, Merchant, CategoryMapping, Alert, AuditLog, UserFeedback,
    TxnType, AlertType, AlertSeverity, AlertStatus, ActorType,
    MappingSource, FeedbackSource,
)


class AnalyticsEngine:
    """
    Stateless service class.  Every method takes a db Session as first arg
    so it can be used both inside FastAPI dependencies and standalone scripts.
    """

    # ── Transaction Ingestion ──────────────────────────────────────────────

    def ingest_transaction(
        self,
        db: Session,
        user_id: int,
        account_id: int,
        amount: float,
        txn_type: str,
        raw_description: str,
        payment_mode: str = "UPI",
        actor_id: Optional[int] = None,
        source: str = "manual",
    ) -> Transaction:
        """
        Full pipeline:
          categorise → insert → update merchant cache →
          run anomaly check → log audit
        """
        # ── Auto-categorise ────────────────────────────────────────────────
        category, subcategory, confidence = self._auto_categorise(
            db, user_id, raw_description, amount, txn_type
        )

        # ── Find or create merchant ────────────────────────────────────────
        merchant = self._get_or_create_merchant(db, raw_description, category)

        # ── Insert transaction ─────────────────────────────────────────────
        txn = Transaction(
            user_id          = user_id,
            account_id       = account_id,
            merchant_id      = merchant.merchant_id if merchant else None,
            amount           = amount,
            txn_type         = TxnType(txn_type),
            category         = category,
            subcategory      = subcategory,
            raw_description  = raw_description[:500],
            payment_mode     = payment_mode,
            user_verified    = False,
            confidence_score = confidence,
            txn_timestamp    = datetime.utcnow(),
        )
        db.add(txn)
        db.flush()  # get txn_id

        # ── Check for anomaly ──────────────────────────────────────────────
        if txn_type == "debit":
            self._check_and_create_alert(db, txn)

        # ── Audit log ──────────────────────────────────────────────────────
        self._log_audit(
            db, actor_id=actor_id or user_id,
            actor_type=ActorType.USER,
            action="CREATE_TRANSACTION",
            resource_type="transaction",
            resource_id=txn.txn_id,
            new_value={"amount": amount, "category": category, "source": source},
        )

        db.commit()
        db.refresh(txn)
        return txn

    # ── Category Confirmation ──────────────────────────────────────────────

    def confirm_category(
        self,
        db: Session,
        txn_id: int,
        corrected_category: str,
        corrected_subcategory: str = "",
        user_id: Optional[int] = None,
        source: str = "user_ui",
    ) -> UserFeedback:
        """
        User confirms / corrects a category.
        1. Insert UserFeedback
        2. Update Transaction
        3. Upsert CategoryMapping
        4. Audit log
        """
        txn = db.query(Transaction).filter(Transaction.txn_id == txn_id).first()
        if not txn:
            raise ValueError(f"Transaction {txn_id} not found")

        old_category = txn.category

        # Insert feedback
        fb = UserFeedback(
            txn_id               = txn_id,
            corrected_category   = corrected_category,
            corrected_subcategory= corrected_subcategory,
            source               = FeedbackSource(source),
            created_at           = datetime.utcnow(),
        )
        db.add(fb)

        # Update transaction
        txn.category     = corrected_category
        txn.subcategory  = corrected_subcategory
        txn.user_verified= True

        # Upsert category mapping
        if txn.merchant_id:
            self._upsert_category_mapping(
                db, user_id or txn.user_id,
                txn.merchant_id, corrected_category, corrected_subcategory,
                source=MappingSource.USER,
            )

        # Audit
        self._log_audit(
            db, actor_id=user_id or txn.user_id,
            actor_type=ActorType.USER,
            action="UPDATE_CATEGORY",
            resource_type="transaction",
            resource_id=txn_id,
            old_value={"category": old_category},
            new_value={"category": corrected_category},
        )

        db.commit()
        db.refresh(fb)
        return fb

    # ── PDF / OCR Ingestion ────────────────────────────────────────────────

    def ingest_from_ocr(
        self,
        db: Session,
        user_id: int,
        account_id: int,
        ocr_result: dict,
    ) -> Optional[Transaction]:
        """Insert transaction derived from OCR receipt."""
        amount = float(ocr_result.get("ocr_amount", 0))
        if amount <= 0:
            return None
        return self.ingest_transaction(
            db, user_id=user_id, account_id=account_id,
            amount=amount, txn_type="debit",
            raw_description=ocr_result.get("ocr_merchant", "OCR Receipt"),
            payment_mode="Cash",
            source="ocr",
        )

    def ingest_from_pdf(
        self,
        db: Session,
        user_id: int,
        account_id: int,
        pdf_results: list[dict],
    ) -> list[Transaction]:
        """Bulk-insert transactions from PDF statement."""
        inserted = []
        for row in pdf_results:
            if "error" in row:
                continue
            amount = float(row.get("ocr_amount", 0) or row.get("amount", 0))
            if amount <= 0:
                continue
            txn = self.ingest_transaction(
                db, user_id=user_id, account_id=account_id,
                amount=amount, txn_type="debit",
                raw_description=row.get("pdf_row", "")[:200],
                payment_mode="Net Banking",
                source="pdf",
            )
            inserted.append(txn)
        return inserted

    # ── Private helpers ────────────────────────────────────────────────────

    def _auto_categorise(
        self, db: Session, user_id: int, description: str, amount: float, txn_type: str
    ) -> tuple[str, str, float]:
        """Run quick categorisation: user mapping → merchant cache → ML."""
        try:
            # Check user-specific mappings
            user_mappings = {
                cm.merchant.clean_name: cm.category
                for cm in db.query(CategoryMapping)
                .filter(CategoryMapping.user_id == user_id)
                .all()
                if cm.merchant
            }
            from ml_models.categorization_model.inference import categorize_transaction
            result = categorize_transaction(
                raw_description=description,
                amount=amount,
                merchant_name=description.split()[0] if description else "",
                txn_type=txn_type,
                user_mappings=user_mappings,
            )
            return (
                result.get("category", "Uncategorized"),
                result.get("subcategory", ""),
                float(result.get("confidence", 0.5)),
            )
        except Exception:
            return "Uncategorized", "", 0.5

    def _get_or_create_merchant(
        self, db: Session, raw_description: str, category: str
    ) -> Optional[Merchant]:
        """Find existing merchant by clean name or create a new one."""
        clean = raw_description.split()[0][:50] if raw_description else "Unknown"
        merchant = db.query(Merchant).filter(
            Merchant.clean_name.ilike(clean)
        ).first()
        if not merchant:
            merchant = Merchant(
                raw_name=raw_description[:500],
                clean_name=clean,
                default_category=category,
                created_at=datetime.utcnow(),
            )
            db.add(merchant)
            db.flush()
        return merchant

    def _check_and_create_alert(self, db: Session, txn: Transaction) -> None:
        """Run simple threshold-based anomaly check and insert alert if needed."""
        try:
            # Large transaction alert (> 50,000)
            if txn.amount > 50_000:
                alert = Alert(
                    user_id    = txn.user_id,
                    txn_id     = txn.txn_id,
                    alert_type = AlertType.LARGE_TRANSACTION,
                    severity   = AlertSeverity.HIGH,
                    status     = AlertStatus.OPEN,
                    message    = f"Large transaction of ₹{txn.amount:,.0f} detected.",
                    created_at = datetime.utcnow(),
                )
                db.add(alert)
        except Exception:
            pass

    def _upsert_category_mapping(
        self, db: Session, user_id: int, merchant_id: int,
        category: str, subcategory: str, source: MappingSource
    ) -> None:
        existing = db.query(CategoryMapping).filter(
            CategoryMapping.user_id    == user_id,
            CategoryMapping.merchant_id== merchant_id,
        ).first()
        if existing:
            existing.category   = category
            existing.subcategory= subcategory
            existing.source     = source
            existing.confidence = 1.0
            existing.updated_at = datetime.utcnow()
        else:
            db.add(CategoryMapping(
                user_id     = user_id,
                merchant_id = merchant_id,
                category    = category,
                subcategory = subcategory,
                confidence  = 1.0,
                source      = source,
            ))

    def _log_audit(
        self, db: Session,
        actor_id: Optional[int],
        actor_type: ActorType,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
    ) -> None:
        log = AuditLog(
            actor_id      = actor_id,
            actor_type    = actor_type,
            action        = action,
            resource_type = resource_type,
            resource_id   = resource_id,
            old_value     = old_value,
            new_value     = new_value,
            created_at    = datetime.utcnow(),
        )
        db.add(log)


# Singleton
analytics_engine = AnalyticsEngine()
