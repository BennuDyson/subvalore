from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://subvalore:subvalore_secret@localhost:5432/subvalore"

    # Data freshness
    data_stale_minutes: int = 60

    # Scheduler
    scheduler_enabled: bool = True
    refresh_interval_hours: int = 24   # how often to refresh all known tickers

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
