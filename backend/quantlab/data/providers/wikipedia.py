"""Current S&P 500 and Nasdaq-100 members from Wikipedia.

Wikipedia gives the CURRENT list only, so these universes are not point-in-time: a backtest on
them suffers survivorship bias and the app shows a warning.
"""
from __future__ import annotations

import datetime as dt
import io

import httpx
import pandas as pd

from quantlab.data.providers.base import MemberList, ProviderError
from quantlab.data.symbols import normalize_ticker

PAGES = {
    "SP500": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", ("Symbol",), ("Security",), (490, 515)),
    "NDX100": ("https://en.wikipedia.org/wiki/Nasdaq-100", ("Ticker", "Symbol"), ("Company", "Security"), (95, 110)),
}


class WikipediaConstituentProvider:
    name = "wikipedia"
    point_in_time = False

    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    def fetch_members(self, universe_code: str, as_of: dt.date) -> MemberList:
        if universe_code not in PAGES:
            raise ProviderError(f"Wikipedia provider does not know {universe_code}")
        url, ticker_cols, name_cols, (lo, hi) = PAGES[universe_code]
        try:
            r = httpx.get(url, headers={"User-Agent": self.user_agent}, timeout=30, follow_redirects=True)
            r.raise_for_status()
            tables = pd.read_html(io.StringIO(r.text), attrs={"id": "constituents"})
        except Exception as e:
            raise ProviderError(f"Wikipedia download failed for {universe_code}: {e}") from e
        return parse_member_table(tables, ticker_cols, name_cols, (lo, hi), as_of)


def parse_member_table(tables, ticker_cols, name_cols, bounds, as_of) -> MemberList:
    for t in tables:
        tcol = next((c for c in ticker_cols if c in t.columns), None)
        if tcol is None:
            continue
        ncol = next((c for c in name_cols if c in t.columns), None)
        tickers, names = [], {}
        for _, row in t.iterrows():
            try:
                tk = normalize_ticker("US", str(row[tcol]))
            except ValueError:
                continue
            tickers.append(tk)
            if ncol:
                names[tk] = str(row[ncol])
        tickers = sorted(set(tickers))
        lo, hi = bounds
        if not lo <= len(tickers) <= hi:
            raise ProviderError(f"Member table has {len(tickers)} rows, expected {lo}-{hi}; refusing to use it")
        return MemberList(as_of_date=as_of, tickers=tickers, names=names)
    raise ProviderError("No constituents table found")
