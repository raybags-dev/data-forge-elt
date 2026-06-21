"""DataForge ELT — Production Streamlit Dashboard.

Provides an interactive overview of pipeline runs, crawler status,
warehouse tables, dbt results, and log streaming.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ── Page configuration (must be first Streamlit call) ─────────────────────────
st.set_page_config(
    page_title="DataForge ELT",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
_API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:8000")
_LOG_PATH: Path = Path(os.environ.get("LOG_PATH", "./logs/pipeline.log"))
_DATALAKE_PATH: Path = Path(os.environ.get("DATALAKE_PATH", "./datalake"))
_SCREENSHOTS_PATH: Path = Path(os.environ.get("SCREENSHOTS_PATH", "./logs/screenshots"))
_CACHE_TTL: int = 300  # 5 minutes
_LOG_TAIL_LINES: int = 200


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _api_get(path: str) -> Any:
    """Perform a GET request against the FastAPI backend.

    Returns the parsed JSON body, or None on any error.

    Args:
        path: URL path relative to the API base, e.g. ``/api/v1/pipeline/runs``.
    """
    try:
        import httpx

        url = f"{_API_BASE_URL}{path}"
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _api_post(path: str, body: dict | None = None) -> Any:
    """Perform a POST request against the FastAPI backend.

    Args:
        path: URL path relative to the API base.
        body: Optional JSON payload.
    """
    try:
        import httpx

        url = f"{_API_BASE_URL}{path}"
        resp = httpx.post(url, json=body or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


# ── Cached data loaders ────────────────────────────────────────────────────────

@st.cache_data(ttl=_CACHE_TTL)
def _load_pipeline_runs() -> list[dict]:
    """Fetch pipeline run records from the API."""
    data = _api_get("/api/v1/pipeline/runs")
    return data if isinstance(data, list) else []


@st.cache_data(ttl=_CACHE_TTL)
def _load_crawler_status() -> list[dict]:
    """Fetch crawler status records from the API."""
    data = _api_get("/api/v1/crawl/status")
    return data if isinstance(data, list) else []


@st.cache_data(ttl=_CACHE_TTL)
def _load_datasets() -> list[dict]:
    """Fetch dataset metadata from the API."""
    data = _api_get("/api/v1/datasets")
    return data if isinstance(data, list) else []


@st.cache_data(ttl=_CACHE_TTL)
def _load_warehouse_tables() -> list[dict]:
    """Fetch DuckDB table list from the API."""
    data = _api_get("/api/v1/datasets/tables")
    return data if isinstance(data, list) else []


@st.cache_data(ttl=_CACHE_TTL)
def _load_dbt_results() -> dict:
    """Fetch latest dbt test results from the API."""
    data = _api_get("/api/v1/dbt/results")
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=_CACHE_TTL)
def _load_logs(level_filter: str = "ALL") -> list[str]:
    """Read the last N lines from the pipeline log file.

    Args:
        level_filter: One of ALL, INFO, WARNING, ERROR.
    """
    if not _LOG_PATH.exists():
        return ["[No log file found]"]
    try:
        lines = _LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-_LOG_TAIL_LINES:]
        if level_filter == "ALL":
            return tail
        return [ln for ln in tail if level_filter.upper() in ln.upper()]
    except Exception as exc:
        return [f"[Error reading log: {exc}]"]


# ── KPI helpers ────────────────────────────────────────────────────────────────

def _compute_kpis(runs: list[dict], datasets: list[dict]) -> dict:
    """Derive top-level KPI values from loaded data.

    Args:
        runs: Pipeline run records.
        datasets: Dataset metadata records.
    """
    total_datasets = len(datasets)
    total_rows = sum(int(d.get("row_count", 0)) for d in datasets)
    last_run = runs[0].get("started_at", "—") if runs else "—"

    # Freshness: ratio of datasets updated in last 24 h
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    fresh = 0
    for d in datasets:
        updated = d.get("updated_at") or d.get("created_at")
        if updated:
            try:
                ts = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
                if (now - ts).total_seconds() < 86400:
                    fresh += 1
            except Exception:
                pass
    freshness = round(fresh / total_datasets * 100) if total_datasets else 0

    return {
        "total_datasets": total_datasets,
        "total_rows": total_rows,
        "last_run": last_run,
        "freshness": freshness,
    }


# ── Page renderers ─────────────────────────────────────────────────────────────

def _render_overview() -> None:
    """Render the Overview page with KPIs and charts."""
    st.header("Overview")

    runs = _load_pipeline_runs()
    datasets = _load_datasets()
    kpis = _compute_kpis(runs, datasets)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Datasets", kpis["total_datasets"])
    c2.metric("Total Rows", f"{kpis['total_rows']:,}")
    c3.metric("Last Pipeline Run", kpis["last_run"])
    c4.metric("Freshness Score", f"{kpis['freshness']}%")

    st.divider()
    _render_ingestion_timeline(runs)
    _render_source_pie(datasets)


def _render_ingestion_timeline(runs: list[dict]) -> None:
    """Render the ingestion timeline chart.

    Args:
        runs: Pipeline run records.
    """
    st.subheader("Ingestion Timeline")
    if not runs:
        st.info("No pipeline runs recorded yet.")
        return

    import plotly.express as px

    df = pd.DataFrame(runs)
    if "started_at" not in df.columns or "rows_processed" not in df.columns:
        st.info("Timeline data unavailable — run a pipeline first.")
        return

    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce")
    df = df.dropna(subset=["started_at"])
    fig = px.line(
        df.sort_values("started_at"),
        x="started_at",
        y="rows_processed",
        title="Rows Processed Over Time",
        labels={"started_at": "Time", "rows_processed": "Rows"},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_source_pie(datasets: list[dict]) -> None:
    """Render the source distribution pie chart.

    Args:
        datasets: Dataset metadata records.
    """
    st.subheader("Source Distribution")
    if not datasets:
        st.info("No datasets loaded yet.")
        return

    import plotly.express as px

    df = pd.DataFrame(datasets)
    if "source" not in df.columns or "row_count" not in df.columns:
        st.info("Source distribution data unavailable.")
        return

    grouped = df.groupby("source")["row_count"].sum().reset_index()
    fig = px.pie(grouped, names="source", values="row_count", title="Rows by Source")
    st.plotly_chart(fig, use_container_width=True)


def _status_badge_html(status: str) -> str:
    """Return an HTML badge string for a pipeline status value.

    Args:
        status: One of 'success', 'failed', 'running', or any other string.
    """
    colours = {
        "success": "#28a745",
        "failed": "#dc3545",
        "running": "#007bff",
    }
    colour = colours.get(status.lower(), "#6c757d")
    return (
        f'<span style="background:{colour};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.85em;">{status}</span>'
    )


def _render_pipeline_page() -> None:
    """Render the Pipeline page."""
    st.header("Pipeline Runs")

    runs = _load_pipeline_runs()
    if not runs:
        st.info("No pipeline runs found. Trigger a run via the API or CLI.")
        return

    df = pd.DataFrame(runs)
    display_cols = [c for c in ["run_id", "status", "duration", "rows_processed", "started_at"] if c in df.columns]

    st.subheader("Run History")
    for _, row in df[display_cols].iterrows():
        cols = st.columns(len(display_cols))
        for i, col_name in enumerate(display_cols):
            val = row[col_name]
            if col_name == "status":
                cols[i].markdown(_status_badge_html(str(val)), unsafe_allow_html=True)
            else:
                cols[i].write(val)

    _render_recent_errors(runs)


def _render_recent_errors(runs: list[dict]) -> None:
    """Show recent error messages from pipeline runs.

    Args:
        runs: Pipeline run records.
    """
    errors = [r for r in runs if str(r.get("status", "")).lower() == "failed"]
    if not errors:
        return
    st.subheader("Recent Errors")
    for run in errors[:5]:
        st.error(
            f"Run `{run.get('run_id', '?')}` failed at "
            f"{run.get('started_at', '?')}: {run.get('error', 'Unknown error')}"
        )


def _render_crawler_page() -> None:
    """Render the Crawler page."""
    st.header("Crawler Status")

    statuses = _load_crawler_status()
    if not statuses:
        st.info("No crawler data yet. Start a crawl to populate this view.")
    else:
        df = pd.DataFrame(statuses)
        st.dataframe(df, use_container_width=True)
        _render_error_rate_chart(df)

    _render_screenshots_gallery()


def _render_error_rate_chart(df: pd.DataFrame) -> None:
    """Bar chart of error rates per crawler source.

    Args:
        df: DataFrame with crawler status rows.
    """
    if "source" not in df.columns or "error_rate" not in df.columns:
        return
    import plotly.express as px

    fig = px.bar(df, x="source", y="error_rate", title="Error Rate by Source (%)")
    st.plotly_chart(fig, use_container_width=True)


def _render_screenshots_gallery() -> None:
    """Display crawler screenshots from the screenshots directory."""
    st.subheader("Screenshots")
    if not _SCREENSHOTS_PATH.exists():
        st.info("No screenshots directory found.")
        return
    images = sorted(_SCREENSHOTS_PATH.glob("*.png"))
    if not images:
        st.info("No screenshots captured yet.")
        return
    cols = st.columns(3)
    for i, img_path in enumerate(images[:9]):
        cols[i % 3].image(str(img_path), caption=img_path.name, use_container_width=True)


def _render_warehouse_page() -> None:
    """Render the Warehouse page."""
    st.header("DuckDB Warehouse")

    tables = _load_warehouse_tables()
    if not tables:
        st.info("No warehouse tables found. Load data first.")
        return

    df = pd.DataFrame(tables)
    st.subheader("Tables")
    st.dataframe(df, use_container_width=True)

    _render_table_preview(df)


def _render_table_preview(tables_df: pd.DataFrame) -> None:
    """Show first 100 rows of a selected warehouse table.

    Args:
        tables_df: DataFrame listing available tables.
    """
    st.subheader("Table Preview")
    if "name" not in tables_df.columns:
        return

    table_name = st.selectbox("Select table", tables_df["name"].tolist())
    if not table_name:
        return

    preview_data = _api_get(f"/api/v1/datasets/preview/{table_name}?limit=100")
    if preview_data is None:
        st.info(f"Could not load preview for {table_name}.")
        return

    rows = preview_data if isinstance(preview_data, list) else preview_data.get("rows", [])
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("Table is empty.")


def _render_dbt_page() -> None:
    """Render the dbt page with test results and model lineage."""
    st.header("dbt")

    results = _load_dbt_results()
    _render_dbt_test_summary(results)
    _render_dbt_lineage()
    _render_dbt_actions()


def _render_dbt_test_summary(results: dict) -> None:
    """Display dbt test pass/fail counts.

    Args:
        results: dbt result dict from the API.
    """
    st.subheader("Test Results")
    if not results:
        st.info("No dbt results available yet.")
        return

    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    total = passed + failed
    c1, c2, c3 = st.columns(3)
    c1.metric("Passed", passed)
    c2.metric("Failed", failed)
    c3.metric("Total Tests", total)


def _render_dbt_lineage() -> None:
    """Render a static mermaid model lineage diagram."""
    st.subheader("Model Lineage")
    mermaid = """
