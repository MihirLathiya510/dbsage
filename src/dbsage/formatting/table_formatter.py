"""Result formatter — converts query results to LLM-friendly pipe-delimited tables.

Avoids raw Python tuple output like [(1, 'john@test.com')].
Produces deterministic, structured output the LLM can parse easily.
"""

from typing import Any

_MAX_CELL_WIDTH = 80


def _truncate(value: Any) -> str:
    """Convert a value to string and truncate if too long."""
    s = str(value) if value is not None else "NULL"
    if len(s) > _MAX_CELL_WIDTH:
        return s[:_MAX_CELL_WIDTH - 3] + "..."
    return s


def format_as_table(rows: list[dict[str, Any]]) -> str:
    """Format a list of row dicts as a pipe-delimited table.

    Example output:
        id | email          | created_at
        ---+----------------+-----------
        1  | john@test.com  | 2024-01-02

    Returns "(no results)" for empty result sets.
    """
    if not rows:
        return "(no results)"

    headers = list(rows[0].keys())
    cells = [[_truncate(row.get(h)) for h in headers] for row in rows]

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row_cells in cells:
        for i, cell in enumerate(row_cells):
            widths[i] = max(widths[i], len(cell))

    def _format_row(values: list[str]) -> str:
        return " | ".join(v.ljust(widths[i]) for i, v in enumerate(values))

    separator = "-+-".join("-" * w for w in widths)

    lines = [
        _format_row(headers),
        separator,
        *[_format_row(row_cells) for row_cells in cells],
    ]
    return "\n".join(lines)


def format_column_list(columns: list[dict[str, Any]]) -> str:
    """Format describe_table output as a readable column list.

    Example output:
        id          INT      PK   NOT NULL
        user_id     INT      MUL  NOT NULL
        email       VARCHAR       NOT NULL
        created_at  DATETIME      YES
    """
    if not columns:
        return "(no columns found)"

    lines = []
    for col in columns:
        name = str(col.get("column_name", ""))
        dtype = str(col.get("data_type", "")).upper()
        key = str(col.get("column_key", ""))
        nullable = "YES" if col.get("is_nullable") == "YES" else "NOT NULL"
        extra = str(col.get("extra", ""))

        key_label = {"PRI": "PK", "UNI": "UQ", "MUL": "IDX"}.get(key, "   ")
        extra_label = f"  {extra}" if extra else ""
        lines.append(f"{name:<30} {dtype:<15} {key_label}  {nullable}{extra_label}")

    return "\n".join(lines)
