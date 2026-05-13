"""Result formatter — converts query results to beautiful, readable plain-text output.

Every MCP tool response follows a consistent visual structure:
  1. section_header  — ── tool_name: subtitle ──────────────────────────────
  2. body            — table / column list / list / JSON samples
  3. footer          — row count · timing · notes

No ANSI color codes. Unicode box-drawing characters only (safe in all modern terminals).
Uses wcwidth for accurate display-width of CJK/emoji characters.
"""

from typing import Any

from wcwidth import wcswidth

# ── Constants ─────────────────────────────────────────────────────────────────

_MAX_CELL_WIDTH: int = 80  # max characters in a single table cell
_TERM_WIDTH: int = 120  # terminal width: vertical-mode trigger + section fill

# Heavy-head box: bold header row, light body rows
_TL = "┏"  # top-left
_TM = "┳"  # top-mid (column separator, top)
_TR = "┓"  # top-right
_H = "━"  # heavy horizontal (header row bars)
_HL = "┡"  # left junction: heavy → light (after header)
_HM = "╇"  # mid junction: heavy → light
_HR = "┩"  # right junction: heavy → light
_VH = "┃"  # heavy vertical (header cells)
_VL = "│"  # light vertical (body cells)
_h = "─"  # light horizontal (body rows, dividers)
_BL = "└"  # bottom-left
_BM = "┴"  # bottom-mid
_BR = "┘"  # bottom-right

# Vertical-mode box: thin lines throughout
_VB_TL = "┌"
_VB_TR = "┐"
_VB_BL = "└"
_VB_BR = "┘"
_VB_H = "─"
_VB_V = "│"
_VB_LM = "├"
_VB_RM = "┤"
_VB_TM = "┬"
_VB_BM = "┴"


# ── Internal helpers ──────────────────────────────────────────────────────────


def _display_width(s: str) -> int:
    """Terminal display width of s — handles CJK/emoji wide characters via wcwidth.

    Falls back to len(s) if wcwidth cannot determine width (returns -1).
    """
    w = wcswidth(s)
    return len(s) if w < 0 else w


def _truncate(value: Any) -> str:  # noqa: ANN401
    """Convert value to string, sanitize newlines, and truncate to _MAX_CELL_WIDTH.

    JSON objects/arrays (values whose first non-whitespace char is { or [) are
    returned in full — they push wide columns into vertical mode naturally, and
    truncating mid-JSON produces unreadable output.
    """
    s = "NULL" if value is None else str(value)
    s = s.replace("\n", " ").replace("\r", " ")
    stripped = s.lstrip()
    if stripped and stripped[0] in ("{", "["):
        return s
    if _display_width(s) > _MAX_CELL_WIDTH:
        # Truncate by rune count, not byte count
        result = ""
        width = 0
        for ch in s:
            cw = _display_width(ch)
            if width + cw > _MAX_CELL_WIDTH - 3:
                break
            result += ch
            width += cw
        return result + "..."
    return s


def _pad(value: str, width: int, align: str = "left") -> str:
    """Pad value to display-width, accounting for wide characters."""
    pad = max(0, width - _display_width(value))
    return (" " * pad + value) if align == "right" else (value + " " * pad)


def _col_widths(headers: list[str], cells: list[list[str]]) -> list[int]:
    """Compute the required display-width of each column."""
    widths = [_display_width(h) for h in headers]
    for row_cells in cells:
        for i, cell in enumerate(row_cells):
            widths[i] = max(widths[i], _display_width(cell))
    return widths


def _would_overflow(widths: list[int]) -> bool:
    """Return True if a horizontal table would exceed _TERM_WIDTH chars.

    Formula: outer borders (2) + per-column " cell " (width+2) + separators (1 each).
    Total = 2 + sum(w + 3) for each column.
    """
    return (2 + sum(w + 3 for w in widths)) > _TERM_WIDTH


def _is_numeric_col(cells: list[str]) -> bool:
    """Heuristic: True if all non-NULL, non-empty cells look numeric."""
    candidates = [c for c in cells if c not in ("NULL", "")]
    if not candidates:
        return False

    def _looks_numeric(s: str) -> bool:
        return s.lstrip("-+").replace(".", "", 1).replace(",", "").isdigit()

    return all(_looks_numeric(c) for c in candidates)


