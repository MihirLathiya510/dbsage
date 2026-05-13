"""Query execution tools — run safe, read-only SQL queries."""

import re
import time

from dbsage.db.query_executor import execute_query
from dbsage.db.query_rewriter import rewrite_query
from dbsage.db.query_validator import validate_query
from dbsage.exceptions import ForbiddenQueryError
from dbsage.formatting.table_formatter import (
    format_error_result,
    format_query_result,
    section_header,
)
from dbsage.logging_.query_logger import log_query_executed, log_query_rejected
from dbsage.mcp_server.dependencies import (
    get_app_settings,
    get_db_type_for,
    get_engine_for,
    prod_warning,
    resolve_guardrails,
)
from dbsage.mcp_server.server import mcp


@mcp.tool()
async def run_read_only_query(
    query: str, limit: int | None = None, connection: str | None = None
) -> str:
    """Execute a safe read-only SQL SELECT query against the database.

    The query is automatically validated (no INSERT/UPDATE/DELETE/DROP etc.)
    and a LIMIT is injected if none is present.

    Row limit behaviour (two-tier system):
      - Default: DBSAGE_MAX_QUERY_ROWS rows injected automatically (default 100).
      - Override: pass limit=N to request up to DBSAGE_MAX_QUERY_ROWS_HARD_CAP
        rows (default 500). Useful when you need more rows to see distributions.
        The hard cap cannot be exceeded regardless of what is requested.

    To inspect a query's execution plan without running it, use explain_query().

    Allowed: SELECT, SHOW, DESCRIBE, EXPLAIN, WITH (CTEs)
    Forbidden: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        query: A read-only SQL query to execute.
        limit: Optional row count override. Capped at DBSAGE_MAX_QUERY_ROWS_HARD_CAP.
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    max_rows, hard_cap, timeout_ms = resolve_guardrails(connection, settings)
    header = section_header("run_read_only_query")

    # Layer 1: validate — block any forbidden operations
    try:
        validate_query(query)
    except ForbiddenQueryError as e:
        await log_query_rejected(
            query=query, reason="forbidden_keyword", keyword=e.keyword
        )
        body = format_error_result(
            sql=query,
            message=f"Query blocked: forbidden keyword '{e.keyword}'",
            hint="Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH are allowed.",
        )
        return f"{warning}{header}\n\n{body}"

    # Resolve effective row limit: explicit request capped at hard cap, else default
    if limit is not None:
        effective_limit = min(limit, hard_cap)
    else:
        effective_limit = max_rows

    # Detect whether a row limit was already present before rewriting
    if db_type == "mssql":
        limit_injected = not bool(re.search(r"\bTOP\b", query, re.IGNORECASE))
    else:
        limit_injected = not bool(re.search(r"\bLIMIT\b", query, re.IGNORECASE))

    # Layer 2: rewrite — inject LIMIT/TOP if missing
    safe_query = rewrite_query(query, max_rows=effective_limit, db_type=db_type)

    # Layer 3: execute with timeout
    start = time.monotonic()
    rows = await execute_query(safe_query, engine, timeout_ms=timeout_ms)
    elapsed_ms = (time.monotonic() - start) * 1000

    await log_query_executed(
        query=safe_query,
        execution_time_ms=elapsed_ms,
        rows_returned=len(rows),
    )

    body = format_query_result(
        sql=safe_query,
        rows=rows,
        elapsed_ms=elapsed_ms,
        limit_injected=limit_injected,
    )
    return f"{warning}{header}\n\n{body}"


@mcp.tool()
async def explain_query(query: str, connection: str | None = None) -> str:
    """Return the query execution plan for a SQL query.

    Use this to inspect whether a query will use indexes or cause a full table scan
    before actually running it. Helps write efficient queries.

    Pass only the SELECT query — do NOT include 'EXPLAIN' yourself, it is added
    automatically. Example: explain_query("SELECT * FROM orders WHERE user_id = 42")

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        query: A SELECT query to explain (without the EXPLAIN keyword).
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    warning = prod_warning(connection)
    _, _, timeout_ms = resolve_guardrails(connection, settings)
    header = section_header("explain_query")

    # Validate the underlying query first
    try:
        validate_query(query)
    except ForbiddenQueryError as e:
        body = format_error_result(
            sql=query,
            message=f"Query blocked: forbidden keyword '{e.keyword}'",
            hint="Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH are allowed.",
        )
        return f"{warning}{header}\n\n{body}"

    explain_sql = f"EXPLAIN {query.strip()}"
    start = time.monotonic()
    rows = await execute_query(explain_sql, engine, timeout_ms=timeout_ms)
    elapsed_ms = (time.monotonic() - start) * 1000

    body = format_query_result(
        sql=explain_sql,
        rows=rows,
        elapsed_ms=elapsed_ms,
        limit_injected=False,
    )
    return f"{warning}{header}\n\n{body}"
