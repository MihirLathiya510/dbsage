"""Tests for the pipe-delimited table formatter."""

from dbsage.formatting.table_formatter import format_as_table, format_column_list


# --- format_as_table ---

def test_empty_rows_returns_no_results() -> None:
    assert format_as_table([]) == "(no results)"


def test_single_row_single_column() -> None:
    result = format_as_table([{"id": 1}])
    lines = result.split("\n")
    assert "id" in lines[0]
    assert "1" in lines[2]


def test_header_and_separator_and_data() -> None:
    rows = [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}]
    result = format_as_table(rows)
    lines = result.split("\n")
    assert len(lines) == 4  # header, separator, row1, row2
    assert "name" in lines[0]
    assert "age" in lines[0]
    assert "alice" in lines[2]
    assert "bob" in lines[3]


def test_null_values_rendered_as_NULL() -> None:
    result = format_as_table([{"col": None}])
    assert "NULL" in result


def test_long_value_truncated() -> None:
    long_val = "x" * 200
    result = format_as_table([{"col": long_val}])
    assert "..." in result
    # Cell should be at most 80 chars
    cell = result.split("\n")[2].strip()
    assert len(cell) <= 83  # 80 chars + possible padding


def test_columns_aligned_by_width() -> None:
    rows = [{"a": "short", "b": "x" * 20}]
    result = format_as_table(rows)
    header_line = result.split("\n")[0]
    # Both columns should appear in the header
    assert "a" in header_line
    assert "b" in header_line


# --- format_column_list ---

def test_empty_columns_returns_not_found() -> None:
    assert format_column_list([]) == "(no columns found)"


def test_primary_key_shown_as_PK() -> None:
    cols = [{"column_name": "id", "data_type": "int", "is_nullable": "NO",
             "column_key": "PRI", "extra": "auto_increment"}]
    result = format_column_list(cols)
    assert "PK" in result
    assert "id" in result
    assert "INT" in result


def test_nullable_column_shown_as_YES() -> None:
    cols = [{"column_name": "bio", "data_type": "text", "is_nullable": "YES",
             "column_key": "", "extra": ""}]
    result = format_column_list(cols)
    assert "YES" in result


def test_index_shown_as_IDX() -> None:
    cols = [{"column_name": "user_id", "data_type": "int", "is_nullable": "NO",
             "column_key": "MUL", "extra": ""}]
    result = format_column_list(cols)
    assert "IDX" in result
