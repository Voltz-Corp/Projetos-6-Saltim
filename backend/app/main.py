import csv
import io
import json
import math
import logging
import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from unicodedata import normalize
from uuid import uuid4
from zoneinfo import ZoneInfo
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import asc, case, desc, func, or_, text
from sqlalchemy.orm import Session

from agent import perguntar

from .database import engine, Base, get_db, run_sql_loaders
from .smtp_mailer import (
    OrderEmail,
    OrderEmailItem,
    get_smtp_settings,
    send_order_email,
)
from .models import (
    Categoria,
    Contagem,
    ContagemLog,
    CriticalityReportItem,
    CriticalityReportRun,
    Estoque,
    EstoqueAtual,
    FeriadoRecife,
    Fornecedor,
    FornecedorIngrediente,
    Ingrediente,
    JobStatus,
    LogContagem,
    Pedido,
    Receita,
    ReceitaIngrediente,
    ResumoDiarioVenda,
    Venda,
)
from .schemas import (
    AgentChatRequest,
    AgentChatResponse,
    IngredienteOut,
    ContagemCreate,
    ContagemDetalheCategoria,
    ContagemDetalheItem,
    ContagemDetalheOut,
    ContagemListItem,
    ContagemOut,
    CriticidadeReportCategoryOut,
    CriticidadeReportItemOut,
    CriticidadeReportLatestOut,
    CriticidadeReportRunOut,
    EstoquePaginado,
    FornecedorCreate,
    FornecedorKpis,
    FornecedorListItem,
    FornecedorListResponse,
    FornecedorOrderOut,
    FornecedorOut,
    FornecedorProductOut,
    FornecedorProfileKpis,
    FornecedorProfileResponse,
    JobStatusOut,
    PedidoCreateRequest,
    PedidoCreateResponse,
    PedidoEmailResult,
    PedidoDetailItem,
    PedidoDetailResponse,
    PedidoGroupOut,
    PedidoOut,
    PedidoPaginado,
    PedidoRecommendationItem,
    PedidoRecommendationRequest,
    PedidoRecommendationResponse,
    RecommendedOrderGroup,
    RecommendedOrderItem,
    SupplierOption,
    AtualizacaoLote,
    AtualizacaoIngrediente,
    LogContagemOut,
    ResultadoLote,
    DashboardAlert,
    DashboardCards,
    DashboardCategoryItem,
    DashboardFilters,
    DashboardHolidayFilter,
    DashboardHistoryPoint,
    DashboardIngredientFilter,
    DashboardKpi,
    DashboardMonthFilter,
    DashboardNamedMetric,
    DashboardRecipeItem,
    DashboardRankItem,
    DashboardResponse,
    DashboardRevenueSummary,
    DashboardUnitCategoryGroup,
    DashboardUnitRankGroup,
)


PRODUCTION_CATEGORY_ID = "CAT0015"
DASHBOARD_STOCK_UNITS = ("KG", "UND", "L")
AGENT_ROWS_PREVIEW_LIMIT = 5
RECIFE_TZ = ZoneInfo("America/Recife")
logger = logging.getLogger(__name__)


PURCHASE_NEEDED_FALLBACK_SQL = """
WITH latest_date AS (
    SELECT max("date") AS reference_date
    FROM ml.abt_reposicao
    WHERE y_comprar = 1
      AND is_compravel = 1
)
SELECT
    abt.ingredient_id,
    abt.nome_ingrediente AS ingrediente,
    abt.categoria,
    abt.unidade,
    abt.saldo_atual AS estoque_atual,
    abt.y_qtd_comprar AS qtd_sugerida,
    abt.y_nivel_criticidade AS criticidade,
    abt.criticidade_score,
    abt."date" AS data_referencia
FROM ml.abt_reposicao abt
JOIN latest_date latest ON latest.reference_date = abt."date"
WHERE abt.y_comprar = 1
  AND abt.is_compravel = 1
ORDER BY
    abt.criticidade_score DESC NULLS LAST,
    abt.y_qtd_comprar DESC NULLS LAST,
    abt.nome_ingrediente ASC
LIMIT :limit
"""

PURCHASE_NEEDED_FALLBACK_COUNT_SQL = """
WITH latest_date AS (
    SELECT max("date") AS reference_date
    FROM ml.abt_reposicao
    WHERE y_comprar = 1
      AND is_compravel = 1
)
SELECT count(1)
FROM ml.abt_reposicao abt
JOIN latest_date latest ON latest.reference_date = abt."date"
WHERE abt.y_comprar = 1
  AND abt.is_compravel = 1
"""


def _now_recife() -> datetime:
    return datetime.now(RECIFE_TZ)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_sql_loaders()
    ensure_ml_schema()
    Base.metadata.create_all(bind=engine)
    ensure_contagem_estoque_schema()
    ensure_pedidos_schema()
    yield


app = FastAPI(title="Saltim Café API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------


def ensure_ml_schema() -> None:
    statements = (
        "CREATE SCHEMA IF NOT EXISTS ml",
        """
        CREATE TABLE IF NOT EXISTS ml.job_status (
            id BIGSERIAL PRIMARY KEY,
            dia DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            inicio_em TIMESTAMPTZ,
            fim_em TIMESTAMPTZ,
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            error_message TEXT,
            CONSTRAINT uq_job_status_dia UNIQUE (dia),
            CONSTRAINT ck_job_status_status CHECK (status IN ('running', 'pending', 'success', 'failed'))
        )
        """,
        "ALTER TABLE ml.job_status ADD COLUMN IF NOT EXISTS inicio_em TIMESTAMPTZ",
        "ALTER TABLE ml.job_status ADD COLUMN IF NOT EXISTS fim_em TIMESTAMPTZ",
        "CREATE INDEX IF NOT EXISTS idx_job_status_dia ON ml.job_status (dia)",
    )
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def ensure_contagem_estoque_schema() -> None:
    statements = (
        "ALTER TABLE contagens ADD COLUMN IF NOT EXISTS data_contagem DATE",
        (
            "UPDATE contagens "
            "SET data_contagem = date(criada_em) "
            "WHERE data_contagem IS NULL"
        ),
        "ALTER TABLE contagens ALTER COLUMN data_contagem SET NOT NULL",
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_contagens_data_contagem "
            "ON contagens (data_contagem)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_contagens_data_contagem "
            "ON contagens (data_contagem)"
        ),
        "ALTER TABLE contagens ADD COLUMN IF NOT EXISTS estoque_snapshot_data DATE",
        "ALTER TABLE contagem_log ADD COLUMN IF NOT EXISTS estoque_id TEXT",
        "ALTER TABLE contagem_log ADD COLUMN IF NOT EXISTS estoque_data DATE",
        "ALTER TABLE contagem_log ADD COLUMN IF NOT EXISTS estoque_quantidade NUMERIC(14, 4)",
        (
            "CREATE INDEX IF NOT EXISTS idx_contagens_estoque_snapshot_data "
            "ON contagens (estoque_snapshot_data)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_contagem_log_estoque "
            "ON contagem_log (estoque_id)"
        ),
        (
            "UPDATE contagens "
            "SET estoque_snapshot_data = (SELECT max(date(date_time)) FROM estoques) "
            "WHERE estoque_snapshot_data IS NULL "
            "AND EXISTS (SELECT 1 FROM estoques)"
        ),
        (
            "DO $$ BEGIN "
            "IF NOT EXISTS ("
            "SELECT 1 "
            "FROM pg_constraint c "
            "JOIN pg_attribute a "
            "ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
            "WHERE c.contype = 'f' "
            "AND c.conrelid = 'contagem_log'::regclass "
            "AND c.confrelid = 'estoques'::regclass "
            "AND a.attname = 'estoque_id'"
            ") THEN "
            "ALTER TABLE contagem_log "
            "ADD CONSTRAINT fk_contagem_log_estoque "
            "FOREIGN KEY (estoque_id) REFERENCES estoques(id); "
            "END IF; "
            "END $$"
        ),
    )
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def ensure_pedidos_schema() -> None:
    statements = (
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS estoque_aplicado_em TIMESTAMPTZ",
    )
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def _countable_items_total(db: Session) -> int:
    return (
        db.query(func.count(Ingrediente.id))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .scalar()
        or 0
    )


def _resolve_estoque_snapshot_data(db: Session, reference_date: Optional[date] = None) -> Optional[date]:
    reference_date = reference_date or _now_recife().date()
    snapshot = (
        db.query(func.max(func.date(Estoque.date_time)))
        .filter(func.date(Estoque.date_time) <= reference_date)
        .scalar()
    )
    if snapshot is None:
        snapshot = db.query(func.max(func.date(Estoque.date_time))).scalar()
    return snapshot


def _estoque_snapshot_for_ingredient(
    db: Session,
    ingredient_id: str,
    snapshot_date: Optional[date],
) -> Optional[Estoque]:
    if snapshot_date is None:
        return None
    return (
        db.query(Estoque)
        .filter(Estoque.ingredient_id == ingredient_id)
        .filter(func.date(Estoque.date_time) == snapshot_date)
        .order_by(Estoque.date_time.desc(), Estoque.id.desc())
        .first()
    )


def _latest_logs_by_ingredient(logs: list[ContagemLog]) -> dict[str, ContagemLog]:
    ordered = sorted(logs, key=lambda log: (log.criado_em, log.id))
    return {log.ingrediente_id: log for log in ordered}


def _contagem_counts(
    contagem: Contagem,
    db: Session,
    total_itens: Optional[int] = None,
) -> dict[str, int]:
    if total_itens is None:
        total_itens = _countable_items_total(db)

    logs = (
        db.query(ContagemLog)
        .join(Ingrediente, Ingrediente.id == ContagemLog.ingrediente_id)
        .filter(ContagemLog.contagem_id == contagem.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .all()
    )
    latest_logs = _latest_logs_by_ingredient(logs)
    itens_contados = len(latest_logs)
    itens_alterados = sum(1 for log in latest_logs.values() if round(float(log.delta), 3) != 0)
    itens_sem_alteracao = itens_contados - itens_alterados

    return {
        "total_itens": total_itens,
        "itens_contados": itens_contados,
        "itens_alterados": itens_alterados,
        "itens_sem_alteracao": itens_sem_alteracao,
        "itens_nao_contados": max(total_itens - itens_contados, 0),
    }


def _contagem_list_item(
    contagem: Contagem,
    db: Session,
    total_itens: Optional[int] = None,
) -> ContagemListItem:
    return ContagemListItem(
        id=contagem.id,
        label=contagem.label,
        data_contagem=contagem.data_contagem,
        status=contagem.status,
        estoque_snapshot_data=contagem.estoque_snapshot_data,
        criada_em=contagem.criada_em,
        finalizada_em=contagem.finalizada_em,
        **_contagem_counts(contagem, db, total_itens),
    )


@app.post("/api/contagens", response_model=ContagemOut)
def create_contagem(payload: ContagemCreate, db: Session = Depends(get_db)):
    today = _now_recife().date()
    label = payload.label or f"Contagem {today.strftime('%d/%m/%Y')}"
    existing = (
        db.query(Contagem)
        .filter(Contagem.data_contagem == today)
        .order_by(Contagem.id.desc())
        .first()
    )
    if existing is not None:
        changed = False
        if existing.estoque_snapshot_data is None:
            existing.estoque_snapshot_data = _resolve_estoque_snapshot_data(db)
            changed = True
        if existing.status == "finalizada":
            existing.status = "em_andamento"
            existing.finalizada_em = None
            changed = True
        if changed:
            db.commit()
            db.refresh(existing)
        return existing

    contagem = Contagem(
        label=label,
        data_contagem=today,
        status="em_andamento",
        estoque_snapshot_data=_resolve_estoque_snapshot_data(db),
    )
    db.add(contagem)
    db.commit()
    db.refresh(contagem)
    return contagem


@app.get("/api/contagens", response_model=list[ContagemListItem])
def list_contagens(db: Session = Depends(get_db)):
    contagens = db.query(Contagem).order_by(Contagem.criada_em.desc(), Contagem.id.desc()).all()
    total_itens = _countable_items_total(db)
    return [_contagem_list_item(contagem, db, total_itens) for contagem in contagens]


@app.get("/api/contagens/{contagem_id}", response_model=ContagemOut)
def get_contagem(contagem_id: int, db: Session = Depends(get_db)):
    contagem = db.query(Contagem).filter(Contagem.id == contagem_id).first()
    if contagem is None:
        raise HTTPException(status_code=404, detail="Contagem não encontrada")
    return contagem


@app.get("/api/contagens/{contagem_id}/detalhe", response_model=ContagemDetalheOut)
def get_contagem_detalhe(contagem_id: int, db: Session = Depends(get_db)):
    contagem = db.query(Contagem).filter(Contagem.id == contagem_id).first()
    if contagem is None:
        raise HTTPException(status_code=404, detail="Contagem não encontrada")

    ingredientes = (
        db.query(Ingrediente)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Categoria.name.asc(), Ingrediente.name.asc())
        .all()
    )
    logs = (
        db.query(ContagemLog)
        .join(Ingrediente, Ingrediente.id == ContagemLog.ingrediente_id)
        .filter(ContagemLog.contagem_id == contagem.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .all()
    )
    logs_by_ingredient = _latest_logs_by_ingredient(logs)

    categorias: dict[str, dict] = {}
    for ingrediente in ingredientes:
        group = categorias.setdefault(
            ingrediente.category_id,
            {
                "category_id": ingrediente.category_id,
                "categoria": ingrediente.category,
                "items": [],
            },
        )
        log = logs_by_ingredient.get(ingrediente.id)
        snapshot = _estoque_snapshot_for_ingredient(
            db,
            ingrediente.id,
            contagem.estoque_snapshot_data,
        )
        if log is None:
            status = "nao_contado"
            item = ContagemDetalheItem(
                ingrediente_id=ingrediente.id,
                ingrediente_nome=ingrediente.name,
                unit=ingrediente.unit,
                quantidade_atual=float(ingrediente.current_qty),
                estoque_id=snapshot.id if snapshot else None,
                estoque_data=(
                    snapshot.date_time.date()
                    if snapshot and snapshot.date_time
                    else contagem.estoque_snapshot_data
                ),
                estoque_quantidade=float(snapshot.quantity) if snapshot else None,
                status=status,
            )
        else:
            delta = round(float(log.delta), 3)
            status = "sem_alteracao" if delta == 0 else "alterado"
            item = ContagemDetalheItem(
                ingrediente_id=ingrediente.id,
                ingrediente_nome=ingrediente.name,
                unit=ingrediente.unit,
                quantidade_atual=float(ingrediente.current_qty),
                estoque_id=log.estoque_id,
                estoque_data=log.estoque_data,
                estoque_quantidade=(
                    float(log.estoque_quantidade)
                    if log.estoque_quantidade is not None
                    else None
                ),
                quantidade_anterior=float(log.quantidade_anterior),
                quantidade_nova=float(log.quantidade_nova),
                delta=delta,
                status=status,
                contado_em=log.criado_em,
            )
        group["items"].append(item)

    detalhe_categorias = []
    for group in categorias.values():
        items = group["items"]
        itens_contados = sum(1 for item in items if item.status != "nao_contado")
        itens_alterados = sum(1 for item in items if item.status == "alterado")
        itens_sem_alteracao = sum(1 for item in items if item.status == "sem_alteracao")
        detalhe_categorias.append(
            ContagemDetalheCategoria(
                category_id=group["category_id"],
                categoria=group["categoria"],
                total_itens=len(items),
                itens_contados=itens_contados,
                itens_alterados=itens_alterados,
                itens_sem_alteracao=itens_sem_alteracao,
                itens_nao_contados=len(items) - itens_contados,
                items=items,
            )
        )

    counts = _contagem_counts(contagem, db, len(ingredientes))
    return ContagemDetalheOut(
        id=contagem.id,
        label=contagem.label,
        data_contagem=contagem.data_contagem,
        status=contagem.status,
        estoque_snapshot_data=contagem.estoque_snapshot_data,
        criada_em=contagem.criada_em,
        finalizada_em=contagem.finalizada_em,
        categorias=detalhe_categorias,
        **counts,
    )


@app.patch("/api/contagens/{contagem_id}/finalizar", response_model=ContagemOut)
def finalizar_contagem(contagem_id: int, db: Session = Depends(get_db)):
    contagem = db.query(Contagem).filter(Contagem.id == contagem_id).first()
    if contagem is None:
        raise HTTPException(status_code=404, detail="Contagem não encontrada")
    counts = _contagem_counts(contagem, db)
    if counts["itens_nao_contados"] > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "A contagem só pode ser finalizada quando todos os itens "
                "compráveis forem contados."
            ),
        )
    contagem.status = "finalizada"
    contagem.finalizada_em = _now_recife()
    db.commit()
    db.refresh(contagem)
    return contagem

