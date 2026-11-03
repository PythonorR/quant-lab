import datetime as dt

import pytest
from sqlalchemy import func, select

from quantlab.data import calendars, ingest
from quantlab.data import repository as repo
from quantlab.db.models import PriceBar, PriceFetchLog
from tests.fakes import FakePrices, make_providers

START = dt.date(2024, 1, 2)


def _inst(db, market="US", ticker="AAA"):
    i = ingest.get_or_create_instrument(db, market, ticker, name=ticker)
    db.commit()
    return i


def _run(db, inst, prov, now, start=START):
    snap = ingest.new_snapshot(db, "prices")
    r = ingest.ensure_prices(db, inst, start, snap, now=now, providers=prov)
    db.commit()
    return snap, r


def _rows(db):
    return db.scalar(select(func.count()).select_from(PriceBar))


def test_first_download_stores_every_finished_session(db, now):
    inst = _inst(db)
    fake = FakePrices()
    _, r = _run(db, inst, make_providers([fake]), now)
    expected = calendars.sessions("US", START, dt.date(2024, 3, 14))
    assert r.outcome == "downloaded" and r.rows_written == len(expected)
    cov = repo.check_coverage(db, inst, START, dt.date(2024, 3, 31), now=now)
    assert cov.status == "ready"
    assert cov.end == dt.date(2024, 3, 14)  # clipped to the last finished session
    assert cov.bars == len(expected) and cov.missing_count == 0


def test_unfinished_bar_is_never_stored(db, now):
    inst = _inst(db)
    fake = FakePrices()
    fake.extra_dates = [dt.date(2024, 3, 15)]  # NYSE has not closed yet at `now`
    _run(db, inst, make_providers([fake]), now)
    assert db.scalar(select(func.max(PriceBar.date))) == dt.date(2024, 3, 14)


def test_second_call_is_a_no_op(db, now):
    inst = _inst(db)
    fake = FakePrices()
    _run(db, inst, make_providers([fake]), now)
    n = _rows(db)
    _, r = _run(db, inst, make_providers([fake]), now)
    assert r.outcome == "up_to_date" and _rows(db) == n and len(fake.calls) == 1


def test_new_day_refetches_whole_range_but_writes_only_new_rows(db, now):
    inst = _inst(db)
    fake = FakePrices()
    _run(db, inst, make_providers([fake]), now)
    n = _rows(db)
    later = now + dt.timedelta(days=4)  # Tue 19 Mar: 15 and 18 Mar are now final
    _, r = _run(db, inst, make_providers([fake]), later)
    assert fake.calls[-1][2] == START  # full range requested again
    assert r.rows_written == 2 and _rows(db) == n + 2


def test_dividend_adjustment_creates_new_version_and_old_snapshot_is_reproducible(db, now):
    inst = _inst(db)
    fake = FakePrices()
    snap1, _ = _run(db, inst, make_providers([fake]), now)
    n = _rows(db)

    # A dividend on 1 Mar: every adjusted price before it moves by 2%.
    fake.adj_ratio, fake.adj_before = 0.98, dt.date(2024, 3, 1)
    later = now + dt.timedelta(days=4)
    snap2, r = _run(db, inst, make_providers([fake]), later)
    changed = len(calendars.sessions("US", START, dt.date(2024, 2, 29)))
    assert r.rows_written == changed + 2  # changed history + 2 new days
    assert _rows(db) == n + changed + 2

    d = dt.date(2024, 1, 2)
    old = repo.load_prices(db, [inst.id], d, d, snapshot_id=snap1.id).iloc[0]
    new = repo.load_prices(db, [inst.id], d, d, snapshot_id=snap2.id).iloc[0]
    assert old.adj_close == pytest.approx(old.close)
    assert new.adj_close == pytest.approx(new.close * 0.98)
    # Adjusted open is scaled by the same factor: 99 * 0.98 (n=... close 100+n, open close-1)
    assert new.adj_open == pytest.approx(new.open * 0.98)
    # The old snapshot does not see days downloaded later.
    assert repo.load_prices(db, [inst.id], START, dt.date(2024, 3, 31), snap1.id).date.max() == dt.date(2024, 3, 14)
    assert repo.load_prices(db, [inst.id], START, dt.date(2024, 3, 31), snap2.id).date.max() == dt.date(2024, 3, 18)


