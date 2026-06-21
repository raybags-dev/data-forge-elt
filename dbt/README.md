# DataForge dbt Project

Production-quality dbt project transforming raw crawled data into analytics-ready marts using dbt-duckdb.

## Quick Start

```bash
# Install dependencies
dbt deps

# Seed reference data
dbt seed

# Run all models
dbt run

# Run tests
dbt test

# Generate docs
dbt docs generate && dbt docs serve
```

## Project Structure

| Layer | Materialization | Purpose |
|---|---|---|
| `staging` | view | Clean and standardize raw sources |
| `intermediate` | ephemeral | Business logic and enrichment |
| `marts/core` | table | Dimensions and facts |
| `marts/analytics` | table | Reporting and BI-ready aggregates |
| `incremental` | incremental | Append-only event tables |
| `snapshots` | snapshot | SCD Type 2 history tracking |

## Sources

- **Reddit** — posts, scores, engagement
- **Steam** — game metadata and pricing
- **IMDb** — title ratings and metadata
- **News** — article freshness and volume

## Key Features Demonstrated

- Source definitions with freshness checks
- Custom generic and singular tests
- Jinja macros (normalize_text, clean_html, safe_cast, calculate_growth)
- Incremental models with `is_incremental()` guard
- SCD Type 2 snapshots
- dbt_utils package integration
- Seeds for reference data
- Analyses for exploratory SQL
- Full column-level documentation
