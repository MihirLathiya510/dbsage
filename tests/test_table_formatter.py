"""Tests for the table formatter — both legacy and new beautiful output functions."""

from dbsage.formatting.table_formatter import (
    format_as_table,
    format_column_list,
    format_column_list_v2,
    format_column_values,
    format_error_result,
    format_json_samples,
    format_query_result,
    format_relationships,
    format_results_table,
    format_section,
    format_simple_list,
    format_vertical_rows,
    section_header,
)

# ── Legacy: format_as_table ───────────────────────────────────────────────────


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


def test_null_values_rendered_as_null() -> None:
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
    assert "a" in header_line
    assert "b" in header_line


# ── Legacy: format_column_list ────────────────────────────────────────────────


def test_empty_columns_returns_not_found() -> None:
    assert format_column_list([]) == "(no columns found)"


def test_primary_key_shown_as_pk() -> None:
    cols = [
        {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "PRI",
            "extra": "auto_increment",
        }
    ]
    result = format_column_list(cols)
    assert "PK" in result
    assert "id" in result
    assert "INT" in result


def test_nullable_column_shown_as_yes() -> None:
    cols = [
        {
            "column_name": "bio",
            "data_type": "text",
            "is_nullable": "YES",
            "column_key": "",
            "extra": "",
        }
    ]
    result = format_column_list(cols)
    assert "YES" in result


def test_index_shown_as_idx() -> None:
    cols = [
        {
            "column_name": "user_id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "MUL",
            "extra": "",
        }
    ]
    result = format_column_list(cols)
    assert "IDX" in result


# ── New: section_header ───────────────────────────────────────────────────────


def test_section_header_fills_to_120_chars() -> None:
    result = section_header("list_tables")
    assert len(result) == 120


def test_section_header_contains_tool_name() -> None:
    result = section_header("list_tables")
    assert "list_tables" in result


def test_section_header_with_subtitle() -> None:
    result = section_header("describe_table", "users")
    assert "describe_table: users" in result
    assert len(result) == 120


def test_section_header_starts_with_dashes() -> None:
    result = section_header("foo")
    assert result.startswith("── foo")


# ── New: format_results_table ─────────────────────────────────────────────────


def test_format_results_table_empty_returns_empty_string() -> None:
    assert format_results_table([]) == ""


def test_format_results_table_has_heavy_header_border() -> None:
    rows = [{"id": 1, "name": "alice"}]
    result = format_results_table(rows)
    assert "┏" in result
    assert "┃" in result


def test_format_results_table_has_light_body_border() -> None:
    rows = [{"id": 1, "name": "alice"}]
    result = format_results_table(rows)
    assert "│" in result
    assert "└" in result


def test_format_results_table_header_correct() -> None:
    rows = [{"id": 1, "email": "a@b.com"}]
    result = format_results_table(rows)
    assert "id" in result
    assert "email" in result


def test_format_results_table_data_correct() -> None:
    rows = [{"id": 1, "status": "active"}]
    result = format_results_table(rows)
    assert "active" in result
    assert "1" in result


def test_format_results_table_null_rendered() -> None:
    rows = [{"col": None}]
    result = format_results_table(rows)
    assert "NULL" in result


# ── New: format_vertical_rows ─────────────────────────────────────────────────


def test_format_vertical_rows_shows_row_header() -> None:
    rows = [{"id": 1, "col": "val"}]
    result = format_vertical_rows(rows)
    assert "Row 1" in result


def test_format_vertical_rows_shows_keys_and_values() -> None:
    rows = [{"id": 42, "email": "test@example.com"}]
    result = format_vertical_rows(rows)
    assert "id" in result
    assert "42" in result
    assert "email" in result
    assert "test@example.com" in result


def test_format_vertical_rows_multiple_rows() -> None:
    rows = [{"id": 1}, {"id": 2}]
    result = format_vertical_rows(rows)
    assert "Row 1" in result
    assert "Row 2" in result


def test_format_vertical_rows_empty_returns_empty() -> None:
    assert format_vertical_rows([]) == ""


# ── New: format_query_result ──────────────────────────────────────────────────


def test_format_query_result_shows_sql_echo() -> None:
    rows = [{"id": 1}]
    result = format_query_result("SELECT id FROM users LIMIT 10", rows, 5.0)
    assert "SELECT id FROM users LIMIT 10" in result


def test_format_query_result_shows_row_count() -> None:
    rows = [{"id": 1}, {"id": 2}]
    result = format_query_result("SELECT id FROM t LIMIT 10", rows, 3.0)
    assert "2 rows" in result


def test_format_query_result_empty_shows_zero_rows() -> None:
    result = format_query_result("SELECT id FROM t LIMIT 10", [], 2.0)
    assert "0 rows" in result
    assert "┏" not in result  # no table for empty result


def test_format_query_result_shows_timing() -> None:
    result = format_query_result("SELECT 1", [{"id": 1}], 47.0)
    assert "47ms" in result


