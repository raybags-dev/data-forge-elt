"""DuckDB loader — loads DataFrames from the lake into DuckDB warehouse."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from loguru import Logger

    from warehouse.duckdb.models import LoadResult
    from warehouse.duckdb.warehouse import DuckDBWarehouse


class DuckDBLoader:
    """Loads Parquet files or DataFrames from the data lake into DuckDB.

    Acts as the bridge between the data lake layer and the DuckDB warehouse.

    Args:
        warehouse: DuckDBWarehouse instance to write into.
        logger: Loguru Logger for structured logging.
    """

    def __init__(
        self,
        warehouse: DuckDBWarehouse,
        logger: Logger,
    ) -> None:
        self._warehouse = warehouse
        self._log = logger

    def load_parquet(
        self,
        table_name: str,
        parquet_path: Path,
        schema: str = "main",
        mode: str = "append",
    ) -> LoadResult:
        """Load a Parquet file from disk into a DuckDB table.

        Args:
            table_name: Target DuckDB table name.
            parquet_path: Path to the Parquet file.
            schema: DuckDB schema name.
            mode: Load mode: 'append', 'overwrite', or 'incremental'.

        Returns:
            LoadResult with row counts and status.
        """
        self._log.info(f"Loading {parquet_path.name} → {schema}.{table_name}")
        return self._warehouse.load_parquet(
            table_name=table_name,
            parquet_path=parquet_path,
            schema=schema,
            mode=mode,
        )

    def load_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        schema: str = "main",
        mode: str = "append",
    ) -> LoadResult:
        """Load a DataFrame into a DuckDB table.

        Args:
            table_name: Target DuckDB table name.
            df: DataFrame to load.
            schema: DuckDB schema name.
            mode: Load mode: 'append', 'overwrite', or 'incremental'.

        Returns:
            LoadResult with row counts and status.
        """
        self._log.info(
            f"Loading DataFrame ({len(df):,} rows) → {schema}.{table_name}"
        )
        return self._warehouse.load_dataframe(
            table_name=table_name,
            df=df,
            schema=schema,
            mode=mode,
        )
