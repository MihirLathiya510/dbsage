"""Semantic schema loader — reads and caches config/semantic_schema.json.

Provides lookup functions for table descriptions, column meanings,
vocabulary mapping, and common analytics queries.

The JSON file is loaded once and held in memory. If the file is missing
or malformed, all lookups return None/empty gracefully — the MCP continues
working, just without semantic enrichment.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SEMANTIC_JSON = Path(__file__).parents[3] / "config" / "semantic_schema.json"


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    """Load and cache the semantic schema JSON. Returns {} on any error."""
    if not _SEMANTIC_JSON.exists():
        return {}
    try:
        return json.loads(_SEMANTIC_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_database_info() -> dict[str, Any]:
    """Return the top-level database description block."""
    return _load().get("database", {})


def get_vocabulary() -> dict[str, str]:
    """Return the business vocabulary mapping (term → table name)."""
    return _load().get("vocabulary", {})


def get_table_meta(table_name: str) -> dict[str, Any] | None:
    """Return semantic metadata for a specific table, or None if not defined."""
    tables = _load().get("tables", {})
    # Case-insensitive lookup
    for key, value in tables.items():
        if key.lower() == table_name.lower():
            return {"_table_name": key, **value}
    return None


def get_all_tables_meta() -> dict[str, Any]:
    """Return semantic metadata for all documented tables."""
    return _load().get("tables", {})


def get_common_analytics() -> list[dict[str, Any]]:
    """Return predefined common analytics queries."""
    return _load().get("common_analytics", [])


def search_by_term(query: str) -> list[dict[str, Any]]:
    """Search vocabulary and table metadata for a business term.

    Returns a list of matches, each with:
      - type: "vocabulary" | "table" | "column" | "tag"
      - table: table name
      - match: what matched
      - description: explanation
    """
    q = query.lower()
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Exact vocabulary match
    vocab = get_vocabulary()
    for term, mapping in vocab.items():
        if q in term.lower() or term.lower() in q:
            key = f"vocab:{term}"
            if key not in seen:
                seen.add(key)
                results.append({
                    "type": "vocabulary",
                    "term": term,
                    "maps_to": mapping,
                    "description": f'Business term "{term}" maps to → {mapping}',
                })

    # 2. Table name / description / tag match
    for table_name, meta in get_all_tables_meta().items():
        table_desc: str = meta.get("description", "")
        tags: list[str] = meta.get("tags", [])

        name_match = q in table_name.lower()
        desc_match = q in table_desc.lower()
        tag_match = any(q in tag for tag in tags)

        if name_match or desc_match or tag_match:
            key = f"table:{table_name}"
            if key not in seen:
                seen.add(key)
                results.append({
                    "type": "table",
                    "table": table_name,
                    "description": table_desc,
                    "tags": tags,
                })

        # 3. Column description match
        for col_name, col_desc in meta.get("columns", {}).items():
            if q in col_name.lower() or q in str(col_desc).lower():
                key = f"col:{table_name}.{col_name}"
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "type": "column",
                        "table": table_name,
                        "column": col_name,
                        "description": col_desc,
                    })

    return results
