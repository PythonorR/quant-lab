import datetime as dt

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from quantlab.api.convert import cov_out
from quantlab.api.deps import get_db
from quantlab.api.schemas import CoverageRequest, CoverageSummaryOut, EnsureRequest, JobOut
from quantlab.config import get_settings
from quantlab.data import jobs
from quantlab.data import repository as repo
from quantlab.data.universes import BY_CODE
from quantlab.db.models import DataJob

router = APIRouter(prefix="/api/data", tags=["data"])


def _job_out(j: DataJob) -> JobOut:
    return JobOut(id=j.id, kind=j.kind, status=j.status, done=j.done, total=j.total, failures=j.failures or [],
                  message=j.message, snapshot_id=j.snapshot_id, created_at=j.created_at, finished_at=j.finished_at)


def _check(req: EnsureRequest):
    if req.universe and req.universe not in BY_CODE:
        raise HTTPException(400, f"Unknown universe {req.universe}")


@router.post("/ensure", response_model=JobOut, status_code=202)
def ensure(req: EnsureRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Start downloading whatever price history is missing. Poll GET /api/data/jobs/{id}."""
    _check(req)
    start = req.start or dt.date.fromisoformat(get_settings().default_history_start)
    job = jobs.create_price_job(db, req.instrument_ids, req.universe, req.watchlist_id, start)
    if job.total == 0:
        raise HTTPException(400, "No stocks to download. Is the universe list downloaded?")
    bg.add_task(jobs.run_price_job, job.id)
    return _job_out(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
def job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(DataJob, job_id)
    if j is None:
        raise HTTPException(404, "No such job")
    return _job_out(j)


@router.get("/jobs", response_model=list[JobOut])
def recent_jobs(db: Session = Depends(get_db)):
    return [_job_out(j) for j in db.scalars(select(DataJob).order_by(DataJob.id.desc()).limit(20))]


@router.post("/coverage", response_model=CoverageSummaryOut)
def coverage(req: CoverageRequest, db: Session = Depends(get_db)):
    """Database-only check: is everything needed for [start, end] stored? Backtests call this first."""
    _check(req)
    start = req.start or dt.date.fromisoformat(get_settings().default_history_start)
    end = req.end or dt.date.today()
    targets = jobs.resolve_targets(db, req.instrument_ids, req.universe, req.watchlist_id)
    items = [repo.check_coverage(db, i, start, end) for i in targets]
    counts = {k: sum(1 for c in items if c.status == k) for k in ("ready", "incomplete", "needs_download", "unavailable")}
    return CoverageSummaryOut(**counts, all_downloaded=bool(items) and counts["needs_download"] == 0 and counts["unavailable"] == 0,
                              items=[cov_out(c) for c in items])
