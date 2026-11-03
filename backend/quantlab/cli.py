"""Command line: quantlab <command>. Run `quantlab -h` for help."""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys

from sqlalchemy import func, select

from quantlab.config import get_settings
from quantlab.data import ingest, jobs
from quantlab.data.providers.base import ProviderError
from quantlab.data.symbols import normalize_ticker
from quantlab.data.universes import BY_CODE
from quantlab.db import migrate
from quantlab.db.models import Instrument, PriceBar, PriceCoverage, UniverseMemberSet, Watchlist
from quantlab.db.session import new_session


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def cmd_init_db(a) -> None:
    migrate.upgrade()
    print(f"Database ready: {get_settings().database_url}")


def cmd_listings(a) -> None:
    markets = ["KR", "US"] if a.market == "all" else [a.market]
    s = new_session()
    rc = 0
    for m in markets:
        try:
            r = ingest.ingest_listings(s, m)
            s.commit()
            print(f"{m}: {r.received} stocks ({r.added} new, {r.updated} changed, {r.delisted} no longer listed)")
        except ProviderError as e:
            s.rollback()
            print(f"{m}: FAILED - {e}", file=sys.stderr)
            rc = 1
    s.close()
    if rc:
        sys.exit(rc)


def cmd_universe(a) -> None:
    codes = [c for c, d in BY_CODE.items() if d.kind == "index"] if a.code == "all" else [a.code]
    s = new_session()
    rc = 0
    for c in codes:
        r = ingest.ingest_universe(s, c, since=a.since)
        kind = "historical (point-in-time)" if r.point_in_time else "current members only"
        print(f"{c}: {r.sets_written} member list(s) stored, latest has {r.members_latest} stocks [{kind}]")
        for e in r.errors[:5]:
            print(f"  ! {e}", file=sys.stderr)
        if r.errors and not r.sets_written:
            rc = 1
    s.close()
    if rc:
        sys.exit(rc)


def _parse_targets(s, spec: str) -> list[int]:
    ids = []
    for tok in filter(None, (t.strip() for t in spec.split(","))):
        market, _, ticker = tok.partition(":")
        market = market.upper()
        t = normalize_ticker(market, ticker)
        inst = s.scalar(select(Instrument).where(Instrument.market == market, Instrument.ticker == t))
        if inst is None:
            # Not in the listing (yet): create it so the download can be attempted.
            inst = ingest.get_or_create_instrument(s, market, t, source="manual")
            s.commit()
        ids.append(inst.id)
    return ids


def cmd_prices(a) -> None:
    s = new_session()
    ids = _parse_targets(s, a.tickers) if a.tickers else []
    targets = jobs.resolve_targets(s, ids, a.universe, a.watchlist)
    if not targets:
        print("Nothing to download (is the universe list downloaded?)", file=sys.stderr)
        sys.exit(1)
    start = a.start or _date(get_settings().default_history_start)
    print(f"Checking {len(targets)} stock(s) from {start} ...")

    def progress(done, total, r):
        extra = f" ({r.rows_written} rows written)" if r.outcome == "downloaded" else ""
        msg = f" - {r.message}" if r.message else ""
        print(f"[{done}/{total}] {r.ticker}: {r.outcome}{extra}{msg}")

    snap, results = ingest.ensure_prices_many(s, targets, start, description="cli", progress=progress)
    bad = [r for r in results if r.outcome in ("failed", "unavailable")]
    print(f"Snapshot #{snap.id}: {len(results) - len(bad)} ok, {len(bad)} failed/unavailable")
    s.close()


def cmd_preload(a) -> None:
    """Listings + index member lists + price history for index members and watchlists."""
    for m in ("KR", "US"):
        try:
            cmd_listings(argparse.Namespace(market=m))
        except SystemExit:
            pass
    for c in (c for c, d in BY_CODE.items() if d.kind == "index"):
        try:
            cmd_universe(argparse.Namespace(code=c, since=None))
        except SystemExit:
            pass
    s = new_session()
    wl_ids = list(s.scalars(select(Watchlist.id)))
    s.close()
    for c in (c for c, d in BY_CODE.items() if d.kind == "index"):
        try:
            cmd_prices(argparse.Namespace(tickers=None, universe=c, watchlist=None, start=a.start))
        except SystemExit:
            pass
    for w in wl_ids:
        try:
            cmd_prices(argparse.Namespace(tickers=None, universe=None, watchlist=w, start=a.start))
        except SystemExit:
            pass


def cmd_status(a) -> None:
    s = new_session()
    for m in ("KR", "US"):
        n = s.scalar(select(func.count()).select_from(Instrument).where(Instrument.market == m, Instrument.is_listed))
        print(f"{m} listed stocks: {n}")
    for c, d in BY_CODE.items():
        if d.kind == "all":
            continue  # "All US / Korean stocks" come from the listings above
        sets = s.scalar(select(func.count()).select_from(UniverseMemberSet).where(UniverseMemberSet.universe_code == c))
        latest = s.scalar(select(UniverseMemberSet.member_count).where(UniverseMemberSet.universe_code == c)
                          .order_by(UniverseMemberSet.as_of_date.desc(), UniverseMemberSet.snapshot_id.desc()))
        print(f"{c}: {latest or 0} stocks ({sets} dated list(s))")
    ok = s.scalar(select(func.count()).select_from(PriceCoverage).where(PriceCoverage.status == "ok"))
    bad = s.scalar(select(func.count()).select_from(PriceCoverage).where(PriceCoverage.status != "ok"))
    rows = s.scalar(select(func.count()).select_from(PriceBar))
    print(f"Price history: {ok} stocks stored, {bad} unavailable, {rows} bar rows (all versions)")
    s.close()


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="quantlab")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create / upgrade the database").set_defaults(fn=cmd_init_db)

    sp = sub.add_parser("listings", help="download the list of all stocks")
    sp.add_argument("--market", choices=["KR", "US", "all"], default="all")
    sp.set_defaults(fn=cmd_listings)

    sp = sub.add_parser("universe", help="download index member lists")
    sp.add_argument("--code", choices=[*[c for c, d in BY_CODE.items() if d.kind == "index"], "all"], default="all")
    sp.add_argument("--since", type=_date, help="first date for historical lists (KR indices)")
    sp.set_defaults(fn=cmd_universe)

    sp = sub.add_parser("prices", help="download daily price history into the database")
    sp.add_argument("--tickers", help="comma list like KR:005930,US:AAPL")
    sp.add_argument("--universe", choices=list(BY_CODE))
    sp.add_argument("--watchlist", type=int)
    sp.add_argument("--start", type=_date)
    sp.set_defaults(fn=cmd_prices)

    sp = sub.add_parser("preload", help="listings + index lists + prices for index members and watchlists")
    sp.add_argument("--start", type=_date)
    sp.set_defaults(fn=cmd_preload)

    sub.add_parser("status", help="what is stored").set_defaults(fn=cmd_status)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
