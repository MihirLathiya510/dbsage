"""Shared singleton resources for the MCP server.

All tools import from here — never instantiate engines or settings directly.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from dbsage.db.connection_pool import get_engine
from dbsage.db.connection_registry import get_engine_for_profile
from dbsage.mcp_server.config import Settings, get_settings


def get_db_engine() -> AsyncEngine:
    """Return the shared async database engine (legacy single-DB path)."""
    settings = get_settings()
    return get_engine(settings)


def get_app_settings() -> Settings:
    """Return the singleton settings instance."""
    return get_settings()


def prod_warning(connection: str | None) -> str:
    """Return a warning banner string if the connection requires confirmation.

    Returns an empty string for non-sensitive connections.
    """
    settings = get_settings()
    resolved = connection or settings.default_connection or None
    if resolved and resolved in settings.connections:
        profile = settings.connections[resolved]
        if profile.requires_confirmation:
            return (
                f"[WARNING: {resolved} — sensitive connection. "
                "Queries are read-only.]\n\n"
            )
    return ""


def resolve_guardrails(
    connection: str | None, settings: Settings
) -> tuple[int, int, int]:
    """Return (max_query_rows, max_query_rows_hard_cap, query_timeout_ms).

    Per-profile overrides take precedence over global settings.
    """
    resolved = connection or settings.default_connection or None
    if resolved and resolved in settings.connections:
        profile = settings.connections[resolved]
        max_rows = (
            profile.max_query_rows
            if profile.max_query_rows is not None
            else settings.max_query_rows
        )
        timeout = (
            profile.query_timeout_ms
            if profile.query_timeout_ms is not None
            else settings.query_timeout_ms
        )
    else:
        max_rows = settings.max_query_rows
        timeout = settings.query_timeout_ms
    return max_rows, settings.max_query_rows_hard_cap, timeout


def get_engine_for(name: str | None = None) -> AsyncEngine:
    """Return the engine for a named connection profile, or the legacy default.

    Resolution order:
    1. If name is given and matches a profile → use that profile's engine.
    2. If name is None and default_connection is set → use that profile's engine.
    3. Otherwise → fall back to legacy DBSAGE_DB_* env var engine.

    Args:
        name: Optional named connection profile. Pass None to use the default.
    """
    settings = get_settings()
    resolved = name or settings.default_connection or None
    if resolved and resolved in settings.connections:
        profile = settings.connections[resolved]
        password = settings.get_password_for(profile)
        return get_engine_for_profile(resolved, profile, password)
    return get_engine(settings)  # legacy fallback
