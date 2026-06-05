from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from .database import (
    execute_query,
    get_schema,
    list_table_profiles,
    quote_column_name,
    quote_table_name,
)

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - dependency is declared in requirements
    genai = None
    types = None


MAX_SAMPLE_ROWS = 3
MAX_SAMPLE_COLUMNS = 5
MAX_TABLES = 3
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"


class ContextTarget(BaseModel):
    table: str
    columns: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class ContextPlan(BaseModel):
    targets: list[ContextTarget] = Field(default_factory=list)


@dataclass(frozen=True)
class ContextSample:
    table: str
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class TableProfile:
    table: str
    columns: list[str]
    searchable_text: str


def _client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def _normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9_\s]", " ", value)
    return re.sub(r"\s+", " ", value)


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_text(value)
    return {token for token in normalized.split() if len(token) > 2}


def _table_profiles() -> list[TableProfile]:
    profiles: list[TableProfile] = []
    for raw_profile in list_table_profiles():
        table = raw_profile["table"]
        columns = list(raw_profile["columns"])
        searchable_text = " ".join([table, *columns])
        profiles.append(
            TableProfile(
                table=table,
                columns=columns,
                searchable_text=searchable_text,
            )
        )
    return profiles


def _table_columns(table_name: str) -> list[str]:
    for profile in _table_profiles():
        if profile.table == table_name:
            return profile.columns
    return []


def _default_columns_for_table(table_name: str) -> list[str]:
    columns = _table_columns(table_name)
    preferred = [
        column
        for column in columns
        if not column.lower().startswith("id")
        and not column.lower().endswith("_id")
    ]
    selected = preferred[:MAX_SAMPLE_COLUMNS]
    return selected if selected else columns[:MAX_SAMPLE_COLUMNS]


def _score_profile(question: str, profile: TableProfile) -> int:
    question_tokens = _tokenize(question)
    profile_tokens = _tokenize(profile.searchable_text)
    overlap = question_tokens & profile_tokens
    score = len(overlap)

    for column in profile.columns:
        column_tokens = _tokenize(column)
        if column_tokens & question_tokens:
            score += 2

    table_tokens = _tokenize(profile.table)
    if table_tokens & question_tokens:
        score += 1

    domain_boosts = {
        "estoque": ("estoque_atual", "estoques", "ml.abt_reposicao"),
        "ingrediente": ("ingredientes", "receitas_ingredientes"),
        "receita": ("receitas", "vendas", "resumo_mensal_vendas"),
        "faturamento": ("vendas", "resumo_mensal_vendas"),
        "venda": ("vendas", "resumo_diario_vendas", "resumo_mensal_vendas"),
        "fornecedor": ("fornecedores", "fornecedores_ingredientes"),
        "pedido": ("pedidos", "pedidos_log", "ml.abt_pedidos_eventos"),
        "criticidade": ("ml.criticidade_report_items", "ml.criticidade_report_runs"),
        "contagem": ("contagens", "contagem_log", "log_contagem"),
    }

    normalized_question = _normalize_text(question)
    for term, table_names in domain_boosts.items():
        if term in normalized_question and profile.table in table_names:
            score += 5

    return score


def _fallback_plan(question: str) -> ContextPlan:
    profiles = _table_profiles()
    ranked = sorted(
        ((profile, _score_profile(question, profile)) for profile in profiles),
        key=lambda item: item[1],
        reverse=True,
    )

    candidates: list[ContextTarget] = []
    for profile, score in ranked:
        if score <= 0:
            continue
        candidates.append(
            ContextTarget(
                table=profile.table,
                columns=_default_columns_for_table(profile.table),
            )
        )

    if not candidates:
        for profile in profiles[:MAX_TABLES]:
            candidates.append(
                ContextTarget(
                    table=profile.table,
                    columns=_default_columns_for_table(profile.table),
                )
            )

    return ContextPlan(targets=candidates[:MAX_TABLES])


def select_context_plan(question: str) -> ContextPlan:
    client = _client()
    if client is None or types is None:
        return _fallback_plan(question)

    schema_overview = get_schema()
    system_instruction = (
        "Voce e um roteador semantico de contexto para um agente Text-to-SQL "
        "do Saltim Cafe. Escolha ate 3 tabelas uteis para a pergunta e ate "
        "5 colunas por tabela. Use nomes de tabela exatamente como aparecem "
        "no schema, incluindo prefixo ml. quando for schema de ML."
    )
    prompt = (
        f"Schema disponivel:\n{schema_overview}\n\n"
        f"Pergunta do usuario:\n{question}\n\n"
        "Retorne JSON com as tabelas e colunas mais informativas para "
        "desambiguar a pergunta."
    )

    response = client.models.generate_content(
        model=os.getenv("GOOGLE_MODEL", DEFAULT_MODEL),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ContextPlan,
            temperature=0.1,
        ),
    )

    plan = response.parsed or ContextPlan()
    valid_tables = {profile.table for profile in _table_profiles()}
    normalized_targets: list[ContextTarget] = []

    for target in plan.targets:
        if target.table not in valid_tables:
            continue
        valid_columns = set(_table_columns(target.table))
        columns = [column for column in target.columns if column in valid_columns]
        if not columns:
            columns = _default_columns_for_table(target.table)
        normalized_targets.append(
            ContextTarget(
                table=target.table,
                columns=columns[:MAX_SAMPLE_COLUMNS],
                reason=target.reason,
            )
        )

    if not normalized_targets:
        return _fallback_plan(question)

    return ContextPlan(targets=normalized_targets[:MAX_TABLES])


def _build_sample_sql(
    table: str,
    columns: list[str],
    limit: int = MAX_SAMPLE_ROWS,
) -> str:
    projection = (
        ", ".join(quote_column_name(column) for column in columns)
        if columns
        else "*"
    )
    return f"SELECT {projection} FROM {quote_table_name(table)} LIMIT {limit}"


def fetch_context_samples_from_plan(plan: ContextPlan) -> list[ContextSample]:
    samples: list[ContextSample] = []

    for target in plan.targets:
        columns = target.columns or _default_columns_for_table(target.table)
        sql = _build_sample_sql(target.table, columns)
        try:
            rows = execute_query(sql)
        except Exception:
            continue

        if rows:
            samples.append(
                ContextSample(table=target.table, columns=columns, rows=rows)
            )

    return samples


def fetch_context_samples(question: str) -> list[ContextSample]:
    plan = select_context_plan(question)
    return fetch_context_samples_from_plan(plan)


def render_context_samples(samples: list[ContextSample]) -> str:
    if not samples:
        return ""

    blocks: list[str] = []
    for sample in samples:
        blocks.append(f"Tabela candidata: {sample.table}")
        if sample.columns:
            blocks.append(f"Colunas uteis: {', '.join(sample.columns)}")
        for index, row in enumerate(sample.rows, 1):
            blocks.append(f"Linha {index}: {row}")

    return "\n".join(blocks).strip()


def build_enriched_context(question: str) -> str:
    samples = fetch_context_samples(question)
    return render_context_samples(samples)


def build_context_payload(question: str) -> dict[str, Any]:
    plan = select_context_plan(question)
    samples = fetch_context_samples_from_plan(plan)
    return {
        "question": question,
        "targets": [target.model_dump() for target in plan.targets],
        "context": render_context_samples(samples),
        "samples": [
            {"table": sample.table, "columns": sample.columns, "rows": sample.rows}
            for sample in samples
        ],
    }
