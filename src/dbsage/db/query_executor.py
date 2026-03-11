"""Async query executor with timeout enforcement.

All queries pass through here after validation and rewriting.
Enforces asyncio.timeout() — never blocks the event loop.
"""

import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from dbsage.exceptions import ConnectionPoolError, QueryTimeoutError


async def execute_query(
    sql: str,
    engine: AsyncEngine,
    timeout_ms: int = 3000,
) -> list[dict[str, Any]]:
    """Execute a SQL query and return results as a list of dicts.

    Raises:
        QueryTimeoutError: if the query exceeds timeout_ms.
        ConnectionPoolError: on SQLAlchemy connection errors.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with asyncio.timeout(timeout_ms / 1000):
            async with session_factory() as session:
                result = await session.execute(text(sql))
                return [dict(row._mapping) for row in result.fetchall()]
    except TimeoutError as e:
        raise QueryTimeoutError(f"Query exceeded timeout of {timeout_ms}ms") from e
    except SQLAlchemyError as e:
        raise ConnectionPoolError(f"Database error: {e}") from e
