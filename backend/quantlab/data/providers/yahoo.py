"""Yahoo Finance (via yfinance): daily prices for US and KOSPI/KOSDAQ stocks.

We request auto_adjust=False: Yahoo's Open/High/Low/Close are split-adjusted and 'Adj Close' is
additionally dividend-adjusted, so adjusted OHLC = OHLC * AdjClose / Close.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from quantlab.data.providers.base import SPLITS_AND_DIVIDENDS, PriceHistory, ProviderError, validate_bars
from quantlab.data.symbols import yahoo_symbol


class YahooPriceProvider:
    name = "yahoo"

    def supports(self, market, ticker, exchange) -> bool:
        return yahoo_symbol(market, ticker, exchange) is not None

    def fetch_daily(self, market, ticker, exchange, start: dt.date, end: dt.date) -> PriceHistory:
        import yfinance as yf

        sym = yahoo_symbol(market, ticker, exchange)
        if sym is None:
            raise ProviderError(f"Yahoo does not cover {market}:{ticker}")
        try:
            t = yf.Ticker(sym)
            raw = t.history(
                start=start.isoformat(),
                end=(end + dt.timedelta(days=1)).isoformat(),  # yfinance 'end' is exclusive
                interval="1d",
                auto_adjust=False,
                actions=False,
                raise_errors=True,
            )
        except Exception as e:  # yfinance raises many types
            raise ProviderError(f"Yahoo download failed for {sym}: {e}") from e
        if raw is None or raw.empty:
            return PriceHistory(pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"]),
                                self.name, SPLITS_AND_DIVIDENDS)
        df = raw.rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close",
                     "Adj Close": "adj_close", "Volume": "volume"}
        )
        # Index is tz-aware in the exchange's time zone; the calendar date is the session date.
        df.index = [ts.date() for ts in df.index]
        df = validate_bars(df)
        df = df[(df.index >= start) & (df.index <= end)]

        name_en = None
        try:
            info = t.get_info() or {}
            name_en = info.get("longName") or info.get("shortName")
        except Exception:
            pass  # the name is a nice-to-have
        return PriceHistory(df, self.name, SPLITS_AND_DIVIDENDS, name_en=name_en)
