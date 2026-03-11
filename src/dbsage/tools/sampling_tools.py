"""Data sampling tools — row and column sampling for database exploration.

Tools: sample_table, sample_column_values, table_row_count, inspect_json_column
"""

import json
from typing import Any

from dbsage.db.query_executor import execute_query
from dbsage.exceptions import TableBlacklistedError
from dbsage.formatting.table_formatter import (
    format_column_values,
    format_json_samples,
    format_results_table,
    section_header,
)
from dbsage.mcp_server.dependencies import get_app_settings, get_db_engine
from dbsage.mcp_server.server import mcp


@mcp.tool()
async def sample_table(table_name: str, limit: int = 0) -> str:
    """Return a sample of rows from a table.

    Helps the LLM understand column meanings, value formats, and data distribution
    before constructing queries.

    Args:
        table_name: Name of the table to sample.
        limit: Number of rows to return. Defaults to DBSAGE_DEFAULT_SAMPLE_LIMIT (10).
                Capped at DBSAGE_MAX_QUERY_ROWS (100).
    """
    settings = get_app_settings()
    engine = get_db_engine()
    header = section_header("sample_table", table_name)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    max_rows = settings.max_query_rows
    effective_limit = limit if 1 <= limit <= max_rows else settings.default_sample_limit

    sql = f"SELECT * FROM `{table_name}` LIMIT {effective_limit}"  # noqa: S608  # nosec B608
    rows = await execute_query(sql, engine, timeout_ms=settings.query_timeout_ms)

    if not rows:
        return f"{header}\n\n  (no rows found)"

    table = format_results_table(rows)
    n = len(rows)
    row_word = "row" if n == 1 else "rows"
    return f"{header}\n\n{table}\n\n  {n} {row_word}"


@mcp.tool()
async def sample_column_values(
    table_name: str, column_name: str, limit: int = 20
) -> str:
    """Return distinct values for a column.

    Helps the LLM understand categorical values, enums, and value distributions
    (e.g. what statuses exist, what currencies are used).

    Args:
        table_name: Name of the table.
        column_name: Name of the column to sample distinct values from.
        limit: Maximum number of distinct values to return (default 20, max 100).
    """
    settings = get_app_settings()
    engine = get_db_engine()
    header = section_header("sample_column_values", f"{table_name}.{column_name}")

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    effective_limit = min(max(1, limit), settings.max_query_rows)

    sql = (
        f"SELECT DISTINCT `{column_name}` AS value, COUNT(*) AS count"  # noqa: S608  # nosec B608
        f" FROM `{table_name}`"
        f" GROUP BY `{column_name}`"
        f" ORDER BY count DESC"
        f" LIMIT {effective_limit}"
    )
    rows = await execute_query(sql, engine, timeout_ms=settings.query_timeout_ms)

    if not rows:
        return f"{header}\n\n  (no values found in {table_name}.{column_name})"

    body = format_column_values(rows)
    n = len(rows)
    val_word = "distinct value" if n == 1 else "distinct values"
    return f"{header}\n\n{body}\n\n  {n} {val_word}"


@mcp.tool()
async def table_row_count(table_name: str) -> str:
    """Return the approximate row count for a table.

    Uses information_schema for a fast estimate rather than a full COUNT(*) scan.
    Useful for understanding table scale before querying.

    Args:
        table_name: Name of the table to count rows in.
    """
    settings = get_app_settings()
    engine = get_db_engine()
    header = section_header("table_row_count", table_name)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    sql = f"""
        SELECT TABLE_ROWS AS row_count
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = '{table_name}'
    """  # noqa: S608  # nosec B608
    rows = await execute_query(sql, engine, timeout_ms=settings.query_timeout_ms)

    if not rows or rows[0]["row_count"] is None:
        return (
            f"{header}\n\n  (table '{table_name}' not found or row count unavailable)"
        )

    count = int(rows[0]["row_count"])
    if count >= 1_000_000:
        human = f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        human = f"{count / 1_000:.1f}k"
    else:
        human = str(count)

    return f"{header}\n\n  {table_name}: ~{human} rows"


@mcp.tool()
async def inspect_json_column(table_name: str, column_name: str, limit: int = 5) -> str:
    """Return formatted JSON samples from a JSON column.

    Helps the LLM understand the structure of JSON/JSONB columns before querying
    nested fields.

    Args:
        table_name: Name of the table.
        column_name: Name of the JSON column to inspect.
        limit: Number of non-null samples to return (default 5, max 20).
    """
    settings = get_app_settings()
    engine = get_db_engine()
    header = section_header("inspect_json_column", f"{table_name}.{column_name}")

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    effective_limit = min(max(1, limit), 20)

    sql = (
        f"SELECT `{column_name}` AS json_value"  # noqa: S608  # nosec B608
        f" FROM `{table_name}`"
        f" WHERE `{column_name}` IS NOT NULL"
        f" LIMIT {effective_limit}"
    )
    rows = await execute_query(sql, engine, timeout_ms=settings.query_timeout_ms)

    if not rows:
        return f"{header}\n\n  (no non-null values found in {table_name}.{column_name})"

    json_strings: list[str] = []
    for row in rows:
        raw: Any = row["json_value"]
        try:
            parsed: Any = json.loads(raw) if isinstance(raw, str) else raw
            formatted = json.dumps(parsed, indent=2, default=str)
        except (json.JSONDecodeError, TypeError):
            formatted = str(raw)
        json_strings.append(formatted)

    body = format_json_samples(json_strings)
    return f"{header}\n\n{body}"
