from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    movies_db_path: str = "movies.db"
    movies_backend: Literal["sqlite", "sqlalchemy"] = "sqlite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