def test_format_query_result_sub_millisecond_timing() -> None:
    result = format_query_result("SELECT 1", [{"id": 1}], 0.4)
    assert "<1ms" in result


def test_format_query_result_limit_injected_shows_note() -> None:
    result = format_query_result(
        "SELECT * FROM t LIMIT 100", [{"id": 1}], 5.0, limit_injected=True
    )
    assert "auto-injected" in result


def test_format_query_result_no_limit_note_when_not_injected() -> None:
    result = format_query_result(
        "SELECT * FROM t LIMIT 5", [{"id": 1}], 5.0, limit_injected=False
    )
    assert "auto-injected" not in result


def test_format_query_result_wide_table_triggers_vertical_mode() -> None:
    # 10 columns with 15-char names → exceeds 120-char terminal width
    row = {f"column_{i:02d}": f"value_{i:010d}" for i in range(10)}
    result = format_query_result("SELECT *", [row], 5.0)
    assert "Row 1" in result
    assert "vertical mode" in result


def test_format_query_result_sql_indented() -> None:
    result = format_query_result("SELECT id\nFROM users", [{"id": 1}], 5.0)
    assert "  SELECT id" in result
    assert "  FROM users" in result


# ── New: format_error_result ──────────────────────────────────────────────────


def test_format_error_result_shows_sql() -> None:
    result = format_error_result("DROP TABLE users", "blocked")
    assert "DROP TABLE users" in result


def test_format_error_result_shows_x_marker() -> None:
    result = format_error_result("DROP TABLE users", "blocked")
    assert "✗" in result


def test_format_error_result_shows_message() -> None:
    result = format_error_result(
        "DROP TABLE t", "Query blocked: forbidden keyword 'DROP'"
    )
    assert "Query blocked" in result
    assert "DROP" in result


def test_format_error_result_shows_hint() -> None:
    result = format_error_result("DROP TABLE t", "blocked", "Only SELECT is allowed.")
    assert "Only SELECT is allowed." in result


def test_format_error_result_no_hint_when_empty() -> None:
    result = format_error_result("DROP TABLE t", "blocked")
    lines = [ln for ln in result.splitlines() if ln.strip()]
    assert len(lines) == 2  # SQL line + error line


# ── New: format_column_list_v2 ────────────────────────────────────────────────


def test_format_column_list_v2_empty_returns_message() -> None:
    assert format_column_list_v2([]) == "(no columns found)"


def test_format_column_list_v2_shows_column_count_footer() -> None:
    cols = [
        {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "PRI",
            "extra": "auto_increment",
        },
        {
            "column_name": "email",
            "data_type": "varchar",
            "is_nullable": "YES",
            "column_key": "",
            "extra": "",
        },
    ]
    result = format_column_list_v2(cols)
    assert "2 columns" in result


def test_format_column_list_v2_pk_in_footer() -> None:
    cols = [
        {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "PRI",
            "extra": "auto_increment",
        }
    ]
    result = format_column_list_v2(cols)
    assert "PK on id" in result


def test_format_column_list_v2_nullable_count_in_footer() -> None:
    cols = [
        {
            "column_name": "a",
            "data_type": "int",
            "is_nullable": "NO",
            "column_key": "",
            "extra": "",
        },
        {
            "column_name": "b",
            "data_type": "text",
            "is_nullable": "YES",
            "column_key": "",
            "extra": "",
        },
    ]
    result = format_column_list_v2(cols)
    assert "1 nullable" in result


def test_format_column_list_v2_fk_annotation_uses_fk_arrow() -> None:
    cols = [
        {
            "column_name": "org_id",
            "data_type": "bigint",
            "is_nullable": "NO",
            "column_key": "MUL",
            "extra": "",
        }
    ]
    fk_map = {"org_id": "organizations.id"}
    result = format_column_list_v2(cols, fk_map=fk_map)
    assert "FK →" in result
    assert "organizations.id" in result


def test_format_column_list_v2_fk_count_in_footer() -> None:
    cols = [
        {
            "column_name": "org_id",
            "data_type": "bigint",
            "is_nullable": "NO",
            "column_key": "MUL",
            "extra": "",
        }
    ]
    fk_map = {"org_id": "organizations.id"}
    result = format_column_list_v2(cols, fk_map=fk_map)
    assert "1 FK" in result


# ── New: format_simple_list ───────────────────────────────────────────────────


def test_format_simple_list_indents_items() -> None:
    result = format_simple_list(["users", "orders"])
    assert "  users" in result
    assert "  orders" in result


def test_format_simple_list_includes_footer() -> None:
    result = format_simple_list(["users"], footer="1 table")
    assert "1 table" in result


def test_format_simple_list_no_footer_when_empty_string() -> None:
    result = format_simple_list(["users"])
    assert "users" in result
    # No extra blank line + footer line
    lines = result.splitlines()
    assert len(lines) == 1


# ── New: format_section ───────────────────────────────────────────────────────


