<div align="center">
  <img src="assets/logo.png" alt="dbsage logo" width="250" />

# dbsage

**AI Database Copilot** — a production-grade [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives LLMs safe, structured, read-only access to relational databases.

</div>

Connect Claude Code, Cursor, or any MCP-compatible AI tool directly to your MySQL or PostgreSQL database. The server enforces strict read-only guarantees, injects query limits, caches schema metadata, and provides business-context annotations so the LLM understands your database without guessing.

---

## Features

| Capability | Details |
|---|---|
| **Read-only safety** | Blocks INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE at the validator level |
| **Automatic LIMIT injection** | Queries without a LIMIT get one added automatically (default 100 rows) |
| **Query timeout** | Every query runs under a configurable timeout (default 10 s) |
| **Schema caching** | Table lists, column definitions, and FK relationships cached with TTL (default 5 min) |
| **Table blacklisting** | Hide sensitive tables from the LLM via env var or JSON config |
| **Semantic layer** | Attach business descriptions, column meanings, and vocabulary to your schema |
| **Structured logging** | JSON logs in production, human-readable in dev mode |
| **MySQL + PostgreSQL** | Async drivers (aiomysql / asyncpg) via SQLAlchemy 2.0 |

---

## Tools Exposed to the LLM

### Discovery
| Tool | Description |
|---|---|
| `list_tables` | List all visible tables in the database |
| `search_tables` | Filter tables by keyword |

### Schema Inspection
| Tool | Description |
|---|---|
| `describe_table` | Column names, types, keys, and nullability |
| `table_relationships` | Foreign key relationships for a table or the whole database |
| `schema_summary` | Full database overview: all tables with row counts, sizes, and FK map |

### Data Sampling
| Tool | Description |
|---|---|
| `sample_table` | Return N rows from a table |
| `sample_column_values` | Distinct values with counts for a column |
| `table_row_count` | Fast approximate row count from `information_schema` |
| `inspect_json_column` | Pretty-print JSON samples from a JSON/JSONB column |

### Query Execution
| Tool | Description |
|---|---|
| `run_read_only_query` | Execute a validated, LIMIT-injected SELECT query |
| `explain_query` | Return the query execution plan (EXPLAIN) |

### Semantic Intelligence
| Tool | Description |
|---|---|
| `get_database_context` | Full business mental model — domain, vocabulary, common analytics |
| `get_table_semantics` | Business description and column meanings for a specific table |
| `search_schema_by_meaning` | Find tables/columns by business term (e.g. "lender", "loan") |

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- MySQL 5.7+ or PostgreSQL 13+
- Network access to your database (VPN/tunnel if behind a private VPC)

---

## Installation

```bash
git clone https://github.com/your-org/dbsage.git
cd dbsage

# Install dependencies (creates .venv automatically)
uv sync
```

---

## Configuration

Copy the example environment file and fill in your database credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Database connection
DBSAGE_DB_HOST=your-db-host.rds.amazonaws.com
DBSAGE_DB_PORT=3306
DBSAGE_DB_NAME=your_database
DBSAGE_DB_USER=readonly_user
DBSAGE_DB_PASSWORD=your_password
DBSAGE_DB_TYPE=mysql   # or postgresql

# Safety guardrails
DBSAGE_MAX_QUERY_ROWS=100
DBSAGE_QUERY_TIMEOUT_MS=3000
DBSAGE_SLOW_QUERY_THRESHOLD_MS=2000
DBSAGE_DEFAULT_SAMPLE_LIMIT=10

# Caching
DBSAGE_CACHE_TTL_SECONDS=300

# Security — tables to hide from the LLM
DBSAGE_BLACKLISTED_TABLES=["admin_tokens","internal_logs"]

# Logging — true for human-readable output, false for JSON
DBSAGE_DEV_MODE=true
```

> **Security note:** The database user should have `SELECT` privileges only. Never use an admin credential.

### Additional blacklist via JSON

You can also manage the blacklist in `config/blacklist_tables.json` (merged with the env var at startup):

```json
{
  "blacklisted_tables": ["admin_tokens", "internal_logs", "audit_secrets"]
}
```

---

## Connecting to AI Tools

The server communicates over **stdio** (standard MCP transport). Every tool below uses the same underlying command:

```bash
uv run --directory /path/to/dbsage dbsage
```

Replace `/path/to/dbsage` with the absolute path to this repository on your machine.

---

### Claude Code (CLI)

Add the server to your Claude Code MCP configuration:

```bash
claude mcp add dbsage \
  --command "uv" \
  --args "run,--directory,/path/to/dbsage,dbsage"
```

Or edit `~/.claude/claude_code_config.json` directly:

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/dbsage", "dbsage"]
    }
  }
}
```

Verify the server is registered:

```bash
claude mcp list
```

---

### Cursor IDE

Create or edit `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` for global config):

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/dbsage", "dbsage"]
    }
  }
}
```

Restart Cursor after saving. The dbsage tools will appear in the MCP tools panel.

---

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "dbsage": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/dbsage", "dbsage"]
    }
  }
}
```

