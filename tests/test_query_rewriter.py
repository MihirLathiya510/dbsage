"""Tests for the query rewriter — LIMIT injection."""

from dbsage.db.query_rewriter import rewrite_query


def test_injects_limit_when_missing() -> None:
    """A query without LIMIT must have LIMIT injected."""
    result = rewrite_query("SELECT * FROM users")
    assert result == "SELECT * FROM users LIMIT 100"


def test_preserves_existing_limit() -> None:
    """A query that already has LIMIT must not be modified."""
    result = rewrite_query("SELECT * FROM users LIMIT 5")
    assert result == "SELECT * FROM users LIMIT 5"


def test_preserves_existing_limit_case_insensitive() -> None:
    """LIMIT detection must be case-insensitive."""
    result = rewrite_query("SELECT * FROM users limit 10")
    assert "limit 10" in result.lower()
    assert result.count("LIMIT") + result.count("limit") == 1


def test_handles_trailing_semicolon() -> None:
    """Trailing semicolons must be stripped before LIMIT is injected."""
    result = rewrite_query("SELECT * FROM users;")
    assert result == "SELECT * FROM users LIMIT 100"


def test_handles_trailing_whitespace_and_semicolon() -> None:
    """Trailing whitespace + semicolons must be handled cleanly."""
    result = rewrite_query("SELECT * FROM users ;  ")
    assert result == "SELECT * FROM users LIMIT 100"


def test_respects_custom_max_rows() -> None:
    """Custom max_rows must be used in the injected LIMIT."""
    result = rewrite_query("SELECT * FROM users", max_rows=50)
    assert result == "SELECT * FROM users LIMIT 50"


def test_cte_query_gets_limit() -> None:
    """CTE queries without LIMIT must also get one injected."""
    sql = "WITH cte AS (SELECT id FROM users) SELECT * FROM cte"
    result = rewrite_query(sql)
    assert result.endswith("LIMIT 100")


def test_show_query_gets_limit() -> None:
    """SHOW queries must also get LIMIT injected."""
    result = rewrite_query("SHOW TABLES")
    assert result == "SHOW TABLES LIMIT 100"