def test_format_section_has_title_and_underline() -> None:
    result = format_section("Tables (3)", "  users\n  orders")
    lines = result.splitlines()
    assert lines[0] == "Tables (3)"
    assert set(lines[1]) == {"─"}  # underline is all dashes


def test_format_section_underline_same_width_as_title() -> None:
    title = "Relationships (5)"
    result = format_section(title, "body")
    lines = result.splitlines()
    assert len(lines[1]) == len(title)


def test_format_section_body_present() -> None:
    result = format_section("Title", "my body content")
    assert "my body content" in result


# ── New: format_relationships ─────────────────────────────────────────────────


def test_format_relationships_shows_from_and_to() -> None:
    fks = [
        {
            "from_table": "orders",
            "from_column": "user_id",
            "to_table": "users",
            "to_column": "id",
        }
    ]
    result = format_relationships(fks)
    assert "orders.user_id" in result
    assert "users.id" in result


def test_format_relationships_aligned_arrows() -> None:
    fks = [
        {
            "from_table": "orders",
            "from_column": "user_id",
            "to_table": "users",
            "to_column": "id",
        },
        {
            "from_table": "order_items",
            "from_column": "order_id",
            "to_table": "orders",
            "to_column": "id",
        },
    ]
    result = format_relationships(fks)
    lines = result.splitlines()
    arrow_positions = [line.index("→") for line in lines if "→" in line]
    # All arrows must be at the same column position
    assert len(set(arrow_positions)) == 1


def test_format_relationships_empty_returns_empty() -> None:
    assert format_relationships([]) == ""


# ── New: format_column_values ─────────────────────────────────────────────────


def test_format_column_values_shows_value_and_count() -> None:
    rows = [{"value": "active", "count": 100}, {"value": "inactive", "count": 20}]
    result = format_column_values(rows)
    assert "active" in result
    assert "100" in result
    assert "inactive" in result


def test_format_column_values_right_aligns_counts() -> None:
    rows = [{"value": "a", "count": 1000}, {"value": "b", "count": 5}]
    result = format_column_values(rows)
    lines = [ln for ln in result.splitlines() if ln.strip()]
    # Closing ")" should be at same position in every line (right-aligned)
    close_positions = [ln.rfind(")") for ln in lines]
    assert len(set(close_positions)) == 1


def test_format_column_values_formats_count_with_commas() -> None:
    rows = [{"value": "pending", "count": 1204}]
    result = format_column_values(rows)
    assert "1,204" in result


def test_format_column_values_empty_returns_empty() -> None:
    assert format_column_values([]) == ""


# ── New: format_json_samples ──────────────────────────────────────────────────


def test_format_json_samples_shows_sample_headers() -> None:
    result = format_json_samples(['{"a": 1}', '{"b": 2}'])
    assert "Sample 1" in result
    assert "Sample 2" in result


def test_format_json_samples_shows_json_content() -> None:
    result = format_json_samples(['{"key": "value"}'])
    assert "key" in result
    assert "value" in result


def test_format_json_samples_shows_count_footer() -> None:
    result = format_json_samples(['{"a": 1}', '{"b": 2}'])
    assert "2 samples" in result


def test_format_json_samples_single_sample_singular() -> None:
    result = format_json_samples(['{"a": 1}'])
    assert "1 sample" in result
    assert "samples" not in result


def test_format_json_samples_has_section_dividers() -> None:
    result = format_json_samples(['{"a": 1}', '{"b": 2}'])
    assert "────" in result


def test_format_json_samples_empty_returns_empty() -> None:
    assert format_json_samples([]) == ""


# ── _truncate JSON detection ──────────────────────────────────────────────────


def test_truncate_json_object_not_truncated() -> None:
    from dbsage.formatting.table_formatter import _truncate

    long_json = '{"key": "' + "v" * 200 + '"}'
    assert _truncate(long_json) == long_json


def test_truncate_json_array_not_truncated() -> None:
    from dbsage.formatting.table_formatter import _truncate

    long_json = "[" + ", ".join(str(i) for i in range(100)) + "]"
    assert _truncate(long_json) == long_json


def test_truncate_json_with_leading_whitespace_not_truncated() -> None:
    from dbsage.formatting.table_formatter import _truncate

    long_json = '  {"key": "' + "v" * 200 + '"}'
    assert _truncate(long_json) == long_json


def test_truncate_normal_long_string_still_capped() -> None:
    from dbsage.formatting.table_formatter import _truncate

    long_str = "x" * 200
    result = _truncate(long_str)
    assert result.endswith("...")
    assert len(result) < 90  # well under 200


def test_truncate_null_value() -> None:
    from dbsage.formatting.table_formatter import _truncate

    assert _truncate(None) == "NULL"


def test_format_results_table_json_column_full_value_present() -> None:
    long_json = '{"address": "' + "a" * 200 + '"}'
    rows = [{"id": 1, "data": long_json}]
    result = format_results_table(rows)
    # Full JSON must appear somewhere in the output (not cut off mid-string)
    assert long_json in result
