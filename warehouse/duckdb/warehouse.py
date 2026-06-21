"""DuckDB warehouse — high-level operations over a DuckDB database."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from warehouse.duckdb.models import LoadResult, TableInfo
from warehouse.duckdb.schema import SchemaInferrer

if TYPE_CHECKING:
    from loguru import Logger

    from warehouse.duckdb.connection import DuckDBConnection


class DuckDBWarehouse:
    """High-level DuckDB warehouse interface.

    Wraps a DuckDBConnection to provide schema management, table loading
    (append / overwrite / incremental), and metadata queries.

    Args:
        connection: DuckDBConnection instance to use for all operations.
        logger: Loguru Logger for structured logging.
    """

    def __init__(
        self,
        connection: "DuckDBConnection",
        logger: "Logger",
    ) -> None:
        self._conn = connection
        self._log = logger
        self._inferrer = SchemaInferrer()

    def create_schema(self, schema_name: str) -> None:
        """Create a DuckDB schema if it does not already exist.

        Args:
            schema_name: Name of the schema to create.
        """
        self._conn.execute(
            f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'
        )
        self._log.debug(f"Schema ensured: {schema_name}")

    def table_exists(self, table_name: str, schema: str = "main") -> bool:
        """Check whether a table exists in the given schema.

        Args:
            table_name: Table name to check.
            schema: DuckDB schema name.

        Returns:
            True if the table exists, False otherwise.
        """
        df = self._conn.fetchdf(
            "SELECT count(*) AS cnt FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ?",
            [schema, table_name],
        )
        return int(df["cnt"].iloc[0]) > 0

    def load_parquet(
        self,
        table_name: str,
        parquet_path: Path | str,
        schema: str = "main",
        mode: str = "append",
    ) -> LoadResult:
        """Load a Parquet file into a DuckDB table.

        Args:
            table_name: Target table name.
            parquet_path: Path to the Parquet file.
            schema: DuckDB schema name.
            mode: 'append', 'overwrite', or 'incremental'.

        Returns:
            LoadResult with row counts and timing.
        """
        df = pd.read_parquet(str(parquet_path), engine="pyarrow")
        return self.load_dataframe(table_name, df, schema, mode)

    def load_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        schema: str = "main",
        mode: str = "append",
    ) -> LoadResult:
        """Load a DataFrame into a DuckDB table.

        Args:
            table_name: Target table name.
            df: DataFrame to load.
            schema: DuckDB schema name.
            mode: 'append', 'overwrite', or 'incremental'.

        Returns:
            LoadResult with row counts and timing.
        """
        start = time.monotonic()
        self._log.info(
            f"Loading {len(df):,} rows → {schema}.{table_name} (mode={mode})"
        )

        df = self._add_metadata_columns(df)

        if mode == "overwrite":
            rows_loaded, rows_skipped = self._load_overwrite(table_name, df, schema)
        elif mode == "incremental":
            rows_loaded, rows_skipped = self._load_incremental(
                table_name, df, schema
            )
        else:
            rows_loaded, rows_skipped = self._load_append(table_name, df, schema)

        duration = time.monotonic() - start
        self._log.info(
            f"Loaded {rows_loaded:,} rows, skipped {rows_skipped:,} "
            f"→ {schema}.{table_name} ({duration:.2f}s)"
        )

        return LoadResult(
            table_name=table_name,
            schema=schema,
            rows_loaded=rows_loaded,
            rows_skipped=rows_skipped,
            mode=mode,
            duration_seconds=duration,
            success=True,
        )

    def query(self, sql: str) -> pd.DataFrame:
        """Execute arbitrary SQL and return results as a DataFrame.

        Args:
            sql: SQL query string.

        Returns:
            Query results as a pandas DataFrame.
        """
        return self._conn.fetchdf(sql)

    def get_table_info(
        self, table_name: str, schema: str = "main"
    ) -> TableInfo | None:
        """Retrieve metadata for a single table.

        Args:
            table_name: Table name to inspect.
            schema: DuckDB schema name.

        Returns:
            TableInfo if the table exists, else None.
        """
        if not self.table_exists(table_name, schema):
            return None

        columns = self._get_columns(table_name, schema)
        row_count = self._get_row_count(table_name, schema)

        return TableInfo(
            name=table_name,
            schema=schema,
            row_count=row_count,
            columns=columns,
        )

    def list_tables(self, schema: str = "main") -> list[TableInfo]:
        """Return metadata for all tables in *schema*.

        Args:
            schema: DuckDB schema name to inspect.

        Returns:
            List of TableInfo objects.
        """
        df = self._conn.fetchdf(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? ORDER BY table_name",
            [schema],
        )

        results: list[TableInfo] = []
        for table_name in df["table_name"].tolist():
            info = self.get_table_info(table_name, schema)
            if info:
                results.append(info)
        return results

    def register_parquet_view(self, view_name: str, parquet_path: str) -> None:
        """Register a Parquet file as a DuckDB view.

        Useful for exposing raw lake files as dbt sources without loading
        data into the warehouse.

        Args:
            view_name: Name for the virtual view.
            parquet_path: Filesystem path to the Parquet file.
        """
        self._conn.execute(
            f"CREATE OR REPLACE VIEW \"{view_name}\" AS "
            f"SELECT * FROM read_parquet('{parquet_path}')"
        )
        self._log.debug(f"Registered parquet view '{view_name}' → {parquet_path}")

    def _add_metadata_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attach load timestamp metadata to *df*.

        Args:
            df: Source DataFrame.

        Returns:
            DataFrame with an added 'loaded_at' column.
        """
        df = df.copy()
        df["loaded_at"] = datetime.now(tz=timezone.utc)
        return df

    def _ensure_table(
        self, table_name: str, df: pd.DataFrame, schema: str
    ) -> None:
        """Create the table if it does not exist.

        Args:
            table_name: Table to create.
            df: DataFrame whose schema to use.
            schema: DuckDB schema name.
        """
        if not self.table_exists(table_name, schema):
            ddl = self._inferrer.build_create_table_sql(table_name, df, schema)
            self._conn.execute(ddl)

    def _load_append(
        self, table_name: str, df: pd.DataFrame, schema: str
    ) -> tuple[int, int]:
        """Append DataFrame rows to the table.

        Args:
            table_name: Target table name.
            df: DataFrame to append.
            schema: DuckDB schema name.

        Returns:
            Tuple of (rows_loaded, rows_skipped).
        """
        self._ensure_table(table_name, df, schema)
        self._conn.conn.register("_staging_df", df)
        self._conn.execute(
            f'INSERT INTO "{schema}"."{table_name}" SELECT * FROM _staging_df'
        )
        return len(df), 0

    def _load_overwrite(
        self, table_name: str, df: pd.DataFrame, schema: str
    ) -> tuple[int, int]:
        """Drop and recreate the table with *df*.

        Args:
            table_name: Target table name.
            df: DataFrame to load.
            schema: DuckDB schema name.

        Returns:
            Tuple of (rows_loaded, rows_skipped).
        """
        self._conn.execute(f'DROP TABLE IF EXISTS "{schema}"."{table_name}"')
        ddl = self._inferrer.build_create_table_sql(table_name, df, schema)
        self._conn.execute(ddl)
        self._conn.conn.register("_staging_df", df)
        self._conn.execute(
            f'INSERT INTO "{schema}"."{table_name}" SELECT * FROM _staging_df'
        )
        return len(df), 0

    def _load_incremental(
        self, table_name: str, df: pd.DataFrame, schema: str
    ) -> tuple[int, int]:
        """Insert only rows not already present based on loaded_at timestamp.

        Uses the 'loaded_at' column to determine the most recent load and
        only inserts rows with a newer timestamp.

        Args:
            table_name: Target table name.
            df: DataFrame with new rows to potentially load.
            schema: DuckDB schema name.

        Returns:
            Tuple of (rows_loaded, rows_skipped).
        """
        self._ensure_table(table_name, df, schema)

        if not self.table_exists(table_name, schema):
            return self._load_append(table_name, df, schema)

        max_ts_df = self._conn.fetchdf(
            f'SELECT MAX(loaded_at) AS max_ts FROM "{schema}"."{table_name}"'
        )
        max_ts = max_ts_df["max_ts"].iloc[0]

        if max_ts is None or pd.isna(max_ts):
            return self._load_append(table_name, df, schema)

        new_rows = df[df["loaded_at"] > max_ts]
        skipped = len(df) - len(new_rows)

        if len(new_rows) == 0:
            return 0, skipped

        self._conn.conn.register("_staging_df", new_rows)
        self._conn.execute(
            f'INSERT INTO "{schema}"."{table_name}" SELECT * FROM _staging_df'
        )
        return len(new_rows), skipped

    def _get_columns(self, table_name: str, schema: str) -> list[dict]:
        """Retrieve column metadata for a table.

        Args:
            table_name: Table to inspect.
            schema: DuckDB schema name.

        Returns:
            List of dicts with 'name' and 'type' keys.
        """
        df = self._conn.fetchdf(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? "
            "ORDER BY ordinal_position",
            [schema, table_name],
        )
        return [
            {"name": row["column_name"], "type": row["data_type"]}
            for _, row in df.iterrows()
        ]

    def _get_row_count(self, table_name: str, schema: str) -> int | None:
        """Count rows in a table.

        Args:
            table_name: Table to count.
            schema: DuckDB schema name.

        Returns:
            Row count, or None on error.
        """
        try:
            df = self._conn.fetchdf(
                f'SELECT count(*) AS cnt FROM "{schema}"."{table_name}"'
            )
            return int(df["cnt"].iloc[0])
        except Exception:
            return None
