"""Database connectivity and schema extraction utilities."""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Tuple

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine


def get_engine(dsn: str) -> Engine:
    """Create a SQLAlchemy engine for the given DSN."""
    if not dsn:
        raise ValueError("Database DSN is required.")
    return create_engine(dsn, future=True)


def _serialize_schema(inspector) -> Dict[str, List[Dict[str, str]]]:
    schema: Dict[str, List[Dict[str, str]]] = {}
    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
            })
        schema[table_name] = columns
    return schema


_SCHEMA_CACHE: Dict[pathlib.Path, Dict[str, List[Dict[str, str]]]] = {}


def get_or_extract_schema(engine: Engine, cache_path: pathlib.Path) -> Dict[str, List[Dict[str, str]]]:
    """Return a schema cache, generating it if necessary."""
    cache_path = cache_path.resolve()
    if cache_path in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_path]

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
            _SCHEMA_CACHE[cache_path] = schema
            return schema

    inspector = inspect(engine)
    schema = _serialize_schema(inspector)

    with cache_path.open("w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2, ensure_ascii=False)

    _SCHEMA_CACHE[cache_path] = schema
    return schema


def run_sql_query(engine: Engine, sql: str) -> Tuple[List[str], List[Tuple]]:
    """Execute a SQL query and return column names with rows."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()
    return list(columns), rows
