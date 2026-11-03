"""Application settings, read from environment variables (prefix QUANTLAB_)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTLAB_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./quantlab.db"
    # Sent to public data sites (e.g. Wikipedia) that ask clients to identify themselves.
    http_user_agent: str = "QuantLab/0.1 (personal research tool)"
    # FinanceDataReader's public mirror of KRX listing files.
    krx_listing_cache_url: str = (
        "https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/refs/heads/master/data/listing/krx"
    )
    # Price history is downloaded from this date when a stock is first requested.
    default_history_start: str = "2010-01-01"
    # Point-in-time KOSPI 200 / KOSDAQ 150 membership is sampled monthly from this date.
    # KRX does not serve constituent files before 2014-05-02.
    kr_index_history_start: str = "2014-06-01"
    # A daily bar is treated as final only this many minutes after the official close,
    # so providers have time to publish it.
    bar_final_delay_minutes: int = 60
    # Pause between per-stock downloads, to be polite to free data sources.
    download_pause_seconds: float = 0.3


@lru_cache
def get_settings() -> Settings:
    return Settings()