def test_adjusted_ohlc_hand_example(db, now):
    # Hand example: close 200, adj_close 150 -> factor 0.75; open 196 -> 147, high 202 -> 151.5, low 194 -> 145.5
    inst = _inst(db)
    snap = ingest.new_snapshot(db, "prices")
    db.add(PriceBar(instrument_id=inst.id, date=dt.date(2024, 1, 2), snapshot_id=snap.id,
                    open=196, high=202, low=194, close=200, adj_close=150, volume=10))
    db.commit()
    row = repo.load_prices(db, [inst.id], START, START, snap.id).iloc[0]
    assert (row.adj_open, row.adj_high, row.adj_low, row.adj_close) == (147, 151.5, 145.5, 150)


def test_missing_day_is_reported(db, now):
    inst = _inst(db)
    fake = FakePrices()
    gap = dt.date(2024, 2, 6)
    fake.drop = {gap}
    _run(db, inst, make_providers([fake]), now)
    cov = repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now)
    assert cov.status == "incomplete" and cov.missing_dates == [gap] and cov.missing_count == 1


def test_needs_download_when_earlier_start_requested(db, now):
    inst = _inst(db)
    _run(db, inst, make_providers([FakePrices()]), now)
    cov = repo.check_coverage(db, inst, dt.date(2023, 1, 2), dt.date(2024, 3, 14), now=now)
    assert cov.status == "needs_download"


def test_not_downloaded(db, now):
    inst = _inst(db)
    assert repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now).status == "needs_download"


def test_fallback_provider_and_sticky_source(db, now):
    inst = _inst(db, "KR", "005930")
    down, backup = FakePrices("primary", fail=True), FakePrices("backup")
    _run(db, inst, make_providers([down, backup]), now)
    assert inst.coverage.provider == "backup"
    log = db.scalar(select(PriceFetchLog))
    assert log.provider == "backup" and log.adjustment == "splits_and_dividends"
    # Later the primary works again, but the refresh must keep the same source.
    down.fail = False
    _run(db, inst, make_providers([down, backup]), now + dt.timedelta(days=4))
    assert len(down.calls) == 1 and len(backup.calls) == 2


def test_no_data_anywhere_is_unavailable(db, now):
    inst = _inst(db)
    _, r = _run(db, inst, make_providers([FakePrices(empty=True), FakePrices("b", empty=True)]), now)
    assert r.outcome == "unavailable"
    cov = repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now)
    assert cov.status == "unavailable" and "no data" in cov.notes[0]


def test_source_error_is_retryable_not_unavailable(db, now):
    inst = _inst(db)
    fake = FakePrices(fail=True)
    _, r = _run(db, inst, make_providers([FakePrices(empty=True), fake]), now)
    assert r.outcome == "failed"
    cov = repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now)
    assert cov.status == "needs_download" and "try again" in cov.notes[0]
    fake.fail = False  # the source is back: the next attempt downloads normally
    _, r = _run(db, inst, make_providers([fake]), now)
    assert r.outcome == "downloaded"
    assert repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now).status == "ready"


def test_failed_refresh_keeps_existing_data(db, now):
    inst = _inst(db)
    fake = FakePrices()
    _run(db, inst, make_providers([fake]), now)
    fake.fail = True
    _, r = _run(db, inst, make_providers([fake]), now + dt.timedelta(days=4))
    assert r.outcome == "failed" and inst.coverage.status == "ok"
    assert "Last update failed" in inst.coverage.message


def test_late_listing_is_a_note_not_an_error(db, now):
    inst = _inst(db)
    _run(db, inst, make_providers([FakePrices()]), now, start=dt.date(2024, 2, 1))
    # Pretend the stock was requested from 2024-01-02 but only listed on 2024-02-01:
    inst.coverage.coverage_start = START
    db.commit()
    cov = repo.check_coverage(db, inst, START, dt.date(2024, 3, 14), now=now)
    assert cov.status == "ready"
    assert any("Data starts on 2024-02-01" in n for n in cov.notes)
