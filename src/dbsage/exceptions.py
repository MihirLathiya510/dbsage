"""Domain exception hierarchy for dbsage."""


class DBSageError(Exception):
    """Base exception for all dbsage errors."""


class ForbiddenQueryError(DBSageError):
    """Query contains a disallowed SQL operation."""

    def __init__(self, keyword: str, query: str) -> None:
        self.keyword = keyword
        self.query = query
        super().__init__(f"Forbidden keyword '{keyword}' detected in query")


class QueryTimeoutError(DBSageError):
    """Query exceeded the maximum execution time."""


class TableBlacklistedError(DBSageError):
    """Attempted to access a blacklisted table."""

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        super().__init__(f"Table '{table_name}' is blacklisted and cannot be accessed")


class QueryValidationError(DBSageError):
    """Query failed structural validation."""


class ConnectionPoolError(DBSageError):
    """Database connection pool error."""
