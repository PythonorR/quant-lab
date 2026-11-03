import datetime as dt

import pandas as pd
import pytest

from quantlab.data import ingest
from quantlab.data import repository as repo
from quantlab.data.providers.base import ListingRow, ProviderError
from quantlab.data.providers.krx_cache import KrxCacheListingProvider
from quantlab.data.providers.wikipedia import parse_member_table
from quantlab.data.universes import SURVIVORSHIP_WARNING
from quantlab.db.models import Instrument
from tests.fakes import FakeConstituents, FakeListings, make_providers


def test_point_in_time_membership_has_no_look_ahead(db, now):
    lists = {dt.date(2023, 1, 1): ["000001", "000002"], dt.date(2023, 7, 1): ["000002", "000003"]}
    prov = make_providers(constituents={"KOSPI200": FakeConstituents("fake", True, lists)})
    r = ingest.ingest_universe(db, "KOSPI200", since=dt.date(2023, 1, 1), now=now, providers=prov)
    assert r.sets_written == 16 and not r.errors  # 15 monthly samples (Jan 2023..Mar 2024) + 15 Mar 2024

    def members(day):
        return [i.ticker for i in repo.universe_members(db, "KOSPI200", day).instruments]

    assert members(dt.date(2023, 6, 30)) == ["000001", "000002"]
    assert members(dt.date(2023, 7, 3)) == ["000002", "000003"]  # first session of July
    m = repo.universe_members(db, "KOSPI200", dt.date(2023, 7, 3))
    assert m.point_in_time and SURVIVORSHIP_WARNING not in m.warnings
    # Former member that is not in today's listing is kept (and flagged as not listed).
    assert db.query(Instrument).filter_by(ticker="000001").one().is_listed is False
    # Before history starts: earliest list used, with a warning.
    early = repo.universe_members(db, "KOSPI200", dt.date(2020, 1, 2))
    assert early.as_of_date == dt.date(2023, 1, 2) and "history starts" in early.warnings[0]


def test_rerun_only_fetches_new_months(db, now):
    fake = FakeConstituents("fake", True, {dt.date(2023, 1, 1): ["000001"] * 1})
    prov = make_providers(constituents={"KOSPI200": fake})
    ingest.ingest_universe(db, "KOSPI200", since=dt.date(2024, 1, 1), now=now, providers=prov)
    n = len(fake.calls)
    ingest.ingest_universe(db, "KOSPI200", since=dt.date(2024, 1, 1), now=now, providers=prov)
    assert len(fake.calls) == n


def test_membership_respects_snapshot(db, now):
    fake = FakeConstituents("fake", False, {dt.date(2000, 1, 1): ["AAA", "BBB"]})
    prov = make_providers(constituents={"SP500": fake})
    ingest.ingest_universe(db, "SP500", now=now, providers=prov)
    s1 = repo.latest_snapshot_id(db)
    fake.lists = {dt.date(2000, 1, 1): ["AAA", "CCC"]}
    ingest.ingest_universe(db, "SP500", now=now, providers=prov)
    day = dt.date(2024, 3, 20)
    assert [i.ticker for i in repo.universe_members(db, "SP500", day, s1).instruments] == ["AAA", "BBB"]
    newest = repo.universe_members(db, "SP500", day)
    assert [i.ticker for i in newest.instruments] == ["AAA", "CCC"]
    assert not newest.point_in_time and SURVIVORSHIP_WARNING in newest.warnings


def test_failing_source_stops_early(db, now):
    fake = FakeConstituents("fake", True, {}, fail=True)
    r = ingest.ingest_universe(db, "KOSDAQ150", since=dt.date(2020, 1, 1), now=now,
                               providers=make_providers(constituents={"KOSDAQ150": fake}))
    assert r.sets_written == 0 and len(fake.calls) == 3 and "login" in r.errors[0]


def test_member_table_sanity_check():
    t = pd.DataFrame({"Symbol": ["AAA", "BRK.B"], "Security": ["A", "Berkshire"]})
    with pytest.raises(ProviderError):
        parse_member_table([t], ("Symbol",), ("Security",), (490, 515), dt.date(2024, 1, 1))
    ml = parse_member_table([t], ("Symbol",), ("Security",), (1, 5), dt.date(2024, 1, 1))
    assert ml.tickers == ["AAA", "BRK.B"] and ml.names["BRK.B"] == "Berkshire"


def test_krx_listing_parse():
    rows = ["﻿,Code,ISU_CD,Name,Market"] + [f"{i},{i:06d},X,Name{i},KOSDAQ GLOBAL" for i in range(2500)]
    out = KrxCacheListingProvider._parse("\n".join(rows).encode())
    assert out[5].ticker == "000005" and out[5].exchange == "KOSDAQ"
    with pytest.raises(ProviderError):
        KrxCacheListingProvider._parse("\n".join(rows[:100]).encode())


def _listings(db):
    kr = [ListingRow("005930", "삼성전자", "KOSPI"), ListingRow("005935", "삼성전자우", "KOSPI"),
          ListingRow("000660", "SK하이닉스", "KOSPI")]
    us = [ListingRow("AAPL", "Apple Inc.", "NASDAQ", "Apple Inc."), ListingRow("AA", "Alcoa Corp", "NYSE", "Alcoa Corp"),
          ListingRow("AAL", "American Airlines Group", "NASDAQ", "American Airlines Group")]
    prov = make_providers(listings={"KR": FakeListings({"KR": kr}), "US": FakeListings({"US": us})})
    ingest.ingest_listings(db, "KR", prov)
    ingest.ingest_listings(db, "US", prov)
    db.commit()
    return prov


def test_listing_and_english_search(db):
    _listings(db)
    assert [i.ticker for i in repo.search_instruments(db, "samsung electronics")] == ["005930"]
    assert [i.ticker for i in repo.search_instruments(db, "삼성전자")] == ["005930", "005935"]
    assert repo.search_instruments(db, "hynix")[0].ticker == "000660"
    # Exact ticker beats prefix matches and name matches.
    assert [i.ticker for i in repo.search_instruments(db, "aa", market="US")][:2] == ["AA", "AAL"]
    assert repo.search_instruments(db, "apple")[0].ticker == "AAPL"


def test_delisting_and_all_universe(db, now):
    prov = _listings(db)
    prov.listings["US"].rows["US"] = prov.listings["US"].rows["US"][:2]  # AAL disappears
    r = ingest.ingest_listings(db, "US", prov)
    db.commit()
    assert r.delisted == 1
    m = repo.universe_members(db, "US_ALL", dt.date(2024, 3, 1))
    assert [i.ticker for i in m.instruments] == ["AA", "AAPL"]
    assert SURVIVORSHIP_WARNING in m.warnings
    # Delisted stocks rank after listed ones in search.
    assert repo.search_instruments(db, "a", market="US")[-1].ticker == "AAL"
