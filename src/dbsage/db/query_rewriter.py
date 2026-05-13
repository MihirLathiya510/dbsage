"""Query rewriter — injects LIMIT/TOP if the query doesn't already have one.

Ensures the LLM can never accidentally pull unlimited rows from the database.
Dialect-aware: MySQL/PostgreSQL use LIMIT N; MSSQL uses SELECT TOP N.
"""

import re


def rewrite_query(sql: str, max_rows: int = 100, db_type: str = "mysql") -> str:
    """Inject a row limit into a query if one is not already present.

    For MySQL and PostgreSQL: appends LIMIT N.
    For MSSQL: inserts TOP N after SELECT (handles DISTINCT/ALL correctly).
    Handles trailing semicolons correctly.

    Examples (MySQL):
        "SELECT * FROM users"         -> "SELECT * FROM users LIMIT 100"
        "SELECT * FROM users LIMIT 5" -> "SELECT * FROM users LIMIT 5"  (unchanged)
        "SELECT * FROM users;"        -> "SELECT * FROM users LIMIT 100"

    Examples (MSSQL):
        "SELECT * FROM users"         -> "SELECT TOP 100 * FROM users"
        "SELECT TOP 5 * FROM users"   -> "SELECT TOP 5 * FROM users"    (unchanged)
        "SELECT DISTINCT id FROM t"   -> "SELECT DISTINCT TOP 100 id FROM t"
    """
    stripped = sql.rstrip().rstrip(";").rstrip()

    if db_type == "mssql":
        if re.search(r"\bTOP\b", stripped, re.IGNORECASE):
            return stripped
        return re.sub(
            r"(?i)^(\s*SELECT(?:\s+(?:ALL|DISTINCT))?)\s+(?!TOP\b)",
            rf"\1 TOP {max_rows} ",
            stripped,
            count=1,
        )

    # MySQL / PostgreSQL — append LIMIT
    if re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        return stripped
    return f"{stripped} LIMIT {max_rows}"
