"""Tests for the semantic layer — loader and tools."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from dbsage.semantic import semantic_loader


def _patch_schema(data: dict) -> object:
    """Patch semantic_loader._load to return given data and clear lru_cache."""
    semantic_loader._load.cache_clear()
    return patch("dbsage.semantic.semantic_loader._load", return_value=data)


# ── semantic_loader ───────────────────────────────────────────────────────────

def test_get_database_info_returns_db_block() -> None:
    schema = {"database": {"name": "testdb", "description": "A test DB"}}
    with _patch_schema(schema):
        info = semantic_loader.get_database_info()
    assert info["name"] == "testdb"


def test_get_database_info_missing_returns_empty() -> None:
    with _patch_schema({}):
        assert semantic_loader.get_database_info() == {}


def test_get_vocabulary_returns_dict() -> None:
    schema = {"vocabulary": {"deal": "Deals", "lender": "Organizations"}}
    with _patch_schema(schema):
        vocab = semantic_loader.get_vocabulary()
    assert vocab["deal"] == "Deals"
    assert vocab["lender"] == "Organizations"


def test_get_table_meta_found() -> None:
    schema = {
        "tables": {
            "Users": {
                "description": "Platform users",
                "tags": ["core"],
                "columns": {"id": "UUID"},
            }
        }
    }
    with _patch_schema(schema):
        meta = semantic_loader.get_table_meta("Users")
    assert meta is not None
    assert meta["description"] == "Platform users"
    assert meta["_table_name"] == "Users"


def test_get_table_meta_case_insensitive() -> None:
    schema = {"tables": {"Users": {"description": "Platform users"}}}
    with _patch_schema(schema):
        meta = semantic_loader.get_table_meta("users")
    assert meta is not None


def test_get_table_meta_not_found_returns_none() -> None:
    with _patch_schema({"tables": {}}):
        assert semantic_loader.get_table_meta("NonExistent") is None


def test_get_common_analytics_returns_list() -> None:
    schema = {"common_analytics": [{"name": "q1", "sql": "SELECT 1", "description": "test"}]}
    with _patch_schema(schema):
        items = semantic_loader.get_common_analytics()
    assert len(items) == 1
    assert items[0]["name"] == "q1"


def test_search_by_term_vocabulary_match() -> None:
    schema = {
        "vocabulary": {"deal": "Deals", "loan": "Deals"},
        "tables": {},
    }
    with _patch_schema(schema):
        results = semantic_loader.search_by_term("deal")
    vocab_hits = [r for r in results if r["type"] == "vocabulary"]
    assert len(vocab_hits) >= 1
    assert vocab_hits[0]["term"] == "deal"


def test_search_by_term_table_match() -> None:
    schema = {
        "vocabulary": {},
        "tables": {
            "Deals": {"description": "Loan deal applications", "tags": ["loan"], "columns": {}}
        },
    }
    with _patch_schema(schema):
        results = semantic_loader.search_by_term("loan")
    table_hits = [r for r in results if r["type"] == "table"]
    assert any(r["table"] == "Deals" for r in table_hits)


def test_search_by_term_column_match() -> None:
    schema = {
        "vocabulary": {},
        "tables": {
            "Deals": {
                "description": "Deals",
                "tags": [],
                "columns": {"organization_id": "FK to Organizations — the borrower org"},
            }
        },
    }
    with _patch_schema(schema):
        results = semantic_loader.search_by_term("borrower")
    col_hits = [r for r in results if r["type"] == "column"]
    assert len(col_hits) >= 1


def test_search_by_term_no_match_returns_empty() -> None:
    with _patch_schema({"vocabulary": {}, "tables": {}}):
        results = semantic_loader.search_by_term("xyzzy_no_match")
    assert results == []


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    semantic_loader._load.cache_clear()
    with patch("dbsage.semantic.semantic_loader._SEMANTIC_JSON", tmp_path / "missing.json"):
        result = semantic_loader._load()
    assert result == {}
    semantic_loader._load.cache_clear()


def test_load_malformed_json_returns_empty(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {{{")
    semantic_loader._load.cache_clear()
    with patch("dbsage.semantic.semantic_loader._SEMANTIC_JSON", bad):
        result = semantic_loader._load()
    assert result == {}
    semantic_loader._load.cache_clear()


# ── semantic_tools ────────────────────────────────────────────────────────────

def test_get_database_context_with_schema() -> None:
    from dbsage.tools.semantic_tools import get_database_context

    schema = {
        "database": {"name": "testdb", "description": "Test DB", "domain": "testing"},
        "vocabulary": {"deal": "Deals"},
        "common_analytics": [],
    }
    with _patch_schema(schema):
        result = get_database_context()
    assert "testdb" in result
    assert "Test DB" in result
    assert '"deal"' in result
    assert "Deals" in result


def test_get_database_context_empty_schema() -> None:
    from dbsage.tools.semantic_tools import get_database_context

    with _patch_schema({}):
        result = get_database_context()
    assert "no semantic schema" in result


def test_get_table_semantics_found() -> None:
    from dbsage.tools.semantic_tools import get_table_semantics

    schema = {
        "tables": {
            "Users": {
                "description": "Platform users",
                "tags": ["core", "auth"],
                "columns": {"id": "UUID primary key"},
                "common_queries": ["SELECT * FROM Users LIMIT 10"],
            }
        }
    }
    with _patch_schema(schema):
        result = get_table_semantics("Users")
    assert "Users" in result
    assert "Platform users" in result
    assert "core" in result
    assert "UUID primary key" in result
    assert "SELECT * FROM Users" in result


def test_get_table_semantics_not_found() -> None:
    from dbsage.tools.semantic_tools import get_table_semantics

    with _patch_schema({"tables": {}}):
        result = get_table_semantics("NonExistent")
    assert "no semantic metadata" in result


def test_search_schema_by_meaning_returns_results() -> None:
    from dbsage.tools.semantic_tools import search_schema_by_meaning

    schema = {
        "vocabulary": {"lender": "Organizations"},
        "tables": {
            "Organizations": {
                "description": "Companies including lenders and borrowers",
                "tags": ["core", "lender"],
                "columns": {},
            }
        },
    }
    with _patch_schema(schema):
        result = search_schema_by_meaning("lender")
    assert "[vocabulary]" in result
    assert "[table]" in result
    assert "Organizations" in result


def test_search_schema_by_meaning_no_results() -> None:
    from dbsage.tools.semantic_tools import search_schema_by_meaning

    with _patch_schema({"vocabulary": {}, "tables": {}}):
        result = search_schema_by_meaning("xyzzy_no_match")
    assert "no matches" in result
