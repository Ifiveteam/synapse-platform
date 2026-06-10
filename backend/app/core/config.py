"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/synapse"


class Settings:
    """Runtime configuration (.env values)."""

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (postgresql+asyncpg)."""
        value = os.getenv("DATABASE_URL", "").strip()
        return value or _DEFAULT_DATABASE_URL

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations (postgresql+psycopg2)."""
        url = self.database_url
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "+psycopg2", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


@lru_cache
def get_settings() -> Settings:
    return Settings()
