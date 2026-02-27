"""
app/models/currency.py
======================
CURRENCIES table — supported currency registry.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    currency_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code:        Mapped[str] = mapped_column(String(10),  nullable=False, unique=True)
    name:        Mapped[str] = mapped_column(String(100), nullable=False)
    symbol:      Mapped[str] = mapped_column(String(10),  nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Currency code={self.code!r}>"
