"""Structured query logger using structlog.

Named logging_ (with underscore) to avoid shadowing Python's stdlib logging module.
All log events are structured key=value pairs — never interpolated strings.
JSON output in production, human-readable ConsoleRenderer in dev mode.
"""

import logging

import structlog


def configure_logging(dev_mode: bool = False) -> None:
    """Configure structlog processors.

    Call once at server startup (from server.py).
    """
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if dev_mode:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to suppress noise
    logging.basicConfig(level=logging.WARNING)


def get_logger() -> structlog.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger()


async def log_query_executed(
    query: str,
    execution_time_ms: float,
    rows_returned: int,
) -> None:
    """Log a successfully executed query."""
    log = get_logger()
    await log.ainfo(
        "query_executed",
        query=query,
        execution_time_ms=round(execution_time_ms, 2),
        rows_returned=rows_returned,
    )

    # Flag slow queries
    from dbsage.mcp_server.config import get_settings  # avoid circular import

    settings = get_settings()
    if execution_time_ms > settings.slow_query_threshold_ms:
        await log_slow_query(query, execution_time_ms)


async def log_query_rejected(query: str, reason: str, keyword: str) -> None:
    """Log a rejected (forbidden) query."""
    log = get_logger()
    await log.awarning(
        "query_rejected",
        reason=reason,
        keyword=keyword,
        query=query,
    )


async def log_slow_query(query: str, elapsed_ms: float) -> None:
    """Log a query that exceeded the slow query threshold."""
    log = get_logger()
    await log.awarning(
        "slow_query_detected",
        query=query,
        elapsed_ms=round(elapsed_ms, 2),
    )
