from datetime import datetime, timezone
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticker(Base):
    __tablename__ = "tickers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    metrics: Mapped[list["TickerMetrics"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TickerMetrics", back_populates="ticker", cascade="all, delete-orphan"
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PriceHistory", back_populates="ticker", cascade="all, delete-orphan"
    )
    dividend_history: Mapped[list["DividendHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DividendHistory", back_populates="ticker", cascade="all, delete-orphan"
    )
    dataset_stores: Mapped[list["DatasetStore"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DatasetStore", back_populates="ticker", cascade="all, delete-orphan"
    )
    news: Mapped[list["TickerNews"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TickerNews", back_populates="ticker", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["TickerRecommendation"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TickerRecommendation", back_populates="ticker", cascade="all, delete-orphan"
    )
    price_targets: Mapped[list["TickerPriceTarget"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TickerPriceTarget", back_populates="ticker", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ticker symbol={self.symbol!r}>"
