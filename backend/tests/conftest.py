import datetime as dt
import os

os.environ["QUANTLAB_DOWNLOAD_PAUSE_SECONDS"] = "0"
os.environ["QUANTLAB_BAR_FINAL_DELAY_MINUTES"] = "60"

import pytest

from quantlab.config import get_settings
from quantlab.data.providers.registry import set_providers
from quantlab.db import migrate, session

# Friday 2024-03-15 12:00 UTC: KRX closed at 06:30 UTC (final), NYSE has not opened yet.
NOW = dt.datetime(2024, 3, 15, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def db(tmp_path):
    get_settings.cache_clear()
    session.configure(f"sqlite:///{tmp_path}/test.db")
    migrate.upgrade()
    s = session.new_session()
    yield s
    s.close()
    set_providers(None)


@pytest.fixture
def now():
    return NOW
