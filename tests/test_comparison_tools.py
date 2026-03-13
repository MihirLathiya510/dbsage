"""Tests for comparison_tools — cross-connection query, schema diff, find, count."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dbsage.mcp_server.config import ConnectionProfile, Settings

_NO_JSON = Path("/nonexistent/connections.json")


@pytest.fixture(autouse=True)
def no_connections_json() -> None:  # type: ignore[return]
    """Prevent config/connections.json from loading during Settings() construction."""
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", _NO_JSON):
        yield


def _profile(**kwargs: object) -> ConnectionProfile:
    defaults: dict[str, object] = {
        "host": "db.example.com",
        "port": 3306,
        "database": "app_db",
        "user": "ro_user",
        "password_env": "MY_DB_PASSWORD",
        "db_type": "mysql",
        "description": "",
        "requires_confirmation": False,
    }
    defaults.update(kwargs)
    return ConnectionProfile(**defaults)  # type: ignore[arg-type]


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


def _two_conn_settings() -> Settings:
    return _settings(
        connections={
            "primary": _profile(host="primary.db.com"),
            "replica": _profile(host="replica.db.com"),
        }
    )


# ── compare_query_across_connections ──────────────────────────────────────────


async def test_compare_query_blocks_forbidden() -> None:
    from dbsage.tools.comparison_tools import compare_query_across_connections

    s = _two_conn_settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await compare_query_across_connections(
            query="DROP TABLE users",
            connections=["primary", "replica"],
        )
    assert "blocked" in result.lower()


async def test_compare_query_runs_on_both() -> None:
    from dbsage.tools.comparison_tools import compare_query_across_connections

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[{"count": 42}]),
        ),
    ):
        result = await compare_query_across_connections(
            query="SELECT COUNT(*) AS count FROM orders",
            connections=["primary", "replica"],
        )

    assert "=== primary ===" in result
    assert "=== replica ===" in result


async def test_compare_query_one_fails_other_succeeds() -> None:
    from dbsage.tools.comparison_tools import compare_query_across_connections

    s = _two_conn_settings()
    mock_engine = MagicMock()
    call_count = [0]

    async def _side_effect(*args: object, **kwargs: object) -> list:
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("connection refused")
        return [{"count": 10}]

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch("dbsage.tools.comparison_tools.execute_query", side_effect=_side_effect),
    ):
        result = await compare_query_across_connections(
            query="SELECT COUNT(*) AS count FROM orders",
            connections=["primary", "replica"],
        )

    assert "ERROR" in result
    # Both sections should still be present
    assert "=== primary ===" in result
    assert "=== replica ===" in result


async def test_compare_query_no_connections() -> None:
    from dbsage.tools.comparison_tools import compare_query_across_connections

    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await compare_query_across_connections(
            query="SELECT 1",
            connections=[],
        )
    assert "no connections" in result


async def test_compare_query_unknown_profile() -> None:
    from dbsage.tools.comparison_tools import compare_query_across_connections

    # connections dict has no profiles, so "ghost" is unknown
    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await compare_query_across_connections(
            query="SELECT 1",
            connections=["ghost"],
        )
    assert "unknown profile" in result
    assert "=== ghost ===" in result


# ── diff_schema ────────────────────────────────────────────────────────────────


async def test_diff_schema_unknown_connection() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _settings(connections={"primary": _profile()})
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await diff_schema("primary", "nonexistent")

    assert "Unknown connection" in result


async def test_diff_schema_table_list_only_a() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._list_tables",
            new=AsyncMock(side_effect=[
                ["users", "orders", "feature_flags"],
                ["users", "orders"],
            ]),
        ),
    ):
        result = await diff_schema("primary", "replica")

    assert "feature_flags" in result
    assert "primary" in result


async def test_diff_schema_table_list_identical() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._list_tables",
            new=AsyncMock(side_effect=[["users", "orders"], ["users", "orders"]]),
        ),
    ):
        result = await diff_schema("primary", "replica")

    assert "(none)" in result


async def test_diff_schema_column_diff() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    cols_a = [
        {"column_name": "id", "data_type": "int", "is_nullable": "NO"},
        {"column_name": "discount_code", "data_type": "varchar", "is_nullable": "YES"},
    ]
    cols_b = [
        {"column_name": "id", "data_type": "int", "is_nullable": "NO"},
    ]

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._describe_table",
            new=AsyncMock(side_effect=[cols_a, cols_b]),
        ),
    ):
        result = await diff_schema("primary", "replica", table="orders")

    assert "discount_code" in result
    assert "only in primary" in result
    assert "id" in result  # identical columns


# ── find_table_across_connections ──────────────────────────────────────────────


async def test_find_table_found_and_not_found() -> None:
    from dbsage.tools.comparison_tools import find_table_across_connections

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._list_tables",
            new=AsyncMock(side_effect=[
                ["users", "feature_flags"],
                ["users"],
            ]),
        ),
    ):
        result = await find_table_across_connections("feature_flags")

    assert "FOUND" in result
    assert "NOT FOUND" in result
    assert "1 of 2 connections" in result


async def test_find_table_no_connections() -> None:
    from dbsage.tools.comparison_tools import find_table_across_connections

    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await find_table_across_connections("orders")

    assert "no named connection profiles" in result


async def test_find_table_unknown_explicit_connection() -> None:
    from dbsage.tools.comparison_tools import find_table_across_connections

    s = _settings(connections={"primary": _profile()})
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await find_table_across_connections("orders", connections=["ghost"])

    assert "unknown profile" in result
    assert "ghost" in result


# ── compare_row_counts ─────────────────────────────────────────────────────────


async def test_compare_row_counts_returns_counts() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[{"row_count": 1000000}]),
        ),
    ):
        result = await compare_row_counts("orders")

    assert "primary" in result
    assert "replica" in result
    assert "1.0M" in result


async def test_compare_row_counts_no_connections() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await compare_row_counts("orders")

    assert "no named connection profiles" in result


async def test_compare_row_counts_unknown_explicit_connection() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await compare_row_counts("orders", connections=["ghost"])

    assert "unknown profile" in result
    assert "ghost" in result


async def test_compare_row_counts_table_not_found() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await compare_row_counts("nonexistent_table")

    # Missing table renders as — (neutral), not as an ERROR
    assert "—" in result
    assert "ERROR" not in result


async def test_compare_row_counts_thousands_format() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[{"row_count": 42500}]),
        ),
    ):
        result = await compare_row_counts("orders")

    assert "42.5k" in result


async def test_compare_row_counts_small_number() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[{"row_count": 7}]),
        ),
    ):
        result = await compare_row_counts("orders")

    assert "7" in result


async def test_compare_row_counts_query_error() -> None:
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(side_effect=Exception("timeout")),
        ),
    ):
        result = await compare_row_counts("orders")

    assert "ERROR" in result
    assert "primary" in result


async def test_diff_schema_table_list_only_b() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._list_tables",
            new=AsyncMock(side_effect=[
                ["users", "orders"],
                ["users", "orders", "audit_log"],
            ]),
        ),
    ):
        result = await diff_schema("primary", "replica")

    assert "audit_log" in result
    assert "replica" in result


async def test_diff_schema_column_only_b_and_type_diff() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    cols_a = [
        {"column_name": "id", "data_type": "int", "is_nullable": "NO"},
        {"column_name": "status", "data_type": "varchar", "is_nullable": "YES"},
    ]
    cols_b = [
        {"column_name": "id", "data_type": "bigint", "is_nullable": "NO"},
        {"column_name": "status", "data_type": "varchar", "is_nullable": "YES"},
        {"column_name": "archived_at", "data_type": "datetime", "is_nullable": "YES"},
    ]

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._describe_table",
            new=AsyncMock(side_effect=[cols_a, cols_b]),
        ),
    ):
        result = await diff_schema("primary", "replica", table="orders")

    assert "archived_at" in result
    assert "only in replica" in result
    assert "int" in result  # type diff on id
    assert "bigint" in result


async def test_diff_schema_column_nullable_diff() -> None:
    from dbsage.tools.comparison_tools import diff_schema

    s = _two_conn_settings()
    mock_engine = MagicMock()

    # Same type, different nullability
    cols_a = [{"column_name": "email", "data_type": "varchar", "is_nullable": "NO"}]
    cols_b = [{"column_name": "email", "data_type": "varchar", "is_nullable": "YES"}]

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools._describe_table",
            new=AsyncMock(side_effect=[cols_a, cols_b]),
        ),
    ):
        result = await diff_schema("primary", "replica", table="users")

    assert "nullable" in result
    assert "email" in result


async def test_compare_row_counts_null_row_count() -> None:
    """information_schema returns a row but TABLE_ROWS is NULL — show — (neutral)."""
    from dbsage.tools.comparison_tools import compare_row_counts

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.comparison_tools.execute_query",
            new=AsyncMock(return_value=[{"row_count": None}]),
        ),
    ):
        result = await compare_row_counts("orders")

    assert "—" in result
    assert "ERROR" not in result


async def test_find_table_error_on_one_connection() -> None:
    from dbsage.tools.comparison_tools import find_table_across_connections

    s = _two_conn_settings()
    mock_engine = MagicMock()
    call_count = [0]

    async def _side_effect(*args: object, **kwargs: object) -> list:
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("connection refused")
        return ["users"]

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.comparison_tools.get_engine_for", return_value=mock_engine),
        patch("dbsage.tools.comparison_tools._list_tables", side_effect=_side_effect),
    ):
        result = await find_table_across_connections("users")

    assert "ERROR" in result
    assert "primary" in result
