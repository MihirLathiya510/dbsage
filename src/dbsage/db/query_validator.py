"""Query validator — the core safety component of dbsage.

Every SQL query must pass through validate_query() before execution.
Any forbidden keyword or pattern raises ForbiddenQueryError immediately.
"""

import re

from dbsage.exceptions import ForbiddenQueryError

# SQL keywords that must never be executed
FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
)

# Multi-word patterns that must never appear
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "INTO OUTFILE",
    "LOAD DATA",
    "CREATE TEMP",
    "CALL ",
)


def _strip_comments(sql: str) -> str:
    """Remove SQL comments to prevent bypass via comment injection."""
    # Remove -- line comments
    sql = re.sub(r"--[^\n]*", " ", sql)
    # Remove /* block comments */
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def validate_query(sql: str) -> None:
    """Validate that a SQL query is safe for read-only execution.

    Raises ForbiddenQueryError if any forbidden keyword or pattern is found.
    Allows: SELECT, SHOW, DESCRIBE, EXPLAIN, WITH (CTEs).
    """
    clean = _strip_comments(sql).upper()

    # Check forbidden multi-word patterns first (more specific)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in clean:
            raise ForbiddenQueryError(keyword=pattern, query=sql)

    # Check forbidden standalone keywords using word boundaries
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", clean):
            raise ForbiddenQueryError(keyword=keyword, query=sql)