```mermaid
graph LR
    A[stg_reddit_posts] --> B[int_reddit_posts_enriched]
    C[stg_steam_games] --> D[int_steam_games_enriched]
    E[stg_imdb_titles] --> F[int_content_unified]
    G[stg_news_articles] --> F
    B --> F
    D --> F
    F --> H[fct_content]
    F --> I[fct_engagement_metrics]
    H --> J[rpt_daily_ingestion_summary]
    H --> K[rpt_top_content_by_source]
    H --> L[rpt_content_freshness]
```
"""
    st.markdown(mermaid)


def _render_dbt_actions() -> None:
    """Render dbt build and test action buttons."""
    st.subheader("Actions")
    col1, col2 = st.columns(2)
    if col1.button("Run dbt build", type="primary"):
        with st.spinner("Running dbt build…"):
            result = _api_post("/api/v1/dbt/build")
        if "error" in result:
            st.error(f"dbt build failed: {result['error']}")
        else:
            st.success("dbt build completed successfully.")
            st.cache_data.clear()

    if col2.button("Run dbt test"):
        with st.spinner("Running dbt test…"):
            result = _api_post("/api/v1/dbt/test")
        if "error" in result:
            st.error(f"dbt test failed: {result['error']}")
        else:
            st.success("dbt test completed successfully.")
            st.cache_data.clear()


def _render_logs_page() -> None:
    """Render the Logs page with filtering and auto-refresh."""
    st.header("Logs")

    col_level, col_refresh = st.columns([3, 1])
    with col_level:
        level = st.selectbox("Level filter", ["ALL", "INFO", "WARNING", "ERROR"])
    with col_refresh:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)

    if auto_refresh:
        import time

        st.caption(f"Last refreshed: {time.strftime('%H:%M:%S')}")
        st.experimental_rerun() if False else None  # hook for future polling

    lines = _load_logs(level_filter=level)
    log_text = "\n".join(lines)

    st.text_area(
        label="Pipeline Log",
        value=log_text,
        height=500,
        disabled=True,
    )

    if auto_refresh:
        import time

        time.sleep(30)
        st.cache_data.clear()
        st.rerun()


# ── Sidebar navigation ─────────────────────────────────────────────────────────

def _render_sidebar() -> str:
    """Render the sidebar navigation and return the selected page name.

    Returns:
        The navigation page name selected by the user.
    """
    with st.sidebar:
        st.title("DataForge ELT")
        st.caption("Production ELT Dashboard")
        st.divider()
        page = st.radio(
            "Navigate",
            ["Overview", "Pipeline", "Crawler", "Warehouse", "dbt", "Logs"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption(f"API: {_API_BASE_URL}")
    return str(page)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the DataForge ELT Streamlit dashboard."""
    page = _render_sidebar()

    if page == "Overview":
        _render_overview()
    elif page == "Pipeline":
        _render_pipeline_page()
    elif page == "Crawler":
        _render_crawler_page()
    elif page == "Warehouse":
        _render_warehouse_page()
    elif page == "dbt":
        _render_dbt_page()
    elif page == "Logs":
        _render_logs_page()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs this module at import time
    main()
