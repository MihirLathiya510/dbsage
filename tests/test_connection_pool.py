"""Tests for connection_pool — verifies URL construction for MySQL and PostgreSQL."""

from unittest.mock import MagicMock, patch

import pytest

from dbsage.db.connection_pool import build_engine, get_engine
from dbsage.mcp_server.config import Settings


def _make_settings(**kwargs: object) -> Settings:
    defaults = dict(
        db_host="localhost",
        db_port=3306,
        db_name="testdb",
        db_user="admin",
        db_password="secret",
        db_type="mysql",
        cache_ttl_seconds=300,
    )
    defaults.update(kwargs)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_build_engine_mysql_url() -> None:
    settings = _make_settings(db_type="mysql")
    with patch("dbsage.db.connection_pool.create_async_engine") as mock_create:
        mock_create.return_value = MagicMock()
        build_engine(settings)
    url = str(mock_create.call_args[0][0])
    assert "mysql+aiomysql" in url
    assert "localhost" in url
    assert "testdb" in url


def test_build_engine_postgresql_url() -> None:
    settings = _make_settings(db_type="postgresql", db_port=5432)
    with patch("dbsage.db.connection_pool.create_async_engine") as mock_create:
        mock_create.return_value = MagicMock()
        build_engine(settings)
    url = str(mock_create.call_args[0][0])
    assert "postgresql+asyncpg" in url


def test_build_engine_pool_config() -> None:
    settings = _make_settings()
    with patch("dbsage.db.connection_pool.create_async_engine") as mock_create:
        mock_create.return_value = MagicMock()
        build_engine(settings)
    kwargs = mock_create.call_args[1]
    assert kwargs["pool_size"] == 10
    assert kwargs["max_overflow"] == 20
    assert kwargs["pool_recycle"] == 1800


def test_get_engine_returns_singleton() -> None:
    settings = _make_settings()
    mock_eng = MagicMock()
    with patch("dbsage.db.connection_pool.build_engine", return_value=mock_eng):
        with patch("dbsage.db.connection_pool._engine", None):
            import dbsage.db.connection_pool as pool_module
            pool_module._engine = None  # reset singleton
            e1 = get_engine(settings)
            e2 = get_engine(settings)
    assert e1 is e2
