"""Database schema.

Design notes
------------
* Multi-user ready: user-owned tables carry ``user_id``. For now there is one local user (id=1).
* Market data is append-only and versioned by ``DataSnapshot``:
  every download run creates one snapshot, and a price row is written only when it is new or
  its values changed (e.g. adjusted prices move after a dividend). Reading "as of snapshot S"
  takes, per (stock, date), the newest row with ``snapshot_id <= S``. A backtest records S, so a
  re-run sees exactly the same data even after later downloads.
* Index membership is stored as dated lists ("member sets"). Members at date D are the latest set
  with ``as_of_date <= D`` (no look-ahead).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


LOCAL_USER_ID = 1


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


# --------------------------------------------------------------------------- stocks


class Instrument(Base):
    """One tradable stock. ``market`` is 'KR' or 'US'; ``ticker`` is canonical (see data.symbols)."""

    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("market", "ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market: Mapped[str] = mapped_column(String(2), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)  # name as listed (Korean for KR)
    name_en: Mapped[str | None] = mapped_column(String(200), index=True)
    exchange: Mapped[str | None] = mapped_column(String(20))  # KOSPI, KOSDAQ, KONEX, NASDAQ, NYSE, AMEX...
    currency: Mapped[str] = mapped_column(String(3))
    is_listed: Mapped[bool] = mapped_column(Boolean, default=True)
    listing_source: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    coverage: Mapped[PriceCoverage | None] = relationship(back_populates="instrument", uselist=False)


class InstrumentAlias(Base):
    """Extra searchable names, e.g. English names of Korean companies."""

    __tablename__ = "instrument_aliases"
    __table_args__ = (UniqueConstraint("instrument_id", "alias"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(200), index=True)


# --------------------------------------------------------------------------- snapshots & prices


class DataSnapshot(Base):
    """One data download run. Its id is a global, increasing data version."""

    __tablename__ = "data_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # prices | listings | universe
    description: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class PriceBar(Base):
    """Daily bar. open/high/low/close are as delivered by the provider (split-adjusted for Yahoo);
    adj_close additionally includes dividends when the provider supplies it. Adjusted OHLC is
    derived on read: X_adj = X * adj_close / close."""

    __tablename__ = "price_bars"
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("data_snapshots.id"), primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class PriceFetchLog(Base):
    """What was downloaded for one stock in one snapshot: source and adjustment basis.
    Used to label every backtest with its data assumptions."""

    __tablename__ = "price_fetch_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("data_snapshots.id"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    adjustment: Mapped[str] = mapped_column(String(30))  # splits_and_dividends | no_dividends
    requested_start: Mapped[dt.date] = mapped_column(Date)
    requested_end: Mapped[dt.date] = mapped_column(Date)
    rows_received: Mapped[int] = mapped_column(Integer)
    rows_written: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class PriceCoverage(Base):
    """Current download state of one stock (what range has been requested from the provider)."""

    __tablename__ = "price_coverage"
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))  # ok | unavailable (no data) | error (source failed)
    message: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(30))
    adjustment: Mapped[str | None] = mapped_column(String(30))
    coverage_start: Mapped[dt.date | None] = mapped_column(Date)  # earliest date requested
    coverage_end: Mapped[dt.date | None] = mapped_column(Date)  # last final session requested
    first_bar: Mapped[dt.date | None] = mapped_column(Date)
    last_bar: Mapped[dt.date | None] = mapped_column(Date)
    last_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("data_snapshots.id"))
    last_attempt_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    instrument: Mapped[Instrument] = relationship(back_populates="coverage")


# --------------------------------------------------------------------------- universes


class Universe(Base):
    __tablename__ = "universes"
    code: Mapped[str] = mapped_column(String(30), primary_key=True)  # SP500, NDX100, KOSPI200, ...
    name: Mapped[str] = mapped_column(String(100))
    market: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str] = mapped_column(String(10))  # index | all
    # True when historical membership is stored (no survivorship bias from membership).
    point_in_time: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime)


class UniverseMemberSet(Base):
    """The members of a universe as known on ``as_of_date``."""

    __tablename__ = "universe_member_sets"
    __table_args__ = (Index("ix_member_sets_lookup", "universe_code", "as_of_date", "snapshot_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    universe_code: Mapped[str] = mapped_column(ForeignKey("universes.code"))
    as_of_date: Mapped[dt.date] = mapped_column(Date)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("data_snapshots.id"))
    member_count: Mapped[int] = mapped_column(Integer)


class UniverseMember(Base):
    __tablename__ = "universe_members"
    set_id: Mapped[int] = mapped_column(ForeignKey("universe_member_sets.id", ondelete="CASCADE"), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)


# --------------------------------------------------------------------------- watchlists


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, default=LOCAL_USER_ID)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list[WatchlistItem]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan", order_by="WatchlistItem.added_at"
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    added_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    watchlist: Mapped[Watchlist] = relationship(back_populates="items")
    instrument: Mapped[Instrument] = relationship()


# --------------------------------------------------------------------------- background jobs


class DataJob(Base):
    """A background download request (e.g. 'get price history for these 200 stocks')."""

    __tablename__ = "data_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=LOCAL_USER_ID)
    kind: Mapped[str] = mapped_column(String(30))
    params: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|done|failed
    done: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[list] = mapped_column(JSON, default=list)
    message: Mapped[str | None] = mapped_column(Text)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("data_snapshots.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
