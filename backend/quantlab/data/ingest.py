"""Download data from providers and store it in the database (the only code that writes market data).

Backtests never call this module: they read from the database through ``repository``.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import time
from dataclasses import dataclass
from importlib import resources

import numpy as np
import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from quantlab.config import get_settings
from quantlab.data import calendars
from quantlab.data.providers.base import PRICE_COLUMNS, ProviderError
from quantlab.data.providers.registry import Providers, get_providers
from quantlab.data.symbols import CURRENCY, normalize_ticker
from quantlab.data.universes import BY_CODE
from quantlab.db.models import (
    DataSnapshot,
    Instrument,
    InstrumentAlias,
    PriceBar,
    PriceCoverage,
    PriceFetchLog,
    Universe,
    UniverseMember,
    UniverseMemberSet,
    utcnow,
)

log = logging.getLogger(__name__)


def new_snapshot(s: Session, kind: str, description: str = "") -> DataSnapshot:
    snap = DataSnapshot(kind=kind, description=description)
    s.add(snap)
    s.flush()
    return snap


# --------------------------------------------------------------------------- listings


@dataclass
class ListingResult:
    market: str
    received: int
    added: int
    updated: int
    delisted: int


def ingest_listings(s: Session, market: str, providers: Providers | None = None) -> ListingResult:
    providers = providers or get_providers()
    prov = providers.listings[market]
    rows = prov.fetch_listings(market)
    if not rows:
        raise ProviderError(f"{prov.name} returned no {market} listings")
    existing = {i.ticker: i for i in s.scalars(select(Instrument).where(Instrument.market == market))}
    seen, added, updated = set(), 0, 0
    for r in rows:
        seen.add(r.ticker)
        inst = existing.get(r.ticker)
        if inst is None:
            inst = Instrument(market=market, ticker=r.ticker, currency=CURRENCY[market])
            s.add(inst)
            existing[r.ticker] = inst
            added += 1
        elif (inst.name, inst.exchange, inst.is_listed) != (r.name, r.exchange, True):
            updated += 1
        inst.name = r.name
        inst.exchange = r.exchange
        inst.is_listed = True
        inst.listing_source = prov.name
        if r.name_en:
            inst.name_en = r.name_en
    delisted = 0
    for t, inst in existing.items():
        if t not in seen and inst.is_listed:
            inst.is_listed = False
            delisted += 1
    s.flush()
    if market == "KR":
        apply_seed_names(s)
    new_snapshot(s, "listings", f"{market} listings from {prov.name}: {len(rows)} stocks")
    return ListingResult(market, len(rows), added, updated, delisted)


def apply_seed_names(s: Session) -> int:
    """English names for major Korean companies (KRX lists Korean names only)."""
    n = 0
    with resources.files("quantlab.data.seed").joinpath("kr_english_names.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            inst = s.scalar(select(Instrument).where(Instrument.market == "KR", Instrument.ticker == row["ticker"]))
            if inst is None:
                continue
            if not inst.name_en:
                inst.name_en = row["name_en"]
            if not s.scalar(select(InstrumentAlias).where(InstrumentAlias.instrument_id == inst.id,
                                                          InstrumentAlias.alias == row["name_en"])):
                s.add(InstrumentAlias(instrument_id=inst.id, alias=row["name_en"]))
                n += 1
    s.flush()
    return n


def get_or_create_instrument(s: Session, market: str, ticker: str, name: str | None = None,
                             is_listed: bool = True, source: str | None = None) -> Instrument:
    t = normalize_ticker(market, ticker)
    inst = s.scalar(select(Instrument).where(Instrument.market == market, Instrument.ticker == t))
    if inst is None:
        inst = Instrument(market=market, ticker=t, name=name or t, currency=CURRENCY[market],
                          is_listed=is_listed, listing_source=source)
        s.add(inst)
        s.flush()
    return inst


# --------------------------------------------------------------------------- prices


@dataclass
class PriceResult:
    instrument_id: int
    ticker: str
    outcome: str  # up_to_date | downloaded | unavailable | failed
    rows_written: int = 0
    message: str | None = None


def _latest_rows(s: Session, instrument_id: int) -> pd.DataFrame:
    """Newest stored version of every bar of one stock."""
    latest = (
        select(PriceBar.date, func.max(PriceBar.snapshot_id).label("sid"))
        .where(PriceBar.instrument_id == instrument_id)
        .group_by(PriceBar.date)
        .subquery()
    )
    q = select(PriceBar.date, *[getattr(PriceBar, c) for c in PRICE_COLUMNS]).join(
        latest, (PriceBar.date == latest.c.date) & (PriceBar.snapshot_id == latest.c.sid)
    ).where(PriceBar.instrument_id == instrument_id)
    rows = s.execute(q).all()
    df = pd.DataFrame(rows, columns=["date", *PRICE_COLUMNS])
    return df.set_index("date")


def _changed_rows(new: pd.DataFrame, old: pd.DataFrame) -> pd.DataFrame:
    """Rows of ``new`` that are absent from ``old`` or differ in any value."""
    if old.empty:
        return new
    joined = new.join(old, how="left", rsuffix="_old")
    is_new = joined["close_old"].isna()
    differs = np.zeros(len(joined), dtype=bool)
    for c in PRICE_COLUMNS:
        a, b = joined[c].to_numpy(float), joined[f"{c}_old"].to_numpy(float)
        differs |= ~np.isclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=False)
    return new[(is_new | differs).to_numpy()]


def ensure_prices(
    s: Session,
    inst: Instrument,
    start: dt.date,
    snapshot: DataSnapshot,
    now: dt.datetime | None = None,
    providers: Providers | None = None,
) -> PriceResult:
    """Make sure daily bars from ``start`` to the last finished session are stored.

    Rules (they keep every snapshot's adjusted series internally consistent):
    * Only bars of finished sessions are stored (see calendars.last_final_session).
    * A refresh always re-downloads the stock's whole covered range, because adjusted prices of
      old dates change after every dividend or split.
    * A refresh uses the same provider as the first download, so one stock's series never mixes
      sources or adjustment bases.
    """
    providers = providers or get_providers()
    settings = get_settings()
    now = now or dt.datetime.now(dt.timezone.utc)
    final_end = calendars.last_final_session(inst.market, now, settings.bar_final_delay_minutes)
    cov = inst.coverage

    if cov and cov.status == "ok" and cov.coverage_start <= start and cov.coverage_end >= final_end:
        return PriceResult(inst.id, inst.ticker, "up_to_date")

    fetch_start = min(start, cov.coverage_start) if cov and cov.coverage_start else start
    candidates = [p for p in providers.prices if p.supports(inst.market, inst.ticker, inst.exchange)]
    if cov and cov.status == "ok" and cov.provider:
        candidates = [p for p in candidates if p.name == cov.provider]

    errors: list[str] = []
    source_failed = False  # a source errored (network, login...) rather than answering "no data"
    history = None
    for p in candidates:
        try:
            h = p.fetch_daily(inst.market, inst.ticker, inst.exchange, fetch_start, final_end)
        except ProviderError as e:
            errors.append(f"{p.name}: {e}")
            source_failed = True
            continue
        if not h.bars.empty:
            history = h
            break
        errors.append(f"{p.name}: no data")

    if history is None:
        msg = "; ".join(errors) or "No data source covers this stock"
        if cov and cov.status == "ok":
            # Keep the data we already have; just record that the update failed.
            cov.message = f"Last update failed: {msg}"
            cov.last_attempt_at = utcnow()
            return PriceResult(inst.id, inst.ticker, "failed", message=msg)
        if cov is None:
            cov = inst.coverage = PriceCoverage(instrument_id=inst.id)
        # "error": could not reach a source (try again later). "unavailable": sources answered with no data.
        status = "error" if source_failed else "unavailable"
        cov.status, cov.message, cov.last_attempt_at = status, msg, utcnow()
        return PriceResult(inst.id, inst.ticker, "failed" if source_failed else "unavailable", message=msg)

    bars = history.bars[(history.bars.index >= fetch_start) & (history.bars.index <= final_end)]
    changed = _changed_rows(bars, _latest_rows(s, inst.id))
    if not changed.empty:
        s.execute(
            insert(PriceBar),
            [
                {"instrument_id": inst.id, "date": d, "snapshot_id": snapshot.id,
                 **{c: float(row[c]) for c in PRICE_COLUMNS}}
                for d, row in changed.iterrows()
            ],
        )
    s.add(PriceFetchLog(snapshot_id=snapshot.id, instrument_id=inst.id, provider=history.provider,
                        adjustment=history.adjustment, requested_start=fetch_start, requested_end=final_end,
                        rows_received=len(bars), rows_written=len(changed)))
    if cov is None:
        cov = inst.coverage = PriceCoverage(instrument_id=inst.id)
    cov.status, cov.message = "ok", None
    cov.provider, cov.adjustment = history.provider, history.adjustment
    cov.coverage_start, cov.coverage_end = fetch_start, final_end
    s.flush()
    cov.first_bar, cov.last_bar = s.execute(
        select(func.min(PriceBar.date), func.max(PriceBar.date)).where(PriceBar.instrument_id == inst.id)
    ).one()
    cov.last_snapshot_id = snapshot.id
    cov.last_attempt_at = utcnow()
    if history.name_en and not inst.name_en:
        inst.name_en = history.name_en
    s.flush()
    return PriceResult(inst.id, inst.ticker, "downloaded", rows_written=len(changed))


def ensure_prices_many(
    s: Session,
    instruments: list[Instrument],
    start: dt.date,
    description: str = "",
    now: dt.datetime | None = None,
    providers: Providers | None = None,
    progress=None,
) -> tuple[DataSnapshot, list[PriceResult]]:
    """One snapshot for the whole batch; commits after each stock so progress is never lost."""
    snap = new_snapshot(s, "prices", description)
    s.commit()
    pause = get_settings().download_pause_seconds
    results = []
    for i, inst in enumerate(instruments):
        try:
            r = ensure_prices(s, inst, start, snap, now=now, providers=providers)
            s.commit()
        except Exception as e:  # never let one bad stock kill the batch
            s.rollback()
            log.exception("price download failed for %s", inst.ticker)
            r = PriceResult(inst.id, inst.ticker, "failed", message=str(e))
        results.append(r)
        if progress:
            progress(i + 1, len(instruments), r)
        if r.outcome == "downloaded" and pause and providers is None:
            time.sleep(pause)
    return snap, results


# --------------------------------------------------------------------------- universes


def ensure_universe_row(s: Session, code: str, point_in_time: bool, source: str | None) -> Universe:
    d = BY_CODE[code]
    u = s.get(Universe, code)
    if u is None:
        u = Universe(code=code, name=d.name, market=d.market, kind=d.kind)
        s.add(u)
    u.point_in_time, u.source = point_in_time, source
    return u


def sync_universe_catalog(s: Session) -> None:
    for d in BY_CODE.values():
        if s.get(Universe, d.code) is None:
            s.add(Universe(code=d.code, name=d.name, market=d.market, kind=d.kind, point_in_time=False))
    s.flush()


def _monthly_sample_dates(market: str, since: dt.date, until: dt.date) -> list[dt.date]:
    """First session of every month in [since, until], plus ``until`` itself."""
    out, seen_months = [], set()
    for d in calendars.sessions(market, since, until):
        if (d.year, d.month) not in seen_months:
            seen_months.add((d.year, d.month))
            out.append(d)
    if until not in out:
        out.append(until)
    return out


@dataclass
class UniverseResult:
    code: str
    sets_written: int
    members_latest: int
    point_in_time: bool
    errors: list[str]


def ingest_universe(
    s: Session,
    code: str,
    since: dt.date | None = None,
    now: dt.datetime | None = None,
    providers: Providers | None = None,
) -> UniverseResult:
    providers = providers or get_providers()
    d = BY_CODE[code]
    if d.kind != "index":
        raise ValueError(f"{code} is built from the stock listing, not downloaded")
    prov = providers.constituents[code]
    now = now or dt.datetime.now(dt.timezone.utc)
    settings = get_settings()
    final = calendars.last_final_session(d.market, now, settings.bar_final_delay_minutes)

    if prov.point_in_time:
        since = since or dt.date.fromisoformat(settings.kr_index_history_start)
        have = set(s.scalars(select(UniverseMemberSet.as_of_date).where(UniverseMemberSet.universe_code == code)))
        dates = [x for x in _monthly_sample_dates(d.market, since, final) if x not in have]
    else:
        dates = [final]

    u = ensure_universe_row(s, code, prov.point_in_time, prov.name)
    snap = new_snapshot(s, "universe", f"{code} members from {prov.name}")
    errors, written, latest = [], 0, 0
    for day in dates:
        try:
            ml = prov.fetch_members(code, day)
        except ProviderError as e:
            errors.append(f"{day}: {e}")
            if not prov.point_in_time or len(errors) >= 3 and written == 0:
                break  # the source is down or needs a login; stop instead of hammering it
            continue
        mset = UniverseMemberSet(universe_code=code, as_of_date=ml.as_of_date, snapshot_id=snap.id,
                                 member_count=len(ml.tickers))
        s.add(mset)
        s.flush()
        for t in ml.tickers:
            inst = get_or_create_instrument(
                s, d.market, t, name=ml.names.get(t),
                # A historical member missing from today's listing has most likely been delisted.
                is_listed=not prov.point_in_time, source=prov.name,
            )
            s.add(UniverseMember(set_id=mset.id, instrument_id=inst.id))
        written += 1
        latest = len(ml.tickers)
        s.commit()
    if written:
        u.updated_at = utcnow()
    s.commit()
    return UniverseResult(code, written, latest, prov.point_in_time, errors)
