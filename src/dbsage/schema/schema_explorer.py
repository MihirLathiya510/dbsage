"""Schema explorer — queries information_schema for table and column metadata.

Uses raw SQL against information_schema so it works for MySQL, PostgreSQL, and MSSQL.
Results are cached using a TTL cache (default 5 minutes) to avoid repeated
information_schema queries on every tool call.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from dbsage.cache.schema_cache import cache_get, cache_set
from dbsage.db.query_executor import execute_query


async def list_tables(
    engine: AsyncEngine,
    timeout_ms: int = 3000,
    ttl_seconds: int = 300,
    db_type: str = "mysql",
) -> list[str]:
    """Return all user table names in the current database.

    Uses information_schema.TABLES to discover available tables.
    Results are cached for ttl_seconds.
    """
    cache_key = "list_tables"
    cached: list[str] | None = cache_get(cache_key)
    if cached is not None:
        return cached

    db_name_fn = "DB_NAME()" if db_type == "mssql" else "DATABASE()"
    sql = f"""
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = {db_name_fn}
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """  # noqa: S608  # nosec B608
    rows = await execute_query(sql, engine, timeout_ms)
    result = [row["TABLE_NAME"] for row in rows]
    cache_set(cache_key, result, ttl_seconds)
    return result


async def get_foreign_keys(
    engine: AsyncEngine,
    table_name: str | None = None,
    timeout_ms: int = 3000,
    ttl_seconds: int = 300,
    db_type: str = "mysql",
) -> list[dict[str, Any]]:
    """Return foreign key relationships in the database.

    If table_name is given, returns only relationships where that table is the
    source or the target. Otherwise returns all FK relationships.
    Results are cached for ttl_seconds.
    """
    cache_key = f"foreign_keys:{table_name or '*'}"
    cached: list[dict[str, Any]] | None = cache_get(cache_key)
    if cached is not None:
        return cached

    if db_type == "mssql":
        table_filter = ""
        if table_name:
            table_filter = (
                f" AND (fk_cols.TABLE_NAME = '{table_name}'"
                f" OR pk_cols.TABLE_NAME = '{table_name}')"
            )
        sql = f"""
            SELECT
                fk_cols.TABLE_NAME   AS from_table,
                fk_cols.COLUMN_NAME  AS from_column,
                pk_cols.TABLE_NAME   AS to_table,
                pk_cols.COLUMN_NAME  AS to_column,
                rc.CONSTRAINT_NAME   AS constraint_name
            FROM information_schema.REFERENTIAL_CONSTRAINTS rc
            JOIN information_schema.KEY_COLUMN_USAGE fk_cols
                ON rc.CONSTRAINT_NAME = fk_cols.CONSTRAINT_NAME
            JOIN information_schema.KEY_COLUMN_USAGE pk_cols
                ON rc.UNIQUE_CONSTRAINT_NAME = pk_cols.CONSTRAINT_NAME
               AND fk_cols.ORDINAL_POSITION = pk_cols.ORDINAL_POSITION
            WHERE 1=1{table_filter}
            ORDER BY fk_cols.TABLE_NAME, fk_cols.COLUMN_NAME
        """  # noqa: S608  # nosec B608
    else:
        where = (
            "WHERE kcu.TABLE_SCHEMA = DATABASE()"
            " AND kcu.REFERENCED_TABLE_NAME IS NOT NULL"
        )
        if table_name:
            where += (
                f" AND (kcu.TABLE_NAME = '{table_name}'"
                f" OR kcu.REFERENCED_TABLE_NAME = '{table_name}')"
            )
        sql = f"""
            SELECT
                kcu.TABLE_NAME        AS from_table,
                kcu.COLUMN_NAME       AS from_column,
                kcu.REFERENCED_TABLE_NAME  AS to_table,
                kcu.REFERENCED_COLUMN_NAME AS to_column,
                kcu.CONSTRAINT_NAME   AS constraint_name
            FROM information_schema.KEY_COLUMN_USAGE kcu
            {where}
            ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """  # noqa: S608  # nosec B608

    result = await execute_query(sql, engine, timeout_ms)
    cache_set(cache_key, result, ttl_seconds)
    return result


async def get_table_sizes(
    engine: AsyncEngine,
    timeout_ms: int = 3000,
    ttl_seconds: int = 300,
    db_type: str = "mysql",
) -> list[dict[str, Any]]:
    """Return all tables with approximate row counts and size in MB.

    Results are cached for ttl_seconds.
    """
    cache_key = "table_sizes"
    cached: list[dict[str, Any]] | None = cache_get(cache_key)
    if cached is not None:
        return cached

    if db_type == "mssql":
        sql = """
            SELECT
                t.name                                          AS table_name,
                SUM(p.rows)                                     AS row_count,
                ROUND(SUM(a.total_pages) * 8.0 / 1024, 2)      AS size_mb
            FROM sys.tables t
            JOIN sys.indexes i
                ON t.object_id = i.object_id
            JOIN sys.partitions p
                ON i.object_id = p.object_id AND i.index_id = p.index_id
            JOIN sys.allocation_units a
                ON p.partition_id = a.container_id
            WHERE i.index_id <= 1
            GROUP BY t.name
            ORDER BY row_count DESC
        """
    else:
        sql = """
            SELECT
                TABLE_NAME          AS table_name,
                TABLE_ROWS          AS row_count,
                ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_ROWS DESC
        """

    result = await execute_query(sql, engine, timeout_ms)
    cache_set(cache_key, result, ttl_seconds)
    return result


async def describe_table(
    table_name: str,
    engine: AsyncEngine,
    timeout_ms: int = 3000,
    ttl_seconds: int = 300,
    db_type: str = "mysql",
) -> list[dict[str, Any]]:
    """Return column definitions for a table.

    Returns a list of dicts with keys: column_name, data_type, is_nullable,
    column_key, column_default, extra.
    Results are cached for ttl_seconds.
    """
    cache_key = f"describe:{table_name}"
    cached: list[dict[str, Any]] | None = cache_get(cache_key)
    if cached is not None:
        return cached

    if db_type == "mssql":
        sql = f"""
            SELECT
                COLUMN_NAME    AS column_name,
                DATA_TYPE      AS data_type,
                IS_NULLABLE    AS is_nullable,
                ''             AS column_key,
                COLUMN_DEFAULT AS column_default,
                ''             AS extra
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DB_NAME()
              AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """  # noqa: S608  # nosec B608
    else:
        sql = f"""
            SELECT
                COLUMN_NAME   AS column_name,
                DATA_TYPE     AS data_type,
                IS_NULLABLE   AS is_nullable,
                COLUMN_KEY    AS column_key,
                COLUMN_DEFAULT AS column_default,
                EXTRA         AS extra
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """  # noqa: S608  # nosec B608 — table_name is validated by caller (blacklist check)

    result = await execute_query(sql, engine, timeout_ms)
    cache_set(cache_key, result, ttl_seconds)
    return result
