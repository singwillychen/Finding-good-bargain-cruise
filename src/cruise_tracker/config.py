from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    timezone: str = "Asia/Taipei"

    vtg_email: str = ""
    vtg_password: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    scrape_cron: str = "30 3 * * *"
    digest_cron: str = "0 9 * * mon"
    digest_max_items: int = 5
    digest_min_score: float = 60

    sources: str = "vtg,cruisedirect"

    # Polite scraping: random delay between requests, in seconds
    request_delay_min: float = 3.0
    request_delay_max: float = 10.0

    web_base_url: str = "http://localhost:8000"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'cruise.db'}"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def source_list(self) -> list[str]:
        return [s.strip() for s in self.sources.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
