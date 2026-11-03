"""FinanceDataReader: US listings and a fallback source of Korean daily prices."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from quantlab.data.providers.base import NO_DIVIDENDS, ListingRow, PriceHistory, ProviderError, validate_bars
from quantlab.data.symbols import normalize_ticker


class FdrUsListingProvider:
    name = "fdr"

    def fetch_listings(self, market: str) -> list[ListingRow]:
        if market != "US":
            raise ProviderError("FDR listing provider here is used for US only")
        import FinanceDataReader as fdr

        rows: dict[str, ListingRow] = {}
        for exch in ("NYSE", "NASDAQ", "AMEX"):
            try:
                df = fdr.StockListing(exch)
            except Exception as e:
                raise ProviderError(f"FDR {exch} listing failed: {e}") from e
            for r in df.itertuples(index=False):
                sym = str(getattr(r, "Symbol", "") or "").strip()
                name = str(getattr(r, "Name", "") or "").strip()
                if not sym or not name:
                    continue
                try:
                    t = normalize_ticker("US", sym)
                except ValueError:
                    continue
                rows.setdefault(t, ListingRow(ticker=t, name=name, exchange=exch, name_en=name))
        return list(rows.values())


class FdrKrPriceProvider:
    """Naver-sourced Korean prices. These are NOT dividend-adjusted (labelled 'no_dividends');
    the adj_close column simply repeats close. Used only when Yahoo has nothing."""

    name = "fdr"

    def supports(self, market, ticker, exchange) -> bool:
        return market == "KR"

    def fetch_daily(self, market, ticker, exchange, start: dt.date, end: dt.date) -> PriceHistory:
        import FinanceDataReader as fdr

        try:
            raw = fdr.DataReader(ticker, start.isoformat(), end.isoformat())
        except Exception as e:
            raise ProviderError(f"FDR download failed for {ticker}: {e}") from e
        if raw is None or raw.empty:
            return PriceHistory(pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"]),
                                self.name, NO_DIVIDENDS)
        df = raw.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df["adj_close"] = df["close"]
        df.index = [pd.Timestamp(ts).date() for ts in df.index]
        df = validate_bars(df)
        df = df[(df.index >= start) & (df.index <= end)]
        return PriceHistory(df, self.name, NO_DIVIDENDS)
