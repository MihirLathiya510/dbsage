"""Cross-connection comparison tools.

Tools: compare_query_across_connections, diff_schema,
       find_table_across_connections, compare_row_counts
"""

from __future__ import annotations

import asyncio

from dbsage.db.connection_registry import resolve_connections
from dbsage.db.query_executor import execute_query
from dbsage.db.query_rewriter import rewrite_query
from dbsage.db.query_validator import validate_query
from dbsage.exceptions import ForbiddenQueryError
from dbsage.formatting.table_formatter import format_query_result, section_header
from dbsage.mcp_server.dependencies import (
    get_app_settings,
    get_engine_for,
    resolve_guardrails,
)
from dbsage.mcp_server.server import mcp
from dbsage.schema.schema_explorer import describe_table as _describe_table
from dbsage.schema.schema_explorer import list_tables as _list_tables


@mcp.tool()
async def compare_query_across_connections(
    query: str,
    connections: list[str],
) -> str:
    """Run the same query on multiple connections and show results side by side.

    Validates the query once, executes concurrently across all specified connections.
    Each result is shown in a labeled section. If one connection fails its error is
    shown inline — results from other connections are still returned.

    Accepts connection group names (e.g. 'all-prod') in addition to profile names.

    Args:
        query: A read-only SQL query to execute on all specified connections.
        connections: List of profile names or group names.
    """
    settings = get_app_settings()
    header = section_header("compare_query_across_connections")

    # Validate once — block if forbidden
    try:
        validate_query(query)
    except ForbiddenQueryError as e:
        return (
            f"{header}\n\n"
            f"  Query blocked: forbidden keyword '{e.keyword}'\n"
            "  Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH are allowed."
        )

    targets = resolve_connections(connections, settings)
    if not targets:
        return f"{header}\n\n  (no connections to query)"

    async def _run(name: str) -> tuple[str, list[dict] | None, float, str]:  # type: ignore[type-arg]
        """Returns (name, rows or None, elapsed_ms, error)."""
        if name not in settings.connections:
            return name, None, 0.0, f"unknown profile '{name}'"
        try:
            engine = get_engine_for(name)
            _, _, timeout_ms = resolve_guardrails(name, settings)
            max_rows, _, _ = resolve_guardrails(name, settings)
            safe_query = rewrite_query(query, max_rows=max_rows)
            import time

            start = time.monotonic()
            rows = await execute_query(safe_query, engine, timeout_ms=timeout_ms)
            elapsed = (time.monotonic() - start) * 1000
            return name, rows, elapsed, ""
        except Exception as exc:  # noqa: BLE001
            return name, None, 0.0, str(exc)

    results: list[tuple[str, list[dict] | None, float, str]]  # type: ignore[type-arg]
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_run(name)) for name in targets]
    results = [t.result() for t in tasks]

    sections: list[str] = [header, ""]
    for name, rows, elapsed, error in results:
        label = f"=== {name} ==="
        if rows is not None:
            body = format_query_result(
                sql=query,
                rows=rows,
                elapsed_ms=elapsed,
                limit_injected=False,
            )
            sections.append(label)
            sections.append(body)
        else:
            sections.append(label)
            sections.append(f"  ERROR: {error}")
        sections.append("")

    return "\n".join(sections).rstrip()


@mcp.tool()
async def diff_schema(
    connection_a: str,
    connection_b: str,
    table: str = "",
) -> str:
    """Compare schema between two connections.

    Without table: shows which tables exist in one connection but not the other.
    With table: shows column-level diff — columns missing in one, and type or
    nullability differences between the two.

    Args:
        connection_a: First named connection profile.
        connection_b: Second named connection profile.
        table: Optional table name. Omit to diff the full table list.
    """
    settings = get_app_settings()
    subtitle = f"{connection_a} vs {connection_b}" + (f" — {table}" if table else "")
    header = section_header("diff_schema", subtitle)

    for name in (connection_a, connection_b):
        if name not in settings.connections:
            return f"{header}\n\n  Unknown connection profile: '{name}'"

    engine_a = get_engine_for(connection_a)
    engine_b = get_engine_for(connection_b)
    _, _, timeout_a = resolve_guardrails(connection_a, settings)
    _, _, timeout_b = resolve_guardrails(connection_b, settings)

    if not table:
        # Table list diff
        async with asyncio.TaskGroup() as tg:
            ta = tg.create_task(_list_tables(engine_a, timeout_ms=timeout_a))
            tb = tg.create_task(_list_tables(engine_b, timeout_ms=timeout_b))
        tables_a = {t.lower() for t in ta.result()}
        tables_b = {t.lower() for t in tb.result()}

        only_a = sorted(tables_a - tables_b)
        only_b = sorted(tables_b - tables_a)
        both = sorted(tables_a & tables_b)

        lines: list[str] = []
        if only_a:
            lines.append(f"  Tables only in {connection_a}:  {', '.join(only_a)}")
        else:
            lines.append(f"  Tables only in {connection_a}:  (none)")
        if only_b:
            lines.append(f"  Tables only in {connection_b}:  {', '.join(only_b)}")
        else:
            lines.append(f"  Tables only in {connection_b}:  (none)")
        lines.append(f"  Tables in both:              {len(both)} tables")

        return f"{header}\n\n" + "\n".join(lines)

    # Column diff for a specific table
    async with asyncio.TaskGroup() as tg:
        ca = tg.create_task(_describe_table(table, engine_a, timeout_ms=timeout_a))
        cb = tg.create_task(_describe_table(table, engine_b, timeout_ms=timeout_b))
    cols_a = {c["column_name"]: c for c in ca.result()}
    cols_b = {c["column_name"]: c for c in cb.result()}

    all_cols = sorted(set(cols_a) | set(cols_b))
    lines = [f"  Column diff for: {table}", ""]

    only_a_cols = []
    only_b_cols = []
    differ_cols = []
    same_cols = []

    for col in all_cols:
        if col in cols_a and col not in cols_b:
            only_a_cols.append(col)
        elif col in cols_b and col not in cols_a:
            only_b_cols.append(col)
        else:
            a, b = cols_a[col], cols_b[col]
            if a.get("data_type") != b.get("data_type") or a.get(
                "is_nullable"
            ) != b.get("is_nullable"):
                differ_cols.append((col, a, b))
            else:
                same_cols.append(col)

    for col in only_a_cols:
        c = cols_a[col]
        dtype = c.get("data_type", "")
        lines.append(f"  + {col:<35} {dtype}  (only in {connection_a})")
    for col in only_b_cols:
        c = cols_b[col]
        dtype = c.get("data_type", "")
        lines.append(f"  - {col:<35} {dtype}  (only in {connection_b})")
    for col, a, b in differ_cols:
        type_a = a.get("data_type", "?")
        type_b = b.get("data_type", "?")
        null_a = a.get("is_nullable", "?")
        null_b = b.get("is_nullable", "?")
        diff_note = []
        if type_a != type_b:
            diff_note.append(f"type: {type_a} → {type_b}")
        if null_a != null_b:
            diff_note.append(f"nullable: {null_a} → {null_b}")
        lines.append(f"  ~ {col:<35} {', '.join(diff_note)}")
    if same_cols:
        lines.append(f"  = {len(same_cols)} columns identical in both")

    return f"{header}\n\n" + "\n".join(lines)


