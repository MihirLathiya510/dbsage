"""Schema inspection tools — describe tables, relationships, and database overview."""

from dbsage.exceptions import TableBlacklistedError
from dbsage.formatting.table_formatter import format_column_list
from dbsage.mcp_server.dependencies import get_app_settings, get_db_engine
from dbsage.mcp_server.server import mcp
from dbsage.schema.schema_explorer import (
    describe_table as _describe_table,
)
from dbsage.schema.schema_explorer import (
    get_foreign_keys,
    get_table_sizes,
)


@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Return column definitions for a database table.

    Shows column names, data types, nullable status, and key information.
    Use this after list_tables() to understand a table's structure before querying.

    Args:
        table_name: The name of the table to describe.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    columns = await _describe_table(
        table_name, engine, timeout_ms=settings.query_timeout_ms
    )
    return format_column_list(columns)


@mcp.tool()
async def table_relationships(table_name: str = "") -> str:
    """Return foreign key relationships for a table (or the entire database).

    Shows how tables are connected via foreign keys. Use this to understand
    join paths before writing multi-table queries.

    Args:
        table_name: Table to show relationships for.
                    Leave empty to see all FK relationships in the database.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    target = table_name.strip() or None

    if target and target.lower() in blacklisted:
        raise TableBlacklistedError(target)

    fks = await get_foreign_keys(
        engine,
        table_name=target,
        timeout_ms=settings.query_timeout_ms,
    )

    if not fks:
        scope = f"'{target}'" if target else "this database"
        return f"(no foreign key relationships found for {scope})"

    # Filter out relationships where either side is blacklisted
    visible = [
        fk for fk in fks
        if fk["from_table"].lower() not in blacklisted
        and fk["to_table"].lower() not in blacklisted
    ]

    if not visible:
        return "(no visible relationships — all related tables are blacklisted)"

    lines = [
        f"{fk['from_table']}.{fk['from_column']} → {fk['to_table']}.{fk['to_column']}"
        for fk in visible
    ]
    return "\n".join(lines)


@mcp.tool()
async def schema_summary() -> str:
    """Return a high-level overview of the entire database.

    Shows all tables with approximate row counts, sizes, and foreign key
    relationships. Use this as the first step to understand an unfamiliar database.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    blacklisted = {t.lower() for t in settings.blacklisted_tables}

    tables, fks = await _fetch_summary_data(engine, settings.query_timeout_ms)

    visible_tables = [t for t in tables if t["table_name"].lower() not in blacklisted]

    if not visible_tables:
        return "(no tables found)"

    lines: list[str] = ["=== Database Summary ===", ""]

    # Tables section
    lines.append("Tables")
    lines.append("------")
    for t in visible_tables:
        count = t["row_count"] or 0
        size = t["size_mb"] or 0.0
        if count >= 1_000_000:
            count_str = f"{count / 1_000_000:.1f}M rows"
        elif count >= 1_000:
            count_str = f"{count / 1_000:.1f}k rows"
        else:
            count_str = f"{count} rows"
        lines.append(f"  {t['table_name']:<40} {count_str:<15} {size} MB")

    # Relationships section
    visible_fks = [
        fk for fk in fks
        if fk["from_table"].lower() not in blacklisted
        and fk["to_table"].lower() not in blacklisted
    ]

    if visible_fks:
        lines.append("")
        lines.append("Relationships")
        lines.append("-------------")
        for fk in visible_fks:
            lines.append(
                f"  {fk['from_table']}.{fk['from_column']}"
                f" → {fk['to_table']}.{fk['to_column']}"
            )

    return "\n".join(lines)


async def _fetch_summary_data(
    engine: object,
    timeout_ms: int,
) -> tuple[list[dict], list[dict]]:
    """Fetch table sizes and foreign keys concurrently."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncEngine
    eng: AsyncEngine = engine  # type: ignore[assignment]
    async with asyncio.TaskGroup() as tg:
        t_task = tg.create_task(get_table_sizes(eng, timeout_ms))
        fk_task = tg.create_task(get_foreign_keys(eng, timeout_ms=timeout_ms))
    return t_task.result(), fk_task.result()
