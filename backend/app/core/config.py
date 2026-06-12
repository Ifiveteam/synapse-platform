"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/synapse"


class Settings:
    """Runtime configuration (.env values)."""

    @property
    def _raw_database_url(self) -> str:
        value = os.getenv("DATABASE_URL", "").strip()
        return value or _DEFAULT_DATABASE_URL

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (postgresql+asyncpg) — SSL param stripped."""
        return self._raw_database_url.replace("?ssl=require", "")

    @property
    def database_needs_ssl(self) -> bool:
        return "ssl=require" in self._raw_database_url

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations (postgresql+psycopg2)."""
        url = self.database_url
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "+psycopg2", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # asyncpg는 ?ssl=require, psycopg2는 ?sslmode=require
        url = url.replace("?ssl=require", "?sslmode=require")
        return url

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


@lru_cache
def get_settings() -> Settings:
    return Settings()
