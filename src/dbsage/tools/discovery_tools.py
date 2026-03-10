"""Database discovery tools — list and search available tables."""

from dbsage.mcp_server.dependencies import get_app_settings, get_db_engine
from dbsage.mcp_server.server import mcp
from dbsage.schema.schema_explorer import list_tables as _list_tables


@mcp.tool()
async def list_tables() -> str:
    """List all available database tables.

    Returns table names filtered by the blacklist configuration.
    Use this as the first step to explore an unfamiliar database.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    all_tables = await _list_tables(engine, timeout_ms=settings.query_timeout_ms)

    # Filter blacklisted tables
    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    visible_tables = [t for t in all_tables if t.lower() not in blacklisted]

    if not visible_tables:
        return "(no tables found)"

    return "\n".join(visible_tables)


@mcp.tool()
async def search_tables(keyword: str) -> str:
    """Search for tables matching a keyword.

    Useful when the database has many tables and you need to find
    tables related to a specific concept (e.g. 'user', 'order').

    Args:
        keyword: Search term to filter table names by (case-insensitive).
    """
    settings = get_app_settings()
    engine = get_db_engine()

    all_tables = await _list_tables(engine, timeout_ms=settings.query_timeout_ms)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    kw = keyword.lower()
    matches = [
        t for t in all_tables if kw in t.lower() and t.lower() not in blacklisted
    ]

    if not matches:
        return f"(no tables matching '{keyword}')"

    return "\n".join(matches)
