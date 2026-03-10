"""Tests for schema_explorer — mocks execute_query to avoid DB calls."""

from unittest.mock import AsyncMock, patch

import pytest

from dbsage.schema.schema_explorer import (
    describe_table,
    get_foreign_keys,
    get_table_sizes,
    list_tables,
)
from dbsage.cache.schema_cache import cache_invalidate


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Flush schema cache before each test to prevent cross-test pollution."""
    cache_invalidate()


@pytest.fixture
def mock_engine() -> AsyncMock:
    return AsyncMock()


# --- list_tables ---

async def test_list_tables_returns_sorted_names(mock_engine: AsyncMock) -> None:
    rows = [{"TABLE_NAME": "users"}, {"TABLE_NAME": "orders"}]
    with patch("dbsage.schema.schema_explorer.execute_query", AsyncMock(return_value=rows)):
        result = await list_tables(mock_engine)
    assert result == ["users", "orders"]


async def test_list_tables_cached_on_second_call(mock_engine: AsyncMock) -> None:
    rows = [{"TABLE_NAME": "users"}]
    mock_exec = AsyncMock(return_value=rows)
    with patch("dbsage.schema.schema_explorer.execute_query", mock_exec):
        await list_tables(mock_engine)
        await list_tables(mock_engine)
    # execute_query should only be called once (second call hits cache)
    assert mock_exec.call_count == 1


async def test_list_tables_empty_db(mock_engine: AsyncMock) -> None:
    with patch("dbsage.schema.schema_explorer.execute_query", AsyncMock(return_value=[])):
        result = await list_tables(mock_engine)
    assert result == []


# --- describe_table ---

async def test_describe_table_returns_columns(mock_engine: AsyncMock) -> None:
    rows = [
        {"column_name": "id", "data_type": "int", "is_nullable": "NO",
         "column_key": "PRI", "column_default": None, "extra": "auto_increment"},
        {"column_name": "email", "data_type": "varchar", "is_nullable": "NO",
         "column_key": "UNI", "column_default": None, "extra": ""},
    ]
    with patch("dbsage.schema.schema_explorer.execute_query", AsyncMock(return_value=rows)):
        result = await describe_table("users", mock_engine)
    assert len(result) == 2
    assert result[0]["column_name"] == "id"


async def test_describe_table_cached(mock_engine: AsyncMock) -> None:
    rows = [{"column_name": "id", "data_type": "int", "is_nullable": "NO",
             "column_key": "PRI", "column_default": None, "extra": ""}]
    mock_exec = AsyncMock(return_value=rows)
    with patch("dbsage.schema.schema_explorer.execute_query", mock_exec):
        await describe_table("users", mock_engine)
        await describe_table("users", mock_engine)
    assert mock_exec.call_count == 1


# --- get_foreign_keys ---

async def test_get_foreign_keys_all(mock_engine: AsyncMock) -> None:
    rows = [{"from_table": "orders", "from_column": "user_id",
             "to_table": "users", "to_column": "id", "constraint_name": "fk1"}]
    with patch("dbsage.schema.schema_explorer.execute_query", AsyncMock(return_value=rows)):
        result = await get_foreign_keys(mock_engine)
    assert len(result) == 1
    assert result[0]["from_table"] == "orders"


async def test_get_foreign_keys_for_specific_table(mock_engine: AsyncMock) -> None:
    rows: list[dict] = []
    mock_exec = AsyncMock(return_value=rows)
    with patch("dbsage.schema.schema_explorer.execute_query", mock_exec):
        result = await get_foreign_keys(mock_engine, table_name="orders")
    assert result == []
    # Verify the SQL contained the table filter
    called_sql = mock_exec.call_args[0][0]
    assert "orders" in called_sql


# --- get_table_sizes ---

async def test_get_table_sizes_returns_list(mock_engine: AsyncMock) -> None:
    rows = [
        {"table_name": "users", "row_count": 1000, "size_mb": 0.5},
        {"table_name": "orders", "row_count": 50000, "size_mb": 12.3},
    ]
    with patch("dbsage.schema.schema_explorer.execute_query", AsyncMock(return_value=rows)):
        result = await get_table_sizes(mock_engine)
    assert len(result) == 2
    assert result[0]["table_name"] == "users"


async def test_get_table_sizes_cached(mock_engine: AsyncMock) -> None:
    rows = [{"table_name": "users", "row_count": 1000, "size_mb": 0.5}]
    mock_exec = AsyncMock(return_value=rows)
    with patch("dbsage.schema.schema_explorer.execute_query", mock_exec):
        await get_table_sizes(mock_engine)
        await get_table_sizes(mock_engine)
    assert mock_exec.call_count == 1
