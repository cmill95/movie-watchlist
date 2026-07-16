from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    movies_db_path: str = "movies.db"
    movies_backend: Literal["sqlite", "postgres"] = "sqlite"
    database_url: str = ""
    # Signs the session cookie. The default is fine for local dev; production
    # MUST override it (a known key lets anyone forge a session).
    session_secret: str = "dev-insecure-change-me"

    @model_validator(mode="after")
    def _require_database_url_for_postgres(self) -> Self:
        if self.movies_backend == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when MOVIES_BACKEND=postgres")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
