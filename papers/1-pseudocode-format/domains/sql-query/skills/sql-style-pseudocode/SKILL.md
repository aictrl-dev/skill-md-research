---
name: sql-style-pseudocode
description: Write dbt-style analytics pipelines as multi-file SQL models following data-team conventions.
---

# dbt Analytics SQL Style (Pseudocode)

```python
from dataclasses import dataclass, field
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# CORE TYPES
# ─────────────────────────────────────────────────────────────────────────────

SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN",
    "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "WITH", "AS",
    "AND", "OR", "IN", "BETWEEN", "CASE", "WHEN", "THEN", "ELSE", "END",
    "OVER", "PARTITION BY", "ROWS", "RANGE", "PRECEDING", "FOLLOWING",
    "SUM", "COUNT", "AVG", "MIN", "MAX", "DENSE_RANK", "ROW_NUMBER",
    "DATE_TRUNC", "EXTRACT", "COALESCE", "ASC", "DESC",
}

MAJOR_CLAUSES = [  # Each MUST start on its own line
    "WITH", "SELECT", "FROM", "LEFT JOIN",
    "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT",
]

Layer = Literal["staging", "intermediate", "mart"]

@dataclass
class ModelFile:
    """A single dbt model file in the pipeline."""
    filename: str           # "stg_orders.sql", "int_deduped_billing.sql", "fct_revenue.sql"
    layer: Layer            # Determined by prefix: stg_ = staging, int_ = intermediate, fct_/dim_ = mart
    sql: str                # The SQL content
    references: list[str]   # List of {{ ref('model_name') }} dependencies

    @property
    def prefix(self) -> str:
        """Extract naming prefix: stg_, int_, fct_, dim_."""
        return self.filename.split("_")[0] + "_"

@dataclass
class Pipeline:
    """A dbt-style pipeline of model files."""
    models: list[ModelFile]


# ─────────────────────────────────────────────────────────────────────────────
# LAYER NAMING
# ─────────────────────────────────────────────────────────────────────────────

LAYER_PREFIXES = {
    "staging":      ["stg_"],       # 1:1 with source tables
    "intermediate": ["int_"],       # Business logic: dedup, enrichment
    "mart":         ["fct_", "dim_"],  # Final aggregated/dimension tables
}
# Rule: every model filename MUST start with one of these prefixes

# ─────────────────────────────────────────────────────────────────────────────
# ONE CTE PER FILE
# ─────────────────────────────────────────────────────────────────────────────

# Each .sql file has at most ONE WITH block (single CTE):
#
#   WITH source AS (
#       SELECT ... FROM {{ ref('upstream_model') }}
#   )
#   SELECT ... FROM source
#
# Do NOT nest multiple CTEs in one file — split into separate model files.

# ─────────────────────────────────────────────────────────────────────────────
# JINJA ref() REFERENCES
# ─────────────────────────────────────────────────────────────────────────────

# Intermediate and mart models MUST reference upstream via {{ ref('model_name') }}:
#
#   FROM {{ ref('stg_orders') }}
#   LEFT JOIN {{ ref('int_deduped_returns') }}
#
# Never use raw table names except in staging models.

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS JOIN CONVENTION
# ─────────────────────────────────────────────────────────────────────────────

# ALWAYS LEFT JOIN — never INNER JOIN. Preserves all rows from driving table.
#
#   -- GOOD                                    -- BAD
#   FROM {{ ref('stg_transactions') }} t       FROM {{ ref('stg_transactions') }} t
#   LEFT JOIN {{ ref('stg_stores') }} s        INNER JOIN {{ ref('stg_stores') }} s
#       ON s.store_id = t.store_id                 ON s.store_id = t.store_id

# ─────────────────────────────────────────────────────────────────────────────
# NULLABLE DIMENSION HANDLING
# ─────────────────────────────────────────────────────────────────────────────

# Wrap nullable dimension columns with COALESCE(..., '(unknown)'):
#
#   COALESCE(s.city, '(unknown)') AS city
#   COALESCE(ch.channel, '(unknown)') AS channel
#
# Always use exact string '(unknown)' — not 'Unknown', 'N/A', NULL, 'Other'.

# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICATION PATTERN
# ─────────────────────────────────────────────────────────────────────────────

# Deduplicate in a dedicated int_ model BEFORE aggregation:
#
#   -- int_deduped_billing.sql
#   WITH source AS (
#       SELECT
#           subscription_id,
#           event_month,
#           amount,
#           ROW_NUMBER() OVER (
#               PARTITION BY subscription_id, event_month
#               ORDER BY event_id DESC
#           ) AS row_num
#       FROM {{ ref('stg_billing_events') }}
#   )
#   SELECT subscription_id, event_month, amount
#   FROM source
#   WHERE row_num = 1
#
# Never deduplicate inline within an aggregation query.

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION RULES (14-rule checklist)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PerFileRules:
    """Rules applied to EACH model file. Score = pass rate across files."""
    sql_text: str

    def rule_1_keywords_upper(self) -> tuple[bool, str]:
        """All SQL keywords UPPERCASE. Table/column names lowercase."""
        ...

    def rule_2_clause_per_line(self) -> tuple[bool, str]:
        """One MAJOR_CLAUSES entry per line. Never two on same line."""
        ...

    def rule_3_table_aliases(self) -> tuple[bool, str]:
        """Tables aliased with short meaningful names: t, c, s, oi."""
        ...

    def rule_4_column_aliases(self) -> tuple[bool, str]:
        """Computed/aggregated columns use AS alias (descriptive name)."""
        ...

    def rule_5_no_select_star(self) -> tuple[bool, str]:
        """No SELECT * — always list specific columns."""
        ...

    def rule_6_comment_header(self) -> tuple[bool, str]:
        """First line is -- comment describing the model."""
        ...

    def rule_7_left_join_only(self) -> tuple[bool, str]:
        """LEFT JOIN only — no INNER JOIN in analytics pipelines."""
        ...  # FAIL if INNER JOIN detected

    def rule_8_coalesce_unknown(self) -> tuple[bool, str]:
        """Nullable dims wrapped: COALESCE(col, '(unknown)')."""
        ...  # Check task.nullable_dimension_columns

    def rule_9_row_number_dedup(self) -> tuple[bool, str]:
        """Dedup via ROW_NUMBER before aggregation."""
        ...  # Check task.requires_deduplication

    def rule_10_one_cte_per_file(self) -> tuple[bool, str]:
        """Single WITH block, no nested CTEs."""
        ...  # Count WITH occurrences and CTE names

@dataclass
class CrossFileRules:
    """Rules applied across ALL model files. Binary pass/fail."""
    models: dict[str, str]  # filename -> sql_text
    task: dict

    def rule_11_jinja_ref(self) -> tuple[bool, str]:
        """Non-staging models use {{ ref('model_name') }}."""
        ...  # int_ and fct_ models must contain ref()

    def rule_12_layer_naming(self) -> tuple[bool, str]:
        """stg_ for staging, int_ for intermediate, fct_/dim_ for marts."""
        ...  # All filenames start with valid prefix


# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

# Per-file rules (1-10): Each produces a pass rate across all model files.
#   e.g., 3/4 files pass rule_1 → score contribution = 0.75
#
# Cross-file rules (11-12): Binary 0 or 1.
#
# auto_score = sum(per_file_pass_rates) + sum(cross_file_binary)
# Range: 0-12

# ─────────────────────────────────────────────────────────────────────────────
# 12-RULE CHECKLIST SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

# PER-FILE (10) — applied to each model, score = pass rate
#  1. All SQL keywords UPPERCASE
#  2. One major clause per line
#  3. Tables aliased with short meaningful names
#  4. Computed columns use AS alias
#  5. No SELECT *
#  6. Comment header (-- description)
#  7. LEFT JOIN only (no INNER JOIN)
#  8. COALESCE nullable dims to '(unknown)'
#  9. ROW_NUMBER dedup before aggregation
# 10. One CTE per file (single WITH block)

# CROSS-FILE (2) — applied across all files, binary
# 11. Jinja {{ ref() }} in non-staging models
# 12. Layer naming: stg_, int_, fct_/dim_ prefixes
```

## Usage

1. Construct pipeline as a list of `ModelFile` objects
2. Validate each file with `PerFileRules` (10 per-file rules)
3. Validate pipeline with `CrossFileRules` (4 cross-file rules)
4. Score = sum of per-file pass rates + cross-file binary scores
5. Expected range: 0-14
