"""Schema inspection tools — describe tables, relationships, and database overview."""

from dbsage.cache.schema_cache import cache_get, cache_set
from dbsage.db.query_executor import execute_query
from dbsage.exceptions import TableBlacklistedError
from dbsage.formatting.table_formatter import (
    format_column_list_v2,
    format_relationships,
    format_section,
    section_header,
)
from dbsage.mcp_server.dependencies import (
    get_app_settings,
    get_db_type_for,
    get_engine_for,
    prod_warning,
    resolve_guardrails,
)
from dbsage.mcp_server.server import mcp
from dbsage.schema.schema_explorer import (
    describe_table as _describe_table,
)
from dbsage.schema.schema_explorer import (
    get_foreign_keys,
    get_table_sizes,
)


@mcp.tool()
async def describe_table(table_name: str, connection: str | None = None) -> str:
    """Return column definitions for a database table.

    Shows column names, data types, nullable status, and key information.
    Use this after list_tables() to understand a table's structure before querying.

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        table_name: The name of the table to describe.
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    _, _, timeout_ms = resolve_guardrails(connection, settings)
    header = section_header("describe_table", table_name)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    columns = await _describe_table(
        table_name, engine, timeout_ms=timeout_ms, db_type=db_type
    )
    fks = await get_foreign_keys(
        engine, table_name=table_name, timeout_ms=timeout_ms, db_type=db_type
    )
    fk_map = {fk["from_column"]: f"{fk['to_table']}.{fk['to_column']}" for fk in fks}

    body = format_column_list_v2(columns, fk_map=fk_map, table_name=table_name)
    return f"{warning}{header}\n\n{body}"


@mcp.tool()
async def table_relationships(
    table_name: str = "", connection: str | None = None
) -> str:
    """Return foreign key relationships for a table (or the entire database).

    Shows how tables are connected via foreign keys. Use this to understand
    join paths before writing multi-table queries.

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        table_name: Table to show relationships for.
                    Leave empty to see all FK relationships in the database.
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    _, _, timeout_ms = resolve_guardrails(connection, settings)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    target = table_name.strip() or None
    subtitle = target or ""
    header = section_header("table_relationships", subtitle)

    if target and target.lower() in blacklisted:
        raise TableBlacklistedError(target)

    fks = await get_foreign_keys(
        engine, table_name=target, timeout_ms=timeout_ms, db_type=db_type
    )

    if not fks:
        scope = f"'{target}'" if target else "this database"
        msg = f"no foreign key relationships found for {scope}"
        return f"{warning}{header}\n\n  ({msg})"

    # Filter out relationships where either side is blacklisted
    visible = [
        fk
        for fk in fks
        if fk["from_table"].lower() not in blacklisted
        and fk["to_table"].lower() not in blacklisted
    ]

    if not visible:
        return (
            f"{warning}{header}\n\n"
            "  (no visible relationships — all related tables are blacklisted)"
        )

    body = format_relationships(visible)
    count = len(visible)
    rel_word = "relationship" if count == 1 else "relationships"
    return f"{warning}{header}\n\n{body}\n\n  {count} {rel_word}"


@mcp.tool()
async def schema_summary(connection: str | None = None) -> str:
    """Return a high-level overview of the entire database.

    Shows all tables with approximate row counts, sizes, and foreign key
    relationships. Use this as the first step to understand an unfamiliar database.

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    db_type = get_db_type_for(connection)
    warning = prod_warning(connection)
    _, _, timeout_ms = resolve_guardrails(connection, settings)

    # Cache key is connection-aware to prevent cross-connection collisions
    cache_key = f"schema_summary:{connection or 'default'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return f"{warning}{cached}"

    blacklisted = {t.lower() for t in settings.blacklisted_tables}

    tables, fks = await _fetch_summary_data(engine, timeout_ms, db_type)

    visible_tables = [t for t in tables if t["table_name"].lower() not in blacklisted]

    if not visible_tables:
        return f"{warning}{section_header('schema_summary')}\n\n  (no tables found)"

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
    cache_set(cache_key, result, settings.cache_ttl_seconds)
    return f"{warning}{result}"


async def _fetch_summary_data(
    engine: object,
    timeout_ms: int,
    db_type: str = "mysql",
) -> tuple[list[dict], list[dict]]:  # type: ignore[type-arg]
    """Fetch table sizes and foreign keys concurrently."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncEngine

    eng: AsyncEngine = engine  # type: ignore[assignment]
    async with asyncio.TaskGroup() as tg:
        t_task = tg.create_task(get_table_sizes(eng, timeout_ms, db_type=db_type))
        fk_task = tg.create_task(
            get_foreign_keys(eng, timeout_ms=timeout_ms, db_type=db_type)
        )
    return t_task.result(), fk_task.result()


@mcp.tool()
async def show_create_view(view_name: str, connection: str | None = None) -> str:
    """Return the full CREATE VIEW SQL for a database view.

    Use this instead of querying information_schema.VIEWS — SHOW CREATE VIEW
    returns the complete, untruncated SQL definition regardless of length.
    Useful for understanding complex views before querying through them.

    Pass a SELECT query to explain_query() if you want the execution plan.

    Pass connection='<name>' to target a specific named connection profile.
    Call list_connections() to see available profiles.

    Args:
        view_name: Name of the view to inspect.
        connection: Optional named connection profile. Defaults to primary.
    """
    settings = get_app_settings()
    engine = get_engine_for(connection)
    warning = prod_warning(connection)
    _, _, timeout_ms = resolve_guardrails(connection, settings)
    header = section_header("show_create_view", view_name)

    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if view_name.lower() in blacklisted:
        raise TableBlacklistedError(view_name)

    try:
        rows = await execute_query(
            f"SHOW CREATE VIEW {view_name}",
            engine,
            timeout_ms=timeout_ms,
        )
    except Exception as exc:
        msg = str(exc)
        if "is not VIEW" in msg:
            return (
                f"{warning}{header}\n\n"
                f"  '{view_name}' is a table, not a view. "
                f"Use describe_table() or sample_table() instead."
            )
        raise

    if not rows:
        return f"{warning}{header}\n\n  (view '{view_name}' not found)"

    row = rows[0]
    # MySQL returns: View, Create View, character_set_client, collation_connection
    create_sql: str = str(row.get("Create View", ""))
    charset: str = str(row.get("character_set_client", ""))

    meta_lines = [
        f"  View:           {view_name}",
    ]
    if charset:
        meta_lines.append(f"  Character set:  {charset}")

    meta = "\n".join(meta_lines)
    return f"{warning}{header}\n\n{meta}\n\n{create_sql}"