def _compute_status(item: Ingrediente) -> str:
    qty = float(item.current_qty)
    min_qty = float(item.min_qty)
    if qty <= 0:
        return "Esgotado"
    if qty < min_qty:
        return "Crítico"
    if qty < min_qty * 1.5:
        return "Atenção"
    return "OK"


def _latest_criticidade_run(db: Session) -> Optional[CriticalityReportRun]:
    return (
        db.query(CriticalityReportRun)
        .filter(CriticalityReportRun.status == "success")
        .filter(CriticalityReportRun.total_items > 0)
        .order_by(CriticalityReportRun.generated_at.desc(), CriticalityReportRun.id.desc())
        .first()
    )


def _latest_criticidade_by_ingredient(db: Session) -> tuple[Optional[CriticalityReportRun], dict[str, CriticalityReportItem]]:
    run = _latest_criticidade_run(db)
    if run is None:
        return None, {}
    items = (
        db.query(CriticalityReportItem)
        .filter(CriticalityReportItem.run_id == run.id)
        .all()
    )
    return run, {item.ingredient_id: item for item in items}


def _model_stock_status(ingrediente: Ingrediente, criticidade: Optional[CriticalityReportItem]) -> str:
    if float(ingrediente.current_qty) <= 0:
        return "Esgotado"
    if criticidade is not None and bool(criticidade.necessita_compra):
        return "Crítico"
    return "OK"


def _ingrediente_out(
    ingrediente: Ingrediente,
    criticidade_run: Optional[CriticalityReportRun],
    criticidade_by_ingredient: dict[str, CriticalityReportItem],
) -> IngredienteOut:
    criticidade = criticidade_by_ingredient.get(ingrediente.id)
    return IngredienteOut(
        id=ingrediente.id,
        name=ingrediente.name,
        unit=ingrediente.unit,
        category_id=ingrediente.category_id,
        price=float(ingrediente.price),
        category=ingrediente.category,
        min_qty=float(ingrediente.min_qty),
        current_qty=float(ingrediente.current_qty),
        status=_model_stock_status(ingrediente, criticidade),
        criticidade_predita=criticidade.criticidade_predita if criticidade else None,
        criticidade_report_id=criticidade_run.id if criticidade_run else None,
        criticidade_reference_date=criticidade_run.reference_date if criticidade_run else None,
    )


def _criticidade_item_out(item: CriticalityReportItem) -> CriticidadeReportItemOut:
    return CriticidadeReportItemOut(
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient_name,
        category_id=item.category_id,
        category=item.category,
        unit=item.unit,
        estoque_atual=_as_float(item.estoque_atual),
        stock_position=_as_float(item.stock_position),
        baseline_threshold=_as_float(item.baseline_threshold),
        cobertura_estoque_pct=_as_float(item.cobertura_estoque_pct),
        limiar_alerta_predito_pct=_as_float(item.limiar_alerta_predito_pct),
        limiar_critico_predito_pct=_as_float(item.limiar_critico_predito_pct),
        criticidade_predita=item.criticidade_predita,
        necessita_compra=bool(item.necessita_compra),
        score_alerta_compra=_as_float(item.score_alerta_compra),
        rank_position=item.rank_position,
    )


def _criticidade_report_for_date(db: Session, reference_date: date) -> CriticidadeReportLatestOut:
    run = (
        db.query(CriticalityReportRun)
        .filter(CriticalityReportRun.reference_date == reference_date)
        .order_by(CriticalityReportRun.generated_at.desc(), CriticalityReportRun.id.desc())
        .first()
    )
    if run is None:
        empty_run = CriticidadeReportRunOut(
            status="no_report",
            reference_date=reference_date,
            model_name="XGBoost Regressor",
            model_uri="runs:/58db15b4b9364e6cb1bf7d9ebe65f922/model",
            error_message="Nenhum relatório de criticidade foi gerado para hoje.",
        )
        return CriticidadeReportLatestOut(
            run=empty_run,
            distribution=[],
            categories=[],
            critical_items=[],
            zero_items=[],
            examples_critical=[],
            examples_ok=[],
        )

    items = (
        db.query(CriticalityReportItem)
        .filter(CriticalityReportItem.run_id == run.id)
        .order_by(CriticalityReportItem.rank_position.asc())
        .all()
    )
    item_outputs = [_criticidade_item_out(item) for item in items]
    zero_outputs = [item for item in item_outputs if item.estoque_atual <= 0]
    critical_outputs = [
        item for item in item_outputs if item.necessita_compra and item.estoque_atual > 0
    ]
    ok_outputs = [item for item in item_outputs if not item.necessita_compra]

    categories: list[CriticidadeReportCategoryOut] = []
    category_names = sorted({item.category or "Sem categoria" for item in item_outputs})
    for category in category_names:
        category_items = [(item) for item in item_outputs if (item.category or "Sem categoria") == category]
        total_items = len(category_items)
        alert_count = sum(1 for item in category_items if item.necessita_compra)
        ok_count = total_items - alert_count
        categories.append(
            CriticidadeReportCategoryOut(
                category=category,
                total_items=total_items,
                ok_count=ok_count,
                alert_count=alert_count,
                alert_rate=(alert_count / total_items if total_items else 0.0),
            )
        )
    categories.sort(key=lambda item: (item.alert_count, item.alert_rate), reverse=True)

    distribution = []
    if run.total_items > 0:
        distribution = [
            {"status": "OK", "count": run.ok_count, "rate": 1 - run.alert_rate},
            {"status": "Alerta de compra", "count": run.alert_count, "rate": run.alert_rate},
        ]

    return CriticidadeReportLatestOut(
        run=CriticidadeReportRunOut(
            id=run.id,
            reference_date=run.reference_date,
            generated_at=run.generated_at,
            status=run.status,
            contagem_id=run.contagem_id,
            contagem_status=run.contagem_status,
            model_name=run.model_name,
            model_uri=run.model_uri,
            model_run_id=run.model_run_id,
            total_items=run.total_items,
            ok_count=run.ok_count,
            alert_count=run.alert_count,
            alert_rate=run.alert_rate,
            metrics=run.metrics or {},
            stability=run.stability or {},
            error_message=run.error_message,
        ),
        distribution=distribution,
        categories=categories,
        critical_items=critical_outputs,
        zero_items=zero_outputs,
        examples_critical=critical_outputs[:5],
        examples_ok=sorted(ok_outputs, key=lambda item: abs(item.score_alerta_compra))[:5],
    )


def _upsert_job_status(
    db: Session,
    dia: date,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    db.execute(
        text("""
            INSERT INTO ml.job_status (
                dia,
                status,
                inicio_em,
                fim_em,
                atualizado_em,
                error_message
            )
            VALUES (
                :dia,
                :status,
                CASE WHEN :status = 'running' THEN now() ELSE NULL END,
                CASE WHEN :status IN ('pending', 'success', 'failed') THEN now() ELSE NULL END,
                now(),
                :error_message
            )
            ON CONFLICT (dia)
            DO UPDATE SET
                status = EXCLUDED.status,
                inicio_em = CASE
                    WHEN EXCLUDED.status = 'running' THEN now()
                    ELSE COALESCE(ml.job_status.inicio_em, EXCLUDED.inicio_em)
                END,
                fim_em = CASE
                    WHEN EXCLUDED.status = 'running' THEN NULL
                    WHEN EXCLUDED.status IN ('pending', 'success', 'failed') THEN now()
                    ELSE ml.job_status.fim_em
                END,
                atualizado_em = now(),
                error_message = EXCLUDED.error_message
            """),
        {"dia": dia, "status": status, "error_message": error_message},
    )
    db.commit()


def _job_status_for_date(db: Session, dia: date) -> JobStatusOut:
    status = (
        db.query(JobStatus)
        .filter(JobStatus.dia == dia)
        .order_by(JobStatus.atualizado_em.desc(), JobStatus.id.desc())
        .first()
    )
    if status is None:
        return JobStatusOut(dia=dia, status="pending")
    return JobStatusOut.model_validate(status)


def _ensure_criticidade_failed_run(
    db: Session,
    reference_date: date,
    error_message: str,
) -> None:
    existing = (
        db.query(CriticalityReportRun)
        .filter(CriticalityReportRun.reference_date == reference_date)
        .order_by(CriticalityReportRun.generated_at.desc(), CriticalityReportRun.id.desc())
        .first()
    )
    if existing is not None:
        return

    db.add(
        CriticalityReportRun(
            reference_date=reference_date,
            status="failed",
            model_name="XGBoost Regressor",
            model_uri="runs:/58db15b4b9364e6cb1bf7d9ebe65f922/model",
            model_run_id="58db15b4b9364e6cb1bf7d9ebe65f922",
            metrics={
                "status": "failed",
                "source": "backend_subprocess_fallback",
            },
            stability={},
            error_message=error_message[:4000],
        )
    )
    db.commit()


@app.get("/api/ml/criticidade/job-status/latest", response_model=JobStatusOut)
def get_latest_criticidade_job_status(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return _job_status_for_date(db, _now_recife().date())


@app.get("/api/ml/criticidade/relatorio/latest", response_model=CriticidadeReportLatestOut)
def get_latest_criticidade_report(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return _criticidade_report_for_date(db, _now_recife().date())


@app.post("/api/ml/criticidade/relatorio/run", response_model=CriticidadeReportLatestOut)
def run_criticidade_report(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    reference_date = _now_recife().date()
    _upsert_job_status(db, reference_date, "running")
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "ml" / "jobs" / "generate_criticality_report.py"
    python_path = project_root / ".venv" / "bin" / "python"
    python_executable = str(python_path) if python_path.exists() else sys.executable
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql+psycopg://saltim:saltim123@localhost:55432/saltim_db")
    env.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")

    result = subprocess.run(
        [python_executable, str(script_path), "--reference-date", "today"],
        cwd=str(project_root),
        env=env,
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    process_output = (
        result.stderr
        or result.stdout
        or "O job terminou sem registrar uma rodada em criticidade_report_runs."
    )
    if result.returncode not in {0, 1}:
        _upsert_job_status(
            db,
            reference_date,
            "failed",
            process_output[:2000],
        )
        _ensure_criticidade_failed_run(db, reference_date, process_output)
        return _criticidade_report_for_date(db, reference_date)

    db.expire_all()
    if (
        db.query(CriticalityReportRun)
        .filter(CriticalityReportRun.reference_date == reference_date)
        .first()
        is None
    ):
        _upsert_job_status(db, reference_date, "failed", process_output[:2000])
        _ensure_criticidade_failed_run(db, reference_date, process_output)
        db.expire_all()
    return _criticidade_report_for_date(db, reference_date)


def _as_float(value) -> float:
    return float(value or 0)


EXPORT_FORMATS = {
    "csv": ("text/csv; charset=utf-8", "csv"),
    "json": ("application/json; charset=utf-8", "json"),
    "xml": ("application/xml; charset=utf-8", "xml"),
    "yaml": ("application/x-yaml; charset=utf-8", "yaml"),
    "excel": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
    "pdf": ("application/pdf", "pdf"),
}

SALTIM_ORANGE = "#F07820"
SALTIM_DARK = "#232323"
SALTIM_CREAM = "#FEF4E8"
SALTIM_STONE = "#5F5E5A"
SALTIM_LOGO_PATH = (
    Path(__file__).resolve().parents[2] / "frontend" / "public" / "images" / "saltim_logo.jpg"
)

EXPORT_COLUMN_LABELS = {
    "id": "ID",
    "data_hora": "Data/hora",
    "ingrediente_id": "ID ingrediente",
    "ingrediente": "Ingrediente",
    "categoria": "Categoria",
    "unidade": "Unidade",
    "quantidade": "Quantidade",
    "nome": "Nome",
    "cnpj": "CNPJ",
    "email": "Email",
    "telefone": "Telefone",
    "prazo_medio_entrega_dias": "Prazo medio entrega (dias)",
    "itens_fornecidos": "Itens fornecidos",
    "preco_medio": "Preco medio",
    "pedido_id": "ID pedido",
    "data_pedido": "Data pedido",
    "fornecedor_id": "ID fornecedor",
    "fornecedor": "Fornecedor",
    "valor_total": "Valor total",
    "status": "Status",
    "data_prevista": "Data prevista",
}


def _normalize_export_format(format_value: str) -> str:
    normalized = format_value.strip().lower()
    normalized = {"xlsx": "excel", "xls": "excel", "yml": "yaml"}.get(
        normalized,
        normalized,
    )
    if normalized not in EXPORT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Formato invalido. Use pdf, excel, csv, json, xml ou yaml.",
        )
    return normalized


def _stringify_export_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _export_response(
    rows: list[dict],
    filename: str,
    format_value: str,
    title: str,
    columns: Optional[list[str]] = None,
) -> Response:
    export_format = _normalize_export_format(format_value)
    media_type, extension = EXPORT_FORMATS[export_format]
    content = _serialize_export(rows, export_format, title, columns)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{extension}"'},
    )


def _serialize_export(
    rows: list[dict],
    export_format: str,
    title: str,
    columns: Optional[list[str]] = None,
):
    if export_format == "csv":
        return _serialize_csv(rows, columns)
    if export_format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2, default=str)
    if export_format == "xml":
        return _serialize_xml(rows)
    if export_format == "yaml":
        return _serialize_yaml(rows)
    if export_format == "excel":
        return _serialize_excel(rows, title, columns)
    if export_format == "pdf":
        return _serialize_pdf(rows, title, columns)
    raise AssertionError(export_format)


def _export_columns(rows: list[dict], columns: Optional[list[str]]) -> list[str]:
    return columns or (list(rows[0].keys()) if rows else [])


def _export_headers(columns: list[str]) -> list[str]:
    return [EXPORT_COLUMN_LABELS.get(column, column.replace("_", " ").title()) for column in columns]


def _export_cell_value(value):
    if value is None:
        return None
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _serialize_csv(rows: list[dict], columns: Optional[list[str]]) -> str:
    output = io.StringIO()
    export_columns = _export_columns(rows, columns)
    writer = csv.DictWriter(output, fieldnames=export_columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _stringify_export_value(value) for key, value in row.items()})
    return output.getvalue()


def _serialize_xml(rows: list[dict]) -> str:
    root = Element("export")
    for row in rows:
        row_el = SubElement(root, "row")
        for key, value in row.items():
            field = SubElement(row_el, key)
            field.text = _stringify_export_value(value)
    return tostring(root, encoding="unicode", xml_declaration=True)


def _serialize_yaml(rows: list[dict]) -> str:
    if not rows:
        return "[]\n"
    lines: list[str] = []
    for row in rows:
        lines.append("-")
        for key, value in row.items():
            text = _stringify_export_value(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'  {key}: "{text}"')
    return "\n".join(lines) + "\n"


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _serialize_excel(rows: list[dict], title: str, columns: Optional[list[str]]) -> bytes:
    export_columns = _export_columns(rows, columns)
    headers = _export_headers(export_columns)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = title[:31]
    workbook.properties.creator = "Saltim Cafe"
    workbook.properties.title = title

    worksheet.append(headers)
    for row in rows:
        worksheet.append([_export_cell_value(row.get(column)) for column in export_columns])

    header_fill = PatternFill("solid", fgColor=SALTIM_ORANGE.replace("#", ""))
    header_font = Font(color="FFFFFF", bold=True)
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    worksheet.freeze_panes = "A2"
    if export_columns:
        last_column = get_column_letter(len(export_columns))
        last_row = max(1, worksheet.max_row)
        worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"

    for column_cells in worksheet.columns:
        column_letter = column_cells[0].column_letter
        max_length = 0
        for cell in column_cells:
            value = "" if cell.value is None else _stringify_export_value(cell.value)
            max_length = max(max_length, len(value))
            if isinstance(cell.value, (int, float)):
                cell.alignment = Alignment(horizontal="right")
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 48)

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_header_block(
    title: str,
    title_style: ParagraphStyle,
    meta_style: ParagraphStyle,
) -> Table:
    generated_at = _now_recife().strftime("%d/%m/%Y %H:%M")
    title_cell = [
        Paragraph("Saltim Cafe", meta_style),
        Paragraph(_xml_escape(title), title_style),
        Paragraph(f"Gerado em {generated_at}", meta_style),
    ]
    if SALTIM_LOGO_PATH.exists():
        logo = Image(str(SALTIM_LOGO_PATH), width=18 * mm, height=18 * mm)
    else:
        logo = Paragraph("Saltim", title_style)

    table = Table(
        [[logo, title_cell]],
        colWidths=[23 * mm, 235 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 1.4, colors.HexColor(SALTIM_ORANGE)),
            ]
        )
    )
    return table


