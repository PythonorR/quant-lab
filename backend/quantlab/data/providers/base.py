"""Data provider interfaces.

The rest of the app depends only on these interfaces, so a free source (Yahoo, KRX, Wikipedia)
can later be swapped for a paid API by writing one new class and registering it in
``registry.py``. Providers only fetch; they never touch the database.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

# Price adjustment basis, shown to the user on every backtest.
SPLITS_AND_DIVIDENDS = "splits_and_dividends"
NO_DIVIDENDS = "no_dividends"

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


class ProviderError(Exception):
    """The source could not be reached or returned something unusable."""


@dataclass
class ListingRow:
    ticker: str  # canonical
    name: str
    exchange: str | None
    name_en: str | None = None


@dataclass
class PriceHistory:
    """Daily bars indexed by ``datetime.date`` with PRICE_COLUMNS."""

    bars: pd.DataFrame
    provider: str
    adjustment: str
    name_en: str | None = None  # English company name, if the source knows it


@dataclass
class MemberList:
    as_of_date: dt.date
    tickers: list[str]
    names: dict[str, str] = field(default_factory=dict)


class ListingProvider(Protocol):
    name: str

    def fetch_listings(self, market: str) -> list[ListingRow]: ...


class PriceProvider(Protocol):
    name: str

    def supports(self, market: str, ticker: str, exchange: str | None) -> bool: ...

    def fetch_daily(
        self, market: str, ticker: str, exchange: str | None, start: dt.date, end: dt.date
    ) -> PriceHistory:
        """Bars for sessions in [start, end] inclusive. Empty bars = no data for that range."""
        ...


class ConstituentProvider(Protocol):
    name: str
    point_in_time: bool  # True if fetch_members honours past dates

    def fetch_members(self, universe_code: str, as_of: dt.date) -> MemberList: ...


def validate_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Common clean-up: required columns, no NaN prices, positive prices, sorted unique dates."""
    missing = [c for c in PRICE_COLUMNS if c not in df.columns]
    if missing:
        raise ProviderError(f"Missing columns {missing}")
    df = df[PRICE_COLUMNS].copy()
    df = df.dropna(subset=["open", "high", "low", "close", "adj_close"])
    df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
    df["volume"] = df["volume"].fillna(0).astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df
