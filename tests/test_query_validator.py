"""Tests for the query validator — the core safety component.

Every forbidden keyword and pattern must be tested.
These tests are critical: they prove the read-only guarantee holds.
"""

import pytest

from dbsage.db.query_validator import validate_query
from dbsage.exceptions import ForbiddenQueryError

# --- Forbidden keywords ---

@pytest.mark.parametrize("keyword", [
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
])
def test_blocks_forbidden_keyword(keyword: str) -> None:
    """All mutation keywords must be blocked."""
    with pytest.raises(ForbiddenQueryError) as exc_info:
        validate_query(f"{keyword} TABLE users")
    assert exc_info.value.keyword == keyword


@pytest.mark.parametrize("keyword", [
    "drop",
    "Delete",
    "INSERT",
    "uPdAtE",
])
def test_blocks_forbidden_keyword_case_insensitive(keyword: str) -> None:
    """Keyword blocking must be case-insensitive."""
    with pytest.raises(ForbiddenQueryError):
        validate_query(f"{keyword} FROM users")


# --- Forbidden patterns ---

@pytest.mark.parametrize("pattern,query", [
    ("INTO OUTFILE", "SELECT * FROM users INTO OUTFILE '/tmp/out.csv'"),
    ("LOAD DATA", "LOAD DATA INFILE '/tmp/in.csv' INTO TABLE users"),
    ("CREATE TEMP", "CREATE TEMP TABLE tmp AS SELECT * FROM users"),
    ("CALL ", "CALL stored_proc()"),
])
def test_blocks_forbidden_pattern(pattern: str, query: str) -> None:
    """Multi-word forbidden patterns must be blocked."""
    with pytest.raises(ForbiddenQueryError) as exc_info:
        validate_query(query)
    assert exc_info.value.keyword == pattern


# --- Allowed query types ---

@pytest.mark.parametrize("sql", [
    "SELECT * FROM users",
    "SELECT id, email FROM users WHERE id = 1",
    "SHOW TABLES",
    "SHOW DATABASES",
    "DESCRIBE users",
    "EXPLAIN SELECT * FROM orders WHERE user_id = 42",
    "WITH cte AS (SELECT id FROM users) SELECT * FROM cte",
])
def test_allows_safe_queries(sql: str) -> None:
    """Safe queries must pass validation without raising."""
    validate_query(sql)  # should not raise


# --- Comment bypass prevention ---

def test_blocks_keyword_hidden_in_comment_context() -> None:
    """DROP after comment stripping must still be caught."""
    # After stripping '-- safe', the DROP keyword remains
    with pytest.raises(ForbiddenQueryError):
        validate_query("SELECT 1; -- safe\nDROP TABLE users")


def test_error_stores_query() -> None:
    """ForbiddenQueryError must store the original query."""
    sql = "DROP TABLE users"
    with pytest.raises(ForbiddenQueryError) as exc_info:
        validate_query(sql)
    assert exc_info.value.query == sql