def _render_box_table(
    headers: list[str],
    cells: list[list[str]],
    widths: list[int],
) -> str:
    """Render a heavy-head Unicode box table.

    Header row uses heavy borders (┏━┳━┓ / ┃), body uses light borders (│ / ─).

    Example:
        ┏━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
        ┃ id ┃ email         ┃ created_at ┃
        ┡━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
        │  1 │ john@test.com │ 2024-01-02 │
        │  2 │ jane@test.com │ 2024-01-03 │
        └────┴───────────────┴────────────┘
    """
    # Determine alignment per column (numeric → right-align)
    col_align = [
        "right" if _is_numeric_col([row[i] for row in cells]) else "left"
        for i in range(len(headers))
    ]

    def _top() -> str:
        return _TL + _TM.join(_H * (w + 2) for w in widths) + _TR

    def _header_row() -> str:
        parts = _VH.join(
            f" {_pad(h, w)} " for h, w in zip(headers, widths, strict=True)
        )
        return _VH + parts + _VH

    def _mid() -> str:
        return _HL + _HM.join(_H * (w + 2) for w in widths) + _HR

    def _data_row(row: list[str]) -> str:
        cells_str = _VL.join(
            f" {_pad(cell, w, col_align[i])} "
            for i, (cell, w) in enumerate(zip(row, widths, strict=True))
        )
        return _VL + cells_str + _VL

    def _bottom() -> str:
        return _BL + _BM.join(_h * (w + 2) for w in widths) + _BR

    lines = [_top(), _header_row(), _mid()]
    lines.extend(_data_row(row) for row in cells)
    lines.append(_bottom())
    return "\n".join(lines)


# ── Public: section header ────────────────────────────────────────────────────


def section_header(tool_name: str, subtitle: str = "") -> str:
    """Return a horizontal rule with the tool name (and optional subtitle) embedded.

    Fills to _TERM_WIDTH characters with ─ dashes.

    Examples:
        section_header("list_tables")
        → "── list_tables ─────────────────────────────────────────────────────────"

        section_header("describe_table", "users")
        → "── describe_table: users ────────────────────────────────────────────────"
    """
    label = f"── {tool_name}"
    if subtitle:
        label += f": {subtitle}"
    label += " "
    fill = max(0, _TERM_WIDTH - _display_width(label))
    return label + (_h * fill)


# ── Public: table formatters ──────────────────────────────────────────────────


def format_results_table(rows: list[dict[str, Any]]) -> str:  # noqa: ANN401
    """Render rows as a heavy-head Unicode box table.

    Returns empty string for empty rows — callers handle the "0 rows" footer.

    Example:
        ┏━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
        ┃ id ┃ email         ┃ created_at ┃
        ┡━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
        │  1 │ john@test.com │ 2024-01-02 │
        └────┴───────────────┴────────────┘
    """
    if not rows:
        return ""

    headers = list(rows[0].keys())
    if not headers:
        return ""

    cells = [[_truncate(row.get(h)) for h in headers] for row in rows]
    widths = _col_widths(headers, cells)
    return _render_box_table(headers, cells, widths)


def format_vertical_rows(rows: list[dict[str, Any]]) -> str:  # noqa: ANN401
    """Render rows in vertical/expanded key-value format.

    Used when the table would be wider than _TERM_WIDTH.
    Each row gets its own titled box.

    Example:
        ┌─ Row 1 ──────────────────────────────────────────────────────────────┐
        │ id          │ 1                                                       │
        │ event_type  │ page_view                                               │
        └─────────────────────────────────────────────────────────────────────┘
    """
    if not rows:
        return ""

    headers = list(rows[0].keys())
    key_w = max((_display_width(h) for h in headers), default=8)
    box_w = min(_TERM_WIDTH, 80)  # inner content width
    val_w = box_w - key_w - 5  # " key │ val "

    def _row_block(row: dict[str, Any], n: int) -> str:  # noqa: ANN401
        title = f" Row {n} "
        dash_r = box_w - _display_width(title)
        top = _VB_TL + _VB_H + title + (_VB_H * max(0, dash_r)) + _VB_TR
        bottom = _VB_BL + (_VB_H * (box_w + 2)) + _VB_BR

        body_lines = [top]
        for h in headers:
            key_str = _pad(h, key_w)
            val_str = _pad(_truncate(row.get(h)), val_w)
            body_lines.append(f"{_VB_V} {key_str} {_VB_V} {val_str} {_VB_V}")
        body_lines.append(bottom)
        return "\n".join(body_lines)

    blocks = [_row_block(row, i + 1) for i, row in enumerate(rows)]
    return "\n".join(blocks)


