"""Database discovery tools — list and search available tables."""

from dbsage.formatting.table_formatter import format_simple_list, section_header
from dbsage.mcp_server.dependencies import (
    get_app_settings,
    get_db_type_for,
    get_engine_for,
    prod_warning,
)
from dbsage.mcp_server.server import mcp
from dbsage.schema.schema_explorer import list_tables as _list_tables


@mcp.tool()
async def list_tables(connection: str | None = None) -> str:
    """List all available database tables.

    Returns table names filtered by the blacklist configuration.
    Use this as the first step to explore an unfamiliar database.

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    header = section_header("list_tables")

    all_tables = await _list_tables(
        engine, timeout_ms=settings.query_timeout_ms, db_type=db_type
    )

    # Filter blacklisted tables
    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    visible_tables = [t for t in all_tables if t.lower() not in blacklisted]

    if not visible_tables:
        return f"{warning}{header}\n\n  (no tables found)"

    count = len(visible_tables)
    table_word = "table" if count == 1 else "tables"
    body = format_simple_list(visible_tables, footer=f"{count} {table_word}")
    return f"{warning}{header}\n\n{body}"


@mcp.tool()
async def search_tables(keyword: str, connection: str | None = None) -> str:
    """Search for tables matching a keyword.

    Useful when the database has many tables and you need to find
    tables related to a specific concept (e.g. 'user', 'order').

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        keyword: Search term to filter table names by (case-insensitive).
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    header = section_header("search_tables", f'"{keyword}"')

    all_tables = await _list_tables(
        engine, timeout_ms=settings.query_timeout_ms, db_type=db_type
    )

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    kw = keyword.lower()
    matches = [
        t for t in all_tables if kw in t.lower() and t.lower() not in blacklisted
    ]

    if not matches:
        return f"{warning}{header}\n\n  (no tables matching '{keyword}')"

    count = len(matches)
    match_word = "match" if count == 1 else "matches"
    body = format_simple_list(matches, footer=f"{count} {match_word}")
    return f"{warning}{header}\n\n{body}"
