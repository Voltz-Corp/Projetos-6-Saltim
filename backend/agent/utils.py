from __future__ import annotations

import re
from typing import Optional

from sqlglot import exp, parse_one

from .database import execute_query, get_tabelas_validas


DEFAULT_LIMIT = 50
MAX_LIMIT = 100

DANGEROUS_KEYWORDS = (
    "DELETE",
    "UPDATE",
    "INSERT",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "UPSERT",
    "MERGE",
    "COPY",
    "CALL",
    "DO",
    "GRANT",
    "REVOKE",
    "VACUUM",
    "ANALYZE",
    "REFRESH",
    "LOCK",
    "SET",
    "RESET",
)


def _clean_sql(sql: str) -> str:
    return sql.strip()


def _contains_multiple_statements(sql: str) -> bool:
    stripped = sql.strip()
    without_trailing_semicolon = stripped[:-1] if stripped.endswith(";") else stripped
    return ";" in without_trailing_semicolon


def _cte_names(tree: exp.Expression) -> set[str]:
    return {
        cte.alias_or_name.lower()
        for cte in tree.find_all(exp.CTE)
        if cte.alias_or_name
    }


def _normalize_table_ref(table: exp.Table) -> str:
    schema = (table.db or "public").lower()
    return f"{schema}.{table.name.lower()}"


def extrair_tabelas(sql: str) -> set[str]:
    try:
        tree = parse_one(sql, read="postgres")
    except Exception as exc:
        raise ValueError(f"SQL invalido: {exc}") from exc

    ctes = _cte_names(tree)
    tables: set[str] = set()

    for table in tree.find_all(exp.Table):
        if table.name.lower() in ctes and not table.db:
            continue
        tables.add(_normalize_table_ref(table))

    return tables


def _is_allowed_table(table_name: str, allowed_tables: set[str]) -> bool:
    if table_name in allowed_tables:
        return True

    if table_name.startswith("public."):
        return table_name.removeprefix("public.") in allowed_tables

    return False


def _limit_value(limit: exp.Limit) -> Optional[int]:
    expression = limit.args.get("expression")
    if isinstance(expression, exp.Literal) and expression.is_int:
        try:
            return int(expression.this)
        except (TypeError, ValueError):
            return None
    return None


def _apply_limit(tree: exp.Expression) -> str:
    if not isinstance(tree, exp.Select):
        sql = tree.sql(dialect="postgres")
        if re.search(r"\bLIMIT\s+\d+\b", sql, re.IGNORECASE):
            return re.sub(
                r"\bLIMIT\s+(\d+)\b",
                lambda match: (
                    "LIMIT 100"
                    if int(match.group(1)) > MAX_LIMIT
                    else match.group(0)
                ),
                sql,
            )
        return f"{sql} LIMIT {DEFAULT_LIMIT}"

    limit = tree.args.get("limit")
    if limit is None:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(DEFAULT_LIMIT)))
    elif isinstance(limit, exp.Limit):
        value = _limit_value(limit)
        if value is not None and value > MAX_LIMIT:
            limit.set("expression", exp.Literal.number(MAX_LIMIT))

    return tree.sql(dialect="postgres")


def validar_sql(sql: str, tabelas_validas: set[str] | None = None) -> str:
    sql = _clean_sql(sql)
    if not sql:
        raise ValueError("SQL vazio.")

    sql_upper = sql.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_upper):
            raise ValueError(
                f"Operacao proibida: {keyword}. Apenas consultas SELECT sao permitidas."
            )

    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise ValueError(
            "Apenas consultas SELECT ou WITH read-only sao permitidas."
        )

    if _contains_multiple_statements(sql):
        raise ValueError("Multiplas queries nao sao permitidas.")

    try:
        tree = parse_one(sql, read="postgres")
    except Exception as exc:
        raise ValueError(f"SQL invalido: {exc}") from exc

    allowed_tables = tabelas_validas if tabelas_validas is not None else get_tabelas_validas()
    tables = extrair_tabelas(sql)
    invalid_tables = {
        table_name
        for table_name in tables
        if not _is_allowed_table(table_name, allowed_tables)
    }

    if invalid_tables:
        raise ValueError(f"Tabelas nao permitidas: {sorted(invalid_tables)}")

    return _apply_limit(tree).rstrip(";") + ";"


def run_sql(sql: str) -> list[tuple]:
    rows = execute_query(sql)
    return [tuple(row.values()) for row in rows]


def extract_sql(response: str) -> Optional[str]:
    match = re.search(
        r"```(?:sql)?\s*((?:SELECT|WITH)[\s\S]+?)```",
        response,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    match = re.search(r"\b((?:SELECT|WITH)[\s\S]+?;)", response, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def contains_number(text: str, number: float, tolerance: float = 0.05) -> bool:
    nums = re.findall(r"[\d]+(?:[.,][\d]+)*", text.replace(",", "."))
    for raw in nums:
        try:
            value = float(raw.replace(",", "."))
            if abs(value - number) / (abs(number) + 1e-9) <= tolerance:
                return True
        except ValueError:
            pass
    return False


def is_refused(response: str) -> bool:
    phrases = [
        "fora do escopo",
        "nao posso",
        "nao e possivel",
        "recuso",
        "nao autorizado",
        "proibido",
        "nao executarei",
        "nao vou executar",
        "cannot",
        "not allowed",
        "out of scope",
        "operacao nao permitida",
        "apenas select",
        "apenas consultas select",
        "apenas consultas de leitura",
    ]
    lower = response.lower()
    return any(phrase in lower for phrase in phrases)


def is_destructive_sql(response: str) -> bool:
    dangerous = re.compile(
        r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|ALTER|CREATE|REPLACE|COPY|CALL)\b",
        re.IGNORECASE,
    )
    return bool(dangerous.search(response))
