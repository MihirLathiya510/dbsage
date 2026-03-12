# Contributing to dbsage

dbsage is open to contributions — new tools, bug fixes, documentation improvements, and database driver support. This guide covers how the code is organized, how to add a tool, and what the quality bar looks like.

---

## Architecture

Five layers, each with a clear responsibility:

```
LLM
 │
 │ MCP tool calls
 ▼
┌─────────────────────────────────────────────────────┐
│ Tools (src/dbsage/tools/)                           │
│ @mcp.tool() functions — the LLM's API surface       │
├─────────────────────────────────────────────────────┤
│ Safety (src/dbsage/db/)                             │
│ Validator → Rewriter → Executor (3-layer pipeline)  │
├─────────────────────────────────────────────────────┤
│ Schema (src/dbsage/schema/)                         │
│ information_schema queries with TTL caching         │
├─────────────────────────────────────────────────────┤
│ Semantic (src/dbsage/semantic/)                     │
│ Business context from config/semantic_schema.json   │
├─────────────────────────────────────────────────────┤
│ Formatting (src/dbsage/formatting/)                 │
│ Unicode box tables, section headers, footers        │
└─────────────────────────────────────────────────────┘
 │
 │ SQLAlchemy 2.0 async + aiomysql / asyncpg
 ▼
Database
```

Key files to know:

| File | What it does |
|---|---|
| `src/dbsage/mcp_server/server.py` | FastMCP entrypoint — tools register here via side-effect imports |
| `src/dbsage/mcp_server/config.py` | All configuration — pydantic-settings, `DBSAGE_` prefix |
| `src/dbsage/db/query_validator.py` | Blocks forbidden SQL keywords and patterns |
| `src/dbsage/db/query_rewriter.py` | Injects LIMIT into queries that lack one |
| `src/dbsage/db/query_executor.py` | Runs queries with `asyncio.timeout()` enforcement |
| `src/dbsage/formatting/table_formatter.py` | All output formatting — box tables, section headers |
| `src/dbsage/tools/` | One file per tool category |

---

## Dev setup

1. Fork the repo on GitHub
2. Clone your fork:

```bash
git clone https://github.com/your-username/dbsage.git
cd dbsage
git remote add upstream https://github.com/MihirLathiya510/dbsage.git
uv sync --extra dev
```

No database required — all tests mock the DB layer.

**The full contribution cycle:**

```
fork → clone → branch → change → test locally → push to your fork → open PR → review → merge
```

Always work on a feature branch, not `master`:

```bash
git checkout -b feat/your-tool-name
# make changes
uv run pytest && uv run ruff check src/ && uv run mypy src/
git push origin feat/your-tool-name
# open PR from your fork against MihirLathiya510/dbsage master
```

Keep PRs focused — one tool, one fix, one concern per PR. If your branch drifts behind `upstream/master`, rebase before opening the PR:

```bash
git fetch upstream
git rebase upstream/master
```

---

## How to add a tool

**1. Choose the right file in `src/dbsage/tools/`**

| File | Add tools for... |
|---|---|
| `discovery_tools.py` | Finding and filtering tables |
| `schema_tools.py` | Inspecting table structure and relationships |
| `sampling_tools.py` | Fetching rows or column values |
| `query_tools.py` | Executing or analyzing SQL |
| `semantic_tools.py` | Business-context intelligence |

If the tool doesn't fit any category, create a new file and import it in `server.py`.

**2. Write the function**

```python
@mcp.tool()
async def your_new_tool(table_name: str, limit: int = 10) -> str:
    """One-sentence summary for the LLM.

    More detail if needed. The LLM reads this docstring — make it clear and accurate.
    Describe when to call this tool and what it returns.

    Args:
        table_name: What this parameter means.
        limit: What this controls. Defaults to X, capped at Y.
    """
    settings = get_app_settings()
    engine = get_db_engine()
    header = section_header("your_new_tool", table_name)

    # Check blacklist
    blacklisted = {t.lower() for t in settings.blacklisted_tables}
    if table_name.lower() in blacklisted:
        raise TableBlacklistedError(table_name)

    # Do the work
    rows = await execute_query(your_sql, engine, timeout_ms=settings.query_timeout_ms)

    # Format and return
    body = format_results_table(rows)
    return f"{header}\n\n{body}\n\n  {len(rows)} rows"
```

Rules:
- Always `async def` — the event loop must never block
- All parameters must have type hints — FastMCP uses them for validation
- Return type is always `str` — that's what the LLM receives
- Always respect `blacklisted_tables`
- Always use `settings.query_timeout_ms` when calling `execute_query`
- Use `section_header()` to start the output — it keeps all tool responses consistent
- Use the formatters in `table_formatter.py` — don't invent new output formats

**3. Register the tool in `server.py`**

The tool auto-registers via `@mcp.tool()` when its module is imported. Just add the import:

```python
import dbsage.tools.your_new_tools  # noqa: F401, E402
```

**4. Write the test**

```python
# tests/test_tools.py or a new test file

async def test_your_new_tool_returns_header(mock_engine, mock_settings) -> None:
    # Arrange
    mock_execute_query.return_value = [{"col": "val"}]

    # Act
    result = await your_new_tool("some_table")

    # Assert
    assert "── your_new_tool: some_table" in result
    assert "val" in result


async def test_your_new_tool_respects_blacklist(mock_settings) -> None:
    mock_settings.blacklisted_tables = ["secret_table"]
    with pytest.raises(TableBlacklistedError):
        await your_new_tool("secret_table")
```

---

## Testing conventions

**Mock the database — never hit a real one.**

All DB calls go through `execute_query()`. Mock it at the point of use:

```python
@pytest.fixture
def mock_execute(mocker):
    return mocker.patch("dbsage.tools.your_module.execute_query")
```

**AAA pattern — Arrange, Act, Assert:**

```python
async def test_something() -> None:
    # Arrange
    mock_execute.return_value = [{"id": 1, "name": "test"}]

    # Act
    result = await your_tool("table")

    # Assert
    assert "test" in result
```

**Parametrize safety tests:**

```python
@pytest.mark.parametrize("keyword", [
    "DROP", "DELETE", "INSERT", "UPDATE",
    "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE",
])
async def test_blocks_keyword(keyword: str) -> None:
    with pytest.raises(ForbiddenQueryError):
        validate_query(f"{keyword} FROM users")
```

Every forbidden keyword needs a test. If you add a new forbidden keyword to `query_validator.py`, add it to the parametrize list.

---

## Quality checklist

Before opening a PR, run:

```bash
uv run ruff check src/      # lint + security (must be clean)
uv run ruff format src/     # format
uv run mypy src/            # type check (strict mode, must pass)
uv run pytest               # tests (80% coverage minimum)
```

All four must pass. CI will block merges if any fail.

Additional rules:
- No `print()` — use `structlog` via `query_logger.py`
- No bare `except Exception` — catch specific exceptions
- No hardcoded credentials — everything via `get_app_settings()`
- New tools must have at least: a basic success test, a blacklist test, and (if querying) a timeout test

---

## PR checklist

- [ ] Tool has a clear, accurate docstring (the LLM reads it)
- [ ] All parameters are type-annotated
- [ ] Blacklist check included
- [ ] Output uses `section_header()` and existing formatters
- [ ] Tests cover success path, blacklist, and edge cases
- [ ] `ruff check`, `mypy`, and `pytest` all pass locally
- [ ] No new dependencies added without discussion (the dependency surface affects uvx install time)
