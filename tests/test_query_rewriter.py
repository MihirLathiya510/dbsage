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


# ── MSSQL dialect ─────────────────────────────────────────────────────────────


def test_mssql_injects_top_basic() -> None:
    result = rewrite_query("SELECT * FROM users", db_type="mssql")
    assert result == "SELECT TOP 100 * FROM users"


def test_mssql_injects_top_custom_limit() -> None:
    result = rewrite_query("SELECT * FROM users", max_rows=50, db_type="mssql")
    assert result == "SELECT TOP 50 * FROM users"


def test_mssql_injects_top_after_distinct() -> None:
    result = rewrite_query(
        "SELECT DISTINCT id FROM users", max_rows=20, db_type="mssql"
    )
    assert result == "SELECT DISTINCT TOP 20 id FROM users"


def test_mssql_injects_top_after_all() -> None:
    result = rewrite_query("SELECT ALL id FROM users", max_rows=10, db_type="mssql")
    assert result == "SELECT ALL TOP 10 id FROM users"


def test_mssql_skips_injection_when_top_present() -> None:
    sql = "SELECT TOP 5 * FROM users"
    assert rewrite_query(sql, db_type="mssql") == sql


def test_mssql_strips_semicolon() -> None:
    result = rewrite_query("SELECT * FROM users;", db_type="mssql")
    assert result == "SELECT TOP 100 * FROM users"


def test_mssql_no_limit_keyword_in_output() -> None:
    result = rewrite_query("SELECT * FROM orders", db_type="mssql")
    assert "LIMIT" not in result.upper()


def test_mysql_unchanged_with_explicit_db_type() -> None:
    result = rewrite_query("SELECT * FROM users", db_type="mysql")
    assert result == "SELECT * FROM users LIMIT 100"


def test_postgresql_unchanged_with_explicit_db_type() -> None:
    result = rewrite_query("SELECT * FROM users", db_type="postgresql")
    assert result == "SELECT * FROM users LIMIT 100"
