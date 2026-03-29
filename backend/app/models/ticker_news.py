from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TickerNews(Base):
    __tablename__ = "ticker_news"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id", ondelete="CASCADE"), index=True)

    news_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="news")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_ticker_news_ticker_published", "ticker_id", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<TickerNews ticker_id={self.ticker_id} title={self.title!r:.40}>"