def _pdf_table(
    rows: list[dict],
    columns: list[str],
    header_style: ParagraphStyle,
    cell_style: ParagraphStyle,
    number_style: ParagraphStyle,
    available_width: float,
) -> Table:
    headers = [Paragraph(_xml_escape(header), header_style) for header in _export_headers(columns)]
    data = [headers]
    numeric_columns = {
        "quantidade",
        "valor_total",
        "preco_medio",
        "itens_fornecidos",
        "prazo_medio_entrega_dias",
    }

    if rows:
        for row in rows:
            data.append(
                [
                    Paragraph(
                        _xml_escape(_stringify_export_value(row.get(column))),
                        number_style if column in numeric_columns else cell_style,
                    )
                    for column in columns
                ]
            )
    else:
        data.append([Paragraph("Nenhum registro encontrado.", cell_style)] + [""] * (len(columns) - 1))

    table = Table(
        data,
        colWidths=_pdf_column_widths(rows, columns, available_width),
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(SALTIM_ORANGE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCDAD4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(SALTIM_CREAM)]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if not rows and columns:
        style_commands.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(style_commands))
    return table


def _pdf_column_widths(rows: list[dict], columns: list[str], available_width: float) -> list[float]:
    if not columns:
        return []
    weights: list[float] = []
    for column, header in zip(columns, _export_headers(columns)):
        sample_lengths = [
            len(_stringify_export_value(row.get(column)))
            for row in rows[:80]
        ]
        content_length = max(sample_lengths, default=0)
        weights.append(max(len(header), min(content_length, 26), 5))
    total_weight = sum(weights) or 1
    min_width = 20 * mm
    widths = [max(min_width, available_width * weight / total_weight) for weight in weights]
    width_total = sum(widths)
    if width_total > available_width:
        scale = available_width / width_total
        widths = [width * scale for width in widths]
    return widths


