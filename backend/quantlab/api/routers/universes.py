import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quantlab.api.convert import inst_out
from quantlab.api.deps import get_db
from quantlab.api.schemas import UniverseMembersOut, UniverseOut
from quantlab.data import repository as repo
from quantlab.data.universes import BY_CODE, CATALOG
from quantlab.db.models import Universe, UniverseMemberSet

router = APIRouter(prefix="/api/universes", tags=["universes"])


@router.get("", response_model=list[UniverseOut])
def list_universes(db: Session = Depends(get_db)):
    out = []
    today = dt.date.today()
    for d in CATALOG:
        u = db.get(Universe, d.code)
        m = repo.universe_members(db, d.code, today)
        start = db.scalar(select(func.min(UniverseMemberSet.as_of_date)).where(UniverseMemberSet.universe_code == d.code))
        out.append(UniverseOut(code=d.code, name=d.name, market=d.market, kind=d.kind,
                               point_in_time=bool(u and u.point_in_time), source=u.source if u else None,
                               updated_at=u.updated_at if u else None, member_count=len(m.instruments),
                               history_start=start if (u and u.point_in_time) else None, warnings=m.warnings))
    return out


@router.get("/{code}/members", response_model=UniverseMembersOut)
def members(code: str, date: dt.date | None = None, db: Session = Depends(get_db)):
    if code not in BY_CODE:
        raise HTTPException(404, "Unknown universe")
    m = repo.universe_members(db, code, date or dt.date.today())
    return UniverseMembersOut(code=m.code, name=m.name, date=m.date, as_of_date=m.as_of_date,
                              point_in_time=m.point_in_time, warnings=m.warnings,
                              members=[inst_out(i) for i in m.instruments])
