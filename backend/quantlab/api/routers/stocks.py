import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from quantlab.api.convert import cov_out, inst_out
from quantlab.api.deps import get_db
from quantlab.api.schemas import BarOut, InstrumentOut, PricesOut, StockDetailOut
from quantlab.config import get_settings
from quantlab.data import repository as repo
from quantlab.data.symbols import MARKETS, normalize_ticker

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _get(db: Session, market: str, ticker: str):
    if market not in MARKETS:
        raise HTTPException(404, "Unknown market")
    try:
        t = normalize_ticker(market, ticker)
    except ValueError as e:
        raise HTTPException(404, str(e))
    inst = repo.get_instrument(db, market, t)
    if inst is None:
        raise HTTPException(404, f"No stock {market}:{t}. Try searching by name.")
    return inst


@router.get("/search", response_model=list[InstrumentOut])
def search(q: str = Query(min_length=1, max_length=50), market: str | None = None,
           limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    return [inst_out(i) for i in repo.search_instruments(db, q, market, limit)]


@router.get("/{market}/{ticker}", response_model=StockDetailOut)
def detail(market: str, ticker: str, start: dt.date | None = None, end: dt.date | None = None,
           db: Session = Depends(get_db)):
    inst = _get(db, market, ticker)
    c = inst.coverage
    if start is None:
        # Without an explicit range, describe what has been downloaded (and whether it is up to date).
        start = c.coverage_start if c and c.status == "ok" and c.coverage_start else \
            dt.date.fromisoformat(get_settings().default_history_start)
    cov = repo.check_coverage(db, inst, start, end or dt.date.today())
    rng = (c.coverage_start, c.coverage_end) if c and c.coverage_start else None
    return StockDetailOut(instrument=inst_out(inst), coverage=cov_out(cov), downloaded_range=rng)


@router.get("/{market}/{ticker}/prices", response_model=PricesOut)
def prices(market: str, ticker: str, start: dt.date | None = None, end: dt.date | None = None,
           snapshot_id: int | None = None, db: Session = Depends(get_db)):
    inst = _get(db, market, ticker)
    sid = snapshot_id if snapshot_id is not None else repo.latest_snapshot_id(db)
    df = repo.load_prices(db, [inst.id], start or dt.date(1990, 1, 1), end or dt.date.today(), sid)
    c = inst.coverage
    bars = [BarOut(**r) for r in df.drop(columns=["instrument_id"]).to_dict("records")]
    return PricesOut(snapshot_id=sid, adjustment=c.adjustment if c else None,
                     provider=c.provider if c else None, bars=bars)
