from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from quantlab.api.convert import inst_out
from quantlab.api.deps import get_db
from quantlab.api.schemas import WatchlistIn, WatchlistItemIn, WatchlistOut
from quantlab.db.models import LOCAL_USER_ID, Instrument, Watchlist, WatchlistItem

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


def _out(w: Watchlist) -> WatchlistOut:
    return WatchlistOut(id=w.id, name=w.name, created_at=w.created_at, items=[inst_out(i.instrument) for i in w.items])


def _get(db: Session, wid: int) -> Watchlist:
    w = db.get(Watchlist, wid)
    if w is None or w.user_id != LOCAL_USER_ID:
        raise HTTPException(404, "No such watchlist")
    return w


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(db: Session = Depends(get_db)):
    return [_out(w) for w in db.scalars(select(Watchlist).where(Watchlist.user_id == LOCAL_USER_ID).order_by(Watchlist.id))]


@router.post("", response_model=WatchlistOut, status_code=201)
def create(body: WatchlistIn, db: Session = Depends(get_db)):
    w = Watchlist(name=body.name.strip(), user_id=LOCAL_USER_ID)
    db.add(w)
    db.commit()
    return _out(w)


@router.get("/{wid}", response_model=WatchlistOut)
def get_one(wid: int, db: Session = Depends(get_db)):
    return _out(_get(db, wid))


@router.patch("/{wid}", response_model=WatchlistOut)
def rename(wid: int, body: WatchlistIn, db: Session = Depends(get_db)):
    w = _get(db, wid)
    w.name = body.name.strip()
    db.commit()
    return _out(w)


@router.delete("/{wid}", status_code=204)
def delete(wid: int, db: Session = Depends(get_db)):
    db.delete(_get(db, wid))
    db.commit()


@router.post("/{wid}/items", response_model=WatchlistOut)
def add_item(wid: int, body: WatchlistItemIn, db: Session = Depends(get_db)):
    w = _get(db, wid)
    if db.get(Instrument, body.instrument_id) is None:
        raise HTTPException(404, "No such stock")
    if not any(i.instrument_id == body.instrument_id for i in w.items):
        w.items.append(WatchlistItem(instrument_id=body.instrument_id))
        db.commit()
        db.refresh(w)
    return _out(w)


@router.delete("/{wid}/items/{instrument_id}", response_model=WatchlistOut)
def remove_item(wid: int, instrument_id: int, db: Session = Depends(get_db)):
    w = _get(db, wid)
    w.items = [i for i in w.items if i.instrument_id != instrument_id]
    db.commit()
    db.refresh(w)
    return _out(w)
