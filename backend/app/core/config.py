from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expiration: int = Field(default=60, ge=5, le=10080)
    cors_origins: str = ""
    auth_login_limit: int = Field(default=20, ge=1, le=1000)
    auth_login_window: int = Field(default=60, ge=1, le=86400)
    auth_register_limit: int = Field(default=5, ge=1, le=1000)
    auth_register_window: int = Field(default=300, ge=1, le=86400)

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore", hide_input_in_errors=True)

    @field_validator('database_url')
    @classmethod
    def use_installed_postgres_driver(cls, value: str) -> str:
        # Hosted providers supply generic PostgreSQL URLs; runtime uses psycopg 3.
        for prefix in ('postgres://', 'postgresql://'):
            if value.startswith(prefix):
                return 'postgresql+psycopg://' + value[len(prefix):]
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
