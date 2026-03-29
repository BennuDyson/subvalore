from datetime import datetime, date
from sqlalchemy import ForeignKey, DateTime, String, Date, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TickerRecommendation(Base):
    __tablename__ = "ticker_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strong_buy: Mapped[int | None] = mapped_column(nullable=True)
    buy: Mapped[int | None] = mapped_column(nullable=True)
    hold: Mapped[int | None] = mapped_column(nullable=True)
    sell: Mapped[int | None] = mapped_column(nullable=True)
    strong_sell: Mapped[int | None] = mapped_column(nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="recommendations")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_ticker_recommendations_ticker", "ticker_id"),
    )

    def __repr__(self) -> str:
        return f"<TickerRecommendation ticker_id={self.ticker_id} period={self.period!r}>"
