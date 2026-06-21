"""Schema inference utilities for DuckDB table creation."""

from __future__ import annotations

import pandas as pd

_PANDAS_TO_DUCKDB: dict[str, str] = {
    "object": "VARCHAR",
    "string": "VARCHAR",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
    "int8": "TINYINT",
    "int16": "SMALLINT",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "uint8": "UTINYINT",
    "uint16": "USMALLINT",
    "uint32": "UINTEGER",
    "uint64": "UBIGINT",
    "float16": "FLOAT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "datetime64[ns]": "TIMESTAMP",
    "datetime64[us]": "TIMESTAMP",
    "datetime64[ms]": "TIMESTAMP",
    "datetime64[s]": "TIMESTAMP",
    "date": "DATE",
    "timedelta64[ns]": "INTERVAL",
    "category": "VARCHAR",
}


class SchemaInferrer:
    """Infers DuckDB column types from pandas DataFrame dtypes.

    Used to auto-generate CREATE TABLE statements from DataFrame schemas.
    """

    def infer_from_df(self, df: pd.DataFrame) -> dict[str, str]:
        """Map each column in *df* to its equivalent DuckDB type.

        Args:
            df: DataFrame whose columns should be mapped.

        Returns:
            Dict mapping column name → DuckDB type string.
        """
        result: dict[str, str] = {}
        for col, dtype in df.dtypes.items():
            result[str(col)] = self._map_dtype(dtype)
        return result

    def build_create_table_sql(
        self,
        table_name: str,
        df: pd.DataFrame,
        schema: str = "main",
    ) -> str:
        """Build a CREATE TABLE IF NOT EXISTS statement for *df*.

        Args:
            table_name: Desired table name.
            df: DataFrame whose columns define the schema.
            schema: DuckDB schema name.

        Returns:
            SQL string for table creation.
        """
        col_types = self.infer_from_df(df)
        col_defs = ", ".join(
            f'"{col}" {dtype}' for col, dtype in col_types.items()
        )
        qualified = f'"{schema}"."{table_name}"'
        return f"CREATE TABLE IF NOT EXISTS {qualified} ({col_defs})"

    def build_insert_sql(
        self, table_name: str, columns: list[str], schema: str = "main"
    ) -> str:
        """Build a parameterised INSERT statement.

        Args:
            table_name: Target table name.
            columns: List of column names to insert.
            schema: DuckDB schema name.

        Returns:
            SQL INSERT string with ``?`` placeholders.
        """
        col_list = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join("?" for _ in columns)
        qualified = f'"{schema}"."{table_name}"'
        return f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})"

    def _map_dtype(self, dtype: pd.api.types.CategoricalDtype | object) -> str:
        """Return the DuckDB type string for a pandas dtype.

        Args:
            dtype: Pandas dtype to map.

        Returns:
            DuckDB type string.
        """
        dtype_str = str(dtype)

        if dtype_str in _PANDAS_TO_DUCKDB:
            return _PANDAS_TO_DUCKDB[dtype_str]

        if dtype_str.startswith("datetime64"):
            return "TIMESTAMP"

        if dtype_str.startswith("timedelta"):
            return "INTERVAL"

        if "int" in dtype_str.lower():
            return "BIGINT"

        if "float" in dtype_str.lower():
            return "DOUBLE"

        return "VARCHAR"
