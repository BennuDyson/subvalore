from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Numeric, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dividends: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    stock_splits: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="price_history")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_price_history_ticker_timestamp", "ticker_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory ticker_id={self.ticker_id} timestamp={self.timestamp}>"
