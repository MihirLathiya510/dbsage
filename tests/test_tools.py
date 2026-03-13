"""Integration-style tests for MCP tool functions.

Mocks get_app_settings() and get_db_engine() so no real DB is needed.
Tests verify tool logic: blacklist filtering, LIMIT injection, output formatting.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dbsage.mcp_server.config import Settings


def _settings(**kwargs: object) -> Settings:
    defaults: dict[str, object] = {
        "db_host": "localhost",
        "db_port": 3306,
        "db_name": "db",
        "db_user": "u",
        "db_password": "p",
        "db_type": "mysql",
        "max_query_rows": 100,
        "max_query_rows_hard_cap": 500,
        "query_timeout_ms": 3000,
        "slow_query_threshold_ms": 2000,
        "default_sample_limit": 10,
        "cache_ttl_seconds": 300,
        "blacklisted_tables": [],
        "dev_mode": False,
    }
    defaults.update(kwargs)
    return Settings(**defaults)  # type: ignore[arg-type]


def _patch_deps(settings: Settings) -> tuple:
    mock_engine = MagicMock()
    p_settings = patch(
        "dbsage.mcp_server.dependencies.get_settings", return_value=settings
    )
    p_engine = patch(
        "dbsage.mcp_server.dependencies.get_engine", return_value=mock_engine
    )
    return p_settings, p_engine, mock_engine


# ── discovery_tools ──────────────────────────────────────────────────────────


async def test_list_tables_returns_visible_tables() -> None:
    from dbsage.tools.discovery_tools import list_tables

    settings = _settings()
    p_s, p_e, engine = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.discovery_tools._list_tables",
            AsyncMock(return_value=["users", "orders", "products"]),
        ):
            result = await list_tables()
    assert "users" in result
    assert "orders" in result


async def test_list_tables_filters_blacklisted() -> None:
    from dbsage.tools.discovery_tools import list_tables

    settings = _settings(blacklisted_tables=["secret"])
    p_s, p_e, engine = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.discovery_tools._list_tables",
            AsyncMock(return_value=["users", "secret"]),
        ):
            result = await list_tables()
    assert "secret" not in result
    assert "users" in result


async def test_list_tables_empty_returns_message() -> None:
    from dbsage.tools.discovery_tools import list_tables

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.discovery_tools._list_tables",
            AsyncMock(return_value=[]),
        ):
            result = await list_tables()
    assert "no tables" in result


async def test_search_tables_matches_keyword() -> None:
    from dbsage.tools.discovery_tools import search_tables

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.discovery_tools._list_tables",
            AsyncMock(return_value=["users", "user_profiles", "orders"]),
        ):
            result = await search_tables("user")
    assert "users" in result
    assert "user_profiles" in result
    assert "orders" not in result


async def test_search_tables_no_match_returns_message() -> None:
    from dbsage.tools.discovery_tools import search_tables

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.discovery_tools._list_tables",
            AsyncMock(return_value=["users", "orders"]),
        ):
            result = await search_tables("xyz_nonexistent")
    assert "no tables" in result.lower()


# ── schema_tools ─────────────────────────────────────────────────────────────


async def test_describe_table_formats_columns() -> None:
    from dbsage.tools.schema_tools import describe_table

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    cols = [
        {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "PRI",
            "column_default": None,
            "extra": "auto_increment",
        },
        {
            "column_name": "org_id",
            "data_type": "bigint",
            "is_nullable": "NO",
            "column_key": "MUL",
            "column_default": None,
            "extra": "",
        },
    ]
    fks = [
        {
            "from_table": "users",
            "from_column": "org_id",
            "to_table": "Organizations",
            "to_column": "id",
            "constraint_name": "fk1",
        }
    ]
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools._describe_table", AsyncMock(return_value=cols)
        ):
            with patch(
                "dbsage.tools.schema_tools.get_foreign_keys",
                AsyncMock(return_value=fks),
            ):
                result = await describe_table("users")
    assert "id" in result
    assert "PK" in result
    assert "FK → Organizations.id" in result


async def test_describe_table_raises_on_blacklisted() -> None:
    from dbsage.exceptions import TableBlacklistedError
    from dbsage.tools.schema_tools import describe_table

    settings = _settings(blacklisted_tables=["secret"])
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with pytest.raises(TableBlacklistedError):
            await describe_table("secret")


async def test_table_relationships_formats_fks() -> None:
    from dbsage.tools.schema_tools import table_relationships

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    fks = [
        {
            "from_table": "orders",
            "from_column": "user_id",
            "to_table": "users",
            "to_column": "id",
            "constraint_name": "fk1",
        }
    ]
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.get_foreign_keys",
            AsyncMock(return_value=fks),
        ):
            result = await table_relationships()
    assert "orders.user_id" in result
    assert "users.id" in result
    assert "→" in result


async def test_table_relationships_no_fks() -> None:
    from dbsage.tools.schema_tools import table_relationships

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.get_foreign_keys",
            AsyncMock(return_value=[]),
        ):
            result = await table_relationships()
    assert "no foreign key" in result


async def test_schema_summary_shows_tables_and_relationships() -> None:
    from dbsage.tools.schema_tools import schema_summary

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    tables = [{"table_name": "users", "row_count": 1000, "size_mb": 0.5}]
    fks = [
        {
            "from_table": "orders",
            "from_column": "user_id",
            "to_table": "users",
            "to_column": "id",
            "constraint_name": "fk1",
        }
    ]
    with p_s, p_e:
        with patch("dbsage.tools.schema_tools.cache_get", return_value=None):
            with patch("dbsage.tools.schema_tools.cache_set"):
                with patch(
                    "dbsage.tools.schema_tools.get_table_sizes",
                    AsyncMock(return_value=tables),
                ):
                    with patch(
                        "dbsage.tools.schema_tools.get_foreign_keys",
                        AsyncMock(return_value=fks),
                    ):
                        result = await schema_summary()
    assert "users" in result
    assert "Relationships" in result


async def test_schema_summary_returns_cached_result() -> None:
    from dbsage.tools.schema_tools import schema_summary

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.cache_get", return_value="cached summary"
        ):
            result = await schema_summary()
    assert result == "cached summary"


# ── query_tools ──────────────────────────────────────────────────────────────


async def test_run_read_only_query_returns_table() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    rows = [{"id": 1, "name": "alice"}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.query_tools.execute_query", AsyncMock(return_value=rows)
        ):
            with patch("dbsage.tools.query_tools.log_query_executed", AsyncMock()):
                result = await run_read_only_query("SELECT * FROM users")
    assert "alice" in result
    assert "name" in result


async def test_run_read_only_query_blocks_forbidden() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch("dbsage.tools.query_tools.log_query_rejected", AsyncMock()):
            result = await run_read_only_query("DROP TABLE users")
    assert "✗" in result or "blocked" in result.lower()
    assert "DROP" in result


async def test_run_read_only_query_injects_limit() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings(max_query_rows=50)
    p_s, p_e, _ = _patch_deps(settings)
    captured: list[str] = []

    async def mock_execute(sql: str, *args: object, **kwargs: object) -> list:
        captured.append(sql)
        return []

    with p_s, p_e:
        with patch("dbsage.tools.query_tools.execute_query", mock_execute):
            with patch("dbsage.tools.query_tools.log_query_executed", AsyncMock()):
                await run_read_only_query("SELECT * FROM users")

    assert "LIMIT 50" in captured[0]


async def test_explain_query_returns_plan() -> None:
    from dbsage.tools.query_tools import explain_query

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    plan = [
        {
            "id": 1,
            "select_type": "SIMPLE",
            "table": "users",
            "type": "ALL",
            "key": None,
            "rows": 4,
            "Extra": "",
        }
    ]
    with p_s, p_e:
        with patch(
            "dbsage.tools.query_tools.execute_query", AsyncMock(return_value=plan)
        ):
            result = await explain_query("SELECT * FROM users")
    assert "SIMPLE" in result


async def test_explain_query_blocks_forbidden() -> None:
    from dbsage.tools.query_tools import explain_query

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        result = await explain_query("DROP TABLE users")
    assert "✗" in result or "blocked" in result.lower()


# ── sampling_tools ────────────────────────────────────────────────────────────


async def test_sample_table_returns_rows() -> None:
    from dbsage.tools.sampling_tools import sample_table

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    rows = [{"id": 1, "email": "a@b.com"}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.sampling_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await sample_table("users", limit=1)
    assert "email" in result
    assert "a@b.com" in result


async def test_sample_table_blocks_blacklisted() -> None:
    from dbsage.exceptions import TableBlacklistedError
    from dbsage.tools.sampling_tools import sample_table

    settings = _settings(blacklisted_tables=["secret"])
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with pytest.raises(TableBlacklistedError):
            await sample_table("secret")


async def test_sample_column_values_returns_values() -> None:
    from dbsage.tools.sampling_tools import sample_column_values

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    rows = [{"value": "active", "count": 50}, {"value": "inactive", "count": 10}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.sampling_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await sample_column_values("users", "status")
    assert "active" in result
    assert "50" in result


async def test_table_row_count_formats_human_readable() -> None:
    from dbsage.tools.sampling_tools import table_row_count

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    rows = [{"row_count": 1_500_000}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.sampling_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await table_row_count("users")
    assert "1.5M" in result


async def test_inspect_json_column_parses_json() -> None:
    import json

    from dbsage.tools.sampling_tools import inspect_json_column

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    payload = json.dumps({"key": "value", "nested": {"x": 1}})
    rows = [{"json_value": payload}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.sampling_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await inspect_json_column("users", "metadata")
    assert "key" in result
    assert "value" in result


# ── show_create_view ──────────────────────────────────────────────────────────


async def test_show_create_view_returns_full_sql() -> None:
    from dbsage.tools.schema_tools import show_create_view

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    long_sql = "CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`%` SQL SECURITY DEFINER VIEW `v` AS SELECT id, name FROM users WHERE active = 1 ORDER BY created_at DESC"
    rows = [
        {
            "View": "v",
            "Create View": long_sql,
            "character_set_client": "utf8mb4",
            "collation_connection": "utf8mb4_unicode_ci",
        }
    ]
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await show_create_view("v")
    assert long_sql in result
    assert "show_create_view" in result
    assert "utf8mb4" in result


async def test_show_create_view_raises_on_blacklisted() -> None:
    from dbsage.exceptions import TableBlacklistedError
    from dbsage.tools.schema_tools import show_create_view

    settings = _settings(blacklisted_tables=["secret_view"])
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with pytest.raises(TableBlacklistedError):
            await show_create_view("secret_view")


async def test_show_create_view_not_found() -> None:
    from dbsage.tools.schema_tools import show_create_view

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.execute_query", AsyncMock(return_value=[])
        ):
            result = await show_create_view("nonexistent_view")
    assert "not found" in result


async def test_show_create_view_table_not_view_error() -> None:
    """MySQL 'is not VIEW' error returns a clean user-facing message."""
    from dbsage.tools.schema_tools import show_create_view

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    with p_s, p_e:
        with patch(
            "dbsage.tools.schema_tools.execute_query",
            AsyncMock(side_effect=Exception("'RmaRatios' is not VIEW")),
        ):
            result = await show_create_view("RmaRatios")
    assert "is a table, not a view" in result
    assert "describe_table" in result


async def test_inspect_json_column_truncates_large_samples() -> None:
    """Samples larger than 2000 chars are truncated with a notice."""
    import json

    from dbsage.tools.sampling_tools import inspect_json_column

    settings = _settings()
    p_s, p_e, _ = _patch_deps(settings)
    # Build a JSON payload well over 2000 chars
    big_payload = json.dumps({"key_" + str(i): "x" * 100 for i in range(30)})
    assert len(big_payload) > 2000
    rows = [{"json_value": big_payload}]
    with p_s, p_e:
        with patch(
            "dbsage.tools.sampling_tools.execute_query", AsyncMock(return_value=rows)
        ):
            result = await inspect_json_column("users", "metadata")
    assert "truncated" in result


# ── run_read_only_query limit parameter ───────────────────────────────────────


async def test_run_read_only_query_uses_explicit_limit() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings(max_query_rows=100, max_query_rows_hard_cap=500)
    p_s, p_e, _ = _patch_deps(settings)
    captured: list[str] = []

    async def mock_execute(sql: str, *args: object, **kwargs: object) -> list:
        captured.append(sql)
        return []

    with p_s, p_e:
        with patch("dbsage.tools.query_tools.execute_query", mock_execute):
            with patch("dbsage.tools.query_tools.log_query_executed", AsyncMock()):
                await run_read_only_query("SELECT * FROM users", limit=25)

    assert "LIMIT 25" in captured[0]


async def test_run_read_only_query_clamps_limit_to_hard_cap() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings(max_query_rows=100, max_query_rows_hard_cap=50)
    p_s, p_e, _ = _patch_deps(settings)
    captured: list[str] = []

    async def mock_execute(sql: str, *args: object, **kwargs: object) -> list:
        captured.append(sql)
        return []

    with p_s, p_e:
        with patch("dbsage.tools.query_tools.execute_query", mock_execute):
            with patch("dbsage.tools.query_tools.log_query_executed", AsyncMock()):
                await run_read_only_query("SELECT * FROM users", limit=200)

    assert "LIMIT 50" in captured[0]


async def test_run_read_only_query_default_limit_unchanged() -> None:
    from dbsage.tools.query_tools import run_read_only_query

    settings = _settings(max_query_rows=100, max_query_rows_hard_cap=500)
    p_s, p_e, _ = _patch_deps(settings)
    captured: list[str] = []

    async def mock_execute(sql: str, *args: object, **kwargs: object) -> list:
        captured.append(sql)
        return []

    with p_s, p_e:
        with patch("dbsage.tools.query_tools.execute_query", mock_execute):
            with patch("dbsage.tools.query_tools.log_query_executed", AsyncMock()):
                await run_read_only_query("SELECT * FROM users")

    assert "LIMIT 100" in captured[0]
