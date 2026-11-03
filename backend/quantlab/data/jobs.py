"""Background download jobs ("get price history for these stocks"), tracked in the data_jobs table."""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantlab.data import ingest
from quantlab.db.models import DataJob, Instrument, UniverseMember, UniverseMemberSet, Watchlist, utcnow
from quantlab.data.universes import BY_CODE
from quantlab.db.session import new_session

log = logging.getLogger(__name__)


def resolve_targets(s: Session, instrument_ids: list[int], universe: str | None, watchlist_id: int | None) -> list[Instrument]:
    """Every stock needed. For an index universe this is every stock that was EVER a member in the
    stored history (a backtest over past dates needs the former members too)."""
    ids: set[int] = set(instrument_ids)
    if universe:
        d = BY_CODE[universe]
        if d.kind == "all":
            ids |= set(s.scalars(select(Instrument.id).where(Instrument.market == d.market, Instrument.is_listed)))
        else:
            ids |= set(s.scalars(select(UniverseMember.instrument_id).join(UniverseMemberSet)
                                 .where(UniverseMemberSet.universe_code == universe)))
    if watchlist_id is not None:
        wl = s.get(Watchlist, watchlist_id)
        if wl:
            ids |= {it.instrument_id for it in wl.items}
    if not ids:
        return []
    return list(s.scalars(select(Instrument).where(Instrument.id.in_(ids)).order_by(Instrument.market, Instrument.ticker)))


def create_price_job(s: Session, instrument_ids: list[int], universe: str | None, watchlist_id: int | None,
                     start: dt.date) -> DataJob:
    targets = resolve_targets(s, instrument_ids, universe, watchlist_id)
    job = DataJob(kind="prices", params={"instrument_ids": [i.id for i in targets], "start": start.isoformat(),
                                         "universe": universe, "watchlist_id": watchlist_id},
                  total=len(targets))
    s.add(job)
    s.commit()
    return job


def run_price_job(job_id: int, providers=None) -> None:
    s = new_session()
    try:
        job = s.get(DataJob, job_id)
        job.status = "running"
        s.commit()
        ids = job.params["instrument_ids"]
        insts = list(s.scalars(select(Instrument).where(Instrument.id.in_(ids)))) if ids else []
        failures: list[dict] = []

        def progress(done, total, r):
            job.done = done
            if r.outcome in ("failed", "unavailable"):
                failures.append({"ticker": r.ticker, "instrument_id": r.instrument_id,
                                 "outcome": r.outcome, "message": r.message})
                job.failures = list(failures)
            s.commit()

        snap, _ = ingest.ensure_prices_many(
            s, insts, dt.date.fromisoformat(job.params["start"]), description=f"job {job.id}",
            providers=providers, progress=progress)
        job.snapshot_id = snap.id
        job.status = "done"
        job.message = (f"{len(insts) - len(failures)} of {len(insts)} stocks ready"
                       + (f"; {len(failures)} could not be downloaded" if failures else ""))
    except Exception as e:  # pragma: no cover - safety net
        log.exception("job %s failed", job_id)
        s.rollback()
        job = s.get(DataJob, job_id)
        job.status, job.message = "failed", str(e)
    finally:
        job.finished_at = utcnow()
        s.commit()
        s.close()