@mcp.tool()
async def find_table_across_connections(
    table: str,
    connections: list[str] | None = None,
) -> str:
    """Search for a table across multiple connections.

    Reports which connections have the table and which do not.
    If connections is omitted, searches all configured profiles.

    Args:
        table: Table name to search for (exact match, case-insensitive).
        connections: Optional list of profile names or group names. Defaults to all.
    """
    settings = get_app_settings()
    header = section_header("find_table_across_connections", table)

    if not settings.connections:
        return f"{header}\n\n  (no named connection profiles configured)"

    all_names = connections or list(settings.connections.keys())
    targets = resolve_connections(all_names, settings)

    async def _check(name: str) -> tuple[str, bool, str]:
        """Returns (name, found, error)."""
        if name not in settings.connections:
            return name, False, f"unknown profile '{name}'"
        try:
            engine = get_engine_for(name)
            _, _, timeout_ms = resolve_guardrails(name, settings)
            all_tables = await _list_tables(engine, timeout_ms=timeout_ms)
            found = table.lower() in {t.lower() for t in all_tables}
            return name, found, ""
        except Exception as exc:  # noqa: BLE001
            return name, False, str(exc)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_check(name)) for name in targets]
    results = [t.result() for t in tasks]

    col_name = max(len(r[0]) for r in results) + 2
    col_name = max(col_name, 8)

    lines: list[str] = []
    found_count = 0
    for name, found, error in results:
        if error:
            lines.append(f"  {name:<{col_name}} ERROR: {error}")
        elif found:
            lines.append(f"  {name:<{col_name}} FOUND")
            found_count += 1
        else:
            lines.append(f"  {name:<{col_name}} NOT FOUND")

    lines.append("")
    lines.append(f"  {found_count} of {len(targets)} connections have this table")

    return f"{header}\n\n" + "\n".join(lines)


@mcp.tool()
async def compare_row_counts(
    table: str,
    connections: list[str] | None = None,
) -> str:
    """Compare approximate row counts for a table across multiple connections.

    Uses information_schema for fast estimates — no full table scan.
    Useful for spotting data drift between environments or verifying a backfill ran.

    Args:
        table: Table name to compare.
        connections: Optional list of profile names or group names. Defaults to all.
    """
    settings = get_app_settings()
    header = section_header("compare_row_counts", table)

    if not settings.connections:
        return f"{header}\n\n  (no named connection profiles configured)"

    all_names = connections or list(settings.connections.keys())
    targets = resolve_connections(all_names, settings)

    sql = f"""
        SELECT TABLE_ROWS AS row_count
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = '{table}'
    """  # noqa: S608  # nosec B608

    async def _count(name: str) -> tuple[str, int | None, str]:
        """Returns (name, count or None, error)."""
        if name not in settings.connections:
            return name, None, f"unknown profile '{name}'"
        try:
            engine = get_engine_for(name)
            _, _, timeout_ms = resolve_guardrails(name, settings)
            rows = await execute_query(sql, engine, timeout_ms=timeout_ms)
            if not rows or rows[0]["row_count"] is None:
                return name, None, ""
            return name, int(rows[0]["row_count"]), ""
        except Exception as exc:  # noqa: BLE001
            return name, None, str(exc)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_count(name)) for name in targets]
    results = [t.result() for t in tasks]

    col_name = max(len(r[0]) for r in results) + 2
    col_name = max(col_name, 8)

    lines: list[str] = []
    for name, count, error in results:
        if error:
            lines.append(f"  {name:<{col_name}} ERROR: {error}")
        elif count is not None:
            if count >= 1_000_000:
                human = f"{count / 1_000_000:.1f}M"
            elif count >= 1_000:
                human = f"{count / 1_000:.1f}k"
            else:
                human = str(count)
            lines.append(f"  {name:<{col_name}} {human}")
        else:
            lines.append(f"  {name:<{col_name}} —")

    lines.append("")
    lines.append("  (row counts are information_schema estimates and may lag)")

    return f"{header}\n\n" + "\n".join(lines)
