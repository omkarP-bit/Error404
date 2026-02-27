"""
app/models/notification_log.py
================================
NOTIFICATION_LOG table — delivery log for every alert notification.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"

    notification_id: Mapped[int]               = mapped_column(primary_key=True, autoincrement=True)
    alert_id:        Mapped[int]               = mapped_column(
        ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id:         Mapped[int]               = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel:         Mapped[str]               = mapped_column(String(30), nullable=False)   # email/sms/push/in_app
    sent_at:         Mapped[datetime]          = mapped_column(DateTime, nullable=False)
    delivered_at:    Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at:      Mapped[datetime]          = mapped_column(DateTime, default=func.now())

    alert: Mapped["Alert"] = relationship("Alert")
    user:  Mapped["User"]  = relationship("User")

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.notification_id} channel={self.channel!r}>"
