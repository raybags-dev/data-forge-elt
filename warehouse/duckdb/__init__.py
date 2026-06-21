"""DuckDB warehouse subpackage.

Exports DuckDBConnection, DuckDBWarehouse, SchemaInferrer, and data models.
"""

from __future__ import annotations

from warehouse.duckdb.connection import DuckDBConnection
from warehouse.duckdb.models import LoadResult, TableInfo
from warehouse.duckdb.schema import SchemaInferrer
from warehouse.duckdb.warehouse import DuckDBWarehouse

__all__ = [
    "DuckDBConnection",
    "DuckDBWarehouse",
    "SchemaInferrer",
    "LoadResult",
    "TableInfo",
]
