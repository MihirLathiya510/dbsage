"""Query rewriter — injects LIMIT if the query doesn't already have one.

Ensures the LLM can never accidentally pull unlimited rows from the database.
"""

import re


def rewrite_query(sql: str, max_rows: int = 100) -> str:
    """Inject LIMIT into a query if it does not already have one.

    Handles trailing semicolons correctly.

    Examples:
        "SELECT * FROM users"         -> "SELECT * FROM users LIMIT 100"
        "SELECT * FROM users LIMIT 5" -> "SELECT * FROM users LIMIT 5"  (unchanged)
        "SELECT * FROM users;"        -> "SELECT * FROM users LIMIT 100"
    """
    stripped = sql.rstrip().rstrip(";").rstrip()

    # Check if LIMIT already present (case-insensitive, word boundary)
    if re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        return stripped

    return f"{stripped} LIMIT {max_rows}"
