"""Shared singleton resources for the MCP server.

All tools import from here — never instantiate engines or settings directly.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from dbsage.db.connection_pool import get_engine
from dbsage.mcp_server.config import Settings, get_settings


def get_db_engine() -> AsyncEngine:
    """Return the shared async database engine."""
    settings = get_settings()
    return get_engine(settings)


def get_app_settings() -> Settings:
    """Return the singleton settings instance."""
    return get_settings()
