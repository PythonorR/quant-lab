"""Markets and ticker normalisation.

Canonical tickers stored in the DB:
* KR: 6-character KRX short code, e.g. "005930" (Samsung Electronics). Kept as text so the
  leading zeros survive.
* US: upper case, share classes with a dot, e.g. "BRK.B" (Yahoo writes "BRK-B").
"""
from __future__ import annotations

import re

MARKETS = ("KR", "US")
CURRENCY = {"KR": "KRW", "US": "USD"}
# exchange_calendars codes
CALENDAR = {"KR": "XKRX", "US": "XNYS"}

_KR_RE = re.compile(r"^[0-9A-Z]{6}$")


def normalize_ticker(market: str, ticker: str) -> str:
    t = ticker.strip().upper()
    if market == "KR":
        if t.isdigit():
            t = t.zfill(6)
        if not _KR_RE.match(t):
            raise ValueError(f"Not a valid Korean stock code: {ticker!r}")
        return t
    if market == "US":
        t = t.replace("-", ".").replace("/", ".").replace(" ", "")
        if not t or len(t) > 12:
            raise ValueError(f"Not a valid US ticker: {ticker!r}")
        return t
    raise ValueError(f"Unknown market {market!r}")


def yahoo_symbol(market: str, ticker: str, exchange: str | None) -> str | None:
    """Yahoo Finance symbol, or None when Yahoo does not cover the stock."""
    if market == "US":
        return ticker.replace(".", "-")
    if market == "KR":
        suffix = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}.get((exchange or "").upper())
        return ticker + suffix if suffix else None
    return None
