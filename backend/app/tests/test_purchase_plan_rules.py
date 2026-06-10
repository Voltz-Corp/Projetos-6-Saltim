from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.main as main
from app.main import (
    _dashboard_history_reference_date,
    _purchase_display_criticality,
    _purchase_status_is_critical,
    _resolve_purchase_criticality,
    delete_purchase_plan_item,
)


def test_purchase_criticality_prefers_model_report():
    label, source = _resolve_purchase_criticality(
        SimpleNamespace(criticidade_predita="Alerta de compra"),
        "Emergencial",
        stock_position=0,
        forecast_qty=10,
    )

    assert label == "Alerta de compra"
    assert source == "model_report"


def test_purchase_criticality_uses_abt_before_operational_rule():
    label, source = _resolve_purchase_criticality(
        None,
        "Critico",
        stock_position=100,
        forecast_qty=1,
    )

    assert label == "Crítico"
    assert source == "abt_reposicao"


def test_purchase_criticality_falls_back_to_operational_rule():
    label, source = _resolve_purchase_criticality(
        None,
        None,
        stock_position=0,
        forecast_qty=1,
    )

    assert label == "Crítico"
    assert source == "operational_rule"


def test_purchase_criticality_labels_are_normalized_and_prioritized():
    assert _purchase_display_criticality("Atencao") == "Atenção"
    assert _purchase_status_is_critical("Emergencial")
    assert _purchase_status_is_critical("Atenção")
    assert not _purchase_status_is_critical("OK")


def test_dashboard_history_uses_latest_date_shared_by_both_series():
    values = iter(["2026-06-02", "2026-06-09"])
    db = SimpleNamespace(query=lambda *_: SimpleNamespace(scalar=lambda: next(values)))

    assert _dashboard_history_reference_date(db) == "2026-06-02"


def test_delete_purchase_plan_item_recalculates_plan(monkeypatch):
    item = SimpleNamespace(ingredient_id="ING001")
    plan = SimpleNamespace(status="rascunho", items=[item], quotes=[])
    db = SimpleNamespace(commit=lambda: None, refresh=lambda _: None)
    calls = []
    monkeypatch.setattr(main, "_get_purchase_plan_or_404", lambda *_: plan)
    monkeypatch.setattr(main, "_sync_purchase_plan_quotes", lambda *_: calls.append("quotes"))
    monkeypatch.setattr(main, "_recalculate_purchase_plan", lambda *_: calls.append("totals"))
    monkeypatch.setattr(main, "_serialize_purchase_plan", lambda value: value)

    result = delete_purchase_plan_item(1, "ING001", db)

    assert result is plan
    assert plan.items == []
    assert plan.status == "em_revisao"
    assert calls == ["quotes", "totals"]


def test_delete_purchase_plan_item_blocks_approved_plan(monkeypatch):
    plan = SimpleNamespace(status="aprovado", items=[], quotes=[])
    db = SimpleNamespace()
    monkeypatch.setattr(main, "_get_purchase_plan_or_404", lambda *_: plan)

    with pytest.raises(HTTPException) as error:
        delete_purchase_plan_item(1, "ING001", db)

    assert error.value.status_code == 409
