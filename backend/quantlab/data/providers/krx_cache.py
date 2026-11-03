"""Korean stock listings from FinanceDataReader's public mirror of the KRX listing file.

The mirror (a GitHub repository updated every trading day) avoids KRX's login requirement.
File: <base>/<YYYY-MM-DD>.csv with columns Code, Name, Market (KOSPI, KOSDAQ, KOSDAQ GLOBAL, KONEX).
"""
from __future__ import annotations

import datetime as dt
import io

import httpx
import pandas as pd

from quantlab.data.providers.base import ListingRow, ProviderError
from quantlab.data.symbols import normalize_ticker

MIN_EXPECTED_ROWS = 2000  # KRX lists ~2,700 stocks; fewer means a broken file


class KrxCacheListingProvider:
    name = "krx_cache"

    def __init__(self, base_url: str, user_agent: str, today: dt.date | None = None):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.today = today

    def fetch_listings(self, market: str) -> list[ListingRow]:
        if market != "KR":
            raise ProviderError("KRX listing provider covers KR only")
        day = self.today or dt.date.today()
        last_err = None
        with httpx.Client(timeout=30, headers={"User-Agent": self.user_agent}, follow_redirects=True) as c:
            for back in range(0, 15):  # newest file within two weeks (weekends / holidays)
                d = day - dt.timedelta(days=back)
                r = c.get(f"{self.base_url}/{d.isoformat()}.csv")
                if r.status_code == 404:
                    continue
                if r.status_code != 200:
                    last_err = f"HTTP {r.status_code}"
                    continue
                return self._parse(r.content)
        raise ProviderError(f"No KRX listing file found in the last 15 days ({last_err or 'not found'})")

    @staticmethod
    def _parse(content: bytes) -> list[ListingRow]:
        df = pd.read_csv(io.BytesIO(content), dtype={"Code": str}, encoding="utf-8-sig")
        out = []
        for r in df.itertuples(index=False):
            market = str(r.Market).upper()
            exchange = "KOSDAQ" if market.startswith("KOSDAQ") else market
            try:
                t = normalize_ticker("KR", str(r.Code))
            except ValueError:
                continue
            out.append(ListingRow(ticker=t, name=str(r.Name).strip(), exchange=exchange))
        if len(out) < MIN_EXPECTED_ROWS:
            raise ProviderError(f"KRX listing has only {len(out)} rows; refusing to use it")
        return out
