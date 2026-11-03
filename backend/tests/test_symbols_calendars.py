import datetime as dt

import pytest

from quantlab.data import calendars
from quantlab.data.symbols import normalize_ticker, yahoo_symbol


def test_ticker_normalisation():
    assert normalize_ticker("KR", "5930") == "005930"
    assert normalize_ticker("US", "brk-b") == "BRK.B"
    assert normalize_ticker("US", "BRK/B") == "BRK.B"
    with pytest.raises(ValueError):
        normalize_ticker("KR", "ABC")


def test_yahoo_symbols():
    assert yahoo_symbol("US", "BRK.B", "NYSE") == "BRK-B"
    assert yahoo_symbol("KR", "005930", "KOSPI") == "005930.KS"
    assert yahoo_symbol("KR", "247540", "KOSDAQ") == "247540.KQ"
    assert yahoo_symbol("KR", "123456", "KONEX") is None


def test_korean_holidays():
    # Lunar New Year 2024: Fri 9 Feb and substitute holiday Mon 12 Feb.
    days = calendars.sessions("KR", dt.date(2024, 2, 7), dt.date(2024, 2, 14))
    assert days == [dt.date(2024, 2, 7), dt.date(2024, 2, 8), dt.date(2024, 2, 13), dt.date(2024, 2, 14)]


def test_us_holiday():
    assert dt.date(2024, 7, 4) not in calendars.sessions("US", dt.date(2024, 7, 1), dt.date(2024, 7, 5))


def test_close_times_in_utc():
    assert calendars.session_close_utc("KR", dt.date(2024, 3, 15)).hour == 6  # 15:30 KST
    assert calendars.session_close_utc("US", dt.date(2024, 1, 5)).hour == 21  # 16:00 EST
    assert calendars.session_close_utc("US", dt.date(2024, 7, 5)).hour == 20  # 16:00 EDT


def test_last_final_session(now):
    assert calendars.last_final_session("KR", now, 60) == dt.date(2024, 3, 15)
    assert calendars.last_final_session("US", now, 60) == dt.date(2024, 3, 14)
    # 15 minutes after the KRX close the bar is not yet treated as final.
    early = dt.datetime(2024, 3, 15, 6, 45, tzinfo=dt.timezone.utc)
    assert calendars.last_final_session("KR", early, 60) == dt.date(2024, 3, 14)
