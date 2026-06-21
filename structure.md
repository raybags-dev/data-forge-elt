DataForge/

│
├── app/
│   ├── api/
│   ├── ui/
│   └── services/
│
├── crawlers/
│
│   ├── base/
│   │      crawler.py
│   │      browser.py
│   │      retry.py
│   │      rate_limit.py
│   │
│   ├── imdb/
│   ├── steam/
│   ├── reddit/
│   └── news/
│
├── ingestion/
│
│   ├── kaggle/
│   ├── crawler/
│   └── loaders/
│
├── datalake/
│
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── warehouse/
│
│   └── duckdb/
│
├── dbt/
│
│   ├── macros/
│   ├── models/
│   │
│   │     ├── staging/
│   │     ├── intermediate/
│   │     ├── marts/
│   │     ├── incremental/
│   │     ├── snapshots/
│   │     ├── seeds/
│   │     ├── tests/
│   │     └── analyses/
│   │
│   ├── snapshots/
│   ├── tests/
│   └── target/
│
├── dashboard/
│
│      streamlit_app.py
│
├── orchestration/
│
│      pipeline.py
│      scheduler.py
│
├── shared/
│
│      logger.py
│      notifier.py
│      config.py
│      metrics.py
│      retry.py
│
├── docker/
│
├── tests/
│
├── scripts/
│
├── docs/
│
└── README.md


PIPELINE:
            Live Website
                  │

          Playwright Crawler

                  │

             Pandas Cleanup

                  │

          Save Raw Parquet

                  │

         Bronze Data Lake Layer

                  │

         Silver Data Lake Layer

                  │

             DuckDB Import

                  │

              dbt Sources

                  │

            dbt Staging

                  │

        dbt Intermediate Models

                  │

         dbt Incremental Models

                  │

            dbt Mart Tables

                  │

          dbt Tests Execute

                  │

      dbt Documentation Build

                  │

         Streamlit Dashboard

                  │

         Discord Notification


WORKFLOW:

python pipeline.py

    ↓

Download dataset

    ↓

Validate

    ↓

Save parquet

    ↓

Load DuckDB

    ↓

Run dbt

    ↓

Run tests

    ↓

Generate docs

    ↓

Refresh dashboard

    ↓

Send notification

========== DEVELOPMENT ROADMAP=========

Phase 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Repository
Configuration
Logging
Retry
Notifications
Settings

↓

Phase 2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Crawler Framework
Kaggle Framework

↓

Phase 3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Data Lake
Parquet Storage
DuckDB

↓

Phase 4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dbt Project

↓

Phase 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dashboard

↓

Phase 6
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UI

↓

Phase 7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM Assistant

=================================

DataForge/

│
├── app/
│
├── config/
│
│     settings.py
│
├── shared/
│
│     logger.py
│
│     retry.py
│
│     notifier.py
│
│     exceptions.py
│
│     utils.py
│
├── logs/
│
├── tests/
│
├── crawlers/
│
├── ingestion/
│
├── datalake/
│
├── warehouse/
│
├── dbt/
│
├── dashboard/
│
├── orchestration/
│
├── requirements.txt
│
├── .env
│
└── README.md

===========================