"""Tests for structured query logger."""

from unittest.mock import AsyncMock, MagicMock, patch

from dbsage.logging_.query_logger import (
    configure_logging,
    log_query_executed,
    log_query_rejected,
    log_slow_query,
)


def _make_mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.ainfo = AsyncMock()
    logger.awarning = AsyncMock()
    return logger


async def test_log_query_executed_calls_ainfo() -> None:
    mock_log = _make_mock_logger()
    with patch("dbsage.logging_.query_logger.get_logger", return_value=mock_log):
        with patch("dbsage.mcp_server.config.get_settings") as mock_settings:
            mock_settings.return_value.slow_query_threshold_ms = 9999
            await log_query_executed(
                "SELECT 1", execution_time_ms=45.0, rows_returned=1
            )
    mock_log.ainfo.assert_called_once()
    call_kwargs = mock_log.ainfo.call_args[1]
    assert call_kwargs["rows_returned"] == 1
    assert call_kwargs["execution_time_ms"] == 45.0


async def test_log_query_executed_triggers_slow_query_when_threshold_exceeded() -> None:
    mock_log = _make_mock_logger()
    with patch("dbsage.logging_.query_logger.get_logger", return_value=mock_log):
        with patch("dbsage.mcp_server.config.get_settings") as mock_settings:
            mock_settings.return_value.slow_query_threshold_ms = 100
            with patch(
                "dbsage.logging_.query_logger.log_slow_query", AsyncMock()
            ) as mock_slow:
                await log_query_executed(
                    "SELECT * FROM big_table",
                    execution_time_ms=5000.0,
                    rows_returned=100,
                )
                mock_slow.assert_called_once()


async def test_log_query_rejected_calls_awarning() -> None:
    mock_log = _make_mock_logger()
    with patch("dbsage.logging_.query_logger.get_logger", return_value=mock_log):
        await log_query_rejected(
            "DROP TABLE users", reason="forbidden_keyword", keyword="DROP"
        )
    mock_log.awarning.assert_called_once()
    call_kwargs = mock_log.awarning.call_args[1]
    assert call_kwargs["keyword"] == "DROP"
    assert call_kwargs["reason"] == "forbidden_keyword"


async def test_log_slow_query_calls_awarning() -> None:
    mock_log = _make_mock_logger()
    with patch("dbsage.logging_.query_logger.get_logger", return_value=mock_log):
        await log_slow_query("SELECT * FROM users", elapsed_ms=3500.0)
    mock_log.awarning.assert_called_once()
    call_kwargs = mock_log.awarning.call_args[1]
    assert call_kwargs["elapsed_ms"] == 3500.0


def test_configure_logging_dev_mode_doesnt_raise() -> None:
    configure_logging(dev_mode=True)


def test_configure_logging_prod_mode_doesnt_raise() -> None:
    configure_logging(dev_mode=False)
