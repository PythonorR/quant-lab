"""API request/response models."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class InstrumentOut(BaseModel):
    id: int
    market: str
    ticker: str
    name: str
    name_en: str | None
    exchange: str | None
    currency: str
    is_listed: bool


class CoverageOut(BaseModel):
    instrument_id: int
    market: str
    ticker: str
    status: str
    start: dt.date
    end: dt.date
    first_bar: dt.date | None
    last_bar: dt.date | None
    bars: int
    expected_sessions: int
    missing_count: int
    missing_dates: list[dt.date]
    provider: str | None
    adjustment: str | None
    notes: list[str]


class StockDetailOut(BaseModel):
    instrument: InstrumentOut
    coverage: CoverageOut
    downloaded_range: tuple[dt.date, dt.date] | None


class BarOut(BaseModel):
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    adj_open: float
    adj_high: float
    adj_low: float
    adj_close: float
    volume: float


class PricesOut(BaseModel):
    snapshot_id: int
    adjustment: str | None
    provider: str | None
    bars: list[BarOut]


class EnsureRequest(BaseModel):
    instrument_ids: list[int] = Field(default_factory=list)
    universe: str | None = None
    watchlist_id: int | None = None
    start: dt.date | None = None


class CoverageRequest(EnsureRequest):
    end: dt.date | None = None


class CoverageSummaryOut(BaseModel):
    ready: int
    incomplete: int
    needs_download: int
    unavailable: int
    all_downloaded: bool  # nothing needs downloading and nothing is unavailable
    items: list[CoverageOut]


class JobOut(BaseModel):
    id: int
    kind: str
    status: str
    done: int
    total: int
    failures: list[dict]
    message: str | None
    snapshot_id: int | None
    created_at: dt.datetime
    finished_at: dt.datetime | None


class UniverseOut(BaseModel):
    code: str
    name: str
    market: str
    kind: str
    point_in_time: bool
    source: str | None
    updated_at: dt.datetime | None
    member_count: int
    history_start: dt.date | None
    warnings: list[str]


class UniverseMembersOut(BaseModel):
    code: str
    name: str
    date: dt.date
    as_of_date: dt.date | None
    point_in_time: bool
    warnings: list[str]
    members: list[InstrumentOut]


class WatchlistIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WatchlistItemIn(BaseModel):
    instrument_id: int


class WatchlistOut(BaseModel):
    id: int
    name: str
    created_at: dt.datetime
    items: list[InstrumentOut]
