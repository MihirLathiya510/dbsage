# Multi-Connection Setup

dbsage can hold multiple named database connections simultaneously. Every tool that touches a database accepts an optional `connection='<name>'` parameter — leave it blank to hit the default, or pass a name to route the call to a specific profile.

This is useful for: dev/staging/prod environments in one session, primary + read replica routing, cross-database schema comparison, and multi-tenant deployments where each tenant has its own database.

---

## Quick start

Copy the example file and fill in your values:

```bash
cp config/connections.example.json config/connections.json
```

`connections.json` is gitignored — it holds credentials and should never be committed. The example file is always committed as a reference template.

---

## connections.json structure

```json
{
  "default": "primary",
  "connections": {
    "primary": {
      "host": "db1.example.com",
      "port": 3306,
      "database": "app_db",
      "user": "readonly",
      "password": "your_password",
      "db_type": "mysql",
      "description": "Main app DB"
    },
    "replica": {
      "host": "db2.example.com",
      "port": 3306,
      "database": "app_db",
      "user": "readonly",
      "password_env": "REPLICA_DB_PASSWORD",
      "db_type": "mysql",
      "description": "Read replica"
    },
    "analytics": {
      "host": "dw.example.com",
      "port": 5432,
      "database": "warehouse",
      "user": "analyst",
      "password_env": "ANALYTICS_DB_PASSWORD",
      "db_type": "postgresql",
      "description": "Data warehouse"
    }
  },
  "groups": {
    "all-app": ["primary", "replica"],
    "all": ["primary", "replica", "analytics"]
  }
}
```

The top-level keys:

| Key | Required | Description |
|---|---|---|
| `connections` | yes | Map of profile name → connection config |
| `default` | no | Which profile to use when no `connection=` is passed. Falls back to `DBSAGE_*` env vars if omitted. |
| `groups` | no | Named sets of profiles, usable anywhere a connections list is accepted |

---

## Password options

Two ways to supply a password per profile. They can coexist — `password` takes precedence over `password_env`.

**Inline (convenient for local/dev):**

```json
{
  "password": "your_password_here"
}
```

Inline passwords stay in `connections.json`, which is gitignored. Acceptable for developer laptops. Not appropriate for shared environments or CI.

**Via environment variable (recommended for staging/prod):**

```json
{
  "password_env": "PROD_DB_PASSWORD"
}
```

`password_env` is the name of the environment variable to read — not the password itself. The variable must be set in the shell or MCP client `env` block before the server starts.

---

## Per-profile guardrails

Each profile can override the global row limit and query timeout:

```json
{
  "connections": {
    "prod": {
      "host": "prod.example.com",
      "database": "app_db",
      "user": "readonly",
      "password_env": "PROD_DB_PASSWORD",
      "max_query_rows": 25,
      "query_timeout_ms": 1500
    }
  }
}
```

Per-profile values take precedence over `DBSAGE_MAX_QUERY_ROWS` and `DBSAGE_QUERY_TIMEOUT_MS`. Use tighter limits on production connections to reduce blast radius.

---

## Sensitive connections

Mark a profile `requires_confirmation: true` to prepend a warning banner on every response from that connection:

```json
{
  "prod": {
    "host": "prod.example.com",
    "database": "app_db",
    "user": "readonly",
    "password_env": "PROD_DB_PASSWORD",
    "requires_confirmation": true,
    "description": "Production — handle with care"
  }
}
```

When the LLM calls any tool with `connection='prod'`, the response begins with:

```
⚠ WARNING: you are querying a sensitive connection (prod).
```

This makes it visible in the LLM context that the active connection is production — useful for agents that switch between environments.

---

## Connection groups

Define named sets of profiles in the `groups` section. Group names are accepted anywhere a `connections` list is expected — the comparison and ping tools expand them automatically.

```json
{
  "groups": {
    "all-prod": ["prod-us", "prod-eu"],
    "app-tier": ["primary", "replica"]
  }
}
```

Usage:

```
compare_row_counts(table="orders", connections=["all-prod"])
ping_connections(connections=["app-tier"])
diff_schema(connection_a="primary", connection_b="staging")
```

---

## Routing tool calls

All 15 non-connection tools accept `connection='<name>'`:

```
list_tables(connection='analytics')
describe_table('orders', connection='prod')
run_read_only_query('SELECT COUNT(*) FROM users', connection='replica')
sample_table('deals', connection='staging')
```

Omit `connection` to use the profile named in `"default"`, or the `DBSAGE_*` env vars if no default is set.

Call `list_connections()` first to see what profiles are configured and which is the default.

---

## Cross-connection tools

Six tools are designed specifically for multi-connection workflows:

| Tool | What it does |
|---|---|
| `list_connections` | Show all configured profiles, their hosts, types, and whether they are sensitive |
| `ping_connections` | Check reachability and latency for each profile |
| `diff_schema` | Compare table lists or column definitions between two connections |
| `compare_row_counts` | Approximate row count for a table across multiple connections |
| `find_table_across_connections` | Check which connections contain a given table |
| `compare_query_across_connections` | Run the same SELECT on multiple connections and show results side by side |

Full parameter reference and output examples for each: [docs/tools.md](tools.md#connections)

---

## Engines and connection pooling

dbsage lazy-initializes one SQLAlchemy async engine per connection profile. The engine is created on first use and cached for the lifetime of the server process. Connection pool settings (`pool_size`, `max_overflow`, `pool_recycle`) apply independently per engine.

No database connections are opened until a tool actually calls that profile. `ping_connections()` forces a connection check without running a query.
