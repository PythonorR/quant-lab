import datetime as dt

from fastapi.testclient import TestClient

from quantlab.data.providers.base import ListingRow
from quantlab.data.providers.registry import set_providers
from quantlab.data import ingest
from quantlab.main import app
from tests.fakes import FakeListings, FakePrices, make_providers


def test_end_to_end(db):
    prov = make_providers(prices=[FakePrices()],
                          listings={"US": FakeListings({"US": [ListingRow("AAPL", "Apple Inc.", "NASDAQ", "Apple Inc.")]})})
    ingest.ingest_listings(db, "US", prov)
    db.commit()
    set_providers(prov)
    c = TestClient(app)

    hits = c.get("/api/stocks/search", params={"q": "apple"}).json()
    assert hits[0]["ticker"] == "AAPL"
    iid = hits[0]["id"]

    d = c.get("/api/stocks/US/aapl", params={"start": "2024-01-02"}).json()
    assert d["coverage"]["status"] == "needs_download"

    job = c.post("/api/data/ensure", json={"instrument_ids": [iid], "start": "2024-01-02"})
    assert job.status_code == 202
    j = c.get(f"/api/data/jobs/{job.json()['id']}").json()  # TestClient runs background tasks before returning
    assert j["status"] == "done" and j["done"] == 1 and j["failures"] == []

    cov = c.post("/api/data/coverage", json={"instrument_ids": [iid], "start": "2024-01-02", "end": "2024-06-28"}).json()
    assert cov["all_downloaded"] and cov["ready"] == 1

    bars = c.get("/api/stocks/US/AAPL/prices", params={"start": "2024-01-02", "end": "2024-01-05"}).json()
    assert [b["date"] for b in bars["bars"]] == ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    assert bars["adjustment"] == "splits_and_dividends"

    w = c.post("/api/watchlists", json={"name": "My picks"}).json()
    w = c.post(f"/api/watchlists/{w['id']}/items", json={"instrument_id": iid}).json()
    assert [i["ticker"] for i in w["items"]] == ["AAPL"]
    assert c.post("/api/data/coverage", json={"watchlist_id": w["id"], "start": "2024-01-02"}).json()["ready"] == 1

    unis = {u["code"]: u for u in c.get("/api/universes").json()}
    assert unis["US_ALL"]["member_count"] == 1
    assert unis["SP500"]["warnings"] == ["This list has not been downloaded yet."]
    assert c.get("/api/stocks/US/ZZZZ").status_code == 404


def test_stock_page_describes_downloaded_range(db):
    prov = make_providers(prices=[FakePrices()])
    set_providers(prov)
    inst = ingest.get_or_create_instrument(db, "US", "MSFT", name="Microsoft")
    db.commit()
    c = TestClient(app)
    c.post("/api/data/ensure", json={"instrument_ids": [inst.id], "start": "2024-01-02"})
    # No explicit start: the page reports the downloaded range (from 2024), not "missing since 2010".
    cov = c.get("/api/stocks/US/MSFT").json()["coverage"]
    assert cov["status"] == "ready" and cov["start"] == "2024-01-02" and cov["bars"] > 0
    # Asking for an earlier start explicitly still says a download is needed.
    assert c.get("/api/stocks/US/MSFT", params={"start": "2015-01-02"}).json()["coverage"]["status"] == "needs_download"
