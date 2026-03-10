"""Query execution tools — run safe, read-only SQL queries."""

import time

from dbsage.db.query_executor import execute_query
from dbsage.db.query_rewriter import rewrite_query
from dbsage.db.query_validator import validate_query
from dbsage.exceptions import ForbiddenQueryError
from dbsage.formatting.table_formatter import format_as_table
from dbsage.logging_.query_logger import log_query_executed, log_query_rejected
from dbsage.mcp_server.dependencies import get_app_settings, get_db_engine
from dbsage.mcp_server.server import mcp


@mcp.tool()
async def run_read_only_query(sql_query: str) -> str:
    """Execute a safe read-only SQL SELECT query against the database.

    The query is automatically validated (no INSERT/UPDATE/DELETE/DROP etc.)
    and a LIMIT is injected if none is present. Maximum 100 rows returned.

    Allowed: SELECT, SHOW, DESCRIBE, EXPLAIN, WITH (CTEs)
    Forbidden: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE

    Args:
        sql_query: A read-only SQL query to execute.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    # Layer 1: validate — block any forbidden operations
    try:
        validate_query(sql_query)
    except ForbiddenQueryError as e:
        await log_query_rejected(
            query=sql_query, reason="forbidden_keyword", keyword=e.keyword
        )
        return f"Error: {e}"

    # Layer 2: rewrite — inject LIMIT if missing
    safe_query = rewrite_query(sql_query, max_rows=settings.max_query_rows)

    # Layer 3: execute with timeout
    start = time.monotonic()
    rows = await execute_query(safe_query, engine, timeout_ms=settings.query_timeout_ms)
    elapsed_ms = (time.monotonic() - start) * 1000

    await log_query_executed(
        query=safe_query,
        execution_time_ms=elapsed_ms,
        rows_returned=len(rows),
    )

    return format_as_table(rows)


@mcp.tool()
async def explain_query(sql_query: str) -> str:
    """Return the query execution plan for a SQL query.

    Use this to inspect whether a query will use indexes or cause a full table scan
    before actually running it. Helps write efficient queries.

    Args:
        sql_query: A SELECT query to explain.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    # Validate the underlying query first
    try:
        validate_query(sql_query)
    except ForbiddenQueryError as e:
        return f"Error: {e}"

    explain_sql = f"EXPLAIN {sql_query.strip()}"
    rows = await execute_query(
        explain_sql, engine, timeout_ms=settings.query_timeout_ms
    )
    return format_as_table(rows)
