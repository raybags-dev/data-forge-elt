{% docs __overview__ %}

# DataForge dbt Project

**DataForge** is a production-quality ELT pipeline that ingests content from Reddit, Steam, IMDb, and a news aggregator into a DuckDB warehouse, then transforms that raw data into analytics-ready marts using dbt.

---

## Architecture

```
Raw Sources (DuckDB main schema)
        │
        ▼
  ┌─────────────┐
  │   Staging   │  Views — clean, standardize, rename
  └─────────────┘
        │
        ▼
  ┌──────────────┐
  │ Intermediate │  Ephemeral — enrich, union, derive
  └──────────────┘
        │
        ▼
  ┌────────────────────────────┐
  │       Marts / Core         │  Tables — dimensions + facts
  │  dim_sources               │
  │  dim_content_types         │
  │  fct_content               │
  │  fct_engagement_metrics    │
  └────────────────────────────┘
        │
        ▼
  ┌────────────────────────────┐
  │    Marts / Analytics       │  Tables — reporting aggregates
  │  rpt_top_content_by_source │
  │  rpt_content_freshness     │
  │  rpt_daily_ingestion_summary│
  └────────────────────────────┘
        │
        ▼
  ┌─────────────┐   ┌──────────────────┐
  │ Incremental │   │    Snapshots      │
  │ incr_content│   │ scd_steam_prices  │
  │ _events     │   │ scd_reddit_scores │
  └─────────────┘   └──────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Intermediate as ephemeral | Avoids materializing temporary work tables; keeps the warehouse lean |
| Staging as views | Ensures freshness — staging always reflects the current raw layer |
| Facts as tables | Query performance for large aggregation workloads |
| Surrogate keys via dbt_utils | Deterministic, portable MD5-based keys |
| SCD Type 2 snapshots | Preserves price and score history without modifying source tables |
| Incremental unique_key | Enables safe re-runs without creating duplicates |

---

## dbt Features Used

- **Sources** — with freshness thresholds (`warn_after`, `error_after`)
- **Refs** — full DAG dependency resolution
- **Seeds** — reference data for categories and source metadata
- **Macros** — `normalize_text`, `clean_html`, `safe_cast`, `trim_strings`, `calculate_growth`, `generate_surrogate_key`
- **Generic tests** — `unique`, `not_null`, `accepted_values`, `relationships`, `positive_score`, `not_future_date`
- **Singular tests** — referential integrity and uniqueness checks
- **Snapshots** — SCD Type 2 for prices and scores
- **Incremental models** — append-only event log with `is_incremental()` guard
- **Analyses** — exploratory SQL compiled but not materialized
- **dbt_utils** — `generate_surrogate_key`
- **Docs blocks** — this overview and column-level descriptions

{% enddocs %}
