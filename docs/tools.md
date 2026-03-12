# Tool Reference

dbsage exposes 16 tools to the LLM across 5 categories. Every tool returns plain-text output formatted for readability — Unicode box tables, aligned columns, timing on every query.

---

## Discovery

### `list_tables`

List all visible tables in the database. Respects `DBSAGE_BLACKLISTED_TABLES`.

**Start here** when exploring an unfamiliar database.

```
── list_tables ──────────────────────────────────────────────────────────────────

  deals
  deal_types
  lenders
  organizations
  contacts
  facts
  pfs_sheets

  7 tables
```

---

### `search_tables`

Filter tables by keyword (case-insensitive substring match).

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `keyword` | `str` | — | Search term to match against table names |

```
── search_tables: "deal" ────────────────────────────────────────────────────────

  deals
  deal_types
  deal_lenders

  3 matches
```

Useful when the database has dozens of tables and you need to find the relevant ones without reading them all.

---

## Schema

### `describe_table`

Return column definitions for a table: name, data type, nullable, key type, and foreign key references.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Exact table name |

```
── describe_table: deals ─────────────────────────────────────────────────────────

  id                             INT             PK     NOT NULL  auto_increment
  organization_id                BIGINT          FK → organizations.id  NOT NULL
  dealType_id                    INT             FK → deal_types.id  NOT NULL
  name                           VARCHAR         NOT NULL
  status                         VARCHAR         nullable
  created_at                     DATETIME        NOT NULL

  6 columns · PK on id · 2 FKs · 1 nullable
```

---

### `table_relationships`

Show foreign key relationships — either for a single table or the entire database.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | `""` | Leave empty to see all FK relationships |

```
── table_relationships ───────────────────────────────────────────────────────────

  deals.organization_id    →  organizations.id
  deals.dealType_id        →  deal_types.id
  deal_lenders.deal_id     →  deals.id
  deal_lenders.lender_id   →  lenders.id
  contacts.organization_id →  organizations.id
  facts.deal_id            →  deals.id

  6 relationships
```

Use this to understand join paths before writing multi-table queries. Calling `table_relationships("deals")` filters to only relationships involving the `deals` table.

---

### `show_create_view`

Return the full, untruncated `CREATE VIEW` SQL for a database view.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `view_name` | `str` | — | Exact view name |

```
── show_create_view: v_active_deals ─────────────────────────────────────────

  View:           v_active_deals
  Character set:  utf8mb4

CREATE ALGORITHM=UNDEFINED DEFINER=`readonly`@`%` SQL SECURITY DEFINER
VIEW `v_active_deals` AS
SELECT d.id, d.name, dt.name AS deal_type, d.status, d.created_at
FROM deals d
JOIN deal_types dt ON d.dealType_id = dt.id
WHERE d.status IN ('active', 'term_sheet')
```

Use this instead of querying `information_schema.VIEWS` — the `VIEW_DEFINITION` column truncates at 4096 characters. `SHOW CREATE VIEW` always returns the complete SQL.

---

### `schema_summary`

Full database overview in one call: all tables with row counts, sizes, and FK map. Results are cached for `DBSAGE_CACHE_TTL_SECONDS` (default 5 min).

```
── schema_summary ────────────────────────────────────────────────────────────────

Tables (7)
──────────
  deals                                    1.4k rows       0.23 MB
  deal_types                               12 rows         0.01 MB
  lenders                                  89 rows         0.04 MB
  organizations                            342 rows        0.08 MB
  contacts                                 2.1k rows       0.31 MB
  facts                                    18.7k rows      1.42 MB
  pfs_sheets                               621 rows        0.19 MB

Relationships (6)
─────────────────
  deals.organization_id    →  organizations.id
  deals.dealType_id        →  deal_types.id
  ...
```

---

## Sampling

### `sample_table`

Return N rows from a table to understand its data format and value distributions.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Exact table name |
| `limit` | `int` | `DBSAGE_DEFAULT_SAMPLE_LIMIT` (10) | Capped at `DBSAGE_MAX_QUERY_ROWS` (100) |

```
── sample_table: deals ───────────────────────────────────────────────────────────

  ┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
  ┃ id ┃ name                       ┃ status      ┃ created_at          ┃
  ┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
  │  1 │ Midtown Office Refinance   │ active      │ 2024-01-15 09:23:00 │
  │  2 │ Riverside Construction     │ term_sheet  │ 2024-02-03 14:11:00 │
  │  3 │ Harbor Bridge Loan         │ closed      │ 2024-02-18 10:45:00 │
  └────┴────────────────────────────┴─────────────┴─────────────────────┘

  3 rows
```

---

### `sample_column_values`

Return distinct values with counts for a column, ordered by frequency. Useful for understanding enums, statuses, and categorical distributions.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Exact table name |
| `column_name` | `str` | — | Column to sample |
| `limit` | `int` | `20` | Max distinct values, capped at 100 |

```
── sample_column_values: deals.status ────────────────────────────────────────────

  active        (487 rows)
  closed        (312 rows)
  term_sheet    (198 rows)
  dead          (143 rows)
  prospect       (89 rows)

  5 distinct values
```

---

### `table_row_count`

Fast approximate row count using `information_schema` — no full table scan.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Exact table name |

```
── table_row_count: facts ────────────────────────────────────────────────────────

  facts: ~18.7k rows
```

Use this before querying a table to decide whether you need tighter filtering.

---

### `inspect_json_column`

