"""Tests for connection_registry — engine caching, resolve_connections."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dbsage.db.connection_registry import (
    get_engine_for_profile,
    reset_registry,
    resolve_connections,
)
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


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the engine cache before each test."""
    reset_registry()


def test_get_engine_for_profile_creates_engine() -> None:
    profile = _profile()
    mock_engine = MagicMock()
    with patch(
        "dbsage.db.connection_registry._build_from_profile", return_value=mock_engine
    ) as mock_build:
        result = get_engine_for_profile("primary", profile, "secret")
        mock_build.assert_called_once_with(profile, "secret")
        assert result is mock_engine


def test_get_engine_for_profile_caches_engine() -> None:
    profile = _profile()
    mock_engine = MagicMock()
    with patch(
        "dbsage.db.connection_registry._build_from_profile", return_value=mock_engine
    ) as mock_build:
        first = get_engine_for_profile("primary", profile, "secret")
        second = get_engine_for_profile("primary", profile, "secret")
        assert first is second
        assert mock_build.call_count == 1  # created only once


def test_different_profiles_get_different_engines() -> None:
    profile_a = _profile(host="a.db.com", database="db_a")
    profile_b = _profile(host="b.db.com", database="db_b")
    engine_a = MagicMock()
    engine_b = MagicMock()
    engines_map = {"a": engine_a, "b": engine_b}
    call_count = [0]

    def _build(profile: ConnectionProfile, pw: str) -> MagicMock:
        call_count[0] += 1
        return engines_map["a"] if profile.host == "a.db.com" else engines_map["b"]

    with patch("dbsage.db.connection_registry._build_from_profile", side_effect=_build):
        ea = get_engine_for_profile("conn-a", profile_a, "pw")
        eb = get_engine_for_profile("conn-b", profile_b, "pw")
        assert ea is not eb


# ── resolve_connections ────────────────────────────────────────────────────────


def test_resolve_connections_plain_names() -> None:
    settings = _settings(
        connections={"primary": _profile(), "replica": _profile()},
        connection_groups={},
    )
    result = resolve_connections(["primary", "replica"], settings)
    assert result == ["primary", "replica"]


def test_resolve_connections_expands_group() -> None:
    settings = _settings(
        connections={
            "prod-us": _profile(),
            "prod-eu": _profile(),
        },
        connection_groups={"all-prod": ["prod-us", "prod-eu"]},
    )
    result = resolve_connections(["all-prod"], settings)
    assert result == ["prod-us", "prod-eu"]


def test_resolve_connections_deduplicates() -> None:
    settings = _settings(
        connections={"primary": _profile(), "replica": _profile()},
        connection_groups={"both": ["primary", "replica"]},
    )
    result = resolve_connections(["both", "primary"], settings)
    assert result == ["primary", "replica"]


def test_resolve_connections_unknown_name_passed_through() -> None:
    settings = _settings(connections={}, connection_groups={})
    result = resolve_connections(["nonexistent"], settings)
    assert result == ["nonexistent"]


def test_resolve_connections_empty_list() -> None:
    settings = _settings(connections={}, connection_groups={})
    result = resolve_connections([], settings)
    assert result == []


def test_resolve_connections_preserves_order() -> None:
    settings = _settings(
        connections={"a": _profile(), "b": _profile(), "c": _profile()},
        connection_groups={},
    )
    result = resolve_connections(["c", "a", "b"], settings)
    assert result == ["c", "a", "b"]
