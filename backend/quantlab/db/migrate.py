"""Run Alembic migrations and create the local user / universe catalog rows."""
from importlib import resources

from alembic import command
from alembic.config import Config

from quantlab.db.models import LOCAL_USER_ID, User
from quantlab.db.session import get_engine, session_scope


def alembic_config() -> Config:
    ini = resources.files("quantlab").joinpath("alembic.ini")
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(resources.files("quantlab").joinpath("migrations")))
    return cfg


def upgrade() -> None:
    cfg = alembic_config()
    with get_engine().begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    from quantlab.data.ingest import sync_universe_catalog

    with session_scope() as s:
        if s.get(User, LOCAL_USER_ID) is None:
            s.add(User(id=LOCAL_USER_ID, name="Local user"))
        sync_universe_catalog(s)
