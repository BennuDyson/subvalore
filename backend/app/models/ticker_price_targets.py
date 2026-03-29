from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Numeric, String, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TickerPriceTarget(Base):
    __tablename__ = "ticker_price_targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    current: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    mean: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    median: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="price_targets")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_ticker_price_targets_ticker", "ticker_id"),
    )

    def __repr__(self) -> str:
        return f"<TickerPriceTarget ticker_id={self.ticker_id} mean={self.mean}>"