def _draw_pdf_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(SALTIM_ORANGE))
    canvas.setLineWidth(0.6)
    canvas.line(document.leftMargin, 10 * mm, landscape(A4)[0] - document.rightMargin, 10 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor(SALTIM_STONE))
    canvas.drawString(document.leftMargin, 6 * mm, "Saltim Cafe")
    canvas.drawRightString(
        landscape(A4)[0] - document.rightMargin,
        6 * mm,
        f"Pagina {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _serialize_pdf(rows: list[dict], title: str, columns: Optional[list[str]]) -> bytes:
    export_columns = _export_columns(rows, columns)
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SaltimTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(SALTIM_DARK),
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "SaltimMeta",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(SALTIM_STONE),
    )
    header_style = ParagraphStyle(
        "SaltimTableHeader",
        parent=styles["Normal"],
        alignment=1,
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        "SaltimTableCell",
        parent=styles["Normal"],
        fontSize=6.4,
        leading=7.4,
        textColor=colors.HexColor(SALTIM_DARK),
    )
    number_style = ParagraphStyle(
        "SaltimTableNumber",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    story = [_pdf_header_block(title, title_style, meta_style), Spacer(1, 7 * mm)]
    if export_columns:
        story.append(
            _pdf_table(
                rows,
                export_columns,
                header_style,
                cell_style,
                number_style,
                document.width,
            )
        )
    else:
        story.append(Paragraph("Nenhum registro encontrado.", cell_style))

    document.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
    return output.getvalue()


def _percent_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _trend_direction(value: Optional[float], lower_is_better: bool = False) -> str:
    if value is None or abs(value) < 0.05:
        return "neutral"
    is_positive = value > 0
    if lower_is_better:
        is_positive = not is_positive
    return "up" if is_positive else "down"


def _format_percent(value: Optional[float], fallback: str) -> str:
    if value is None:
        return fallback
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


MONTH_ABBR = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


def _month_year_label(value: date) -> str:
    return f"{MONTH_ABBR[value.month - 1]}/{value.year % 100:02d}"


def _week_year_label(value: date) -> str:
    iso_year, iso_week, _ = value.isocalendar()
    return f"S{iso_week:02d}/{iso_year % 100:02d}"


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _shift_month_start(value: date, delta_months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + delta_months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _quarter_label(year: int, quarter: int) -> str:
    return f"Q{quarter}/{year % 100:02d}"


def _parse_month_key(value: str) -> Optional[tuple[int, int]]:
    try:
        year, month = value.split("-", 1)
        parsed_year = int(year)
        parsed_month = int(month)
    except ValueError:
        return None
    if parsed_month < 1 or parsed_month > 12:
        return None
    return parsed_year, parsed_month


def _apply_ingredient_category_filters(query, category_ids: Optional[list[str]]):
    if category_ids:
        return query.filter(Ingrediente.category_id.in_(category_ids))
    return query


def _apply_date_filters(
    query,
    column,
    db: Session,
    days: Optional[int] = None,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
):
    date_column = func.date(column)
    has_explicit_filter = bool(date_from or date_to or month_keys or years or months or event_dates or all_period)

    if not has_explicit_filter and days:
        reference_date = db.query(func.max(date_column)).scalar()
        if reference_date is not None:
            query = query.filter(date_column >= reference_date - timedelta(days=days - 1))

    if date_from:
        query = query.filter(date_column >= date_from)
    if date_to:
        query = query.filter(date_column <= date_to)

    parsed_months = [
        parsed for parsed in (_parse_month_key(value) for value in (month_keys or []))
        if parsed is not None
    ]
    if parsed_months:
        query = query.filter(
            or_(
                *[
                    (func.extract("year", column) == year)
                    & (func.extract("month", column) == month)
                    for year, month in parsed_months
                ]
            )
        )

    if years:
        query = query.filter(func.extract("year", column).in_(years))

    if months:
        query = query.filter(func.extract("month", column).in_(months))

    if event_dates:
        query = query.filter(date_column.in_(event_dates))

    return query


def _event_dates_for_types(db: Session, event_types: Optional[list[str]]) -> list[date]:
    if not event_types:
        return []

    predicates = []
    if "holiday" in event_types:
        predicates.append(ResumoDiarioVenda.is_holiday == 1)
    if "rain" in event_types:
        predicates.append(ResumoDiarioVenda.is_rain_event == 1)
    if "promo" in event_types:
        predicates.append(ResumoDiarioVenda.is_promo_day == 1)

    if not predicates:
        return []

    rows = (
        db.query(ResumoDiarioVenda.date)
        .filter(or_(*predicates))
        .order_by(ResumoDiarioVenda.date)
        .all()
    )
    return [row.date for row in rows]


def _resolve_date_window(
    db: Session,
    column,
    days: int,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> tuple[Optional[date], Optional[date]]:
    date_column = func.date(column)
    reference_date = db.query(func.max(date_column)).scalar()
    if reference_date is None:
        return None, None

    if event_dates:
        return min(event_dates), max(event_dates)

    parsed_months = [
        parsed for parsed in (_parse_month_key(value) for value in (month_keys or []))
        if parsed is not None
    ]
    if parsed_months:
        first_year, first_month = min(parsed_months)
        last_year, last_month = max(parsed_months)
        start = date(first_year, first_month, 1)
        end = _shift_month_start(date(last_year, last_month, 1), 1) - timedelta(days=1)
        return start, end

    if years:
        start_month = min(months or [1])
        end_month = max(months or [12])
        start = date(min(years), start_month, 1)
        end = _shift_month_start(date(max(years), end_month, 1), 1) - timedelta(days=1)
        return start, end

    if months:
        start = date(reference_date.year, min(months), 1)
        end = _shift_month_start(date(reference_date.year, max(months), 1), 1) - timedelta(days=1)
        return start, end

    if date_from or date_to:
        return date_from or reference_date - timedelta(days=days - 1), date_to or reference_date

    if all_period:
        start_date = db.query(func.min(date_column)).scalar()
        return start_date, reference_date

    return reference_date - timedelta(days=days - 1), reference_date


def _stock_total_at_or_before(
    db: Session,
    target_date: date,
    category_ids: Optional[list[str]] = None,
) -> float:
    stock_date = (
        db.query(func.max(func.date(Estoque.date_time)))
        .filter(func.date(Estoque.date_time) <= target_date)
        .scalar()
    )
    if stock_date is None:
        return 0

    query = (
        db.query(func.coalesce(func.sum(Estoque.quantity), 0))
        .join(Ingrediente, Estoque.ingredient_id == Ingrediente.id)
        .filter(func.date(Estoque.date_time) == stock_date)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    query = _apply_ingredient_category_filters(query, category_ids)
    total = query.scalar()
    return _as_float(total)


def _coverage_rows(
    db: Session,
    start_date: date,
    end_date: date,
    current_stock: bool = True,
    category_ids: Optional[list[str]] = None,
) -> list[dict[str, float | str]]:
    days = max(1, (end_date - start_date).days + 1)
    output_rows = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.unit,
            Categoria.name.label("category"),
            func.sum(Venda.quantity * ReceitaIngrediente.qty).label("output"),
        )
        .join(Categoria, Ingrediente.category_id == Categoria.id)
        .join(ReceitaIngrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id)
        .join(Venda, Venda.recipe_id == ReceitaIngrediente.recipe_id)
        .filter(func.date(Venda.date_time).between(start_date, end_date))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    output_query = _apply_ingredient_category_filters(output_rows, category_ids)
    output_rows = (
        output_query
        .group_by(Ingrediente.id, Ingrediente.name, Ingrediente.unit, Categoria.name)
        .all()
    )

    if current_stock:
        stock_query = (
            db.query(EstoqueAtual.ingrediente, EstoqueAtual.qtd)
            .join(Ingrediente, EstoqueAtual.ingrediente == Ingrediente.id)
            .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        )
        stock_query = _apply_ingredient_category_filters(stock_query, category_ids)
        stock_rows = stock_query.all()
        stock_by_id = {row.ingrediente: _as_float(row.qtd) for row in stock_rows}
    else:
        stock_date = (
            db.query(func.max(func.date(Estoque.date_time)))
            .filter(func.date(Estoque.date_time) <= end_date)
            .scalar()
        )
        stock_rows = []
        if stock_date is not None:
            stock_query = (
                db.query(Estoque.ingredient_id, Estoque.quantity)
                .join(Ingrediente, Estoque.ingredient_id == Ingrediente.id)
                .filter(func.date(Estoque.date_time) == stock_date)
                .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
            )
            stock_query = _apply_ingredient_category_filters(stock_query, category_ids)
            stock_rows = stock_query.all()
        stock_by_id = {row.ingredient_id: _as_float(row.quantity) for row in stock_rows}

    coverage = []
    for row in output_rows:
        total_output = _as_float(row.output)
        if total_output <= 0:
            continue
        avg_daily_output = total_output / days
        stock_qty = stock_by_id.get(row.id, 0)
        coverage_days = stock_qty / avg_daily_output if avg_daily_output else 999
        coverage.append(
            {
                "ingredient_id": row.id,
                "name": row.name,
                "category": row.category,
                "unit": row.unit,
                "coverage_days": coverage_days,
                "current_qty": stock_qty,
                "avg_daily_output": avg_daily_output,
            }
        )
    return coverage


def _top_recipe_for_period(
    db: Session,
    start_date: date,
    end_date: date,
    category_ids: Optional[list[str]] = None,
):
    quantity_expr = func.coalesce(func.sum(Venda.quantity), 0).label("quantity")
    query = (
        db.query(Receita.id, Receita.name, quantity_expr)
        .join(Venda, Venda.recipe_id == Receita.id)
        .filter(func.date(Venda.date_time).between(start_date, end_date))
    )
    if category_ids:
        query = query.filter(
            Receita.id.in_(_filtered_recipe_ids_query(db, category_ids=category_ids))
        )
    return (
        query.group_by(Receita.id, Receita.name)
        .order_by(desc(quantity_expr), Receita.name)
        .first()
    )


def _recipe_quantity_for_period(db: Session, recipe_id: str, start_date: date, end_date: date) -> float:
    value = (
        db.query(func.coalesce(func.sum(Venda.quantity), 0))
        .filter(Venda.recipe_id == recipe_id)
        .filter(func.date(Venda.date_time).between(start_date, end_date))
        .scalar()
    )
    return _as_float(value)


def _dashboard_kpis(
    db: Session,
    category_ids: Optional[list[str]] = None,
    days: int = 28,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardKpi]:
    sales_reference = db.query(func.max(func.date(Venda.date_time))).scalar()
    stock_reference = db.query(func.max(func.date(Estoque.date_time))).scalar()
    current_items_query = (
        db.query(func.count(Ingrediente.id))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    current_items = _apply_ingredient_category_filters(current_items_query, category_ids).scalar() or 0
    current_stock_query = (
        db.query(func.coalesce(func.sum(EstoqueAtual.qtd), 0))
        .join(Ingrediente, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    current_stock_qty = _apply_ingredient_category_filters(current_stock_query, category_ids).scalar() or 0
    previous_stock_reference = (stock_reference or date.today()) - timedelta(days=7)
    previous_stock_qty = _stock_total_at_or_before(db, previous_stock_reference, category_ids)
    stock_delta = _percent_change(_as_float(current_stock_qty), previous_stock_qty)

    empty_kpis = [
        DashboardKpi(
            id="ingredients",
            label="Estoque atual",
            value=f"{_as_float(current_stock_qty):,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
            detail=f"{current_items:,}".replace(",", ".") + " ingredientes cadastrados",
            trend_value=stock_delta,
            trend_label=f"{_format_percent(stock_delta, 'sem histórico')} vs {_week_year_label(previous_stock_reference)}",
            trend_direction=_trend_direction(stock_delta),
        )
    ]
    if sales_reference is None:
        return empty_kpis

    current_start, current_end = _resolve_date_window(
        db,
        Venda.date_time,
        days=max(1, days),
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=months,
        event_dates=event_dates,
    )
    if current_start is None or current_end is None:
        return empty_kpis
    window_days = max(1, (current_end - current_start).days + 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)

    current_coverage = _coverage_rows(db, current_start, current_end, current_stock=True, category_ids=category_ids)
    previous_coverage = _coverage_rows(db, previous_start, previous_end, current_stock=False, category_ids=category_ids)
    current_avg_coverage = (
        sum(float(item["coverage_days"]) for item in current_coverage) / len(current_coverage)
        if current_coverage
        else 0
    )
    previous_avg_coverage = (
        sum(float(item["coverage_days"]) for item in previous_coverage) / len(previous_coverage)
        if previous_coverage
        else 0
    )
    coverage_delta = _percent_change(current_avg_coverage, previous_avg_coverage)

    top_recipe = _top_recipe_for_period(db, current_start, current_end, category_ids=category_ids)
    top_recipe_delta = None
    top_recipe_detail = "Sem vendas no período"
    top_recipe_value = "-"
    if top_recipe is not None:
        current_quantity = _as_float(top_recipe.quantity)
        previous_quantity = _recipe_quantity_for_period(
            db,
            top_recipe.id,
            previous_start,
            previous_end,
        )
        top_recipe_delta = _percent_change(current_quantity, previous_quantity)
        top_recipe_value = top_recipe.name
        top_recipe_detail = f"{current_quantity:,.0f}".replace(",", ".") + f" unidades no período"

    previous_by_id = {item["ingredient_id"]: item for item in previous_coverage}
    critical = min(current_coverage, key=lambda item: float(item["coverage_days"]), default=None)
    critical_delta = None
    critical_value = "-"
    critical_detail = "Sem consumo recente"
    if critical is not None:
        previous = previous_by_id.get(str(critical["ingredient_id"]))
        previous_days = float(previous["coverage_days"]) if previous else 0
        critical_delta = _percent_change(float(critical["coverage_days"]), previous_days)
        critical_value = str(critical["name"])
        critical_detail = f"{float(critical['coverage_days']):.1f} dias de cobertura"

    return [
        *empty_kpis,
        DashboardKpi(
            id="coverage",
            label="Cobertura média",
            value=f"{current_avg_coverage:.1f} dias",
            detail="Ingredientes com consumo recente",
            trend_value=coverage_delta,
            trend_label=f"{_format_percent(coverage_delta, 'sem histórico')} vs {_month_year_label(previous_end)}",
            trend_direction=_trend_direction(coverage_delta),
        ),
        DashboardKpi(
            id="top_recipe",
            label="Receita que mais sai",
            value=top_recipe_value,
            detail=top_recipe_detail,
            trend_value=top_recipe_delta,
            trend_label=f"{_format_percent(top_recipe_delta, 'sem histórico')} vs {_month_year_label(previous_end)}",
            trend_direction=_trend_direction(top_recipe_delta),
        ),
        DashboardKpi(
            id="critical_ingredient",
            label="Ingrediente crítico",
            value=critical_value,
            detail=critical_detail,
            trend_value=critical_delta,
            trend_label=f"{_format_percent(critical_delta, 'sem histórico')} vs {_month_year_label(previous_end)}",
            trend_direction=_trend_direction(critical_delta),
        ),
    ]


def _stock_product_rows(
    db: Session,
    order,
    limit: int = 8,
    unit: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
) -> list[DashboardRankItem]:
    value_expr = func.coalesce(EstoqueAtual.qtd, 0).label("value")
    query = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.unit,
            Categoria.name.label("category"),
            value_expr,
        )
        .outerjoin(Categoria, Ingrediente.category_id == Categoria.id)
        .outerjoin(EstoqueAtual, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    query = _apply_ingredient_category_filters(query, category_ids)
    if unit:
        query = query.filter(Ingrediente.unit == unit)

    rows = (
        query
        .order_by(order(value_expr), Ingrediente.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardRankItem(
            id=row.id,
            name=row.name,
            unit=row.unit,
            category=row.category,
            value=_as_float(row.value),
        )
        for row in rows
    ]


def _stock_category_rows(
    db: Session,
    order,
    limit: int = 8,
    unit: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
) -> list[DashboardCategoryItem]:
    value_expr = func.coalesce(func.sum(EstoqueAtual.qtd), 0).label("value")
    query = (
        db.query(Categoria.id, Categoria.name, value_expr)
        .join(Ingrediente, Ingrediente.category_id == Categoria.id)
        .outerjoin(EstoqueAtual, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(Categoria.id != PRODUCTION_CATEGORY_ID)
    )
    if category_ids:
        query = query.filter(Categoria.id.in_(category_ids))
    if unit:
        query = query.filter(Ingrediente.unit == unit)

    rows = (
        query
        .group_by(Categoria.id, Categoria.name)
        .order_by(order(value_expr), Categoria.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardCategoryItem(
            id=row.id,
            name=row.name,
            value=_as_float(row.value),
            unit=unit,
        )
        for row in rows
    ]


def _stock_product_groups(
    db: Session,
    order,
    limit: int = 8,
    category_ids: Optional[list[str]] = None,
) -> list[DashboardUnitRankGroup]:
    return [
        DashboardUnitRankGroup(
            unit=unit,
            items=_stock_product_rows(db, order, limit=limit, unit=unit, category_ids=category_ids),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _stock_category_groups(
    db: Session,
    order,
    limit: int = 8,
    category_ids: Optional[list[str]] = None,
) -> list[DashboardUnitCategoryGroup]:
    return [
        DashboardUnitCategoryGroup(
            unit=unit,
            items=_stock_category_rows(db, order, limit=limit, unit=unit, category_ids=category_ids),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _output_product_rows(
    db: Session,
    order,
    limit: int = 8,
    unit: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
    days: Optional[int] = None,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardRankItem]:
    value_expr = func.coalesce(
        func.sum(Venda.quantity * ReceitaIngrediente.qty), 0
    ).label("value")
    query = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.unit,
            Categoria.name.label("category"),
            value_expr,
        )
        .outerjoin(Categoria, Ingrediente.category_id == Categoria.id)
        .outerjoin(
            ReceitaIngrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id
        )
        .outerjoin(Venda, Venda.recipe_id == ReceitaIngrediente.recipe_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    query = _apply_ingredient_category_filters(query, category_ids)
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=months,
        event_dates=event_dates,
    )
    if unit:
        query = query.filter(Ingrediente.unit == unit)

    rows = (
        query
        .group_by(Ingrediente.id, Ingrediente.name, Ingrediente.unit, Categoria.name)
        .order_by(order(value_expr), Ingrediente.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardRankItem(
            id=row.id,
            name=row.name,
            unit=row.unit,
            category=row.category,
            value=_as_float(row.value),
        )
        for row in rows
    ]


def _output_category_rows(
    db: Session,
    order,
    limit: int = 8,
    unit: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
    days: Optional[int] = None,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardCategoryItem]:
    value_expr = func.coalesce(
        func.sum(Venda.quantity * ReceitaIngrediente.qty), 0
    ).label("value")
    query = (
        db.query(Categoria.id, Categoria.name, value_expr)
        .join(Ingrediente, Ingrediente.category_id == Categoria.id)
        .outerjoin(
            ReceitaIngrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id
        )
        .outerjoin(Venda, Venda.recipe_id == ReceitaIngrediente.recipe_id)
        .filter(Categoria.id != PRODUCTION_CATEGORY_ID)
    )
    if category_ids:
        query = query.filter(Categoria.id.in_(category_ids))
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=months,
        event_dates=event_dates,
    )
    if unit:
        query = query.filter(Ingrediente.unit == unit)

    rows = (
        query
        .group_by(Categoria.id, Categoria.name)
        .order_by(order(value_expr), Categoria.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardCategoryItem(
            id=row.id,
            name=row.name,
            value=_as_float(row.value),
            unit=unit,
        )
        for row in rows
    ]


def _output_product_groups(
    db: Session,
    order,
    limit: int = 8,
    category_ids: Optional[list[str]] = None,
    days: Optional[int] = None,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardUnitRankGroup]:
    return [
        DashboardUnitRankGroup(
            unit=unit,
            items=_output_product_rows(
                db,
                order,
                limit=limit,
                unit=unit,
                category_ids=category_ids,
                days=days,
                all_period=all_period,
                date_from=date_from,
                date_to=date_to,
                month_keys=month_keys,
                years=years,
                months=months,
                event_dates=event_dates,
            ),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _output_category_groups(
    db: Session,
    order,
    limit: int = 8,
    category_ids: Optional[list[str]] = None,
    days: Optional[int] = None,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardUnitCategoryGroup]:
    return [
        DashboardUnitCategoryGroup(
            unit=unit,
            items=_output_category_rows(
                db,
                order,
                limit=limit,
                unit=unit,
                category_ids=category_ids,
                days=days,
                all_period=all_period,
                date_from=date_from,
                date_to=date_to,
                month_keys=month_keys,
                years=years,
                months=months,
                event_dates=event_dates,
            ),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _dashboard_filters(db: Session) -> DashboardFilters:
    categories = (
        db.query(Categoria.id, Categoria.name)
        .filter(Categoria.id != PRODUCTION_CATEGORY_ID)
        .order_by(Categoria.name)
        .all()
    )
    ingredients = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.category_id,
            Categoria.name.label("category"),
        )
        .join(Categoria, Ingrediente.category_id == Categoria.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Categoria.name, Ingrediente.name)
        .all()
    )
    holidays = (
        db.query(FeriadoRecife.data, FeriadoRecife.nome, FeriadoRecife.tipo)
        .order_by(FeriadoRecife.data)
        .all()
    )
    year_expr = func.extract("year", Venda.date_time).label("year")
    month_expr = func.extract("month", Venda.date_time).label("month")
    month_rows = (
        db.query(
            year_expr,
            month_expr,
        )
        .group_by(year_expr, month_expr)
        .order_by(year_expr, month_expr)
        .all()
    )
    return DashboardFilters(
        categories=[
            DashboardCategoryItem(id=row.id, name=row.name, value=0)
            for row in categories
        ],
        ingredients=[
            DashboardIngredientFilter(
                id=row.id,
                name=row.name,
                category_id=row.category_id,
                category=row.category,
            )
            for row in ingredients
        ],
        holidays=[
            DashboardHolidayFilter(date=row.data, name=row.nome, type=row.tipo)
            for row in holidays
        ],
        months=[
            DashboardMonthFilter(
                key=f"{int(row.year)}-{int(row.month):02d}",
                label=_month_year_label(date(int(row.year), int(row.month), 1)),
            )
            for row in month_rows
        ],
    )


def _dashboard_alerts(
    db: Session,
    limit: int = 10,
    category_ids: Optional[list[str]] = None,
    days: int = 28,
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    months: Optional[list[int]] = None,
    event_dates: Optional[list[date]] = None,
) -> list[DashboardAlert]:
    reference_date = db.query(func.max(func.date(Venda.date_time))).scalar()
    if reference_date is None:
        return []

    consumo_expr = func.sum(Venda.quantity * ReceitaIngrediente.qty).label("output")
    query = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.unit,
            Categoria.name.label("category"),
            func.coalesce(EstoqueAtual.qtd, 0).label("current_qty"),
            consumo_expr,
        )
        .join(Categoria, Ingrediente.category_id == Categoria.id)
        .outerjoin(EstoqueAtual, EstoqueAtual.ingrediente == Ingrediente.id)
        .join(ReceitaIngrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id)
        .join(Venda, Venda.recipe_id == ReceitaIngrediente.recipe_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    query = _apply_ingredient_category_filters(query, category_ids)
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=months,
        event_dates=event_dates,
    )
    rows = (
        query.group_by(
            Ingrediente.id,
            Ingrediente.name,
            Ingrediente.unit,
            Categoria.name,
            EstoqueAtual.qtd,
        )
        .all()
    )

    alerts: list[DashboardAlert] = []
    for row in rows:
        total_output = _as_float(row.output)
        if total_output <= 0:
            continue

        avg_daily_output = total_output / max(1, days)
        current_qty = _as_float(row.current_qty)
        coverage_days = current_qty / avg_daily_output if avg_daily_output else 999
        if coverage_days <= 3:
            severity = "Crítico"
        elif coverage_days <= 7:
            severity = "Atenção"
        else:
            severity = "Monitorar"

        alerts.append(
            DashboardAlert(
                ingredient_id=row.id,
                name=row.name,
                category=row.category,
                unit=row.unit,
                current_qty=round(current_qty, 3),
                avg_daily_output=round(avg_daily_output, 3),
                coverage_days=round(coverage_days, 1),
                suggested_qty=round(max(0, avg_daily_output * 7 - current_qty), 3),
                severity=severity,
            )
        )

    return sorted(alerts, key=lambda item: (item.coverage_days, -item.avg_daily_output))[
        :limit
    ]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard(
    category_ids: Optional[list[str]] = Query(default=None),
    days: int = Query(default=90, ge=1, le=730),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    top_stock_products_by_unit = _stock_product_groups(db, desc, category_ids=category_ids)
    bottom_stock_products_by_unit = _stock_product_groups(db, asc, category_ids=category_ids)
    top_stock_categories_by_unit = _stock_category_groups(db, desc, category_ids=category_ids)
    bottom_stock_categories_by_unit = _stock_category_groups(db, asc, category_ids=category_ids)
    output_kwargs = {
        "category_ids": category_ids,
        "days": days,
        "all_period": all_period,
        "date_from": date_from,
        "date_to": date_to,
        "month_keys": month_keys,
        "years": years,
        "months": month_numbers,
        "event_dates": event_dates,
    }
    top_output_products_by_unit = _output_product_groups(db, desc, **output_kwargs)
    bottom_output_products_by_unit = _output_product_groups(db, asc, **output_kwargs)
    top_output_categories_by_unit = _output_category_groups(db, desc, **output_kwargs)
    bottom_output_categories_by_unit = _output_category_groups(db, asc, **output_kwargs)

    return DashboardResponse(
        cards=DashboardCards(
            items=_dashboard_kpis(
                db,
                category_ids=category_ids,
                days=days,
                all_period=all_period,
                date_from=date_from,
                date_to=date_to,
                month_keys=month_keys,
                years=years,
                months=month_numbers,
                event_dates=event_dates,
            )
        ),
        top_stock_products_by_unit=top_stock_products_by_unit,
        bottom_stock_products_by_unit=bottom_stock_products_by_unit,
        top_stock_categories_by_unit=top_stock_categories_by_unit,
        bottom_stock_categories_by_unit=bottom_stock_categories_by_unit,
        top_output_products_by_unit=top_output_products_by_unit,
        bottom_output_products_by_unit=bottom_output_products_by_unit,
        top_output_categories_by_unit=top_output_categories_by_unit,
        bottom_output_categories_by_unit=bottom_output_categories_by_unit,
        alerts=_dashboard_alerts(
            db,
            category_ids=category_ids,
            days=days,
            all_period=all_period,
            date_from=date_from,
            date_to=date_to,
            month_keys=month_keys,
            years=years,
            months=month_numbers,
            event_dates=event_dates,
        ),
        filters=_dashboard_filters(db),
    )


@app.get("/api/dashboard/estoque-historico", response_model=list[DashboardHistoryPoint])
def get_dashboard_estoque_historico(
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    category_ids: Optional[list[str]] = Query(default=None),
    days: int = Query(default=90, ge=7, le=730),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    date_expr = func.date(Estoque.date_time).label("date")
    value_expr = func.coalesce(func.sum(Estoque.quantity), 0).label("value")
    query = (
        db.query(date_expr, value_expr)
        .join(Ingrediente, Estoque.ingredient_id == Ingrediente.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )
    query = _apply_date_filters(
        query,
        Estoque.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )

    if ingredient_id:
        query = query.filter(Ingrediente.id == ingredient_id)
    elif category_id:
        query = query.filter(Ingrediente.category_id == category_id)
    else:
        query = _apply_ingredient_category_filters(query, category_ids)

    rows = query.group_by(date_expr).order_by(date_expr).all()
    return [
        DashboardHistoryPoint(date=row.date, value=_as_float(row.value))
        for row in rows
    ]


def _filtered_recipe_ids_query(
    db: Session,
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    category_ids: Optional[list[str]] = None,
):
    query = db.query(ReceitaIngrediente.recipe_id).join(
        Ingrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id
    )
    if ingredient_id:
        query = query.filter(Ingrediente.id == ingredient_id)
    elif category_ids:
        query = query.filter(Ingrediente.category_id.in_(category_ids))
    elif category_id:
        query = query.filter(Ingrediente.category_id == category_id)
    else:
        query = query.filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    return query.distinct()


@app.get("/api/dashboard/vendas-historico", response_model=list[DashboardHistoryPoint])
def get_dashboard_vendas_historico(
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    category_ids: Optional[list[str]] = Query(default=None),
    days: int = Query(default=90, ge=7, le=730),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    date_expr = func.date(Venda.date_time).label("date")
    value_expr = func.coalesce(func.sum(Venda.quantity), 0).label("value")
    query = db.query(date_expr, value_expr)
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )

    if ingredient_id or category_id or category_ids:
        query = query.filter(
            Venda.recipe_id.in_(
                _filtered_recipe_ids_query(
                    db,
                    ingredient_id=ingredient_id,
                    category_id=category_id,
                    category_ids=category_ids,
                )
            )
        )

    rows = query.group_by(date_expr).order_by(date_expr).all()
    return [
        DashboardHistoryPoint(date=row.date, value=_as_float(row.value))
        for row in rows
    ]


@app.get("/api/dashboard/faturamento-resumo", response_model=DashboardRevenueSummary)
def get_dashboard_faturamento_resumo(
    months: int = Query(default=12, ge=3, le=36),
    category_ids: Optional[list[str]] = Query(default=None),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    reference_date = db.query(func.max(func.date(Venda.date_time))).scalar()
    if reference_date is None:
        return DashboardRevenueSummary(monthly=[], quarterly=[])

    start_date = (
        db.query(func.min(func.date(Venda.date_time))).scalar()
        if all_period
        else _shift_month_start(_month_start(reference_date), -(months - 1))
    )
    revenue_expr = func.coalesce(func.sum(Venda.quantity * Venda.unit_price), 0).label("value")

    year_expr = func.extract("year", Venda.date_time).label("year")
    month_expr = func.extract("month", Venda.date_time).label("month")
    month_rows = (
        db.query(year_expr, month_expr, revenue_expr)
        .filter(func.date(Venda.date_time) >= start_date)
    )
    month_query = _apply_date_filters(
        month_rows,
        Venda.date_time,
        db,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )
    if category_ids:
        month_query = month_query.filter(
            Venda.recipe_id.in_(_filtered_recipe_ids_query(db, category_ids=category_ids))
        )
    month_rows = month_query.group_by(year_expr, month_expr).order_by(year_expr, month_expr).all()
    monthly = [
        DashboardNamedMetric(
            key=f"{int(row.year)}-{int(row.month):02d}",
            label=_month_year_label(date(int(row.year), int(row.month), 1)),
            value=_as_float(row.value),
        )
        for row in month_rows
    ]

    quarter_expr = func.extract("quarter", Venda.date_time).label("quarter")
    quarter_rows = (
        db.query(year_expr, quarter_expr, revenue_expr)
        .filter(func.date(Venda.date_time) >= start_date)
    )
    quarter_query = _apply_date_filters(
        quarter_rows,
        Venda.date_time,
        db,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )
    if category_ids:
        quarter_query = quarter_query.filter(
            Venda.recipe_id.in_(_filtered_recipe_ids_query(db, category_ids=category_ids))
        )
    quarter_rows = quarter_query.group_by(year_expr, quarter_expr).order_by(year_expr, quarter_expr).all()
    quarterly = [
        DashboardNamedMetric(
            key=f"{int(row.year)}-Q{int(row.quarter)}",
            label=_quarter_label(int(row.year), int(row.quarter)),
            value=_as_float(row.value),
        )
        for row in quarter_rows
    ]

    return DashboardRevenueSummary(monthly=monthly, quarterly=quarterly)


@app.get("/api/dashboard/pedidos-semana", response_model=list[DashboardNamedMetric])
def get_dashboard_pedidos_semana(
    days: int = Query(default=90, ge=7, le=730),
    category_ids: Optional[list[str]] = Query(default=None),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    dow_expr = func.extract("dow", Venda.date_time).label("dow")
    value_expr = func.coalesce(func.sum(Venda.quantity), 0).label("value")
    query = db.query(dow_expr, value_expr)
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )
    if category_ids:
        query = query.filter(
            Venda.recipe_id.in_(_filtered_recipe_ids_query(db, category_ids=category_ids))
        )
    rows = query.group_by(dow_expr).all()
    by_dow = {int(row.dow): _as_float(row.value) for row in rows}
    labels = {
        0: "Dom",
        1: "Seg",
        2: "Ter",
        3: "Qua",
        4: "Qui",
        5: "Sex",
        6: "Sáb",
    }

    return [
        DashboardNamedMetric(key=str(dow), label=labels[dow], value=by_dow.get(dow, 0))
        for dow in [1, 2, 3, 4, 5, 6, 0]
    ]


@app.get("/api/dashboard/receitas-ranking", response_model=list[DashboardRecipeItem])
def get_dashboard_receitas_ranking(
    ingredient_id: Optional[str] = None,
    category_ids: Optional[list[str]] = Query(default=None),
    days: int = Query(default=90, ge=7, le=730),
    all_period: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month_keys: Optional[list[str]] = Query(default=None),
    years: Optional[list[int]] = Query(default=None),
    month_numbers: Optional[list[int]] = Query(default=None),
    event_types: Optional[list[str]] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    event_dates = _event_dates_for_types(db, event_types)
    quantity_expr = func.coalesce(func.sum(Venda.quantity), 0).label("quantity")
    revenue_expr = func.coalesce(func.sum(Venda.quantity * Venda.unit_price), 0).label("revenue")
    query = (
        db.query(Receita.id, Receita.name, quantity_expr, revenue_expr)
        .join(Venda, Venda.recipe_id == Receita.id)
    )
    query = _apply_date_filters(
        query,
        Venda.date_time,
        db,
        days=days,
        all_period=all_period,
        date_from=date_from,
        date_to=date_to,
        month_keys=month_keys,
        years=years,
        months=month_numbers,
        event_dates=event_dates,
    )

    if ingredient_id or category_ids:
        query = query.filter(
            Receita.id.in_(
                _filtered_recipe_ids_query(
                    db,
                    ingredient_id=ingredient_id,
                    category_ids=category_ids,
                )
            )
        )

    rows = (
        query
        .group_by(Receita.id, Receita.name)
        .order_by(desc(quantity_expr), Receita.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardRecipeItem(
            id=row.id,
            name=row.name,
            quantity=_as_float(row.quantity),
            revenue=_as_float(row.revenue),
        )
        for row in rows
    ]


@app.get("/api/estoque", response_model=list[IngredienteOut])
def get_estoque(
    category: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Ingrediente)
        .outerjoin(Categoria)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Categoria.name, Ingrediente.name)
    )
    if category:
        query = query.filter(or_(Ingrediente.category_id == category, Categoria.name == category))
    if q:
        query = query.filter(Ingrediente.name.ilike(f"%{q}%"))
    criticidade_run, criticidade_by_ingredient = _latest_criticidade_by_ingredient(db)
    items = query.all()
    if status:
        items = [
            item
            for item in items
            if _model_stock_status(item, criticidade_by_ingredient.get(item.id)) == status
        ]
    return [_ingrediente_out(item, criticidade_run, criticidade_by_ingredient) for item in items]


@app.get("/api/estoque/paginado", response_model=EstoquePaginado)
def get_estoque_paginado(
    category: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Ingrediente)
        .outerjoin(Categoria)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Categoria.name, Ingrediente.name)
    )
    if category:
        query = query.filter(or_(Ingrediente.category_id == category, Categoria.name == category))
    if q:
        query = query.filter(Ingrediente.name.ilike(f"%{q}%"))
    criticidade_run, criticidade_by_ingredient = _latest_criticidade_by_ingredient(db)
    items = query.all()
    if status:
        items = [
            item
            for item in items
            if _model_stock_status(item, criticidade_by_ingredient.get(item.id)) == status
        ]

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    page_items = items[offset: offset + page_size]

    return EstoquePaginado(
        items=[_ingrediente_out(item, criticidade_run, criticidade_by_ingredient) for item in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/export/estoque")
def export_estoque(
    format: str = Query(default="csv"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Data inicial maior que data final")

    rows = (
        db.query(
            Estoque.id,
            Estoque.date_time,
            Estoque.ingredient_id,
            Ingrediente.name.label("ingredient_name"),
            Categoria.name.label("category"),
            Ingrediente.unit,
            Estoque.quantity,
        )
        .join(Ingrediente, Ingrediente.id == Estoque.ingredient_id)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .filter(func.date(Estoque.date_time) >= date_from)
        .filter(func.date(Estoque.date_time) <= date_to)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Estoque.date_time.asc(), Ingrediente.name.asc())
        .all()
    )
    data = [
        {
            "id": row.id,
            "data_hora": row.date_time,
            "ingrediente_id": row.ingredient_id,
            "ingrediente": row.ingredient_name,
            "categoria": row.category,
            "unidade": row.unit,
            "quantidade": _as_float(row.quantity),
        }
        for row in rows
    ]
    return _export_response(
        data,
        f"estoque_{date_from.isoformat()}_{date_to.isoformat()}",
        format,
        "Historico de estoque",
        [
            "id",
            "data_hora",
            "ingrediente_id",
            "ingrediente",
            "categoria",
            "unidade",
            "quantidade",
        ],
    )


@app.patch("/api/estoque", response_model=ResultadoLote)
def update_estoque(lote: AtualizacaoLote, db: Session = Depends(get_db)):
    contagem = None
    if lote.contagem_id is not None:
        contagem = db.query(Contagem).filter(Contagem.id == lote.contagem_id).first()
        if contagem is None:
            raise HTTPException(status_code=404, detail="Contagem não encontrada")
        if contagem.status == "finalizada":
            contagem.status = "em_andamento"
            contagem.finalizada_em = None

    ids = [u.id for u in lote.updates]
    por_id = {
        i.id: i
        for i in db.query(Ingrediente)
        .filter(Ingrediente.id.in_(ids))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .all()
    }

    count = 0
    for atualizacao in lote.updates:
        ingrediente = por_id.get(atualizacao.id)
        if ingrediente is None:
            continue

        anterior = float(ingrediente.current_qty)
        if contagem is not None:
            delta = round(atualizacao.new_qty - anterior, 3)
            snapshot = _estoque_snapshot_for_ingredient(
                db,
                ingrediente.id,
                contagem.estoque_snapshot_data,
            )
            existing_log = (
                db.query(ContagemLog)
                .filter(ContagemLog.contagem_id == contagem.id)
                .filter(ContagemLog.ingrediente_id == ingrediente.id)
                .order_by(ContagemLog.criado_em.desc(), ContagemLog.id.desc())
                .first()
            )
            if existing_log is None:
                db.add(
                    ContagemLog(
                        contagem_id=contagem.id,
                        ingrediente_id=ingrediente.id,
                        estoque_id=snapshot.id if snapshot else None,
                        estoque_data=(
                            snapshot.date_time.date()
                            if snapshot and snapshot.date_time
                            else contagem.estoque_snapshot_data
                        ),
                        estoque_quantidade=snapshot.quantity if snapshot else None,
                        category_id=ingrediente.category_id,
                        categoria=ingrediente.category,
                        quantidade_anterior=anterior,
                        quantidade_nova=atualizacao.new_qty,
                        delta=delta,
                    )
                )
            else:
                existing_log.estoque_id = snapshot.id if snapshot else None
                existing_log.estoque_data = (
                    snapshot.date_time.date()
                    if snapshot and snapshot.date_time
                    else contagem.estoque_snapshot_data
                )
                existing_log.estoque_quantidade = snapshot.quantity if snapshot else None
                existing_log.category_id = ingrediente.category_id
                existing_log.categoria = ingrediente.category
                existing_log.quantidade_anterior = anterior
                existing_log.quantidade_nova = atualizacao.new_qty
                existing_log.delta = delta
                existing_log.criado_em = _now_recife()
            if ingrediente.estoque_atual is None:
                ingrediente.estoque_atual = EstoqueAtual(
                    id=f"CUR-{ingrediente.id}",
                    qtd=atualizacao.new_qty,
                    data=contagem.data_contagem,
                )
            else:
                ingrediente.estoque_atual.qtd = atualizacao.new_qty
                ingrediente.estoque_atual.data = contagem.data_contagem
        if round(atualizacao.new_qty, 3) == round(anterior, 3):
            continue
        db.add(
            LogContagem(
                ingrediente_id=ingrediente.id,
                quantidade_anterior=anterior,
                quantidade_nova=atualizacao.new_qty,
                delta=round(atualizacao.new_qty - anterior, 3),
                sessao=lote.session_label,
            )
        )
        if contagem is None and ingrediente.estoque_atual is None:
                ingrediente.estoque_atual = EstoqueAtual(
                    id=f"CUR-{ingrediente.id}",
                    qtd=atualizacao.new_qty,
                    data=_now_recife().date(),
                )
        elif contagem is None:
            ingrediente.estoque_atual.qtd = atualizacao.new_qty
            ingrediente.estoque_atual.data = _now_recife().date()
        count += 1

    db.commit()
    return ResultadoLote(
        ok=True,
        atualizados=count,
        contagem_id=contagem.id if contagem is not None else None,
    )


@app.patch("/api/ingredientes/{ingrediente_id}", response_model=IngredienteOut)
def update_ingrediente(
    ingrediente_id: str,
    atualizacao: AtualizacaoIngrediente,
    db: Session = Depends(get_db),
):
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado")

    payload = atualizacao.model_dump(exclude_none=True)
    category = payload.pop("category", None)
    category_id = payload.pop("category_id", None)
    payload.pop("price", None)
    payload.pop("min_qty", None)

    for field, value in payload.items():
        setattr(ingrediente, field, value)

    category_value = category_id or category
    if category_value:
        categoria = (
            db.query(Categoria)
            .filter(or_(Categoria.id == category_value, Categoria.name == category_value))
            .first()
        )
        if categoria is None:
            raise HTTPException(status_code=400, detail="Categoria não encontrada")
        ingrediente.category_id = categoria.id

    db.commit()
    db.refresh(ingrediente)
    return ingrediente


# ---------------------------------------------------------------------------
# Fornecedores
# ---------------------------------------------------------------------------


@app.get("/api/fornecedores", response_model=FornecedorListResponse)
def get_fornecedores(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Fornecedor,
            func.count(FornecedorIngrediente.ingredient_id).label("item_count"),
            func.avg(FornecedorIngrediente.price).label("avg_price"),
        )
        .outerjoin(
            FornecedorIngrediente,
            FornecedorIngrediente.supplier_id == Fornecedor.id,
        )
        .group_by(Fornecedor.id)
        .order_by(Fornecedor.name.asc())
        .all()
    )

    items = [
        FornecedorListItem(
            id=fornecedor.id,
            name=fornecedor.name,
            cnpj=fornecedor.cnpj,
            email=fornecedor.email,
            phone=fornecedor.phone,
            avg_delivery_time=fornecedor.avg_delivery_time,
            item_count=int(item_count or 0),
            avg_price=_as_float(avg_price) if avg_price is not None else None,
        )
        for fornecedor, item_count, avg_price in rows
    ]

    supplier_count = len(items)
    delivery_values = [
        item.avg_delivery_time for item in items if item.avg_delivery_time is not None
    ]
    avg_delivery_time = (
        sum(delivery_values) / len(delivery_values) if delivery_values else 0
    )
    avg_items_per_supplier = (
        sum(item.item_count for item in items) / supplier_count if supplier_count else 0
    )

    scored = [
        item
        for item in items
        if item.avg_price is not None and item.avg_delivery_time is not None
    ]
    best_supplier = None
    if scored:
        min_price = min(item.avg_price for item in scored if item.avg_price is not None)
        max_price = max(item.avg_price for item in scored if item.avg_price is not None)
        min_delivery = min(item.avg_delivery_time for item in scored if item.avg_delivery_time is not None)
        max_delivery = max(item.avg_delivery_time for item in scored if item.avg_delivery_time is not None)

        def score(item: FornecedorListItem) -> float:
            price_range = max_price - min_price
            delivery_range = max_delivery - min_delivery
            price_score = (
                ((item.avg_price or 0) - min_price) / price_range
                if price_range > 0
                else 0
            )
            delivery_score = (
                ((item.avg_delivery_time or 0) - min_delivery) / delivery_range
                if delivery_range > 0
                else 0
            )
            return price_score + delivery_score

        best_supplier = min(scored, key=score)

    return FornecedorListResponse(
        kpis=FornecedorKpis(
            supplier_count=supplier_count,
            avg_delivery_time=round(avg_delivery_time, 2),
            avg_items_per_supplier=round(avg_items_per_supplier, 2),
            best_value_supplier_id=best_supplier.id if best_supplier else None,
            best_value_supplier_name=best_supplier.name if best_supplier else None,
            best_value_detail=(
                f"R$ {best_supplier.avg_price:.2f} médio, "
                f"{best_supplier.avg_delivery_time} "
                f"{'dia' if best_supplier.avg_delivery_time == 1 else 'dias'}"
                if best_supplier
                else "Sem dados suficientes"
            ),
        ),
        items=items,
    )


@app.get("/api/export/fornecedores")
def export_fornecedores(
    format: str = Query(default="csv"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Fornecedor,
            func.count(FornecedorIngrediente.ingredient_id).label("item_count"),
            func.avg(FornecedorIngrediente.price).label("avg_price"),
        )
        .outerjoin(
            FornecedorIngrediente,
            FornecedorIngrediente.supplier_id == Fornecedor.id,
        )
        .group_by(Fornecedor.id)
        .order_by(Fornecedor.name.asc())
        .all()
    )
    data = [
        {
            "id": fornecedor.id,
            "nome": fornecedor.name,
            "cnpj": fornecedor.cnpj,
            "email": fornecedor.email,
            "telefone": fornecedor.phone,
            "prazo_medio_entrega_dias": _as_float(fornecedor.avg_delivery_time)
            if fornecedor.avg_delivery_time is not None
            else None,
            "itens_fornecidos": int(item_count or 0),
            "preco_medio": _as_float(avg_price) if avg_price is not None else None,
        }
        for fornecedor, item_count, avg_price in rows
    ]
    return _export_response(
        data,
        "fornecedores",
        format,
        "Fornecedores cadastrados",
        [
            "id",
            "nome",
            "cnpj",
            "email",
            "telefone",
            "prazo_medio_entrega_dias",
            "itens_fornecidos",
            "preco_medio",
        ],
    )


@app.post("/api/fornecedores", response_model=FornecedorOut)
def create_fornecedor(payload: FornecedorCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome do fornecedor é obrigatório")

    last_id = (
        db.query(Fornecedor.id)
        .filter(Fornecedor.id.like("FOR%"))
        .order_by(Fornecedor.id.desc())
        .first()
    )
    next_number = 1
    if last_id:
        try:
            next_number = int(last_id[0].replace("FOR", "")) + 1
        except ValueError:
            next_number = db.query(func.count(Fornecedor.id)).scalar() + 1

    supplier_id = f"FOR{next_number:04d}"
    while db.query(Fornecedor).filter(Fornecedor.id == supplier_id).first():
        next_number += 1
        supplier_id = f"FOR{next_number:04d}"

    ingredient_ids = [item.ingredient_id for item in payload.ingredients]
    existing_ingredients = {
        ingredient.id
        for ingredient in db.query(Ingrediente)
        .filter(Ingrediente.id.in_(ingredient_ids))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .all()
    }
    missing = sorted(set(ingredient_ids) - existing_ingredients)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Ingredientes inválidos para fornecedor: {', '.join(missing)}",
        )

    fornecedor = Fornecedor(
        id=supplier_id,
        name=name,
        cnpj=payload.cnpj,
        email=payload.email,
        phone=payload.phone,
        avg_delivery_time=payload.avg_delivery_time,
    )
    db.add(fornecedor)
    for item in payload.ingredients:
        db.add(
            FornecedorIngrediente(
                supplier_id=supplier_id,
                ingredient_id=item.ingredient_id,
                price=item.price,
                discount_percent=item.discount_percent,
                min_to_discount=item.min_to_discount,
            )
        )

    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@app.get("/api/fornecedores/{fornecedor_id}", response_model=FornecedorProfileResponse)
def get_fornecedor_profile(fornecedor_id: str, db: Session = Depends(get_db)):
    fornecedor = db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()
    if fornecedor is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    product_rows = (
        db.query(
            Ingrediente.id,
            Ingrediente.name,
            Categoria.name.label("category"),
            EstoqueAtual.qtd,
            Ingrediente.unit,
            FornecedorIngrediente.price,
        )
        .join(FornecedorIngrediente, FornecedorIngrediente.ingredient_id == Ingrediente.id)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .outerjoin(EstoqueAtual, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(FornecedorIngrediente.supplier_id == fornecedor_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Ingrediente.name.asc())
        .all()
    )
    products = [
        FornecedorProductOut(
            ingredient_id=ingredient_id,
            name=name,
            category=category,
            current_qty=_as_float(qtd),
            unit=unit,
            unit_price=_as_float(price),
        )
        for ingredient_id, name, category, qtd, unit, price in product_rows
    ]

    order_rows = (
        db.query(
            Pedido.id,
            Pedido.data_pedido,
            func.sum(Pedido.qty).label("items_qty"),
            func.sum(Pedido.valor).label("total_value"),
            Pedido.status,
        )
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .filter(Pedido.supplier_id == fornecedor_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .group_by(Pedido.id, Pedido.data_pedido, Pedido.status)
        .order_by(Pedido.data_pedido.desc(), Pedido.id.desc())
        .all()
    )
    orders = [
        FornecedorOrderOut(
            id=order_id,
            order_date=order_date,
            items_qty=_as_float(items_qty),
            total_value=_as_float(total_value),
            status=status,
        )
        for order_id, order_date, items_qty, total_value, status in order_rows
    ]

    lead_time = (
        db.query(func.avg(Pedido.data_prevista - Pedido.data_pedido))
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .filter(Pedido.supplier_id == fornecedor_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .scalar()
    )
    orders_count = len(orders)
    delivered_count = sum(
        1 for order in orders if order.status.lower() == "entregue"
    )
    delivery_rate = (delivered_count / orders_count) * 100 if orders_count else 0

    return FornecedorProfileResponse(
        supplier=fornecedor,
        kpis=FornecedorProfileKpis(
            avg_lead_time=round(_as_float(lead_time), 2),
            orders_count=orders_count,
            delivery_rate=round(delivery_rate, 2),
        ),
        products=products,
        orders=orders,
    )


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------


def _pedido_group_key(supplier_id: str, order_date: date) -> str:
    return f"{supplier_id}_{order_date.isoformat()}"


def _discount_rate(discount_percent) -> float:
    value = _as_float(discount_percent)
    return value / 100 if value > 1 else value


def _effective_unit_price(
    price,
    discount_percent,
    min_to_discount,
    qty: float,
) -> tuple[float, bool]:
    unit_price = _as_float(price)
    min_qty = _as_float(min_to_discount)
    rate = _discount_rate(discount_percent)
    applies = rate > 0 and qty >= min_qty
    if applies:
        unit_price *= 1 - rate
    return round(unit_price, 4), applies


def _option_total(price, discount_percent, min_to_discount, qty: float) -> float:
    effective_price, _ = _effective_unit_price(
        price,
        discount_percent,
        min_to_discount,
        qty,
    )
    return round(effective_price * qty, 2)


def _next_pedido_id(db: Session, reserved_ids: Optional[set[str]] = None) -> str:
    reserved_ids = reserved_ids if reserved_ids is not None else set()
    last_id = (
        db.query(Pedido.id)
        .filter(Pedido.id.like("PED%"))
        .order_by(Pedido.id.desc())
        .first()
    )
    next_number = 1
    if last_id:
        try:
            next_number = int(last_id[0].replace("PED", "")) + 1
        except ValueError:
            next_number = db.query(func.count(Pedido.id)).scalar() + 1

    pedido_id = f"PED{next_number:012d}"
    while pedido_id in reserved_ids or db.query(Pedido).filter(Pedido.id == pedido_id).first():
        next_number += 1
        pedido_id = f"PED{next_number:012d}"
    reserved_ids.add(pedido_id)
    return pedido_id


def _add_pedidos_to_estoque_atual(
    db: Session,
    pedidos: list[Pedido],
    delivery_date: date,
) -> None:
    received_by_ingredient: dict[str, float] = {}
    for pedido in pedidos:
        received_by_ingredient[pedido.ingredient_id] = (
            received_by_ingredient.get(pedido.ingredient_id, 0.0)
            + _as_float(pedido.qty)
        )

    for ingredient_id, received_qty in received_by_ingredient.items():
        db.execute(
            text(
                """
                INSERT INTO estoque_atual (id, ingrediente, qtd, data)
                VALUES (:id, :ingrediente, :qtd, :data)
                ON CONFLICT (ingrediente) DO UPDATE
                SET qtd = estoque_atual.qtd + EXCLUDED.qtd,
                    data = EXCLUDED.data
                """
            ),
            {
                "id": f"CUR-{ingredient_id}",
                "ingrediente": ingredient_id,
                "qtd": received_qty,
                "data": delivery_date,
            },
        )


def _pedido_base_query(db: Session):
    return (
        db.query(
            Pedido.id,
            Pedido.supplier_id,
            Fornecedor.name.label("supplier_name"),
            Pedido.ingredient_id,
            Ingrediente.name.label("ingredient_name"),
            Pedido.data_pedido,
            Pedido.qty,
            Pedido.valor,
            Pedido.status,
            Pedido.data_prevista,
        )
        .join(Fornecedor, Fornecedor.id == Pedido.supplier_id)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )


def _apply_pedido_filters(
    query,
    status: Optional[str],
    supplier_id: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
):
    if status:
        query = query.filter(Pedido.status == status)
    if supplier_id:
        query = query.filter(Pedido.supplier_id == supplier_id)
    if date_from:
        query = query.filter(Pedido.data_pedido >= date_from)
    if date_to:
        query = query.filter(Pedido.data_pedido <= date_to)
    return query


def _pedido_group_query(db: Session):
    return (
        db.query(
            Pedido.supplier_id,
            Fornecedor.name.label("supplier_name"),
            Pedido.data_pedido,
            func.max(Pedido.data_prevista).label("data_prevista"),
            func.count(func.distinct(Pedido.ingredient_id)).label("ingredients_count"),
            func.sum(Pedido.qty).label("items_qty"),
            func.sum(Pedido.valor).label("total_value"),
            func.sum(
                case((Pedido.status == "em_transito", 1), else_=0)
            ).label("transit_count"),
        )
        .join(Fornecedor, Fornecedor.id == Pedido.supplier_id)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .group_by(Pedido.supplier_id, Fornecedor.name, Pedido.data_pedido)
    )


def _serialize_pedido_group(row) -> PedidoGroupOut:
    return PedidoGroupOut(
        group_key=_pedido_group_key(row.supplier_id, row.data_pedido),
        supplier_id=row.supplier_id,
        supplier_name=row.supplier_name,
        order_date=row.data_pedido,
        expected_date=row.data_prevista,
        status="em_transito" if int(row.transit_count or 0) > 0 else "entregue",
        ingredients_count=int(row.ingredients_count or 0),
        items_qty=_as_float(row.items_qty),
        total_value=_as_float(row.total_value),
    )


def _get_pedido_group(
    db: Session,
    supplier_id: str,
    order_date: date,
    status: Optional[str] = None,
) -> Optional[PedidoGroupOut]:
    row = _apply_pedido_filters(
        _pedido_group_query(db),
        status,
        supplier_id,
        order_date,
        order_date,
    ).first()
    return _serialize_pedido_group(row) if row else None


def _serialize_pedido(row) -> PedidoOut:
    return PedidoOut(
        id=row.id,
        supplier_id=row.supplier_id,
        supplier_name=row.supplier_name,
        ingredient_id=row.ingredient_id,
        ingredient_name=row.ingredient_name,
        order_date=row.data_pedido,
        items_qty=_as_float(row.qty),
        total_value=_as_float(row.valor),
        status=row.status,
        expected_date=row.data_prevista,
    )


def _send_pedido_emails(
    email_groups: dict[str, dict],
    order_date: date,
) -> list[PedidoEmailResult]:
    settings_error = None
    try:
        settings = get_smtp_settings()
    except Exception as exc:
        logger.exception("Configuracao SMTP invalida")
        settings = None
        settings_error = str(exc)
    results: list[PedidoEmailResult] = []

    for supplier_id, group in sorted(
        email_groups.items(),
        key=lambda item: item[1]["supplier_name"],
    ):
        supplier_name = group["supplier_name"]
        supplier_email = group.get("email")

        if not supplier_email:
            results.append(
                PedidoEmailResult(
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    email=supplier_email,
                    status="missing_email",
                    message="Fornecedor sem email cadastrado.",
                )
            )
            continue

        if settings_error is not None:
            results.append(
                PedidoEmailResult(
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    email=supplier_email,
                    status="failed",
                    message=f"Configuracao SMTP invalida: {settings_error}",
                )
            )
            continue

        if settings is None:
            results.append(
                PedidoEmailResult(
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    email=supplier_email,
                    status="disabled",
                    message="SMTP nao configurado.",
                )
            )
            continue

        order_email = OrderEmail(
            supplier_name=supplier_name,
            supplier_email=supplier_email,
            order_date=order_date,
            expected_date=group["expected_date"],
            items=group["items"],
        )
        try:
            send_order_email(order_email, settings)
        except Exception as exc:
            logger.exception(
                "Falha ao enviar email do pedido para fornecedor %s",
                supplier_id,
            )
            results.append(
                PedidoEmailResult(
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    email=supplier_email,
                    status="failed",
                    message=f"Falha ao enviar email: {exc}",
                )
            )
            continue

        results.append(
            PedidoEmailResult(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                email=supplier_email,
                status="sent",
                message="Email enviado com sucesso.",
            )
        )

    return results


@app.post("/api/pedidos/recomendacao", response_model=PedidoRecommendationResponse)
def recommend_pedidos(
    payload: PedidoRecommendationRequest,
    db: Session = Depends(get_db),
):
    today = date.today()
    response_items: list[PedidoRecommendationItem] = []
    grouped: dict[str, dict] = {}

    for item in payload.items:
        ingredient = (
            db.query(Ingrediente)
            .filter(Ingrediente.id == item.ingredient_id)
            .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
            .first()
        )
        if ingredient is None:
            raise HTTPException(
                status_code=400,
                detail=f"Ingrediente inválido: {item.ingredient_id}",
            )

        option_rows = (
            db.query(
                FornecedorIngrediente.supplier_id,
                Fornecedor.name.label("supplier_name"),
                Fornecedor.avg_delivery_time,
                FornecedorIngrediente.price,
                FornecedorIngrediente.discount_percent,
                FornecedorIngrediente.min_to_discount,
            )
            .join(Fornecedor, Fornecedor.id == FornecedorIngrediente.supplier_id)
            .filter(FornecedorIngrediente.ingredient_id == item.ingredient_id)
            .order_by(Fornecedor.name.asc())
            .all()
        )

        raw_options = []
        for row in option_rows:
            delivery_days = int(row.avg_delivery_time or 0)
            effective_unit_price, discount_applied = _effective_unit_price(
                row.price,
                row.discount_percent,
                row.min_to_discount,
                item.qty,
            )
            raw_options.append(
                {
                    "supplier_id": row.supplier_id,
                    "supplier_name": row.supplier_name,
                    "unit_price": _as_float(row.price),
                    "discount_percent": _as_float(row.discount_percent),
                    "min_to_discount": _as_float(row.min_to_discount),
                    "discount_applied": discount_applied,
                    "effective_unit_price": effective_unit_price,
                    "total_value": round(effective_unit_price * item.qty, 2),
                    "delivery_time_days": delivery_days,
                    "expected_date": today + timedelta(days=delivery_days),
                }
            )

        recommended = None
        if raw_options:
            recommended = min(
                raw_options,
                key=lambda option: (
                    option["total_value"],
                    option["delivery_time_days"],
                    -option["discount_percent"],
                    option["supplier_name"],
                ),
            )

        options: list[SupplierOption] = []
        for option in raw_options:
            detractors: list[str] = []
            if recommended and option["supplier_id"] != recommended["supplier_id"]:
                if option["total_value"] > recommended["total_value"] + 0.005:
                    detractors.append("mais caro")
                if option["delivery_time_days"] > recommended["delivery_time_days"]:
                    detractors.append("entrega mais lenta")
                if option["discount_percent"] < recommended["discount_percent"]:
                    detractors.append("desconto menor")
                if recommended["discount_applied"] and not option["discount_applied"]:
                    detractors.append("não aplica desconto")
            options.append(
                SupplierOption(
                    **option,
                    detractors=detractors,
                    recommended=bool(
                        recommended
                        and option["supplier_id"] == recommended["supplier_id"]
                    ),
                )
            )

        options.sort(
            key=lambda option: (
                option.total_value,
                option.delivery_time_days,
                -option.discount_percent,
                option.supplier_name,
            )
        )

        response_items.append(
            PedidoRecommendationItem(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                category=ingredient.category,
                unit=ingredient.unit,
                qty=item.qty,
                recommended_supplier_id=(
                    recommended["supplier_id"] if recommended else None
                ),
                options=options,
            )
        )

        if recommended:
            group = grouped.setdefault(
                recommended["supplier_id"],
                {
                    "supplier_id": recommended["supplier_id"],
                    "supplier_name": recommended["supplier_name"],
                    "expected_date": recommended["expected_date"],
                    "total_value": 0.0,
                    "items": [],
                },
            )
            group["expected_date"] = max(
                group["expected_date"],
                recommended["expected_date"],
            )
            group["total_value"] += recommended["total_value"]
            group["items"].append(
                RecommendedOrderItem(
                    ingredient_id=ingredient.id,
                    ingredient_name=ingredient.name,
                    qty=item.qty,
                    unit=ingredient.unit,
                    total_value=recommended["total_value"],
                    expected_date=recommended["expected_date"],
                )
            )

    groups = [
        RecommendedOrderGroup(
            supplier_id=group["supplier_id"],
            supplier_name=group["supplier_name"],
            expected_date=group["expected_date"],
            total_value=round(group["total_value"], 2),
            items=group["items"],
        )
        for group in grouped.values()
    ]
    groups.sort(key=lambda group: (group.expected_date, group.supplier_name))

    return PedidoRecommendationResponse(items=response_items, groups=groups)


@app.post("/api/pedidos", response_model=PedidoCreateResponse)
def create_pedidos(payload: PedidoCreateRequest, db: Session = Depends(get_db)):
    today = date.today()
    aggregated: dict[tuple[str, str], float] = {}
    for item in payload.items:
        key = (item.supplier_id, item.ingredient_id)
        aggregated[key] = aggregated.get(key, 0.0) + item.qty

    created = 0
    updated = 0
    touched_groups: set[tuple[str, date]] = set()
    reserved_pedido_ids: set[str] = set()
    email_groups: dict[str, dict] = {}

    for (supplier_id, ingredient_id), qty in aggregated.items():
        option = (
            db.query(
                FornecedorIngrediente,
                Fornecedor.avg_delivery_time.label("avg_delivery_time"),
                Fornecedor.name.label("supplier_name"),
                Fornecedor.email.label("supplier_email"),
                Ingrediente.name.label("ingredient_name"),
                Ingrediente.unit.label("ingredient_unit"),
            )
            .join(Fornecedor, Fornecedor.id == FornecedorIngrediente.supplier_id)
            .join(Ingrediente, Ingrediente.id == FornecedorIngrediente.ingredient_id)
            .filter(FornecedorIngrediente.supplier_id == supplier_id)
            .filter(FornecedorIngrediente.ingredient_id == ingredient_id)
            .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
            .first()
        )
        if option is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Fornecedor inválido para ingrediente: "
                    f"{supplier_id}/{ingredient_id}"
                ),
            )

        (
            fornecedor_ingrediente,
            avg_delivery_time,
            supplier_name,
            supplier_email,
            ingredient_name,
            ingredient_unit,
        ) = option
        delivery_days = int(avg_delivery_time or 0)
        expected_date = today + timedelta(days=delivery_days)
        email_unit_price, _ = _effective_unit_price(
            fornecedor_ingrediente.price,
            fornecedor_ingrediente.discount_percent,
            fornecedor_ingrediente.min_to_discount,
            qty,
        )
        email_group = email_groups.setdefault(
            supplier_id,
            {
                "supplier_name": supplier_name,
                "email": supplier_email,
                "expected_date": expected_date,
                "items": [],
            },
        )
        email_group["expected_date"] = max(email_group["expected_date"], expected_date)
        email_group["items"].append(
            OrderEmailItem(
                name=ingredient_name,
                qty=qty,
                unit=ingredient_unit,
                unit_price=email_unit_price,
                total_value=round(email_unit_price * qty, 2),
            )
        )

        existing = (
            db.query(Pedido)
            .filter(Pedido.supplier_id == supplier_id)
            .filter(Pedido.ingredient_id == ingredient_id)
            .filter(Pedido.data_pedido == today)
            .filter(Pedido.status == "em_transito")
            .first()
        )

        if existing:
            new_qty = _as_float(existing.qty) + qty
            existing.qty = new_qty
            existing.valor = _option_total(
                fornecedor_ingrediente.price,
                fornecedor_ingrediente.discount_percent,
                fornecedor_ingrediente.min_to_discount,
                new_qty,
            )
            existing.data_prevista = expected_date
            existing.status = "em_transito"
            updated += 1
        else:
            db.add(
                Pedido(
                    id=_next_pedido_id(db, reserved_pedido_ids),
                    supplier_id=supplier_id,
                    ingredient_id=ingredient_id,
                    qty=qty,
                    valor=_option_total(
                        fornecedor_ingrediente.price,
                        fornecedor_ingrediente.discount_percent,
                        fornecedor_ingrediente.min_to_discount,
                        qty,
                    ),
                    data_pedido=today,
                    status="em_transito",
                    data_prevista=expected_date,
                )
            )
            created += 1

        touched_groups.add((supplier_id, today))

    db.commit()
    email_results = _send_pedido_emails(email_groups, today)

    groups = [
        group
        for supplier_id, order_date in sorted(touched_groups)
        if (group := _get_pedido_group(db, supplier_id, order_date)) is not None
    ]

    return PedidoCreateResponse(
        groups=groups,
        created=created,
        updated=updated,
        email_results=email_results,
    )


@app.get("/api/pedidos", response_model=PedidoPaginado)
def get_pedidos(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = _apply_pedido_filters(
        _pedido_group_query(db),
        status,
        supplier_id,
        date_from,
        date_to,
    )
    query = query.filter(Pedido.status != "em_transito")
    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    rows = (
        query.order_by(Pedido.data_pedido.desc(), Fornecedor.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PedidoPaginado(
        items=[_serialize_pedido_group(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/export/pedidos")
def export_pedidos(
    format: str = Query(default="csv"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Data inicial maior que data final")

    rows = (
        db.query(
            Pedido.id,
            Pedido.data_pedido,
            Pedido.supplier_id,
            Fornecedor.name.label("supplier_name"),
            Pedido.ingredient_id,
            Ingrediente.name.label("ingredient_name"),
            Categoria.name.label("category"),
            Ingrediente.unit,
            Pedido.qty,
            Pedido.valor,
            Pedido.status,
            Pedido.data_prevista,
        )
        .join(Fornecedor, Fornecedor.id == Pedido.supplier_id)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .filter(Pedido.data_pedido >= date_from)
        .filter(Pedido.data_pedido <= date_to)
        .order_by(Pedido.data_pedido.asc(), Fornecedor.name.asc(), Ingrediente.name.asc())
        .all()
    )
    data = [
        {
            "pedido_id": row.id,
            "data_pedido": row.data_pedido,
            "fornecedor_id": row.supplier_id,
            "fornecedor": row.supplier_name,
            "ingrediente_id": row.ingredient_id,
            "ingrediente": row.ingredient_name,
            "categoria": row.category,
            "unidade": row.unit,
            "quantidade": _as_float(row.qty),
            "valor_total": _as_float(row.valor),
            "status": row.status,
            "data_prevista": row.data_prevista,
        }
        for row in rows
    ]
    return _export_response(
        data,
        f"pedidos_{date_from.isoformat()}_{date_to.isoformat()}",
        format,
        "Historico de pedidos",
        [
            "pedido_id",
            "data_pedido",
            "fornecedor_id",
            "fornecedor",
            "ingrediente_id",
            "ingrediente",
            "categoria",
            "unidade",
            "quantidade",
            "valor_total",
            "status",
            "data_prevista",
        ],
    )


@app.get("/api/pedidos/em-transito", response_model=list[PedidoGroupOut])
def get_pedidos_em_transito(
    supplier_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    rows = (
        _apply_pedido_filters(
            _pedido_group_query(db),
            "em_transito",
            supplier_id,
            date_from,
            date_to,
        )
        .order_by(func.max(Pedido.data_prevista).asc(), Pedido.data_pedido.desc())
        .all()
    )
    return [_serialize_pedido_group(row) for row in rows]


@app.get(
    "/api/pedidos/grupos/{supplier_id}/{order_date}",
    response_model=PedidoDetailResponse,
)
def get_pedido_group_detail(
    supplier_id: str,
    order_date: date,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Pedido.id,
            Pedido.supplier_id,
            Fornecedor.name.label("supplier_name"),
            Pedido.data_pedido,
            Pedido.data_prevista,
            Pedido.status,
            Pedido.ingredient_id,
            Ingrediente.name.label("ingredient_name"),
            Categoria.name.label("category"),
            Ingrediente.unit,
            Pedido.qty,
            Pedido.valor,
        )
        .join(Fornecedor, Fornecedor.id == Pedido.supplier_id)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .filter(Pedido.supplier_id == supplier_id)
        .filter(Pedido.data_pedido == order_date)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Ingrediente.name.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    items = [
        PedidoDetailItem(
            ingredient_id=row.ingredient_id,
            ingredient_name=row.ingredient_name,
            category=row.category,
            unit=row.unit,
            qty=_as_float(row.qty),
            unit_price=(
                _as_float(row.valor) / _as_float(row.qty)
                if _as_float(row.qty) > 0
                else 0
            ),
            total_value=_as_float(row.valor),
        )
        for row in rows
    ]
    first = rows[0]
    expected_date = max(row.data_prevista for row in rows)
    status = (
        "em_transito"
        if any(row.status == "em_transito" for row in rows)
        else "entregue"
    )
    group_key = _pedido_group_key(supplier_id, order_date)

    return PedidoDetailResponse(
        id=group_key,
        group_key=group_key,
        supplier_id=first.supplier_id,
        supplier_name=first.supplier_name,
        order_date=first.data_pedido,
        expected_date=expected_date,
        status=status,
        items_qty=sum(item.qty for item in items),
        total_value=sum(item.total_value for item in items),
        items=items,
    )


@app.patch(
    "/api/pedidos/grupos/{supplier_id}/{order_date}/entregar",
    response_model=PedidoDetailResponse,
)
def mark_pedido_group_delivered(
    supplier_id: str,
    order_date: date,
    db: Session = Depends(get_db),
):
    pedidos = (
        db.query(Pedido)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .filter(Pedido.supplier_id == supplier_id)
        .filter(Pedido.data_pedido == order_date)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .all()
    )
    if not pedidos:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    delivery_time = _now_recife()
    pending_pedidos = [pedido for pedido in pedidos if pedido.status == "em_transito"]
    _add_pedidos_to_estoque_atual(db, pending_pedidos, delivery_time.date())

    for pedido in pedidos:
        if pedido.status == "em_transito":
            pedido.estoque_aplicado_em = delivery_time
        pedido.status = "entregue"

    db.commit()
    return get_pedido_group_detail(supplier_id, order_date, db)


@app.get("/api/pedidos/{pedido_id}", response_model=PedidoDetailResponse)
def get_pedido_detail(pedido_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(
            Pedido.id,
            Pedido.supplier_id,
            Fornecedor.name.label("supplier_name"),
            Pedido.data_pedido,
            Pedido.data_prevista,
            Pedido.status,
            Pedido.ingredient_id,
            Ingrediente.name.label("ingredient_name"),
            Categoria.name.label("category"),
            Ingrediente.unit,
            Pedido.qty,
            Pedido.valor,
        )
        .join(Fornecedor, Fornecedor.id == Pedido.supplier_id)
        .join(Ingrediente, Ingrediente.id == Pedido.ingredient_id)
        .join(Categoria, Categoria.id == Ingrediente.category_id)
        .filter(Pedido.id == pedido_id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .order_by(Ingrediente.name.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    items = [
        PedidoDetailItem(
            ingredient_id=row.ingredient_id,
            ingredient_name=row.ingredient_name,
            category=row.category,
            unit=row.unit,
            qty=_as_float(row.qty),
            unit_price=(
                _as_float(row.valor) / _as_float(row.qty)
                if _as_float(row.qty) > 0
                else 0
            ),
            total_value=_as_float(row.valor),
        )
        for row in rows
    ]
    first = rows[0]

    return PedidoDetailResponse(
        id=first.id,
        group_key=_pedido_group_key(first.supplier_id, first.data_pedido),
        supplier_id=first.supplier_id,
        supplier_name=first.supplier_name,
        order_date=first.data_pedido,
        expected_date=first.data_prevista,
        status=first.status,
        items_qty=sum(item.qty for item in items),
        total_value=sum(item.total_value for item in items),
        items=items,
    )


# ---------------------------------------------------------------------------
# Log de contagem
# ---------------------------------------------------------------------------

def _serializa_log(e: LogContagem) -> LogContagemOut:
    return LogContagemOut(
        id=e.id,
        ingrediente_id=e.ingrediente_id,
        ingrediente_nome=e.ingrediente.name,
        unit=e.ingrediente.unit,
        quantidade_anterior=float(e.quantidade_anterior),
        quantidade_nova=float(e.quantidade_nova),
        delta=float(e.delta),
        sessao=e.sessao,
        criado_em=e.criado_em,
    )


@app.get("/api/log", response_model=list[LogContagemOut])
def get_log(
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(LogContagem)
        .join(Ingrediente)
        .order_by(LogContagem.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [_serializa_log(e) for e in entries]


@app.get("/api/log/{ingrediente_id}", response_model=list[LogContagemOut])
def get_log_ingrediente(ingrediente_id: str, db: Session = Depends(get_db)):
    if not db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first():
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado")

    entries = (
        db.query(LogContagem)
        .filter(LogContagem.ingrediente_id == ingrediente_id)
        .join(Ingrediente)
        .order_by(LogContagem.criado_em.desc())
        .all()
    )
    return [_serializa_log(e) for e in entries]


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------

def _normalize_agent_question(value: str) -> str:
    ascii_text = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _is_purchase_needed_question(message: str) -> bool:
    normalized = _normalize_agent_question(message)
    has_item = any(term in normalized for term in ("item", "itens", "ingrediente", "insumo"))
    has_purchase = any(term in normalized for term in ("compra", "comprar", "repor", "reposicao"))
    has_need = any(term in normalized for term in ("precis", "necess", "alerta", "critico"))
    return has_item and has_purchase and has_need


def _purchase_needed_fallback_rows() -> tuple[list[dict], int]:
    with engine.connect() as conn:
        total = int(conn.execute(text(PURCHASE_NEEDED_FALLBACK_COUNT_SQL)).scalar() or 0)
        result = conn.execute(
            text(PURCHASE_NEEDED_FALLBACK_SQL),
            {"limit": AGENT_ROWS_PREVIEW_LIMIT},
        )
        return [dict(row._mapping) for row in result], total


def _agent_answer(ctx: dict, row_count: int) -> str:
    if ctx.get("answer"):
        return str(ctx["answer"])

    if not ctx.get("is_valid"):
        return (
            ctx.get("error_message")
            or "Nao consegui responder essa pergunta com os dados disponiveis."
        )

    if row_count == 0:
        return "Nao encontrei registros para essa pergunta."
    if row_count == 1:
        return "Encontrei 1 registro relacionado a sua pergunta."
    return f"Encontrei {row_count} registros relacionados a sua pergunta."


@app.post("/api/agent/chat", response_model=AgentChatResponse)
def chat_with_agent(payload: AgentChatRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    session_id = payload.session_id or f"agent-{uuid4().hex}"

    try:
        ctx = perguntar(message, session_id=session_id)
    except Exception as exc:
        ctx = {
            "is_valid": False,
            "error_type": "erro_execucao",
            "error_message": f"Erro ao chamar o agente: {exc}",
            "rows": [],
        }

    rows = ctx.get("rows") or []
    fallback_row_count: Optional[int] = None
    if not rows and _is_purchase_needed_question(message):
        fallback_rows, fallback_total = _purchase_needed_fallback_rows()
        if fallback_rows:
            ctx = {
                **ctx,
                "is_valid": True,
                "error_type": None,
                "error_message": None,
                "answer": (
                    "Encontrei itens com indicacao de compra na base analitica "
                    "mais recente de reposicao."
                ),
                "rows": fallback_rows,
            }
            rows = fallback_rows
            fallback_row_count = fallback_total

    preview_rows = rows[:AGENT_ROWS_PREVIEW_LIMIT]
    columns = list(preview_rows[0].keys()) if preview_rows else []
    row_count = fallback_row_count if fallback_row_count is not None else len(rows)

    return AgentChatResponse(
        session_id=session_id,
        answer=_agent_answer(ctx, row_count),
        rows=preview_rows,
        columns=columns,
        row_count=row_count,
        is_valid=bool(ctx.get("is_valid")),
        error_type=ctx.get("error_type"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
