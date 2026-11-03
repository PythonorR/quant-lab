"""Catalog of stock universes a strategy can use."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UniverseDef:
    code: str
    name: str
    market: str
    kind: str  # index | all


CATALOG: list[UniverseDef] = [
    UniverseDef("SP500", "S&P 500", "US", "index"),
    UniverseDef("NDX100", "Nasdaq 100", "US", "index"),
    UniverseDef("KOSPI200", "KOSPI 200", "KR", "index"),
    UniverseDef("KOSDAQ150", "KOSDAQ 150", "KR", "index"),
    UniverseDef("US_ALL", "All US stocks", "US", "all"),
    UniverseDef("KR_ALL", "All Korean stocks", "KR", "all"),
]
BY_CODE = {u.code: u for u in CATALOG}

# Shown wherever membership is not historical.
SURVIVORSHIP_WARNING = (
    "This list uses today's members for every past date. Companies that left the list "
    "(often because they did badly) are missing, so past results can look better than they really were."
)
LISTED_ONLY_NOTE = "Currently listed stocks only. Delisted companies may be missing."
