from __future__ import annotations

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent import context_enricher
from agent.context_enricher import (
    ContextPlan,
    ContextSample,
    ContextTarget,
    build_context_payload,
    render_context_samples,
    select_context_plan,
)


PROFILES = [
    {
        "schema": "public",
        "table": "ingredientes",
        "raw_table": "ingredientes",
        "columns": ["id", "name", "unit", "category_id"],
    },
    {
        "schema": "public",
        "table": "estoque_atual",
        "raw_table": "estoque_atual",
        "columns": ["id", "ingrediente", "qtd", "data"],
    },
    {
        "schema": "ml",
        "table": "ml.criticidade_report_items",
        "raw_table": "criticidade_report_items",
        "columns": ["run_id", "ingredient_id", "ingredient_name", "necessita_compra"],
    },
]


def test_select_context_plan_fallback_sem_google(monkeypatch):
    monkeypatch.setattr(context_enricher, "_client", lambda: None)
    monkeypatch.setattr(context_enricher, "list_table_profiles", lambda: PROFILES)

    plan = select_context_plan("Quais itens estao em criticidade?")

    assert plan.targets
    assert plan.targets[0].table == "ml.criticidade_report_items"


def test_render_context_samples_formata_tabela_qualificada():
    sample = ContextSample(
        table="ml.criticidade_report_items",
        columns=["ingredient_name", "necessita_compra"],
        rows=[{"ingredient_name": "CAFE COADO", "necessita_compra": 1}],
    )

    rendered = render_context_samples([sample])

    assert "Tabela candidata: ml.criticidade_report_items" in rendered
    assert "ingredient_name" in rendered
    assert "CAFE COADO" in rendered


def test_build_context_payload_usa_plano_selecionado(monkeypatch):
    plan = ContextPlan(
        targets=[
            ContextTarget(
                table="ml.criticidade_report_items",
                columns=["ingredient_name", "necessita_compra"],
                reason="criticidade",
            )
        ]
    )

    monkeypatch.setattr(context_enricher, "select_context_plan", lambda question: plan)
    monkeypatch.setattr(
        context_enricher,
        "execute_query",
        lambda sql: [{"ingredient_name": "CAFE COADO", "necessita_compra": 1}],
    )

    payload = build_context_payload("Quais itens precisam de compra?")

    assert payload["targets"][0]["table"] == "ml.criticidade_report_items"
    assert "CAFE COADO" in payload["context"]
