<div align="center">
  <img src="assets/logo.png" alt="dbsage logo" width="220" />

# dbsage

**AI Database Copilot** — a production-grade [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives LLMs safe, structured, read-only access to any MySQL or PostgreSQL database.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green)
![License MIT](https://img.shields.io/badge/license-MIT-lightgrey)

</div>

---

## See it in action

> A user asks Claude: _"How many deals are in the pipeline, broken down by type?"_

```
── get_database_context ─────────────────────────────────────────────────────────

  Domain: commercial real estate lending
  Vocabulary: deal → Deals, loan → Deals, lender → Lenders
  Workflow: Borrower submits Deal → Lenders review → Term sheet issued → Closed

── run_read_only_query ──────────────────────────────────────────────────────────

  SELECT dt.name AS deal_type, COUNT(d.id) AS count
  FROM Deals d
  JOIN DealTypes dt ON d.dealType_id = dt.id
  GROUP BY dt.id ORDER BY count DESC

  ┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
  ┃ deal_type            ┃ count ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
  │ Bridge Loan          │   142 │
  │ Construction Loan    │    89 │
  │ Permanent Financing  │    34 │
  │ Mezzanine            │    12 │
  └──────────────────────┴───────┘

  4 rows · 28ms
```

> **2 tool calls. No manual schema exploration. No guessing table names.**
>
> The semantic layer told Claude what "deal" maps to. The query ran validated and
> LIMIT-enforced before touching the database.

---

## Quick connect

**You do not need to clone this repository.**

Once dbsage is published to PyPI, connect any MCP-compatible client by passing your database credentials as environment variables — no `.env` file, no local setup.

> PyPI publication is in progress. Until then, use the **from-source path** in the collapsible sections below.

### Claude Code

```bash
claude mcp add dbsage \
  --command "uvx" \
  --args "dbsage" \
  --env "DBSAGE_DB_HOST=your-host.rds.amazonaws.com" \
  --env "DBSAGE_DB_NAME=your_database" \
  --env "DBSAGE_DB_USER=readonly_user" \
  --env "DBSAGE_DB_PASSWORD=your_password" \
  --env "DBSAGE_DB_TYPE=mysql"
```

Or edit `~/.claude/claude_code_config.json` directly:

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host.rds.amazonaws.com",
        "DBSAGE_DB_NAME": "your_database",
        "DBSAGE_DB_USER": "readonly_user",
        "DBSAGE_DB_PASSWORD": "your_password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}
```

<details>
<summary>Running from source (until PyPI is available)</summary>

```bash
git clone https://github.com/MihirLathiya510/dbsage.git
cd dbsage
cp .env.example .env   # fill in your database credentials
uv sync
```

Then in your MCP client config:

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/dbsage", "dbsage"]
    }
  }
}
```

</details>

---

### Cursor IDE

Create or edit `.cursor/mcp.json` in your project (or `~/.cursor/mcp.json` for global):

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host",
        "DBSAGE_DB_NAME": "your_database",
        "DBSAGE_DB_USER": "readonly_user",
        "DBSAGE_DB_PASSWORD": "your_password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}
```

Restart Cursor after saving.

<details>
<summary>Running from source</summary>

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/dbsage", "dbsage"]
    }
  }
}
```

</details>

---

### Claude Desktop

Edit the config file for your OS:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uvx",
      "args": ["dbsage"],
      "env": {
        "DBSAGE_DB_HOST": "your-host",
        "DBSAGE_DB_NAME": "your_database",
        "DBSAGE_DB_USER": "readonly_user",
        "DBSAGE_DB_PASSWORD": "your_password",
        "DBSAGE_DB_TYPE": "mysql"
      }
    }
  }
}
```

Restart Claude Desktop after saving.

<details>
<summary>Running from source</summary>

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/dbsage", "dbsage"]
    }
  }
}
```

</details>

---

### Any MCP-compatible client

dbsage speaks standard MCP over stdio. Pass this command with `DBSAGE_*` environment variables for your credentials:

```
uvx dbsage
```

---

## Tools

15 tools across 5 categories. Full reference with output examples: [docs/tools.md](docs/tools.md)

