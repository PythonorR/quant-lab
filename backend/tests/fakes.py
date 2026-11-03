"""Test doubles for the data providers. They implement the same interfaces as the real ones."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from quantlab.data import calendars
from quantlab.data.providers.base import (
    SPLITS_AND_DIVIDENDS, ListingRow, MemberList, PriceHistory, ProviderError,
)
from quantlab.data.providers.registry import Providers


class FakePrices:
    """Deterministic bars on every session: close = 100 + n (n = session index), open = close - 1.
    ``adj_ratio`` sets adj_close/close for dates before ``adj_before`` (simulates a dividend).
    ``drop`` dates are omitted (simulates a source gap). ``extra_dates`` adds bars past the
    requested end (simulates an unfinished live bar)."""

    def __init__(self, name="fake", markets=("KR", "US"), fail=False, empty=False):
        self.name = name
        self.markets = markets
        self.fail = fail
        self.empty = empty
        self.adj_ratio = 1.0
        self.adj_before: dt.date | None = None
        self.drop: set[dt.date] = set()
        self.extra_dates: list[dt.date] = []
        self.calls: list[tuple] = []

    def supports(self, market, ticker, exchange):
        return market in self.markets

    def fetch_daily(self, market, ticker, exchange, start, end):
        self.calls.append((market, ticker, start, end))
        if self.fail:
            raise ProviderError("source down")
        cols = ["open", "high", "low", "close", "adj_close", "volume"]
        if self.empty:
            return PriceHistory(pd.DataFrame(columns=cols), self.name, SPLITS_AND_DIVIDENDS)
        days = [d for d in calendars.sessions(market, dt.date(2000, 1, 3), end + dt.timedelta(days=10))]
        rows = {}
        for n, d in enumerate(days):
            if d < start or d in self.drop or (d > end and d not in self.extra_dates):
                continue
            close = 100.0 + n
            ratio = self.adj_ratio if (self.adj_before and d < self.adj_before) else 1.0
            rows[d] = dict(open=close - 1, high=close + 2, low=close - 3, close=close,
                           adj_close=close * ratio, volume=1000.0 + n)
        df = pd.DataFrame.from_dict(rows, orient="index", columns=cols)
        return PriceHistory(df, self.name, SPLITS_AND_DIVIDENDS, name_en=f"{ticker} Corp")


class FakeListings:
    name = "fake_listings"

    def __init__(self, rows: dict[str, list[ListingRow]]):
        self.rows = rows

    def fetch_listings(self, market):
        return list(self.rows[market])


class FakeConstituents:
    """``lists`` maps an effective date to the member tickers from that date on."""

    def __init__(self, name, point_in_time, lists: dict[dt.date, list[str]], fail=False):
        self.name = name
        self.point_in_time = point_in_time
        self.lists = lists
        self.fail = fail
        self.calls: list[dt.date] = []

    def fetch_members(self, code, as_of):
        self.calls.append(as_of)
        if self.fail:
            raise ProviderError("login required")
        eff = max((d for d in self.lists if d <= as_of), default=None)
        if eff is None:
            raise ProviderError("no data that early")
        return MemberList(as_of_date=as_of, tickers=list(self.lists[eff]))


def make_providers(prices=None, listings=None, constituents=None) -> Providers:
    return Providers(listings=listings or {}, prices=prices or [FakePrices()], constituents=constituents or {})
