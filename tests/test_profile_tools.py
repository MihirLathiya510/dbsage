"""Tests for profile_tools — add_connection and remove_connection."""

import json
from pathlib import Path
from unittest.mock import patch


def _write_connections(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def _read_connections(path: Path) -> dict:
    return json.loads(path.read_text())  # type: ignore[return-value]


# ── add_connection ─────────────────────────────────────────────────────────────


async def test_add_connection_success(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {}})

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings") as mock_settings,
    ):
        result = await add_connection(
            name="test_db",
            host="db.example.com",
            database="app_db",
            user="ro_user",
        )

    assert "test_db" in result
    assert "added" in result
    data = _read_connections(conn_file)
    assert "test_db" in data["connections"]
    profile = data["connections"]["test_db"]
    assert profile["host"] == "db.example.com"
    assert profile["database"] == "app_db"
    assert profile["user"] == "ro_user"
    mock_settings.cache_clear.assert_called_once()


async def test_add_connection_duplicate_name(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(
        conn_file,
        {
            "connections": {
                "existing": {
                    "host": "h",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "db_type": "mysql",
                }
            }
        },
    )

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await add_connection(
            name="existing", host="other.com", database="db", user="u"
        )

    assert "already exists" in result
    # File unchanged — existing profile still there
    data = _read_connections(conn_file)
    assert data["connections"]["existing"]["host"] == "h"


async def test_add_connection_creates_file_if_missing(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"  # does not exist

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings"),
    ):
        result = await add_connection(
            name="new_db", host="h.com", database="db", user="u"
        )

    assert "added" in result
    assert conn_file.exists()
    data = _read_connections(conn_file)
    assert "new_db" in data["connections"]


async def test_add_connection_invalid_db_type(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {}})

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await add_connection(
            name="x", host="h", database="db", user="u", db_type="oracle"
        )

    assert "error" in result
    assert "db_type" in result


async def test_add_connection_invalid_port(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {}})

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await add_connection(
            name="x", host="h", database="db", user="u", port=99999
        )

    assert "error" in result
    assert "port" in result


async def test_add_connection_malformed_json_file(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    conn_file.write_text("{ not valid json }")

    original_content = conn_file.read_text()

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await add_connection(name="x", host="h", database="db", user="u")

    assert "error" in result
    assert "invalid JSON" in result
    # File must not be clobbered
    assert conn_file.read_text() == original_content


async def test_add_connection_empty_name(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {}})

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await add_connection(name="  ", host="h", database="db", user="u")

    assert "error" in result
    assert "name" in result


async def test_add_connection_optional_fields_omitted_when_empty(
    tmp_path: Path,
) -> None:
    from dbsage.tools.profile_tools import add_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {}})

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings"),
    ):
        await add_connection(name="minimal", host="h", database="db", user="u")

    profile = _read_connections(conn_file)["connections"]["minimal"]
    assert "password" not in profile
    assert "password_env" not in profile
    assert "description" not in profile
    assert "requires_confirmation" not in profile


# ── remove_connection ──────────────────────────────────────────────────────────


async def test_remove_connection_success(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import remove_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(
        conn_file,
        {
            "connections": {
                "old": {
                    "host": "h",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "db_type": "mysql",
                }
            }
        },
    )

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings") as mock_settings,
        patch("dbsage.tools.profile_tools.reset_registry") as mock_reset,
    ):
        result = await remove_connection(name="old")

    assert "removed" in result
    data = _read_connections(conn_file)
    assert "old" not in data["connections"]
    mock_settings.cache_clear.assert_called_once()
    mock_reset.assert_called_once()


async def test_remove_connection_unknown_name(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import remove_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(conn_file, {"connections": {"other": {}}})

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await remove_connection(name="ghost")

    assert "error" in result
    assert "ghost" in result


async def test_remove_connection_clears_default(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import remove_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(
        conn_file,
        {
            "default": "primary",
            "connections": {
                "primary": {
                    "host": "h",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "db_type": "mysql",
                }
            },
        },
    )

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings"),
        patch("dbsage.tools.profile_tools.reset_registry"),
    ):
        result = await remove_connection(name="primary")

    data = _read_connections(conn_file)
    assert data.get("default") == ""
    assert "cleared default" in result


async def test_remove_connection_cleans_groups(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import remove_connection

    conn_file = tmp_path / "connections.json"
    _write_connections(
        conn_file,
        {
            "connections": {
                "a": {
                    "host": "h",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "db_type": "mysql",
                },
                "b": {
                    "host": "h",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "db_type": "mysql",
                },
            },
            "groups": {
                "prod": ["a", "b"],
                "solo": ["a"],
            },
        },
    )

    with (
        patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file),
        patch("dbsage.tools.profile_tools.get_settings"),
        patch("dbsage.tools.profile_tools.reset_registry"),
    ):
        await remove_connection(name="a")

    data = _read_connections(conn_file)
    # 'a' removed from 'prod' group; 'solo' group dropped (became empty)
    assert "a" not in data["groups"]["prod"]
    assert "b" in data["groups"]["prod"]
    assert "solo" not in data["groups"]


async def test_remove_connection_no_json_file(tmp_path: Path) -> None:
    from dbsage.tools.profile_tools import remove_connection

    conn_file = tmp_path / "connections.json"  # does not exist

    with patch("dbsage.tools.profile_tools._CONNECTIONS_JSON", conn_file):
        result = await remove_connection(name="any")

    assert "error" in result
    assert "not found" in result
