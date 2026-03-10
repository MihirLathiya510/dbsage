"""Tests for query_executor — mocks async SQLAlchemy session."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dbsage.db.query_executor import execute_query
from dbsage.exceptions import ConnectionPoolError, QueryTimeoutError


@pytest.fixture
def mock_engine() -> AsyncMock:
    return AsyncMock()


def _make_mock_result(rows: list[dict]) -> MagicMock:
    """Build a mock SQLAlchemy result with row._mapping dicts."""
    mock_rows = []
    for row_dict in rows:
        mock_row = MagicMock()
        mock_row._mapping = row_dict
        mock_rows.append(mock_row)
    result = MagicMock()
    result.fetchall.return_value = mock_rows
    return result


async def test_returns_list_of_dicts(mock_engine: AsyncMock) -> None:
    expected = [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]
    mock_result = _make_mock_result(expected)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("dbsage.db.query_executor.async_sessionmaker") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_session)
        result = await execute_query("SELECT * FROM users", mock_engine, timeout_ms=3000)

    assert result == expected


async def test_empty_result_returns_empty_list(mock_engine: AsyncMock) -> None:
    mock_result = _make_mock_result([])
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("dbsage.db.query_executor.async_sessionmaker") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_session)
        result = await execute_query("SELECT 1", mock_engine, timeout_ms=3000)

    assert result == []


async def test_timeout_raises_query_timeout_error(mock_engine: AsyncMock) -> None:
    async def slow_execute(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(10)

    mock_session = AsyncMock()
    mock_session.execute = slow_execute
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("dbsage.db.query_executor.async_sessionmaker") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_session)
        with pytest.raises(QueryTimeoutError):
            await execute_query("SELECT SLEEP(10)", mock_engine, timeout_ms=10)


async def test_sqlalchemy_error_raises_connection_pool_error(mock_engine: AsyncMock) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("connection refused"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("dbsage.db.query_executor.async_sessionmaker") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_session)
        with pytest.raises(ConnectionPoolError):
            await execute_query("SELECT 1", mock_engine, timeout_ms=3000)
