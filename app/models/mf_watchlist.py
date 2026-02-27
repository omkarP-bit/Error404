"""
app/models/mf_watchlist.py
===========================
MF_WATCHLIST table — user's tracked funds.
UNIQUE(user_id, instrument_id) enforced.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MFWatchlist(Base):
    __tablename__ = "mf_watchlist"
    __table_args__ = (UniqueConstraint("user_id", "instrument_id", name="uq_watchlist_user_instrument"),)

    watchlist_id:  Mapped[int]      = mapped_column(primary_key=True, autoincrement=True)
    user_id:       Mapped[int]      = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[int]      = mapped_column(
        ForeignKey("mf_instruments.instrument_id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_at:      Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user:       Mapped["User"]         = relationship("User")
    instrument: Mapped["MFInstrument"] = relationship("MFInstrument", back_populates="watchlist_entries")

    def __repr__(self) -> str:
        return f"<MFWatchlist user={self.user_id} instrument={self.instrument_id}>"
