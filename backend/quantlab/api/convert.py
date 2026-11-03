from dataclasses import asdict

from quantlab.api.schemas import CoverageOut, InstrumentOut
from quantlab.data.repository import Coverage
from quantlab.db.models import Instrument


def inst_out(i: Instrument) -> InstrumentOut:
    return InstrumentOut(id=i.id, market=i.market, ticker=i.ticker, name=i.name, name_en=i.name_en,
                         exchange=i.exchange, currency=i.currency, is_listed=i.is_listed)


def cov_out(c: Coverage) -> CoverageOut:
    return CoverageOut(**asdict(c))
