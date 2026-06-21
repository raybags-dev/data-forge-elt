"""Pydantic models for the DuckDB warehouse layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoadResult(BaseModel):
    """Result of a data load operation into DuckDB.

    Attributes:
        table_name: Target table name.
        db_schema: DuckDB schema name.
        rows_loaded: Number of rows successfully inserted.
        rows_skipped: Number of rows skipped (e.g., duplicates in incremental mode).
        mode: Load mode used: 'append', 'overwrite', or 'incremental'.
        duration_seconds: Wall-clock time for the load operation.
        success: Whether the operation completed without error.
    """

    table_name: str
    db_schema: str = Field(alias="schema", default="main")
    rows_loaded: int
    rows_skipped: int
    mode: str
    duration_seconds: float
    success: bool

    model_config = {"populate_by_name": True}


class TableInfo(BaseModel):
    """Metadata about a table in the DuckDB warehouse.

    Attributes:
        name: Table name.
        db_schema: DuckDB schema name.
        row_count: Approximate row count (None if not yet counted).
        size_bytes: Estimated table size in bytes (None if unavailable).
        columns: List of column descriptors with 'name' and 'type' keys.
    """

    name: str
    db_schema: str = Field(alias="schema", default="main")
    row_count: int | None = None
    size_bytes: int | None = None
    columns: list[dict] = []

    model_config = {"populate_by_name": True}
