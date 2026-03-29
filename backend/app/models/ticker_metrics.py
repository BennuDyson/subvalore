from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Numeric, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TickerMetrics(Base):
    __tablename__ = "ticker_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    pe: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    volume_avg: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    volume_avg_10: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="metrics")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<TickerMetrics ticker_id={self.ticker_id} pe={self.pe}>"
