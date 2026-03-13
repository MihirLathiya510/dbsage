"""Semantic intelligence tools — business-context layer for database understanding.

Provides business-context-aware tools that help LLMs understand database meaning
before writing queries. Reads from config/semantic_schema.json.

Tools:
  get_database_context     — instant mental model of the entire database
  get_table_semantics      — enriched description for a specific table
  search_schema_by_meaning — find tables/columns by business term
"""

from dbsage.mcp_server.server import mcp
from dbsage.semantic.semantic_loader import (
    get_common_analytics,
    get_database_info,
    get_table_meta,
    get_vocabulary,
    search_by_term,
)


@mcp.tool()
def get_database_context(connection: str | None = None) -> str:
    """Return a business-level mental model of the entire database.

    Call this FIRST when exploring an unfamiliar database. Returns:
    - what the database is for
    - core business concepts and which tables represent them
    - vocabulary mapping (business terms to table names)
    - ready-to-run common analytics queries

    This replaces multiple list_tables + describe_table calls with a single
    high-level orientation.

    Pass connection='<name>' to note which connection this context is for.
    Call list_connections() to see available profiles.

    Args:
        connection: Optional named connection profile. Used for context labeling only.
    """
    db_info = get_database_info()
    vocab = get_vocabulary()
    analytics = get_common_analytics()

    if not db_info and not vocab:
        return (
            "(no semantic schema configured — "
            "populate config/semantic_schema.json to enable this tool)"
        )

    lines: list[str] = []

    if db_info:
        db_name = db_info.get("name", "Database")
        conn_label = f" [{connection}]" if connection else ""
        lines.append(f"=== {db_name}{conn_label} ===")
        lines.append("")
        if desc := db_info.get("description"):
            lines.append(desc)
        if domain := db_info.get("domain"):
            lines.append(f"\nDomain: {domain}")
        if workflow := db_info.get("core_workflow"):
            lines.append(f"Core workflow: {workflow}")

    if vocab:
        lines.append("")
        lines.append("Business Vocabulary")
        lines.append("-------------------")
        for term, mapping in vocab.items():
            lines.append(f'  "{term}" → {mapping}')

    if analytics:
        lines.append("")
        lines.append("Common Analytics")
        lines.append("----------------")
        for item in analytics:
            lines.append(f"  {item['name']}: {item.get('description', '')}")
            lines.append(f"    {item['sql']}")

    return "\n".join(lines)


@mcp.tool()
def get_table_semantics(table_name: str) -> str:
    """Return business-level meaning and context for a specific table.

    Enriches raw schema with:
    - plain-English description of what the table represents
    - column-by-column explanations
    - business tags (e.g. 'core', 'lookup', 'financial')
    - example queries for common use cases

    Use after describe_table() to understand not just structure
    but the business meaning of a table.

    Args:
        table_name: Name of the table to get semantic context for.
    """
    meta = get_table_meta(table_name)

    if not meta:
        return (
            f"(no semantic metadata for '{table_name}' — "
            f"add it to config/semantic_schema.json)"
        )

    lines: list[str] = []
    actual_name = meta.get("_table_name", table_name)
    lines.append(f"=== {actual_name} ===")
    lines.append("")

    if desc := meta.get("description"):
        lines.append(desc)

    if tags := meta.get("tags"):
        lines.append(f"\nTags: {', '.join(tags)}")

    if columns := meta.get("columns"):
        lines.append("\nColumn Meanings")
        lines.append("---------------")
        for col, meaning in columns.items():
            lines.append(f"  {col:<30} {meaning}")

    if queries := meta.get("common_queries"):
        lines.append("\nCommon Queries")
        lines.append("--------------")
        for sql in queries:
            lines.append(f"  {sql}")

    return "\n".join(lines)


@mcp.tool()
def search_schema_by_meaning(query: str) -> str:
    """Find tables and columns matching a business concept or term.

    Searches vocabulary mappings, table descriptions, column meanings,
    and tags. Useful when you know the business concept but not the table name.

    Examples:
      search_schema_by_meaning("lender")    -> Organizations table
      search_schema_by_meaning("loan")      -> Deals table
      search_schema_by_meaning("financial") -> Facts, PfsSheets, FinanceSheetTemplates

    Args:
        query: A business term or concept to search for.
    """
    results = search_by_term(query)

    if not results:
        return (
            f"(no matches for '{query}' in semantic schema — "
            f"try a different term or check config/semantic_schema.json)"
        )

    lines: list[str] = [f"Results for '{query}':", ""]

    for r in results:
        match r["type"]:
            case "vocabulary":
                lines.append(f"[vocabulary]  {r['term']} -> {r['maps_to']}")
            case "table":
                desc = r.get("description", "")[:100]
                tags = ", ".join(r.get("tags", []))
                lines.append(f"[table]       {r['table']}")
                if desc:
                    lines.append(f"              {desc}")
                if tags:
                    lines.append(f"              tags: {tags}")
            case "column":
                lines.append(
                    f"[column]      {r['table']}.{r['column']} — {r['description']}"
                )
        lines.append("")

    return "\n".join(lines).rstrip()