| Category  | Tool                       | What it does                                               |
|-----------|----------------------------|------------------------------------------------------------|
| Discovery | `list_tables`              | List all visible tables with row counts                    |
|           | `search_tables`            | Filter tables by keyword                                   |
| Schema    | `describe_table`           | Column names, types, nullability, keys, FK references      |
|           | `table_relationships`      | Foreign key map for one table or the whole database        |
|           | `schema_summary`           | Full overview: all tables with row counts, sizes, FK graph |
| Sampling  | `sample_table`             | Return N rows from a table                                 |
|           | `sample_column_values`     | Distinct values with counts for a column                   |
|           | `table_row_count`          | Fast approximate row count from `information_schema`       |
|           | `inspect_json_column`      | Pretty-print JSON samples from a JSON/JSONB column         |
| Query     | `run_read_only_query`      | Validate, rewrite, and execute a SELECT query              |
|           | `explain_query`            | Return the query execution plan (EXPLAIN)                  |
| Semantic  | `get_database_context`     | Full business mental model: domain, vocabulary, analytics  |
|           | `get_table_semantics`      | Business description and column meanings for one table     |
|           | `search_schema_by_meaning` | Find tables/columns by business term                       |

---

## Semantic layer

The semantic layer is what separates dbsage from a raw SQL proxy. Without it, an LLM has to explore the schema step-by-step before it can answer anything. With it, one call to `get_database_context()` gives Claude a complete business picture.

**Without the semantic layer:**
```
list_tables → describe_table → describe_table → table_relationships
→ sample_column_values → ... (6+ calls just to understand the schema)
```

**With the semantic layer:**
```
get_database_context() → full domain understanding in one call → query runs
```

Add a `config/semantic_schema.json` file to enable it:

```json
{
  "database": {
    "name": "your_db",
    "description": "What this database is for",
    "domain": "e-commerce",
    "core_workflow": "User places Order → Items added → Payment processed → Shipped"
  },
  "vocabulary": {
    "customer": "users",
    "purchase": "orders"
  },
  "tables": {
    "users": {
      "description": "Registered customer accounts",
      "columns": {
        "id": "Unique user identifier (UUID)",
        "email": "Login email address"
      }
    }
  }
}
```

Full cookbook with domain templates (e-commerce, SaaS, financial): [docs/semantic.md](docs/semantic.md)

---

## Configuration

All configuration uses the `DBSAGE_` prefix. Pass values in the MCP client `env` block or in a `.env` file when running from source.

| Variable | Default | Description |
|---|---|---|
| `DBSAGE_DB_HOST` | `localhost` | Database hostname |
| `DBSAGE_DB_PORT` | `3306` | Database port |
| `DBSAGE_DB_NAME` | — | Database name (required) |
| `DBSAGE_DB_USER` | — | Database user (required) |
| `DBSAGE_DB_PASSWORD` | — | Database password (required) |
| `DBSAGE_DB_TYPE` | `mysql` | `mysql` or `postgresql` |
| `DBSAGE_MAX_QUERY_ROWS` | `100` | Hard cap on rows returned |
| `DBSAGE_QUERY_TIMEOUT_MS` | `3000` | Query execution timeout in ms |
| `DBSAGE_SLOW_QUERY_THRESHOLD_MS` | `2000` | Log queries exceeding this (ms) |
| `DBSAGE_DEFAULT_SAMPLE_LIMIT` | `10` | Default row count for `sample_table` |
| `DBSAGE_CACHE_TTL_SECONDS` | `300` | Schema metadata cache TTL in seconds |
| `DBSAGE_BLACKLISTED_TABLES` | `[]` | Tables hidden from the LLM |
| `DBSAGE_DEV_MODE` | `false` | Human-readable logs (JSON otherwise) |

You can also manage the blacklist in `config/blacklist_tables.json` — it merges with the env var at startup.

---

## Security

- **Read-only at the validator level.** INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE are blocked before execution, not just discouraged. Indirect mutation paths (`SELECT INTO OUTFILE`, `LOAD DATA INFILE`, `CREATE TEMP TABLE`) are also blocked.
- **Credentials never leak.** The database password is `SecretStr` — it never appears in logs, stack traces, or repr output.
- **No runaway queries.** Every execution runs under `asyncio.timeout()`. Results are hard-capped at `DBSAGE_MAX_QUERY_ROWS` regardless of what the SQL says.
- **Sensitive tables stay hidden.** `DBSAGE_BLACKLISTED_TABLES` removes tables from all tool responses before the LLM sees them.
- **Recommended:** create a database user with `SELECT` privilege only — defense in depth beyond the validator.

---

## Development

```bash
git clone https://github.com/MihirLathiya510/dbsage.git
cd dbsage
uv sync --extra dev

uv run pytest               # 121 tests, ~95% coverage
uv run ruff check src/      # lint + security scan
uv run mypy src/            # strict type check
```

Contributing guide, how to add a tool, and the PR checklist: [docs/contributing.md](docs/contributing.md)

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- MySQL 5.7+ or PostgreSQL 13+
- Network access to your database

---

## License

MIT
