"""Which provider is used for what. Swap implementations here (e.g. a paid API later)."""
from __future__ import annotations

from dataclasses import dataclass, field

from quantlab.config import get_settings
from quantlab.data.providers.base import ConstituentProvider, ListingProvider, PriceProvider


@dataclass
class Providers:
    listings: dict[str, ListingProvider]  # market -> provider
    prices: list[PriceProvider]  # tried in order; first that supports the stock and returns data wins
    constituents: dict[str, ConstituentProvider]  # universe code -> provider
    extra: dict = field(default_factory=dict)


_override: Providers | None = None


def set_providers(p: Providers | None) -> None:
    """Tests inject fake providers here."""
    global _override
    _override = p


def get_providers() -> Providers:
    if _override is not None:
        return _override
    from quantlab.data.providers.fdr import FdrKrPriceProvider, FdrUsListingProvider
    from quantlab.data.providers.krx_cache import KrxCacheListingProvider
    from quantlab.data.providers.pykrx_index import PykrxConstituentProvider
    from quantlab.data.providers.wikipedia import WikipediaConstituentProvider
    from quantlab.data.providers.yahoo import YahooPriceProvider

    s = get_settings()
    wiki = WikipediaConstituentProvider(s.http_user_agent)
    krx = PykrxConstituentProvider()
    return Providers(
        listings={"KR": KrxCacheListingProvider(s.krx_listing_cache_url, s.http_user_agent), "US": FdrUsListingProvider()},
        prices=[YahooPriceProvider(), FdrKrPriceProvider()],
        constituents={"SP500": wiki, "NDX100": wiki, "KOSPI200": krx, "KOSDAQ150": krx},
    )
