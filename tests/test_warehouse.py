"""Tests for the DuckDB warehouse layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from shared.logger import get_logger
from warehouse.duckdb.connection import DuckDBConnection
from warehouse.duckdb.models import LoadResult, TableInfo
from warehouse.duckdb.schema import SchemaInferrer
from warehouse.duckdb.warehouse import DuckDBWarehouse


@pytest.fixture()
def logger():
    """Return a test logger."""
    return get_logger("test_warehouse")


@pytest.fixture()
def conn():
    """Return an in-memory DuckDB connection (yields, closes after test)."""
    with DuckDBConnection(":memory:") as c:
        yield c


@pytest.fixture()
def warehouse(conn: DuckDBConnection, logger):
    """Return a DuckDBWarehouse backed by an in-memory connection."""
    return DuckDBWarehouse(connection=conn, logger=logger)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return a small DataFrame for warehouse load tests."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95.5, 87.0, 91.2],
        }
    )


# ── DuckDBConnection tests ────────────────────────────────────────────────────


def test_connection_context_manager() -> None:
    """The context manager must open and close the connection cleanly."""
    with DuckDBConnection(":memory:") as c:
        assert c._conn is not None
        df = c.fetchdf("SELECT 42 AS answer")
        assert df["answer"].iloc[0] == 42

    assert c._conn is None


def test_connection_execute_returns_result() -> None:
    """execute() must return a result that can be fetched."""
    with DuckDBConnection(":memory:") as c:
        rel = c.execute("SELECT 1+1 AS val")
        df = rel.df()
        assert df["val"].iloc[0] == 2


def test_connection_fetchdf_returns_dataframe() -> None:
    """fetchdf() must return a pandas DataFrame."""
    with DuckDBConnection(":memory:") as c:
        df = c.fetchdf("SELECT 'hello' AS word, 99 AS num")
        assert isinstance(df, pd.DataFrame)
        assert df["word"].iloc[0] == "hello"


def test_connection_executemany() -> None:
    """executemany() must insert all rows from params_list."""
    with DuckDBConnection(":memory:") as c:
        c.execute("CREATE TABLE nums (n INTEGER)")
        c.executemany("INSERT INTO nums VALUES (?)", [[1], [2], [3]])
        df = c.fetchdf("SELECT count(*) AS cnt FROM nums")
        assert df["cnt"].iloc[0] == 3


# ── DuckDBWarehouse tests ─────────────────────────────────────────────────────


def test_table_exists_false_initially(warehouse: DuckDBWarehouse) -> None:
    """table_exists() must return False before any table is created."""
    assert warehouse.table_exists("nonexistent_table") is False


def test_load_dataframe_creates_table(
    warehouse: DuckDBWarehouse, sample_df: pd.DataFrame
) -> None:
    """load_dataframe() must create the table and insert the rows."""
    result = warehouse.load_dataframe("test_table", sample_df)

    assert isinstance(result, LoadResult)
    assert result.success is True
    assert result.rows_loaded == len(sample_df)
    assert warehouse.table_exists("test_table") is True

    stored = warehouse.query('SELECT * FROM "main"."test_table"')
    # +1 for the added loaded_at column
    assert len(stored) == len(sample_df)


def test_load_dataframe_append_adds_rows(
    warehouse: DuckDBWarehouse, sample_df: pd.DataFrame
) -> None:
    """Calling load_dataframe twice in append mode must double the row count."""
    warehouse.load_dataframe("append_table", sample_df, mode="append")
    warehouse.load_dataframe("append_table", sample_df, mode="append")

    stored = warehouse.query('SELECT * FROM "main"."append_table"')
    assert len(stored) == len(sample_df) * 2


def test_load_dataframe_overwrite_replaces_rows(
    warehouse: DuckDBWarehouse, sample_df: pd.DataFrame
) -> None:
    """Overwrite mode must replace previous data, not add to it."""
    warehouse.load_dataframe("ow_table", sample_df, mode="append")
    warehouse.load_dataframe("ow_table", sample_df, mode="overwrite")

    stored = warehouse.query('SELECT * FROM "main"."ow_table"')
    assert len(stored) == len(sample_df)


def test_load_parquet_appends(
    warehouse: DuckDBWarehouse,
    sample_df: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """load_parquet() must read the file and append rows to the table."""
    pq_path = tmp_path / "test.parquet"
    sample_df.to_parquet(pq_path, engine="pyarrow", index=False)

    result = warehouse.load_parquet("parquet_table", pq_path)

    assert result.success is True
    assert result.rows_loaded == len(sample_df)
    assert warehouse.table_exists("parquet_table") is True


def test_warehouse_query_returns_df(warehouse: DuckDBWarehouse) -> None:
    """query() must return a DataFrame for arbitrary SQL."""
    df = warehouse.query("SELECT 100 AS num, 'test' AS label")
    assert isinstance(df, pd.DataFrame)
    assert df["num"].iloc[0] == 100


def test_get_table_info_returns_none_for_missing(
    warehouse: DuckDBWarehouse,
) -> None:
    """get_table_info() must return None if the table does not exist."""
    assert warehouse.get_table_info("does_not_exist") is None


def test_get_table_info_returns_metadata(
    warehouse: DuckDBWarehouse, sample_df: pd.DataFrame
) -> None:
    """get_table_info() must return accurate column and row count metadata."""
    warehouse.load_dataframe("info_table", sample_df)

    info = warehouse.get_table_info("info_table")

    assert isinstance(info, TableInfo)
    assert info.name == "info_table"
    assert info.row_count == len(sample_df)
    assert len(info.columns) > 0


def test_list_tables_returns_all(
    warehouse: DuckDBWarehouse, sample_df: pd.DataFrame
) -> None:
    """list_tables() must return info for every table in the schema."""
    warehouse.load_dataframe("alpha", sample_df)
    warehouse.load_dataframe("beta", sample_df)

    tables = warehouse.list_tables()
    names = [t.name for t in tables]

    assert "alpha" in names
    assert "beta" in names


def test_create_schema(warehouse: DuckDBWarehouse) -> None:
    """create_schema() must not raise and schema must be queryable."""
    warehouse.create_schema("analytics")
    df = warehouse.query(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name = 'analytics'"
    )
    assert len(df) == 1


def test_register_parquet_view(
    warehouse: DuckDBWarehouse,
    sample_df: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """register_parquet_view() must create a queryable virtual view."""
    pq_path = tmp_path / "view_source.parquet"
    sample_df.to_parquet(pq_path, engine="pyarrow", index=False)

    warehouse.register_parquet_view("raw_view", str(pq_path))

    result = warehouse.query("SELECT * FROM raw_view")
    assert len(result) == len(sample_df)


# ── SchemaInferrer tests ──────────────────────────────────────────────────────


def test_schema_inferrer_maps_types() -> None:
    """SchemaInferrer must map standard pandas dtypes to DuckDB types."""
    inferrer = SchemaInferrer()

    df = pd.DataFrame(
        {
            "name": pd.Series(["a"], dtype="object"),
            "count": pd.Series([1], dtype="int64"),
            "score": pd.Series([1.0], dtype="float64"),
            "ts": pd.to_datetime(["2024-01-01"]),
        }
    )

    mapping = inferrer.infer_from_df(df)

    assert mapping["name"] == "VARCHAR"
    assert mapping["count"] == "BIGINT"
    assert mapping["score"] == "DOUBLE"
    assert mapping["ts"] == "TIMESTAMP"


def test_schema_inferrer_build_create_table_sql() -> None:
    """build_create_table_sql() must produce valid CREATE TABLE SQL."""
    inferrer = SchemaInferrer()
    df = pd.DataFrame({"id": pd.Series([1], dtype="int64"), "label": ["x"]})

    sql = inferrer.build_create_table_sql("my_table", df)

    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "my_table" in sql
    assert "BIGINT" in sql
    assert "VARCHAR" in sql
