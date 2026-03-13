"""Tests for connection_tools — list_connections and ping_connections."""

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
        "description": "Test DB",
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


# ── list_connections ───────────────────────────────────────────────────────────


async def test_list_connections_no_profiles() -> None:
    from dbsage.tools.connection_tools import list_connections

    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await list_connections()

    assert "no named connection profiles" in result


async def test_list_connections_shows_names() -> None:
    from dbsage.tools.connection_tools import list_connections

    s = _settings(
        connections={
            "primary": _profile(host="primary.db.com", description="Main DB"),
            "replica": _profile(host="replica.db.com", description="Read replica"),
        },
        default_connection="primary",
    )
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await list_connections()

    assert "primary" in result
    assert "replica" in result
    assert "primary.db.com" in result
    assert "Main DB" in result


async def test_list_connections_marks_sensitive() -> None:
    from dbsage.tools.connection_tools import list_connections

    s = _settings(
        connections={
            "prod": _profile(requires_confirmation=True),
        },
    )
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await list_connections()

    assert "YES" in result


async def test_list_connections_shows_groups() -> None:
    from dbsage.tools.connection_tools import list_connections

    s = _settings(
        connections={"primary": _profile()},
        connection_groups={"all-dev": ["primary"]},
    )
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await list_connections()

    assert "all-dev" in result


# ── ping_connections ───────────────────────────────────────────────────────────


async def test_ping_connections_no_profiles() -> None:
    from dbsage.tools.connection_tools import ping_connections

    s = _settings()
    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await ping_connections()

    assert "no named connection profiles" in result


async def test_ping_connections_ok() -> None:
    from dbsage.tools.connection_tools import ping_connections

    s = _settings(connections={"primary": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.connection_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.connection_tools.execute_query",
            new=AsyncMock(return_value=[{"1": 1}]),
        ),
    ):
        result = await ping_connections()

    assert "OK" in result
    assert "primary" in result


async def test_ping_connections_failed() -> None:
    from dbsage.tools.connection_tools import ping_connections

    s = _settings(connections={"flaky": _profile()})
    mock_engine = MagicMock()

    with (
        patch("dbsage.mcp_server.dependencies.get_settings", return_value=s),
        patch("dbsage.tools.connection_tools.get_engine_for", return_value=mock_engine),
        patch(
            "dbsage.tools.connection_tools.execute_query",
            new=AsyncMock(side_effect=Exception("connection refused")),
        ),
    ):
        result = await ping_connections()

    assert "FAILED" in result
    assert "flaky" in result


async def test_ping_connections_unknown_profile() -> None:
    from dbsage.tools.connection_tools import ping_connections

    s = _settings(connections={"primary": _profile()})

    with patch("dbsage.mcp_server.dependencies.get_settings", return_value=s):
        result = await ping_connections(connections=["nonexistent"])

    assert "unknown profile" in result