Restart Claude Desktop after saving.

---

### Any MCP-Compatible Client

The server speaks standard MCP over stdio. Pass this command to any client:

```
uv run --directory /path/to/dbsage dbsage
```

---

## Semantic Schema (Optional but Recommended)

The semantic layer makes the LLM understand your database at a business level, not just a structural level. Edit `config/semantic_schema.json`:

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
    "purchase": "orders",
    "item": "products"
  },
  "tables": {
    "users": {
      "description": "Registered customer accounts",
      "tags": ["core", "auth"],
      "columns": {
        "id": "Unique user identifier (UUID)",
        "email": "Login email address",
        "created_at": "Account creation timestamp"
      },
      "common_queries": [
        "SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 20"
      ]
    }
  },
  "common_analytics": [
    {
      "name": "Orders by day",
      "description": "Daily order volume",
      "sql": "SELECT DATE(created_at) as day, COUNT(*) as orders FROM orders GROUP BY day ORDER BY day DESC LIMIT 30"
    }
  ]
}
```

Once populated, the LLM can call `get_database_context()` and immediately understand the business domain without exploring the schema step by step.

---

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Lint
uv run ruff check src/

# Type check
uv run mypy src/

# Run the server directly (for debugging)
uv run dbsage
```

### Test coverage

The test suite targets 80% coverage minimum and currently runs at ~95%:

```bash
uv run pytest --cov=src/dbsage --cov-report=html
open htmlcov/index.html
```

---

## Project Structure

```
src/dbsage/
├── mcp_server/          # Server entrypoint, config, dependency injection
├── tools/               # MCP tool definitions (one file per capability group)
├── db/                  # Query validator, rewriter, executor, connection pool
├── schema/              # information_schema queries with TTL caching
├── semantic/            # Semantic schema loader and search
├── formatting/          # Pipe-delimited table formatter for LLM output
├── cache/               # TTL in-memory cache for schema metadata
├── logging_/            # structlog setup (named logging_ to avoid stdlib clash)
└── exceptions.py        # Domain exception hierarchy

config/
├── blacklist_tables.json   # Tables to hide from the LLM
└── semantic_schema.json    # Business context annotations

tests/                   # 121 unit tests, all mocked (no live DB required)
```

---

## Security Model

- **Database credentials**: store in `.env`, never commit to version control (`.env` is in `.gitignore`)
- **Read-only enforcement**: validator runs before every query execution; forbidden keywords raise `ForbiddenQueryError`
- **Result limits**: queries capped at `DBSAGE_MAX_QUERY_ROWS` rows regardless of the SQL written
- **Execution timeout**: `asyncio.timeout()` wraps every database call
- **Table blacklisting**: sensitive tables removed from all tool responses before the LLM sees them
- **Secrets in logs**: `db_password` is `SecretStr` — never appears in logs or repr output

---

## License

MIT
