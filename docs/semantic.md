# Semantic Layer

The semantic layer is an optional JSON file that attaches business meaning to your database schema. Without it, dbsage works fine — the LLM can still explore and query. With it, the LLM understands your database the way a domain expert would.

**File location:** `config/semantic_schema.json`

---

## Why it exists

LLMs are good at SQL but bad at guessing. A column named `status` could mean anything. A table named `facts` tells you nothing. The semantic layer solves this by giving the LLM a business vocabulary before it writes a single query.

The practical difference: with a well-populated semantic schema, `get_database_context()` replaces 6–10 exploratory tool calls with one. Claude knows what "deal", "lender", and "closed" mean in your domain without having to sample and infer.

---

## Minimal viable setup

You don't need to fill in everything to get value. Even a small file makes a measurable difference.

**5-minute version:**

```json
{
  "database": {
    "name": "your_db",
    "description": "One sentence: what this database is for."
  },
  "vocabulary": {
    "customer": "users",
    "order": "orders"
  }
}
```

That's it. Claude will now know what "customer" and "order" map to, and `get_database_context()` will return your description instead of a blank page.

---

## Full schema reference

Every field is optional. Add only what's useful.

```json
{
  "database": {
    "name": "your_db",
    "description": "What this database represents in plain English.",
    "domain": "Short label for the business domain (e.g. e-commerce, fintech, SaaS)",
    "core_workflow": "The main business process as a flow: A → B → C"
  },

  "vocabulary": {
    "business_term": "ActualTableName",
    "customer":      "users",
    "purchase":      "orders",
    "item":          "products"
  },

  "tables": {
    "TableName": {
      "description": "Plain-English description of what this table stores.",
      "tags": ["core", "financial", "lookup"],
      "columns": {
        "column_name": "What this column means in business terms.",
        "status":      "Pipeline stage: active, term_sheet, closed, dead"
      },
      "common_queries": [
        "SELECT * FROM TableName WHERE status = 'active' LIMIT 20"
      ]
    }
  },

  "common_analytics": [
    {
      "name": "Short name for this query",
      "description": "What question this answers",
      "sql": "SELECT ..."
    }
  ]
}
```

### Field guide

| Field | Description |
|---|---|
| `database.name` | Used as the header in `get_database_context()` output |
| `database.description` | The elevator pitch — what does this database store and why? |
| `database.domain` | Business domain label. Helps Claude frame its understanding. |
| `database.core_workflow` | The main operational flow. Gives Claude causal context. |
| `vocabulary` | Maps business terms to table names. Powers `search_schema_by_meaning`. |
| `tables[T].description` | What this table stores, in business terms. |
| `tables[T].tags` | Free-form labels. Searchable via `search_schema_by_meaning`. |
| `tables[T].columns[C]` | Column meaning. More useful than "VARCHAR NOT NULL". |
| `tables[T].common_queries` | Ready-to-run SQL surfaced by `get_database_context()`. |
| `common_analytics` | Database-wide analytics queries. Best candidates for frequent questions. |

---

## Before and after

### Without semantic layer

```
User: "What's the total loan value of active deals?"

Claude: Let me explore the schema.
  → list_tables()              # find relevant tables
  → describe_table("deals")   # understand columns
  → sample_column_values("deals", "status")  # learn what 'active' means
  → describe_table("deal_types")  # understand the FK
  → run_read_only_query(...)   # finally run the query
```

**5 tool calls** just to understand the schema.

### With semantic layer

```
User: "What's the total loan value of active deals?"

Claude: Let me check the database context.
  → get_database_context()   # full picture in one call
  → run_read_only_query(...)  # run the query
```

**2 tool calls.** Claude already knew "deal" → `Deals`, "active" is a `status` value, and `loan_amount` is the column it needs.

---

## Domain templates

### E-commerce

```json
{
  "database": {
    "name": "storefront",
    "description": "Online retail platform — products, customers, and orders.",
    "domain": "e-commerce",
    "core_workflow": "Customer browses Products → adds to Cart → places Order → fulfillment tracked"
  },
  "vocabulary": {
    "customer": "users",
    "purchase": "orders",
    "item": "products",
    "cart": "cart_items"
  },
  "tables": {
    "users": {
      "description": "Registered customer accounts.",
      "tags": ["core", "auth"],
      "columns": {
        "id": "Unique customer identifier (UUID)",
        "email": "Login email — also used for transactional emails",
        "created_at": "Account creation date"
      }
    },
    "orders": {
      "description": "Completed purchase transactions.",
      "tags": ["core", "transaction"],
      "columns": {
        "id": "Unique order ID",
        "user_id": "FK to users — who placed the order",
        "total_cents": "Order total in cents (divide by 100 for USD)",
        "status": "fulfillment state: pending, shipped, delivered, returned"
      },
      "common_queries": [
        "SELECT DATE(created_at) as day, COUNT(*) as orders, SUM(total_cents)/100 as revenue FROM orders WHERE status != 'returned' GROUP BY day ORDER BY day DESC LIMIT 30"
      ]
    }
  },
  "common_analytics": [
    {
      "name": "Revenue by day",
      "description": "Daily GMV for the last 30 days",
      "sql": "SELECT DATE(created_at) as day, SUM(total_cents)/100 as revenue FROM orders WHERE status != 'returned' GROUP BY day ORDER BY day DESC LIMIT 30"
    }
  ]
}
```

