# QuantLab

Build your own investment strategy without coding, test it on past data, and try it with paper money.
QuantLab is a research and experiment tool. It never promises returns.

**Status: Phase 1 of 6 — data layer, stock search, index lists, watchlists.**

```
backend/    FastAPI + SQLAlchemy + Alembic (Python 3.11+)
  quantlab/data/providers/   swappable data sources (Yahoo, FinanceDataReader, KRX/pykrx, Wikipedia)
  quantlab/data/ingest.py    the only code that writes market data
  quantlab/data/repository.py read-only access used by everything else (backtests will read only here)
  tests/                     pytest, with fake providers (no network needed)
frontend/   Next.js 16 (App Router) + Tailwind + lightweight-charts; desktop web layout, works on phones; light/dark theme
```

## Run it

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
quantlab init-db                 # creates quantlab.db (SQLite)
pytest -q                        # 30 tests, no network needed
quantlab listings                # all Korean + US stocks (names, tickers)
quantlab universe                # S&P 500, Nasdaq 100 (+ KOSPI 200 / KOSDAQ 150 with KRX_ID/KRX_PW)
quantlab prices --tickers KR:005930,US:AAPL --start 2015-01-01
quantlab status
uvicorn quantlab.main:app --reload --port 8000     # API docs at http://localhost:8000/docs
```

`quantlab preload` does listings + all index lists + price history for every index member and every
watchlist in one go (thousands of stocks, slow on free sources; run it overnight).

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000 (proxies /api/* to the backend)
```

After changing backend API models, regenerate the TypeScript types (with the backend venv active):
`npm run gen:api`.

## Data rules

* **Snapshots.** Every download run is a numbered snapshot. A price row is written only when it is new
  or changed (adjusted prices of old dates move after every dividend or split). Reading "as of snapshot
  N" gives exactly what was stored then, so a backtest re-run later sees identical data.
* **Consistent adjusted series.** A refresh re-downloads the stock's whole stored range from the same
  source as before, so one series never mixes sources or adjustment bases.
* **Only finished days.** A daily bar is stored only once its session closed at least 60 minutes ago
  (KRX closes 15:30 KST, NYSE 16:00 New York time; each market uses its own holiday calendar).
* **Adjusted prices.** Yahoo: splits and dividends (`adj = price × AdjClose / Close`). The Korean fallback
  source (Naver via FinanceDataReader) is *not* dividend-adjusted, and is labelled so everywhere.
* **Completeness.** For any date range the app reports per stock: ready / incomplete (lists missing
  trading days) / needs download / unavailable. A failed download (network, login) is kept separate
  from "the source has no data" and can be retried.
* **Index members.** KOSPI 200 / KOSDAQ 150: historical lists sampled monthly from KRX (point-in-time,
  from mid-2014). S&P 500 / Nasdaq 100 / "all stocks": today's members only, with a survivorship-bias
  warning. Delisted stocks may be missing; the app says "Currently listed stocks only".

| Data | Source | Notes |
|---|---|---|
| Korean stock list | FinanceDataReader's daily KRX listing mirror (GitHub) | Korean names; English names for ~40 large caps are seeded, more are filled in from Yahoo when prices are downloaded |
| US stock list | FinanceDataReader (NYSE, NASDAQ, AMEX) | |
| Daily prices | Yahoo (yfinance); Korean fallback: FinanceDataReader | |
| S&P 500, Nasdaq 100 | Wikipedia | current members only |
| KOSPI 200, KOSDAQ 150 | KRX via pykrx | needs `KRX_ID` / `KRX_PW` (free KRX data portal account) |

To switch to a paid source, implement the interface in `backend/quantlab/data/providers/base.py` and
register it in `registry.py`.
