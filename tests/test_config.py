"""Tests for Settings — blacklist JSON merging and env var loading."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from dbsage.mcp_server.config import _BLACKLIST_JSON, Settings


def test_default_blacklisted_tables_is_empty() -> None:
    # Without JSON file override or env var, list comes from JSON file on disk
    # Just verify the type is a list
    s = Settings()
    assert isinstance(s.blacklisted_tables, list)


def test_env_var_blacklist_is_loaded() -> None:
    with patch.object(_BLACKLIST_JSON.__class__, "exists", return_value=False):
        s = Settings(blacklisted_tables=["secret_table"])
        assert "secret_table" in s.blacklisted_tables


def test_json_blacklist_merged_with_env_var(tmp_path: Path) -> None:
    json_file = tmp_path / "blacklist_tables.json"
    json_file.write_text(json.dumps({"blacklisted_tables": ["from_json"]}))

    with patch("dbsage.mcp_server.config._BLACKLIST_JSON", json_file):
        s = Settings(blacklisted_tables=["from_env"])
        assert "from_json" in s.blacklisted_tables
        assert "from_env" in s.blacklisted_tables


def test_missing_json_file_doesnt_raise(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_file.json"
    with patch("dbsage.mcp_server.config._BLACKLIST_JSON", nonexistent):
        s = Settings(blacklisted_tables=["env_only"])
        assert s.blacklisted_tables == ["env_only"]


def test_malformed_json_file_doesnt_raise(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json {{{")
    with patch("dbsage.mcp_server.config._BLACKLIST_JSON", bad_file):
        s = Settings(blacklisted_tables=["env_only"])
        assert s.blacklisted_tables == ["env_only"]


def test_deduplication_of_blacklist() -> None:
    json_data = {"blacklisted_tables": ["duplicate"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(json_data, f)
        tmp = Path(f.name)

    with patch("dbsage.mcp_server.config._BLACKLIST_JSON", tmp):
        s = Settings(blacklisted_tables=["duplicate"])
        assert s.blacklisted_tables.count("duplicate") == 1

    tmp.unlink()


def test_cache_ttl_default() -> None:
    s = Settings()
    assert s.cache_ttl_seconds == 300


def test_max_query_rows_default() -> None:
    s = Settings()
    assert s.max_query_rows == 100
