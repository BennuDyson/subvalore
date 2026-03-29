from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DatasetStore(Base):
    """
    General-purpose table for storing structured financial datasets as JSONB.
    Used for: income_statement, quarterly_income_statement, balance_sheet,
    earnings_dates, calendar, earnings_estimate, revenue_estimate, eps_trend,
    growth_estimates, insider_purchases, insider_transactions.
    """

    __tablename__ = "dataset_store"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    dataset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="dataset_stores")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_dataset_store_ticker_type", "ticker_id", "dataset_type"),
    )

    def __repr__(self) -> str:
        return f"<DatasetStore ticker_id={self.ticker_id} type={self.dataset_type!r}>"
