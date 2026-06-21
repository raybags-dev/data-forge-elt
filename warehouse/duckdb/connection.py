"""DuckDB connection context manager."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any

import duckdb
import pandas as pd


class DuckDBConnection:
    """Manages a DuckDB database connection with context manager support.

    Supports both file-based and in-memory (``":memory:"``) databases.

    Args:
        db_path: Filesystem path to the DuckDB database file, or ``":memory:"``.
        read_only: Open the database in read-only mode.
    """

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        read_only: bool = False,
    ) -> None:
        self._db_path = str(db_path)
        self._read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Open the DuckDB connection.

        Returns:
            Active DuckDB connection object.
        """
        if self._conn is None:
            self._conn = duckdb.connect(
                database=self._db_path,
                read_only=self._read_only,
            )
        return self._conn

    def disconnect(self) -> None:
        """Close the DuckDB connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> DuckDBConnection:
        """Open connection on entering the context manager."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close connection on exiting the context manager."""
        self.disconnect()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Return active connection, connecting first if needed.

        Returns:
            Active DuckDB connection.
        """
        if self._conn is None:
            return self.connect()
        return self._conn

    def execute(
        self, query: str, params: list[Any] | None = None
    ) -> duckdb.DuckDBPyRelation:
        """Execute a SQL statement and return a relation.

        Args:
            query: SQL query string.
            params: Optional positional parameters for the query.

        Returns:
            DuckDB relation representing the result.
        """
        if params:
            return self.conn.execute(query, params)
        return self.conn.execute(query)

    def fetchdf(
        self, query: str, params: list[Any] | None = None
    ) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame.

        Args:
            query: SQL query string.
            params: Optional positional parameters.

        Returns:
            Query results as a pandas DataFrame.
        """
        result = self.execute(query, params)
        return result.df()

    def executemany(self, query: str, params_list: list[list[Any]]) -> None:
        """Execute a SQL statement once per row in *params_list*.

        Args:
            query: SQL query template with ``?`` placeholders.
            params_list: List of parameter lists, one per execution.
        """
        self.conn.executemany(query, params_list)
