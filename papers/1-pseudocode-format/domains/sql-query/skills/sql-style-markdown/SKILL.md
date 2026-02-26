---
name: sql-style
description: Write dbt-style analytics pipelines as multi-file SQL models. Use when generating analytics SQL that follows data-team conventions for staging, intermediate, and mart layers.
---

# dbt Analytics SQL Style Guide

Write clean, modular analytics SQL as a pipeline of dbt model files. Each file is one logical step. Clarity and convention adherence beat cleverness.

## Pipeline Structure

### Layer Naming Conventions

Every model file must follow a naming prefix that indicates its layer:

| Prefix | Layer | Purpose | Example |
|--------|-------|---------|---------|
| `stg_` | Staging | 1:1 with source tables, light renaming/casting | `stg_orders.sql` |
| `int_` | Intermediate | Business logic: dedup, enrichment, joins | `int_deduped_returns.sql` |
| `fct_` | Fact (mart) | Final aggregated metric tables | `fct_revenue_by_channel.sql` |
| `dim_` | Dimension (mart) | Final descriptive entity tables | `dim_customers.sql` |

### One CTE Per File

Each model file should contain at most **one WITH block** with a single CTE (the `source` or `renamed` step), then the main SELECT. Do not nest multiple CTEs in one file — split into separate model files instead.

```sql
-- models/staging/stg_orders.sql
WITH source AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        status
    FROM {{ ref('raw_orders') }}
)
SELECT
    order_id,
    customer_id,
    order_date,
    status
FROM source
```

### Jinja `ref()` References

Models must reference their upstream dependencies using `{{ ref('model_name') }}`:

```sql
-- models/intermediate/int_deduped_channels.sql
WITH source AS (
    SELECT
        customer_id,
        channel,
        attributed_at,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY attributed_at ASC
        ) AS row_num
    FROM {{ ref('stg_customer_channels') }}
)
SELECT
    customer_id,
    channel
FROM source
WHERE row_num = 1
```

Never use raw table names in intermediate or mart models — always `{{ ref() }}`.

## SQL Formatting Rules

### Keyword Conventions

All SQL keywords UPPERCASE. Table/column names and aliases remain lowercase.

Keywords include: `SELECT`, `FROM`, `WHERE`, `JOIN`, `LEFT JOIN`, `ON`, `GROUP BY`, `ORDER BY`, `HAVING`, `LIMIT`, `WITH`, `AS`, `AND`, `OR`, `IN`, `BETWEEN`, `CASE`, `WHEN`, `THEN`, `ELSE`, `END`, `OVER`, `PARTITION BY`, `ROWS`, `RANGE`, `PRECEDING`, `FOLLOWING`, `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `DENSE_RANK`, `ROW_NUMBER`, `DATE_TRUNC`, `EXTRACT`, `COALESCE`, `ASC`, `DESC`.

### Clause Layout

One major clause per line — never two clauses on the same line:
```sql
SELECT
    c.name,
    SUM(t.amount) AS total_revenue
FROM {{ ref('stg_customers') }} c
LEFT JOIN {{ ref('stg_transactions') }} t
    ON t.customer_id = c.customer_id
GROUP BY c.name
ORDER BY total_revenue DESC
```

## Aliasing

### Table Aliases
Always alias tables: `customers c`, `transactions t`, `order_items oi`. Use the alias consistently throughout the query.

### Column Aliases
All computed/aggregated columns must use `AS` with a descriptive name:
- Good: `SUM(t.amount) AS total_revenue`, `COUNT(*) AS order_count`
- Bad: `SUM(t.amount)` (no alias), `SUM(t.amount) AS s` (meaningless)

## Column Selection

**No SELECT *** — always list specific columns. This applies inside CTEs too.

## Comment Headers

Every model file starts with a `--` comment describing its purpose:
```sql
-- Deduplicate customer_channels to primary attribution (earliest per customer)
WITH source AS (
    ...
)
```

## Analytics Join Convention

### LEFT JOIN Only

In analytics pipelines, always use `LEFT JOIN` — never `INNER JOIN`. This preserves all rows from the driving table and prevents silent data loss when dimension tables have missing records.

```sql
-- GOOD: preserves all transactions even if store is missing
FROM {{ ref('stg_transactions') }} t
LEFT JOIN {{ ref('stg_stores') }} s
    ON s.store_id = t.store_id

-- BAD: silently drops transactions with missing stores
FROM {{ ref('stg_transactions') }} t
INNER JOIN {{ ref('stg_stores') }} s
    ON s.store_id = t.store_id
```

## Handling Nullable Dimensions

### COALESCE to '(unknown)'

When joining to dimension tables that may have missing records (LEFT JOIN), wrap nullable dimension columns with `COALESCE(..., '(unknown)')`:

```sql
SELECT
    COALESCE(s.city, '(unknown)') AS city,
    COALESCE(ch.channel, '(unknown)') AS channel,
    SUM(t.amount) AS total_revenue
FROM {{ ref('stg_transactions') }} t
LEFT JOIN {{ ref('stg_stores') }} s
    ON s.store_id = t.store_id
LEFT JOIN {{ ref('int_deduped_channels') }} ch
    ON ch.customer_id = t.customer_id
GROUP BY
    COALESCE(s.city, '(unknown)'),
    COALESCE(ch.channel, '(unknown)')
```

Always use the exact string `'(unknown)'` — not `'Unknown'`, `'N/A'`, `NULL`, or `'Other'`.

## Deduplication Pattern

### ROW_NUMBER Before Aggregation

When source data has duplicates, deduplicate in an intermediate model using ROW_NUMBER before any aggregation:

```sql
-- models/intermediate/int_deduped_billing.sql
WITH source AS (
    SELECT
        subscription_id,
        event_month,
        amount,
        ROW_NUMBER() OVER (
            PARTITION BY subscription_id, event_month
            ORDER BY event_id DESC
        ) AS row_num
    FROM {{ ref('stg_billing_events') }}
)
SELECT
    subscription_id,
    event_month,
    amount
FROM source
WHERE row_num = 1
```

Never deduplicate inline within an aggregation query — always create a separate intermediate model.

## Quick Checklist

Before submitting, verify each model file:
- [ ] All SQL keywords are UPPERCASE
- [ ] One major clause per line
- [ ] Tables aliased with short meaningful names
- [ ] Computed columns have AS alias with descriptive name
- [ ] No SELECT *
- [ ] Comment header describing the model
- [ ] LEFT JOIN only (no INNER JOIN)
- [ ] COALESCE nullable dimensions to '(unknown)'
- [ ] ROW_NUMBER dedup in dedicated intermediate model
- [ ] One CTE per file (single WITH block)

Across all model files:
- [ ] Jinja `{{ ref('model_name') }}` references between models
- [ ] Layer naming: stg_, int_, fct_/dim_ prefixes
