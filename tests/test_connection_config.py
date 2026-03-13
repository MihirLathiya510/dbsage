"""Tests for ConnectionProfile model and load_connections_json validator."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dbsage.mcp_server.config import ConnectionProfile, Settings


def _minimal_profile_data(**overrides: object) -> dict:
    data: dict = {
        "host": "db.example.com",
        "port": 3306,
        "database": "app_db",
        "user": "ro_user",
    }
    data.update(overrides)
    return data


def test_connection_profile_defaults() -> None:
    p = ConnectionProfile(**_minimal_profile_data())  # type: ignore[arg-type]
    assert p.db_type == "mysql"
    assert p.description == ""
    assert p.requires_confirmation is False
    assert p.max_query_rows is None
    assert p.query_timeout_ms is None
    assert p.password == ""
    assert p.password_env == ""


def test_connection_profile_requires_confirmation() -> None:
    p = ConnectionProfile(**_minimal_profile_data(requires_confirmation=True))  # type: ignore[arg-type]
    assert p.requires_confirmation is True


def test_load_connections_json_populates_connections(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "default": "primary",
                "groups": {"all-dev": ["primary"]},
                "connections": {
                    "primary": _minimal_profile_data(description="Main DB"),
                },
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    assert "primary" in s.connections
    assert s.connections["primary"].description == "Main DB"
    assert s.default_connection == "primary"
    assert s.connection_groups == {"all-dev": ["primary"]}


def test_missing_connections_json_does_not_raise(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_file.json"
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", nonexistent):
        s = Settings()
    assert s.connections == {}


def test_malformed_connections_json_does_not_raise(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not { valid json {{")
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", bad_file):
        s = Settings()
    assert s.connections == {}


def test_malformed_profile_skipped_silently(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "good": _minimal_profile_data(),
                    "bad": {"host": "only-host-no-required-fields"},
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    assert "good" in s.connections
    assert "bad" not in s.connections


def test_multiple_profiles_loaded(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "primary": _minimal_profile_data(host="primary.db.com"),
                    "replica": _minimal_profile_data(host="replica.db.com"),
                    "analytics": _minimal_profile_data(
                        host="analytics.db.com", db_type="postgresql"
                    ),
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    assert len(s.connections) == 3
    assert s.connections["analytics"].db_type == "postgresql"


def test_get_password_for_inline_password(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "primary": _minimal_profile_data(password="direct_secret")
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    pw = s.get_password_for(s.connections["primary"])
    assert pw == "direct_secret"


def test_get_password_for_reads_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MY_SECRET_PW", "super_secret")
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "primary": _minimal_profile_data(password_env="MY_SECRET_PW")
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    pw = s.get_password_for(s.connections["primary"])
    assert pw == "super_secret"


def test_get_password_for_inline_takes_precedence_over_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MY_SECRET_PW", "env_secret")
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "primary": _minimal_profile_data(
                        password="inline_secret",
                        password_env="MY_SECRET_PW",
                    )
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    pw = s.get_password_for(s.connections["primary"])
    assert pw == "inline_secret"  # inline wins


def test_get_password_for_missing_env_returns_empty(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps(
            {
                "connections": {
                    "primary": _minimal_profile_data(
                        password_env="DEFINITELY_NOT_SET_XYZ"
                    )
                }
            }
        )
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    pw = s.get_password_for(s.connections["primary"])
    assert pw == ""


def test_get_password_for_neither_set_returns_empty(tmp_path: Path) -> None:
    conn_file = tmp_path / "connections.json"
    conn_file.write_text(
        json.dumps({"connections": {"primary": _minimal_profile_data()}})
    )
    with patch("dbsage.mcp_server.config._CONNECTIONS_JSON", conn_file):
        s = Settings()
    pw = s.get_password_for(s.connections["primary"])
    assert pw == ""
