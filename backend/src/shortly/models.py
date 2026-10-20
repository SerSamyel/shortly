from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from shortly.db import Base

# SQLite only auto-increments INTEGER PRIMARY KEY, so use BIGINT on Postgres only.
BigId = BigInteger().with_variant(Integer(), "sqlite")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    # Codes are unique forever: deleted links keep their row (deleted_at) so a code is never reused.
    code: Mapped[str] = mapped_column(String(32), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_url: Mapped[str] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_clicks: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


class ClickDaily(Base):
    __tablename__ = "click_daily"

    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0)


class ClickReferrer(Base):
    __tablename__ = "click_referrers"

    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0)


class ClickCountry(Base):
    __tablename__ = "click_countries"

    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    country: Mapped[str] = mapped_column(String(16), primary_key=True)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0)


class ClickVisitor(Base):
    """One row per (link, day, visitor hash): unique visitors per day are a row count."""

    __tablename__ = "click_visitors"

    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    visitor_hash: Mapped[str] = mapped_column(String(64), primary_key=True)


class ProcessedEvent(Base):
    """Event ids the consumer already applied, so redelivered events are not double-counted."""

    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
