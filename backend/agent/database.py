from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect, text

try:
    from app.database import engine
except ModuleNotFoundError:  # pragma: no cover - supports root-level module execution
    from backend.app.database import engine


ALLOWED_SCHEMAS = ("public", "ml")


def _qualified_table(schema: str, table: str) -> str:
    return table if schema == "public" else f"{schema}.{table}"


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def quote_table_name(table_name: str) -> str:
    return ".".join(_quote_identifier(part) for part in table_name.split("."))


def quote_column_name(column_name: str) -> str:
    return ".".join(_quote_identifier(part) for part in column_name.split("."))


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def normalize_row(row: Any) -> dict[str, Any]:
    return {key: normalize_value(value) for key, value in dict(row).items()}


def get_tabelas_validas() -> set[str]:
    inspector = inspect(engine)
    tables: set[str] = set()

    for schema in ALLOWED_SCHEMAS:
        for table_name in inspector.get_table_names(schema=schema):
            qualified = f"{schema}.{table_name}"
            tables.add(qualified)
            if schema == "public":
                tables.add(table_name)

    return tables


def list_table_profiles() -> list[dict[str, Any]]:
    inspector = inspect(engine)
    profiles: list[dict[str, Any]] = []

    for schema in ALLOWED_SCHEMAS:
        for table_name in inspector.get_table_names(schema=schema):
            columns = [
                column["name"]
                for column in inspector.get_columns(table_name, schema=schema)
            ]
            profiles.append(
                {
                    "schema": schema,
                    "table": _qualified_table(schema, table_name),
                    "raw_table": table_name,
                    "columns": columns,
                }
            )

    return profiles


def get_schema() -> str:
    schema_parts: list[str] = []
    for profile in list_table_profiles():
        columns = ", ".join(profile["columns"])
        schema_parts.append(f"Tabela {profile['table']}: {columns}")
    return "\n".join(schema_parts)


def execute_query(sql: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [normalize_row(row._mapping) for row in result]


if __name__ == "__main__":
    print(get_schema())
