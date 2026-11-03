"""FastAPI application. Run: uvicorn quantlab.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quantlab.api.routers import data, stocks, universes, watchlists

DISCLAIMER = ("QuantLab is a research and experimentation tool. It does not give investment advice "
              "and never promises returns. Past results do not predict future results.")

app = FastAPI(title="QuantLab API", version="0.1.0", description=DISCLAIMER)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (stocks.router, data.router, universes.router, watchlists.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    return {"ok": True, "disclaimer": DISCLAIMER}
