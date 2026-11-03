"""Trading calendars for KRX (Korea) and NYSE (US), via exchange_calendars.

Each market uses its own holiday calendar and its own close time:
* KRX regular session 09:00-15:30 KST (UTC+9, no daylight saving).
* NYSE regular session 09:30-16:00 America/New_York (UTC-5 / UTC-4 with daylight saving).
Session timestamps from exchange_calendars are in UTC, which is how the two markets are put on
one time line. (The cross-market signal-to-fill rule that builds on this lives in the engine,
Phase 2.)
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd

from quantlab.data.symbols import CALENDAR

CALENDAR_START = "2000-01-01"


@lru_cache(maxsize=4)
def get_calendar(market: str):
    return xcals.get_calendar(CALENDAR[market], start=CALENDAR_START)


def sessions(market: str, start: dt.date, end: dt.date) -> list[dt.date]:
    """Trading days (sessions) in [start, end], inclusive."""
    if end < start:
        return []
    cal = get_calendar(market)
    s = max(pd.Timestamp(start), cal.first_session)
    e = min(pd.Timestamp(end), cal.last_session)
    if e < s:
        return []
    return [d.date() for d in cal.sessions_in_range(s, e)]


def session_close_utc(market: str, day: dt.date) -> dt.datetime:
    ts = get_calendar(market).session_close(pd.Timestamp(day))
    return ts.to_pydatetime().replace(tzinfo=dt.timezone.utc)


def last_final_session(market: str, now_utc: dt.datetime, delay_minutes: int) -> dt.date:
    """Latest session whose daily bar is final: its close was at least ``delay_minutes`` ago.

    A bar for a session that is still trading (or just closed) is never stored, so a signal can
    only ever be computed from a finished day.
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=dt.timezone.utc)
    cutoff = now_utc - dt.timedelta(minutes=delay_minutes)
    today = now_utc.date()
    for d in reversed(sessions(market, today - dt.timedelta(days=20), today + dt.timedelta(days=1))):
        if session_close_utc(market, d) <= cutoff:
            return d
    raise RuntimeError(f"No finished session found for {market} near {now_utc}")
