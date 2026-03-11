"""Schema inspection tools — describe tables, relationships, and database overview."""

from dbsage.cache.schema_cache import cache_get, cache_set
from dbsage.exceptions import TableBlacklistedError
from dbsage.formatting.table_formatter import (
    format_column_list_v2,
    format_relationships,
    format_section,
    section_header,
)
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
    header = section_header("describe_table", table_name)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    columns = await _describe_table(
        table_name, engine, timeout_ms=settings.query_timeout_ms
    )
    fks = await get_foreign_keys(
        engine, table_name=table_name, timeout_ms=settings.query_timeout_ms
    )
    fk_map = {fk["from_column"]: f"{fk['to_table']}.{fk['to_column']}" for fk in fks}

    body = format_column_list_v2(columns, fk_map=fk_map, table_name=table_name)
    return f"{header}\n\n{body}"


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
    subtitle = target or ""
    header = section_header("table_relationships", subtitle)

    if target and target.lower() in blacklisted:
        raise TableBlacklistedError(target)

    fks = await get_foreign_keys(
        engine,
        table_name=target,
        timeout_ms=settings.query_timeout_ms,
    )

    if not fks:
        scope = f"'{target}'" if target else "this database"
        return f"{header}\n\n  (no foreign key relationships found for {scope})"

    # Filter out relationships where either side is blacklisted
    visible = [
        fk
        for fk in fks
        if fk["from_table"].lower() not in blacklisted
        and fk["to_table"].lower() not in blacklisted
    ]

    if not visible:
        return (
            f"{header}\n\n"
            "  (no visible relationships — all related tables are blacklisted)"
        )

    body = format_relationships(visible)
    count = len(visible)
    rel_word = "relationship" if count == 1 else "relationships"
    return f"{header}\n\n{body}\n\n  {count} {rel_word}"


@mcp.tool()
async def schema_summary() -> str:
    """Return a high-level overview of the entire database.

    Shows all tables with approximate row counts, sizes, and foreign key
    relationships. Use this as the first step to understand an unfamiliar database.
    """
    settings = get_app_settings()
    engine = get_db_engine()

    cached = cache_get("schema_summary")
    if cached is not None:
        return str(cached)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}

    tables, fks = await _fetch_summary_data(engine, settings.query_timeout_ms)

    visible_tables = [t for t in tables if t["table_name"].lower() not in blacklisted]

    if not visible_tables:
        return section_header("schema_summary") + "\n\n  (no tables found)"

    header = section_header("schema_summary")
    sections: list[str] = [header, ""]

    # Tables section
    table_lines: list[str] = []
    for t in visible_tables:
        count = t["row_count"] or 0
        size = t["size_mb"] or 0.0
        if count >= 1_000_000:
            count_str = f"{count / 1_000_000:.1f}M rows"
        elif count >= 1_000:
            count_str = f"{count / 1_000:.1f}k rows"
        else:
            count_str = f"{count} rows"
        table_lines.append(f"  {t['table_name']:<40} {count_str:<15} {size} MB")

    sections.append(
        format_section(f"Tables ({len(visible_tables)})", "\n".join(table_lines))
    )

    # Relationships section
    visible_fks = [
        fk
        for fk in fks
        if fk["from_table"].lower() not in blacklisted
        and fk["to_table"].lower() not in blacklisted
    ]

    if visible_fks:
        rel_body = format_relationships(visible_fks)
        sections.append("")
        sections.append(format_section(f"Relationships ({len(visible_fks)})", rel_body))

    result = "\n".join(sections)
    cache_set("schema_summary", result, settings.cache_ttl_seconds)
    return result


async def _fetch_summary_data(
    engine: object,
    timeout_ms: int,
) -> tuple[list[dict], list[dict]]:  # type: ignore[type-arg]
    """Fetch table sizes and foreign keys concurrently."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncEngine

    eng: AsyncEngine = engine  # type: ignore[assignment]
    async with asyncio.TaskGroup() as tg:
        t_task = tg.create_task(get_table_sizes(eng, timeout_ms))
        fk_task = tg.create_task(get_foreign_keys(eng, timeout_ms=timeout_ms))
    return t_task.result(), fk_task.result()