def format_query_result(
    sql: str,
    rows: list[dict[str, Any]],  # noqa: ANN401
    elapsed_ms: float,
    limit_injected: bool = False,
) -> str:
    """Full formatted query result: SQL echo + table/vertical + footer.

    Does NOT include section_header — callers prepend that.

    Args:
        sql:             The rewritten SQL that was actually executed.
        rows:            Result rows as list of dicts.
        elapsed_ms:      Wall-clock execution time in milliseconds.
        limit_injected:  True if a LIMIT was added by the query rewriter.

    Structure:
        {indented sql}

        {table body}

        {N rows · Xms · notes}
    """
    # SQL echo — indent each line 2 spaces
    sql_lines = [f"  {line}" for line in sql.strip().splitlines()]
    sql_block = "\n".join(sql_lines)

    # Timing
    time_str = "<1ms" if elapsed_ms < 1 else f"{elapsed_ms:.0f}ms"

    if not rows:
        footer = f"  0 rows · {time_str}"
        return f"{sql_block}\n\n{footer}"

    # Table or vertical mode
    headers = list(rows[0].keys())
    cells = [[_truncate(row.get(h)) for h in headers] for row in rows]
    widths = _col_widths(headers, cells)
    vertical = _would_overflow(widths)

    if vertical:
        table_body = format_vertical_rows(rows)
    else:
        table_body = _render_box_table(headers, cells, widths)

    # Footer
    n = len(rows)
    row_word = "row" if n == 1 else "rows"
    footer_parts = [f"  {n} {row_word} · {time_str}"]
    if limit_injected:
        footer_parts.append("LIMIT auto-injected")
    if vertical:
        footer_parts.append("(vertical mode — result too wide for table)")
    footer = " · ".join(footer_parts)

    return f"{sql_block}\n\n{table_body}\n\n{footer}"


def format_error_result(sql: str, message: str, hint: str = "") -> str:
    """Format a blocked/error query result.

    Example:
          DROP TABLE users

          ✗ Query blocked: forbidden keyword 'DROP'
          Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH are allowed.
    """
    sql_lines = [f"  {line}" for line in sql.strip().splitlines()]
    sql_block = "\n".join(sql_lines)
    body = f"\n  ✗ {message}"
    if hint:
        body += f"\n  {hint}"
    return f"{sql_block}\n{body}"


# ── Public: schema / column formatters ───────────────────────────────────────


def format_column_list_v2(
    columns: list[dict[str, Any]],  # noqa: ANN401
    fk_map: dict[str, str] | None = None,
    table_name: str = "",
) -> str:
    """Column list with FK annotations and a summary footer.

    Uses 'FK →' (not 'IDX →') for FK-annotated columns.
    Appends: "  N columns · PK on col · M FKs · K nullable"

    Example:
        id                             INT             PK   NOT NULL  auto_increment
        organization_id                BIGINT          FK → organizations.id  NOT NULL
        email                          VARCHAR(255)         NOT NULL
        created_at                     DATETIME             nullable

        4 columns · PK on id · 1 FK · 1 nullable
    """
    if not columns:
        return "(no columns found)"

    lines: list[str] = []
    pk_col: str | None = None
    nullable_count = 0
    fk_count = len(fk_map) if fk_map else 0

    for col in columns:
        name = str(col.get("column_name", ""))
        dtype = str(col.get("data_type", "")).upper()
        key = str(col.get("column_key", ""))
        nullable = col.get("is_nullable") == "YES"
        extra = str(col.get("extra", ""))

        if nullable:
            nullable_count += 1

        if key == "PRI" and pk_col is None:
            pk_col = name

        # Key label: FK annotation takes priority over plain key type
        if fk_map and name in fk_map:
            key_label = f"FK → {fk_map[name]}"
        else:
            key_label = {"PRI": "PK", "UNI": "UQ", "MUL": "IDX"}.get(key, "   ")

        null_label = "nullable" if nullable else "NOT NULL"
        extra_label = f"  {extra}" if extra else ""
        line = f"  {name:<30} {dtype:<15} {key_label:<5}  {null_label}{extra_label}"
        lines.append(line)

    # Footer summary
    parts: list[str] = [f"{len(columns)} column{'s' if len(columns) != 1 else ''}"]
    if pk_col:
        parts.append(f"PK on {pk_col}")
    if fk_count:
        parts.append(f"{fk_count} FK{'s' if fk_count != 1 else ''}")
    if nullable_count:
        parts.append(f"{nullable_count} nullable")

    lines.append("")
    lines.append(f"  {' · '.join(parts)}")
    return "\n".join(lines)