---

### SaaS

```json
{
  "database": {
    "name": "saas_platform",
    "description": "B2B SaaS platform — organizations, users, subscriptions, and usage.",
    "domain": "SaaS",
    "core_workflow": "Organization signs up → Users invited → Subscription created → Usage tracked"
  },
  "vocabulary": {
    "customer": "organizations",
    "account": "organizations",
    "seat": "memberships",
    "plan": "subscriptions"
  },
  "tables": {
    "organizations": {
      "description": "Customer accounts (companies). Each org has one subscription.",
      "tags": ["core", "billing"],
      "columns": {
        "id": "Unique org ID",
        "name": "Company name",
        "created_at": "When the org signed up (trial start)"
      }
    },
    "subscriptions": {
      "description": "Active billing plans for each organization.",
      "tags": ["billing", "financial"],
      "columns": {
        "organization_id": "FK to organizations",
        "plan": "Plan tier: starter, growth, enterprise",
        "mrr_cents": "Monthly recurring revenue in cents",
        "status": "active, trialing, cancelled, past_due"
      }
    }
  },
  "common_analytics": [
    {
      "name": "MRR by plan",
      "description": "Monthly recurring revenue breakdown by plan tier",
      "sql": "SELECT plan, COUNT(*) as customers, SUM(mrr_cents)/100 as mrr FROM subscriptions WHERE status = 'active' GROUP BY plan ORDER BY mrr DESC"
    },
    {
      "name": "Churn this month",
      "description": "Subscriptions cancelled in the current month",
      "sql": "SELECT COUNT(*) as churned FROM subscriptions WHERE status = 'cancelled' AND MONTH(updated_at) = MONTH(NOW()) AND YEAR(updated_at) = YEAR(NOW())"
    }
  ]
}
```

---

### Financial / lending

```json
{
  "database": {
    "name": "lending_platform",
    "description": "Commercial real estate deal management — loans, borrowers, and lenders.",
    "domain": "commercial real estate lending",
    "core_workflow": "Borrower submits Deal → Lenders review → Term sheet → Underwriting → Closed"
  },
  "vocabulary": {
    "deal": "deals",
    "loan": "deals",
    "borrower": "organizations",
    "sponsor": "organizations",
    "lender": "lenders"
  },
  "tables": {
    "deals": {
      "description": "Commercial real estate loan transactions. Each deal has a type and tracks its pipeline stage.",
      "tags": ["core", "financial", "transaction"],
      "columns": {
        "id": "Unique deal ID",
        "organization_id": "Borrower organization — FK to organizations",
        "dealType_id": "Loan product — FK to deal_types",
        "status": "Pipeline stage: prospect, active, term_sheet, underwriting, closed, dead",
        "loan_amount": "Requested loan amount in USD",
        "created_at": "Date deal entered the system"
      },
      "common_queries": [
        "SELECT status, COUNT(*) as count FROM deals GROUP BY status ORDER BY count DESC",
        "SELECT * FROM deals WHERE status = 'active' ORDER BY created_at DESC LIMIT 20"
      ]
    }
  },
  "common_analytics": [
    {
      "name": "Pipeline by stage",
      "description": "How many deals are in each pipeline stage",
      "sql": "SELECT status, COUNT(*) as deals FROM deals GROUP BY status ORDER BY deals DESC"
    },
    {
      "name": "Loan volume by type",
      "description": "Total requested loan amount grouped by loan product",
      "sql": "SELECT dt.name as loan_type, COUNT(d.id) as deals, SUM(d.loan_amount) as volume FROM deals d JOIN deal_types dt ON d.dealType_id = dt.id GROUP BY dt.id ORDER BY volume DESC"
    }
  ]
}
```

---

## Column description tips

Good column descriptions answer the question a new engineer would ask.

| Column | Bad description | Good description |
|---|---|---|
| `status` | "Status of the record" | "Pipeline stage: active, term_sheet, closed, dead" |
| `total_cents` | "Total amount" | "Order total in cents — divide by 100 for USD" |
| `org_id` | "Organization ID" | "FK to organizations — the borrower on this deal" |
| `created_at` | "Created timestamp" | "When the deal entered the system (not necessarily when submitted)" |
| `type` | "Type" | "Loan product: bridge, construction, permanent, mezz" |

The pattern: if the column has an enum or unit, say so. If it has a business nuance (e.g. `created_at` vs when something actually happened), say that.

---

## Vocabulary mapping tips

- Map the **terms your users actually use** to the table names your engineers chose
- Plural and singular both work: `"customer"` and `"customers"` can both map to `users`
- The vocabulary is case-insensitive at search time — `"Lender"`, `"lender"`, `"LENDER"` all match
- One term can only map to one table — if "status" is ambiguous, skip it and rely on table-level descriptions instead
