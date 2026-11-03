"""Read-only access to stored market data. Backtests read ONLY through this module (never the internet)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from quantlab.config import get_settings
from quantlab.data import calendars
from quantlab.data.providers.base import NO_DIVIDENDS
from quantlab.data.universes import BY_CODE, LISTED_ONLY_NOTE, SURVIVORSHIP_WARNING
from quantlab.db.models import (
    DataSnapshot,
    Instrument,
    InstrumentAlias,
    PriceBar,
    PriceCoverage,
    Universe,
    UniverseMember,
    UniverseMemberSet,
)

# --------------------------------------------------------------------------- search


def search_instruments(s: Session, q: str, market: str | None = None, limit: int = 20) -> list[Instrument]:
    """Search by ticker or name (listed name, English name, or alias).

    Order: exact ticker, ticker prefix, name prefix, name contains; listed stocks first.
    """
    q = q.strip()
    if not q:
        return []
    ql = q.lower()
    like_any = f"%{ql}%"
    alias_ids = select(InstrumentAlias.instrument_id).where(func.lower(InstrumentAlias.alias).like(like_any))
    name_l, en_l, tk_l = func.lower(Instrument.name), func.lower(func.coalesce(Instrument.name_en, "")), func.lower(Instrument.ticker)
    cond = or_(tk_l.like(f"{ql}%"), name_l.like(like_any), en_l.like(like_any), Instrument.id.in_(alias_ids))
    rank = case(
        (tk_l == ql, 0),
        (tk_l.like(f"{ql}%"), 1),
        (or_(name_l.like(f"{ql}%"), en_l.like(f"{ql}%")), 2),
        else_=3,
    )
    stmt = select(Instrument).where(cond)
    if market:
        stmt = stmt.where(Instrument.market == market)
    stmt = stmt.order_by(
        Instrument.is_listed.desc(), rank, func.length(Instrument.ticker), func.length(Instrument.name), Instrument.ticker
    ).limit(limit)
    return list(s.scalars(stmt))


def get_instrument(s: Session, market: str, ticker: str) -> Instrument | None:
    return s.scalar(select(Instrument).where(Instrument.market == market, Instrument.ticker == ticker))


def latest_snapshot_id(s: Session) -> int:
    return s.scalar(select(func.max(DataSnapshot.id))) or 0


# --------------------------------------------------------------------------- prices


def load_prices(
    s: Session, instrument_ids: list[int], start: dt.date, end: dt.date, snapshot_id: int | None = None
) -> pd.DataFrame:
    """Daily bars as they were in ``snapshot_id`` (default: newest), with adjusted OHLC.

    Columns: instrument_id, date, open, high, low, close, adj_close, volume,
             adj_open, adj_high, adj_low (adj_close already present).
    Adjusted prices: X_adj = X * adj_close / close (removes split and, where the source supports
    it, dividend jumps). Volume is left as delivered.
    """
    snapshot_id = snapshot_id if snapshot_id is not None else latest_snapshot_id(s)
    cols = ["instrument_id", "date", "open", "high", "low", "close", "adj_close", "volume"]
    if not instrument_ids:
        return pd.DataFrame(columns=cols + ["adj_open", "adj_high", "adj_low"])
    latest = (
        select(PriceBar.instrument_id, PriceBar.date, func.max(PriceBar.snapshot_id).label("sid"))
        .where(PriceBar.instrument_id.in_(instrument_ids), PriceBar.snapshot_id <= snapshot_id,
               PriceBar.date >= start, PriceBar.date <= end)
        .group_by(PriceBar.instrument_id, PriceBar.date)
        .subquery()
    )
    stmt = (
        select(*[getattr(PriceBar, c) for c in cols])
        .join(latest, (PriceBar.instrument_id == latest.c.instrument_id) & (PriceBar.date == latest.c.date)
              & (PriceBar.snapshot_id == latest.c.sid))
        .order_by(PriceBar.instrument_id, PriceBar.date)
    )
    df = pd.DataFrame(s.execute(stmt).all(), columns=cols)
    factor = df["adj_close"] / df["close"]
    for c in ("open", "high", "low"):
        df[f"adj_{c}"] = df[c] * factor
    return df


@dataclass
class Coverage:
    """Is the stored data enough for a backtest over [start, end]?

    status:
      ready          - every trading day in the range is stored
      incomplete     - stored, but some trading days are missing (listed in missing_dates)
      needs_download - the range has not been downloaded yet (or is out of date)
      unavailable    - no source has data for this stock
    """

    instrument_id: int
    market: str
    ticker: str
    status: str
    start: dt.date
    end: dt.date
    first_bar: dt.date | None = None
    last_bar: dt.date | None = None
    bars: int = 0
    expected_sessions: int = 0
    missing_count: int = 0
    missing_dates: list[dt.date] = field(default_factory=list)
    provider: str | None = None
    adjustment: str | None = None
    notes: list[str] = field(default_factory=list)


def check_coverage(
    s: Session, inst: Instrument, start: dt.date, end: dt.date, now: dt.datetime | None = None
) -> Coverage:
    now = now or dt.datetime.now(dt.timezone.utc)
    final = calendars.last_final_session(inst.market, now, get_settings().bar_final_delay_minutes)
    end = min(end, final)
    cov: PriceCoverage | None = inst.coverage
    out = Coverage(inst.id, inst.market, inst.ticker, "needs_download", start, end)
    if cov is None:
        out.notes.append("Price history has not been downloaded yet.")
        return out
    out.provider, out.adjustment = cov.provider, cov.adjustment
    if cov.status == "unavailable":
        out.status = "unavailable"
        out.notes.append(f"No price data available: {cov.message}")
        return out
    if cov.status == "error":
        out.notes.append(f"Download failed, try again later: {cov.message}")
        return out  # stays needs_download: nothing usable is stored
    out.first_bar, out.last_bar = cov.first_bar, cov.last_bar
    if cov.coverage_start > start or cov.coverage_end < end:
        out.notes.append(
            f"Stored range is {cov.coverage_start} to {cov.coverage_end}; {start} to {end} is needed."
        )
        return out
    if cov.message:
        out.notes.append(cov.message)
    if cov.adjustment == NO_DIVIDENDS:
        out.notes.append("Prices are not adjusted for dividends (source limitation).")

    dates = set(
        s.scalars(select(PriceBar.date).distinct().where(
            PriceBar.instrument_id == inst.id, PriceBar.date >= start, PriceBar.date <= end))
    )
    out.bars = len(dates)
    if not dates:
        out.status = "unavailable"
        out.notes.append("No trading data in this period (the stock may not have been listed yet).")
        return out
    first = min(dates)
    expected = calendars.sessions(inst.market, start, end)
    if first > start and (not expected or first > expected[0]):
        out.notes.append(f"Data starts on {first}: listed later, or the source has no older data.")
    expected_from_first = [d for d in expected if d >= first]
    out.expected_sessions = len(expected_from_first)
    missing = sorted(set(expected_from_first) - dates)
    out.missing_count = len(missing)
    out.missing_dates = missing[:20]
    if missing:
        out.status = "incomplete"
        out.notes.append(f"{len(missing)} trading day(s) missing from the source.")
    else:
        out.status = "ready"
    return out


# --------------------------------------------------------------------------- universes


@dataclass
class Membership:
    code: str
    name: str
    market: str
    date: dt.date
    point_in_time: bool
    as_of_date: dt.date | None  # date of the member list actually used
    instruments: list[Instrument]
    warnings: list[str]


def universe_members(
    s: Session, code: str, on: dt.date, snapshot_id: int | None = None
) -> Membership:
    """Members of a universe on date ``on``, using only lists known on or before that date."""
    d = BY_CODE[code]
    u = s.get(Universe, code)
    warnings: list[str] = []
    if d.kind == "all":
        insts = list(s.scalars(select(Instrument).where(Instrument.market == d.market, Instrument.is_listed)
                               .order_by(Instrument.ticker)))
        warnings += [SURVIVORSHIP_WARNING, LISTED_ONLY_NOTE]
        return Membership(code, d.name, d.market, on, False, None, insts, warnings)

    snapshot_id = snapshot_id if snapshot_id is not None else latest_snapshot_id(s)
    base = select(UniverseMemberSet).where(UniverseMemberSet.universe_code == code,
                                           UniverseMemberSet.snapshot_id <= snapshot_id)
    mset = s.scalar(base.where(UniverseMemberSet.as_of_date <= on)
                    .order_by(UniverseMemberSet.as_of_date.desc(), UniverseMemberSet.snapshot_id.desc()))
    pit = bool(u and u.point_in_time)
    if mset is None:
        # No list from on/before this date. For a current-only list we fall back to it, with a warning;
        # for a historical list, the date is before our history starts.
        earliest = s.scalar(base.order_by(UniverseMemberSet.as_of_date, UniverseMemberSet.snapshot_id.desc()))
        if earliest is None:
            return Membership(code, d.name, d.market, on, pit, None, [],
                              ["This list has not been downloaded yet."])
        mset = earliest
        if pit:
            warnings.append(f"Membership history starts on {earliest.as_of_date}; that list is used for earlier dates.")
    if not pit:
        warnings.append(SURVIVORSHIP_WARNING)
    insts = list(s.scalars(select(Instrument).join(UniverseMember, UniverseMember.instrument_id == Instrument.id)
                           .where(UniverseMember.set_id == mset.id).order_by(Instrument.ticker)))
    warnings.append(LISTED_ONLY_NOTE)
    return Membership(code, d.name, d.market, on, pit, mset.as_of_date, insts, warnings)