# ── Public: list / section formatters ────────────────────────────────────────


def format_simple_list(items: list[str], footer: str = "") -> str:
    """Format an indented list with optional footer.

    Example:
          users
          orders
          products

          3 tables
    """
    lines = [f"  {item}" for item in items]
    if footer:
        lines.append("")
        lines.append(f"  {footer}")
    return "\n".join(lines)


def format_section(title: str, body: str) -> str:
    """Render a titled section with a light underline.

    Example:
        Tables (12)
        ───────────
        {body}
    """
    underline = _h * _display_width(title)
    return f"{title}\n{underline}\n{body}"


def format_relationships(fks: list[dict[str, Any]]) -> str:  # noqa: ANN401
    """Format FK relationships with aligned arrows.

    Computes max width of 'from_table.from_column' across all FKs,
    then right-pads each left side so arrows align perfectly.

    Example:
        orders.user_id        →  users.id
        order_items.order_id  →  orders.id
    """
    if not fks:
        return ""

    left_parts = [f"{fk['from_table']}.{fk['from_column']}" for fk in fks]
    max_left = max(_display_width(p) for p in left_parts)

    lines = [
        f"  {_pad(left, max_left)}  →  {fk['to_table']}.{fk['to_column']}"
        for left, fk in zip(left_parts, fks, strict=True)
    ]
    return "\n".join(lines)


def format_column_values(rows: list[dict[str, Any]]) -> str:  # noqa: ANN401
    """Format sample_column_values output with right-aligned counts.

    Expects rows with 'value' and 'count' keys.

    Example:
        completed    (1,204 rows)
        pending        (340 rows)
        cancelled       (87 rows)
    """
    if not rows:
        return ""

    count_strs = [f"({row['count']:,} rows)" for row in rows]
    max_count_w = max(_display_width(c) for c in count_strs)
    max_val_w = max(_display_width(str(row["value"])) for row in rows)

    lines = [
        f"  {_pad(str(row['value']), max_val_w)}  {_pad(cs, max_count_w, 'right')}"
        for row, cs in zip(rows, count_strs, strict=True)
    ]
    return "\n".join(lines)


def format_json_samples(samples_text: list[str]) -> str:
    """Format inspect_json_column output with titled sections and a count footer.

    Args:
        samples_text: Pre-formatted JSON strings, one per sample.

    Example:
        Sample 1
        ────────
        {
          "device": "mobile"
        }

        Sample 2
        ────────
        ...

        2 samples
    """
    if not samples_text:
        return ""

    blocks: list[str] = []
    for i, json_str in enumerate(samples_text, 1):
        label = f"Sample {i}"
        underline = _h * _display_width(label)
        # Indent JSON body 2 spaces
        indented = "\n".join(f"  {line}" for line in json_str.splitlines())
        blocks.append(f"  {label}\n  {underline}\n{indented}")

    n = len(samples_text)
    footer = f"\n  {n} sample{'s' if n != 1 else ''}"
    return "\n\n".join(blocks) + footer


# ── Legacy functions (kept for backward compatibility) ────────────────────────


def format_as_table(rows: list[dict[str, Any]]) -> str:  # noqa: ANN401
    """Format rows as a pipe-delimited table.

    Legacy function — use format_results_table for new code.

    Example:
        id | email          | created_at
        ---+----------------+-----------
        1  | john@test.com  | 2024-01-02
    """
    if not rows:
        return "(no results)"

    headers = list(rows[0].keys())
    cells = [[_truncate(row.get(h)) for h in headers] for row in rows]

    # Calculate column widths using legacy len() for backward compat
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


def format_column_list(
    columns: list[dict[str, Any]],  # noqa: ANN401
    fk_map: dict[str, str] | None = None,
) -> str:
    """Format describe_table output as a readable column list (legacy).

    Example:
        id                             INT             PK   NOT NULL  auto_increment
        organization_id                BIGINT          IDX → Organizations.id  NOT NULL
        email                          VARCHAR              NOT NULL
        created_at                     DATETIME             YES
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
        if fk_map and name in fk_map:
            key_label = f"IDX → {fk_map[name]}"
        extra_label = f"  {extra}" if extra else ""
        lines.append(f"{name:<30} {dtype:<15} {key_label}  {nullable}{extra_label}")

    return "\n".join(lines)