Pretty-print JSON samples from a JSON or JSONB column.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Exact table name |
| `column_name` | `str` | — | Name of the JSON column |
| `limit` | `int` | `5` | Number of samples, max 20 |

```
── inspect_json_column: deals.metadata ───────────────────────────────────────────

  Sample 1
  ────────
  {
    "source": "broker",
    "referral_id": "BRK-2041",
    "priority": "high"
  }

  Sample 2
  ────────
  {
    "source": "direct",
    "priority": "standard"
  }

  2 samples
```

---

## Query

### `run_read_only_query`

Execute a validated, LIMIT-injected SELECT query. Three layers of protection run before the database sees it:

1. **Validate** — block forbidden keywords (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE) and patterns (`INTO OUTFILE`, `LOAD DATA`, etc.)
2. **Rewrite** — inject `LIMIT` if absent
3. **Execute** — run under `asyncio.timeout()`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `query` | `str` | — | A SELECT, SHOW, DESCRIBE, EXPLAIN, or WITH query |
| `limit` | `int \| None` | `None` | Override row count. `None` uses `DBSAGE_MAX_QUERY_ROWS` (100). Explicit values are capped at `DBSAGE_MAX_QUERY_ROWS_HARD_CAP` (500). |

```
── run_read_only_query ───────────────────────────────────────────────────────────

  SELECT d.name, dt.name AS type, d.status
  FROM deals d
  JOIN deal_types dt ON d.dealType_id = dt.id
  WHERE d.status = 'active'
  ORDER BY d.created_at DESC
  LIMIT 100

  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
  ┃ name                       ┃ type                ┃ status ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
  │ Midtown Office Refinance   │ Bridge Loan         │ active │
  │ Westside Mixed Use         │ Construction Loan   │ active │
  │ ...                        │ ...                 │ ...    │
  └────────────────────────────┴─────────────────────┴────────┘

  47 rows · 34ms · LIMIT auto-injected
```

**Blocked query example:**

```
── run_read_only_query ───────────────────────────────────────────────────────────

  DROP TABLE users

  ✗ Query blocked: forbidden keyword 'DROP'
  Only SELECT, SHOW, DESCRIBE, EXPLAIN, and WITH are allowed.
```

---

### `explain_query`

Return the EXPLAIN execution plan for a query to inspect index usage before running it.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `query` | `str` | — | The SELECT query to explain |

```
── explain_query ─────────────────────────────────────────────────────────────────

  EXPLAIN SELECT * FROM deals WHERE organization_id = 42

  ┏━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┓
  ┃ type  ┃ key         ┃ ref               ┃ rows ┃ Extra    ┃
  ┡━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━┩
  │ ref   │ idx_org_id  │ const             │   14 │          │
  └───────┴─────────────┴───────────────────┴──────┴──────────┘

  1 row · 12ms
```

A `type` of `ALL` with a high `rows` estimate means a full table scan — use filtering or check indexes with `describe_table` first.

---

## Semantic

These tools read from `config/semantic_schema.json`. They return empty/hint responses if the file doesn't exist, so they're always safe to call.

### `get_database_context`

Return a full business mental model of the database: what it's for, the core workflow, business vocabulary, and ready-to-run analytics queries. No parameters.

```
=== vine_marketplace ===

Commercial real estate deal management platform for lenders and borrowers.

Domain: commercial real estate lending
Core workflow: Borrower submits Deal → Lenders review → Term sheet issued → Loan closed

Business Vocabulary
-------------------
  "deal"    → Deals
  "loan"    → Deals
  "lender"  → Lenders
  "sponsor" → Organizations

Common Analytics
----------------
  Deals by status: Active deal pipeline distribution
    SELECT status, COUNT(*) as count FROM Deals GROUP BY status ORDER BY count DESC
  Pipeline by loan type: Volume breakdown by deal category
    SELECT dt.name, COUNT(*) FROM Deals d JOIN DealTypes dt ON ...
```

**Call this first.** It replaces multiple `list_tables` + `describe_table` calls with a single orientation.

---

### `get_table_semantics`

Return business-level context for a specific table: plain-English description, column meanings, tags, and example queries.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `table_name` | `str` | — | Table to get semantic context for |

```
=== Deals ===

Active and historical commercial real estate loan transactions.
Each deal belongs to an organization (the borrower/sponsor) and has a type.

Tags: core, financial, transaction

Column Meanings
---------------
  id                             Unique deal identifier
  organization_id                Borrower/sponsor — FK to Organizations
  dealType_id                    Loan product type — FK to DealTypes
  status                         Current pipeline stage (active, term_sheet, closed, dead)
  created_at                     When the deal entered the system

Common Queries
--------------
  SELECT * FROM Deals WHERE status = 'active' ORDER BY created_at DESC LIMIT 20
```

---

### `search_schema_by_meaning`

Find tables and columns by business term. Searches vocabulary mappings, table descriptions, column meanings, and tags.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `query` | `str` | — | Business term or concept to search for |

```
Results for 'financial':

[table]       Facts
              Financial data points attached to deals (NOI, DSCR, LTV, cap rate)
              tags: financial, analytics

[table]       PfsSheets
              Personal financial statements submitted by borrowers
              tags: financial, compliance

[column]      Deals.loan_amount — Total requested loan value in USD
```

Note: this tool searches the **semantic schema** (your `config/semantic_schema.json`), not the database itself. It finds tables by business vocabulary, not by running SQL `LIKE` queries.
