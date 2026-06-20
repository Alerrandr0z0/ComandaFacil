from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "change_me_in_production"
    app_debug: bool = True
    app_host: str = "0.0.0.0"  # nosec B104
    app_port: int = 8000

    # PostgreSQL (Write DB)
    database_url: str = "postgresql+asyncpg://comandafacil:change_me@localhost:5432/comandafacil"

    # MongoDB (Read DB)
    mongo_url: str = (
        "mongodb://comandafacil:change_me@localhost:27017/comandafacil_read?authSource=admin"
    )
    mongo_db: str = "comandafacil_read"

    # JWT
    jwt_secret_key: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Logging
    log_level: str = "INFO"
    log_dir: str = "logs/franquias"
    log_rotation_when: str = "midnight"
    log_backup_count: int = 30

    # Stripe
    stripe_secret_key: str = "sk_test_change_me"
    stripe_webhook_secret: str = "whsec_change_me"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
