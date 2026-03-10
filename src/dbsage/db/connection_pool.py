"""Async SQLAlchemy connection pool factory.

Supports MySQL (aiomysql) and PostgreSQL (asyncpg).
Uses pool_recycle=1800 to avoid stale connections on RDS.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from dbsage.mcp_server.config import Settings

# Module-level singleton — shared across all tool calls
_engine: AsyncEngine | None = None


def build_engine(settings: Settings) -> AsyncEngine:
    """Build an AsyncEngine from settings. Not cached — use get_engine() instead."""
    password = settings.db_password.get_secret_value()

    if settings.db_type == "postgresql":
        url = (
            f"postgresql+asyncpg://{settings.db_user}:{password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )
    else:
        url = (
            f"mysql+aiomysql://{settings.db_user}:{password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )

    return create_async_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,  # required for RDS — avoids stale connections
        echo=False,
    )


def get_engine(settings: Settings) -> AsyncEngine:
    """Return the singleton AsyncEngine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = build_engine(settings)
    return _engine
