"""Point-in-time KOSPI 200 / KOSDAQ 150 members from KRX via pykrx.

pykrx >= 1.2 needs a (free) KRX data portal account: set KRX_ID and KRX_PW environment
variables. KRX serves constituent files from 2014-05-02 onward.
"""
from __future__ import annotations

import datetime as dt
import os

from quantlab.data.providers.base import MemberList, ProviderError
from quantlab.data.symbols import normalize_ticker

INDEX_CODES = {"KOSPI200": ("1028", (195, 205)), "KOSDAQ150": ("2203", (145, 155))}


class PykrxConstituentProvider:
    name = "pykrx"
    point_in_time = True

    def fetch_members(self, universe_code: str, as_of: dt.date) -> MemberList:
        if universe_code not in INDEX_CODES:
            raise ProviderError(f"pykrx provider does not know {universe_code}")
        if not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
            raise ProviderError("KRX login required: set KRX_ID and KRX_PW (free account at data.krx.co.kr)")
        from pykrx import stock

        code, (lo, hi) = INDEX_CODES[universe_code]
        try:
            raw = stock.get_index_portfolio_deposit_file(code, as_of.strftime("%Y%m%d"), alternative=True)
        except Exception as e:
            raise ProviderError(f"KRX constituent download failed: {e}") from e
        tickers = sorted({normalize_ticker("KR", str(t)) for t in (raw or [])})
        if not lo <= len(tickers) <= hi:
            raise ProviderError(
                f"{universe_code} on {as_of} returned {len(tickers)} members, expected {lo}-{hi}"
            )
        return MemberList(as_of_date=as_of, tickers=tickers)
