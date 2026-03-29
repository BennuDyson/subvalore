from datetime import datetime, date
from sqlalchemy import ForeignKey, DateTime, Numeric, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DividendHistory(Base):
    __tablename__ = "dividend_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="dividend_history")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_dividend_history_ticker_date", "ticker_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<DividendHistory ticker_id={self.ticker_id} date={self.date} value={self.value}>"
