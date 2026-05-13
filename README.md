<div align="center">
  <img src="assets/logo.png" alt="dbsage logo" width="220" />

# dbsage

**Safe, read-only database access for AI tools.**

dbsage is an MCP server that lets LLMs explore schemas, understand business context, and run validated queries — without any risk of writing to your database.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green)
![License MIT](https://img.shields.io/badge/license-MIT-lightgrey)

</div>

## Why dbsage

Most teams reach a point where they want an AI to help answer data questions, but they're not comfortable giving it raw database access. Direct access means write risk, uncapped queries, and no guardrails around sensitive tables.

dbsage sits between the AI and the database. It enforces read-only access at the query level, injects row limits and timeouts, hides tables you flag as off-limits, and returns structured output that LLMs can reason about cleanly. You can also describe your schema in plain language so the AI arrives with business context instead of starting from scratch every time.

## What it looks like in practice

A teammate asks how many deals are in the pipeline, grouped by type. dbsage loads the database context, then runs:

```sql
SELECT dt.name AS deal_type, COUNT(d.id) AS count
FROM Deals d
JOIN DealTypes dt ON d.dealType_id = dt.id
GROUP BY dt.id
ORDER BY count DESC;
```

```text
deal_type             count
Bridge Loan             142
Construction Loan        89
Permanent Financing      34
Mezzanine                12

4 rows in 28ms
```

Because the semantic config maps `deal` to the right table, there's no guesswork about table names or join paths.

Before shipping a release, you might want to check whether staging still matches production:

```text
Schema comparison: prod to staging

Tables only in prod:
  audit_log
  feature_flags

Tables only in staging:
  none

Tables in both: 147
```

Or compare row counts across environments:

```text
orders
  prod       4.3M
  replica    4.3M
  staging    18.4k
```

Named connection profiles handle all of this from one place, no switching VPNs or opening separate clients.

## Quick start

Once published to PyPI, this is all you need:

```bash
uvx dbsage
```

Client configuration:

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

PyPI publication is still in progress. To run from source:

```bash
git clone https://github.com/your-org/dbsage.git
cd dbsage
cp .env.example .env
uv sync
```

Then point your client at the local project:

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

## Tools

dbsage has 23 tools. Full reference in [docs/tools.md](docs/tools.md).

### Discovery and schema

`list_tables` and `search_tables` let you find tables by name or keyword, with row counts included.

`describe_table` returns column names, types, nullability, and foreign key references. `table_relationships` maps how tables connect across the whole database or for a specific table. `schema_summary` pulls that together into a single overview with sizes and row counts. `show_create_view` returns the full SQL definition for a view.

### Sampling

`sample_table` pulls a small set of rows so the AI can understand what the data actually looks like. `sample_column_values` returns distinct values with counts for a column, useful for categorical fields. `table_row_count` returns a fast approximate count from `information_schema`. `inspect_json_column` pretty-prints samples from JSON or JSONB columns.

### Query execution

`run_read_only_query` validates, rewrites, and executes a SELECT query with limits and timeout enforced. `explain_query` returns the execution plan so you can check for full scans before running anything expensive.

### Semantic context

`get_database_context` returns the domain, vocabulary, and analytics notes from your semantic config. `get_table_semantics` returns the business description and column meanings for a specific table. `search_schema_by_meaning` lets you find tables and columns by business term rather than exact name.

### Connections

`list_connections` shows configured profiles and `ping_connections` checks connectivity and latency across them. `add_connection` and `remove_connection` let you add or remove profiles at runtime without restarting the server. `compare_query_across_connections` runs the same query across multiple databases, `diff_schema` compares table structures between environments, `find_table_across_connections` checks which connections have a given table, and `compare_row_counts` gives you a quick cross-environment count comparison.

## Semantic config

The semantic config turns raw schema details into something the AI can actually use. Instead of every conversation starting with table discovery and guesswork, you document the domain once and it's available on every call.

Create `config/semantic_schema.json`:

```json
{
  "database": {
    "name": "your_db",
    "description": "What this database is for",
    "domain": "e-commerce",
    "core_workflow": "User places Order, Items added, Payment processed, Shipped"
  },
  "vocabulary": {
    "customer": "users",
    "purchase": "orders"
  },
  "tables": {
    "users": {
      "description": "Registered customer accounts",
      "columns": {
        "id": "Unique user identifier UUID",
        "email": "Login email address"
      }
    }
  }
}
```

You can include a plain-language database description, business vocabulary mappings, core workflows, table and column descriptions, and common query patterns. Full guide in [docs/semantic.md](docs/semantic.md).

## Multiple connections

Every database-facing tool accepts an optional `connection` parameter that routes the call to a named profile. Leave it blank to use the default.

Copy `config/connections.example.json` to `config/connections.json` and fill in your profiles. For local development, an inline password is fine:

```json
{
  "connections": {
    "dev": {
      "host": "dev-db.example.com",
      "database": "app_db",
      "user": "readonly",
      "password": "your_password_here",
      "db_type": "mysql"
    }
  }
}
```

For production, use `password_env` and set `requires_confirmation: true`. Responses from that connection will include a warning banner, and the password never appears in config or logs:

```json
{
  "connections": {
    "prod": {
      "host": "prod-db.example.com",
      "database": "app_db",
      "user": "readonly",
      "password_env": "PROD_DB_PASSWORD",
      "db_type": "mysql",
      "requires_confirmation": true
    }
  }
}
```

If both `password` and `password_env` are set, `password` takes precedence. You can also tighten `max_query_rows` and `query_timeout_ms` per profile. Connection groups let you target several profiles together:

```json
{
  "default": "primary",
  "groups": {
    "all-prod": ["prod-us", "prod-eu"]
  },
  "connections": {}
}
```

Full guide in [docs/multi-connection.md](docs/multi-connection.md).

## Configuration

All environment variables use the `DBSAGE_` prefix.

| Variable | Default | Notes |
|---|---|---|
| `DBSAGE_DB_HOST` | `localhost` | |
| `DBSAGE_DB_PORT` | `3306` | |
| `DBSAGE_DB_NAME` | required | |
| `DBSAGE_DB_USER` | required | |
| `DBSAGE_DB_PASSWORD` | required | |
| `DBSAGE_DB_TYPE` | `mysql` | `mysql`, `postgresql`, or `mssql` |
| `DBSAGE_MAX_QUERY_ROWS` | `100` | Default LIMIT when query has none |
| `DBSAGE_MAX_QUERY_ROWS_HARD_CAP` | `500` | Ceiling for explicit limits |
| `DBSAGE_QUERY_TIMEOUT_MS` | `3000` | |
| `DBSAGE_SLOW_QUERY_THRESHOLD_MS` | `2000` | Logs queries slower than this |
| `DBSAGE_DEFAULT_SAMPLE_LIMIT` | `10` | Default rows for `sample_table` |
| `DBSAGE_CACHE_TTL_SECONDS` | `300` | Schema metadata cache TTL |
| `DBSAGE_BLACKLISTED_TABLES` | `[]` | Tables hidden from all tools |
| `DBSAGE_DEV_MODE` | `false` | Human-readable logs |

You can also manage hidden tables in `config/blacklist_tables.json`. Values there are merged with the environment variable at startup.

## Security

dbsage validates every query before it reaches the database. INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, and REVOKE are blocked outright, along with indirect mutation paths like `SELECT INTO OUTFILE`, `LOAD DATA INFILE`, and `CREATE TEMP TABLE`.

Passwords are stored as `SecretStr` throughout, so they won't appear in logs, stack traces, or repr output. Every query runs with a timeout, gets a default row limit if it doesn't include one, and is capped at `DBSAGE_MAX_QUERY_ROWS_HARD_CAP` even if the caller requests more. Blacklisted tables are stripped from every tool response.

For the strongest guarantee, create a database user with SELECT privilege only. dbsage enforces read-only at the application layer, but a SELECT-only credential adds a second layer that can't be bypassed.

## Development

```bash
git clone https://github.com/your-org/dbsage.git
cd dbsage
uv sync --extra dev

uv run pytest
uv run ruff check src/
uv run mypy src/
```

276 tests, around 96% coverage. Strict mypy and ruff security checks run on every commit via Lefthook.

Contributing guide in [docs/contributing.md](docs/contributing.md).

## Requirements

Python 3.12+, uv, and MySQL 5.7+, PostgreSQL 13+, or SQL Server 2017+. For MSSQL, also install the Microsoft ODBC Driver and run `uv sync --extra mssql`.

```bash
curl -LsSf https://docs.astral.sh/uv/install.sh | sh
```

## License

MIT
