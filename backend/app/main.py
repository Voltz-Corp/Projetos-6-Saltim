import math
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from .database import engine, Base, get_db, run_sql_loaders
from .models import (
    Categoria,
    Estoque,
    EstoqueAtual,
    Ingrediente,
    LogContagem,
    Receita,
    ReceitaIngrediente,
    Venda,
)
from .schemas import (
    IngredienteOut,
    EstoquePaginado,
    AtualizacaoLote,
    AtualizacaoIngrediente,
    LogContagemOut,
    ResultadoLote,
    DashboardAlert,
    DashboardCards,
    DashboardCategoryItem,
    DashboardFilters,
    DashboardHistoryPoint,
    DashboardIngredientFilter,
    DashboardRecipeItem,
    DashboardRankItem,
    DashboardResponse,
    DashboardUnitCategoryGroup,
    DashboardUnitRankGroup,
)


PRODUCTION_CATEGORY_ID = "CAT0015"
DASHBOARD_STOCK_UNITS = ("KG", "UND")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_sql_loaders()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Saltim Café API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

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


def _as_float(value) -> float:
    return float(value or 0)


def _stock_product_rows(
    db: Session,
    order,
    limit: int = 8,
    unit: Optional[str] = None,
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
) -> list[DashboardCategoryItem]:
    value_expr = func.coalesce(func.sum(EstoqueAtual.qtd), 0).label("value")
    query = (
        db.query(Categoria.id, Categoria.name, value_expr)
        .join(Ingrediente, Ingrediente.category_id == Categoria.id)
        .outerjoin(EstoqueAtual, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(Categoria.id != PRODUCTION_CATEGORY_ID)
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


def _stock_product_groups(db: Session, order, limit: int = 8) -> list[DashboardUnitRankGroup]:
    return [
        DashboardUnitRankGroup(
            unit=unit,
            items=_stock_product_rows(db, order, limit=limit, unit=unit),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _stock_category_groups(db: Session, order, limit: int = 8) -> list[DashboardUnitCategoryGroup]:
    return [
        DashboardUnitCategoryGroup(
            unit=unit,
            items=_stock_category_rows(db, order, limit=limit, unit=unit),
        )
        for unit in DASHBOARD_STOCK_UNITS
    ]


def _output_product_rows(db: Session, order, limit: int = 8) -> list[DashboardRankItem]:
    value_expr = func.coalesce(
        func.sum(Venda.quantity * ReceitaIngrediente.qty), 0
    ).label("value")
    rows = (
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


def _output_category_rows(db: Session, order, limit: int = 8) -> list[DashboardCategoryItem]:
    value_expr = func.coalesce(
        func.sum(Venda.quantity * ReceitaIngrediente.qty), 0
    ).label("value")
    rows = (
        db.query(Categoria.id, Categoria.name, value_expr)
        .join(Ingrediente, Ingrediente.category_id == Categoria.id)
        .outerjoin(
            ReceitaIngrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id
        )
        .outerjoin(Venda, Venda.recipe_id == ReceitaIngrediente.recipe_id)
        .filter(Categoria.id != PRODUCTION_CATEGORY_ID)
        .group_by(Categoria.id, Categoria.name)
        .order_by(order(value_expr), Categoria.name)
        .limit(limit)
        .all()
    )
    return [
        DashboardCategoryItem(id=row.id, name=row.name, value=_as_float(row.value))
        for row in rows
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
    )


def _dashboard_alerts(db: Session, limit: int = 10) -> list[DashboardAlert]:
    reference_date = db.query(func.max(func.date(Venda.date_time))).scalar()
    if reference_date is None:
        return []

    start_date = reference_date - timedelta(days=27)
    consumo_expr = func.sum(Venda.quantity * ReceitaIngrediente.qty).label("output")
    rows = (
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
        .filter(func.date(Venda.date_time).between(start_date, reference_date))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .group_by(
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

        avg_daily_output = total_output / 28
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
def get_dashboard(db: Session = Depends(get_db)):
    top_stock_products_by_unit = _stock_product_groups(db, desc)
    bottom_stock_products_by_unit = _stock_product_groups(db, asc)
    top_stock_categories_by_unit = _stock_category_groups(db, desc)
    top_output_products = _output_product_rows(db, desc)
    bottom_output_products = _output_product_rows(db, asc)
    top_output_categories = _output_category_rows(db, desc)
    bottom_output_categories = _output_category_rows(db, asc)

    total_items = (
        db.query(func.count(Ingrediente.id))
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .scalar()
        or 0
    )
    total_stock_qty = (
        db.query(func.coalesce(func.sum(EstoqueAtual.qtd), 0))
        .join(Ingrediente, EstoqueAtual.ingrediente == Ingrediente.id)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
        .scalar()
        or 0
    )

    top_categories_card = [
        item
        for group in top_stock_categories_by_unit
        for item in group.items[:1]
    ]
    bottom_categories_card = [
        item
        for group in _stock_category_groups(db, asc)
        for item in group.items[:1]
    ]
    top_products_card = [
        item
        for group in top_stock_products_by_unit
        for item in group.items[:1]
    ]
    bottom_products_card = [
        item
        for group in bottom_stock_products_by_unit
        for item in group.items[:1]
    ]

    return DashboardResponse(
        cards=DashboardCards(
            total_items=total_items,
            total_stock_qty=_as_float(total_stock_qty),
            top_categories_by_unit=top_categories_card,
            bottom_categories_by_unit=bottom_categories_card,
            top_products_by_unit=top_products_card,
            bottom_products_by_unit=bottom_products_card,
        ),
        top_stock_products_by_unit=top_stock_products_by_unit,
        bottom_stock_products_by_unit=bottom_stock_products_by_unit,
        top_stock_categories_by_unit=top_stock_categories_by_unit,
        top_output_products=top_output_products,
        bottom_output_products=bottom_output_products,
        top_output_categories=top_output_categories,
        bottom_output_categories=bottom_output_categories,
        alerts=_dashboard_alerts(db),
        filters=_dashboard_filters(db),
    )


@app.get("/api/dashboard/estoque-historico", response_model=list[DashboardHistoryPoint])
def get_dashboard_estoque_historico(
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    days: int = Query(default=90, ge=7, le=730),
    db: Session = Depends(get_db),
):
    reference_date = db.query(func.max(func.date(Estoque.date_time))).scalar()
    if reference_date is None:
        return []

    start_date = reference_date - timedelta(days=days - 1)
    date_expr = func.date(Estoque.date_time).label("date")
    value_expr = func.coalesce(func.sum(Estoque.quantity), 0).label("value")
    query = (
        db.query(date_expr, value_expr)
        .join(Ingrediente, Estoque.ingredient_id == Ingrediente.id)
        .filter(func.date(Estoque.date_time) >= start_date)
        .filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    )

    if ingredient_id:
        query = query.filter(Ingrediente.id == ingredient_id)
    elif category_id:
        query = query.filter(Ingrediente.category_id == category_id)

    rows = query.group_by(date_expr).order_by(date_expr).all()
    return [
        DashboardHistoryPoint(date=row.date, value=_as_float(row.value))
        for row in rows
    ]


def _filtered_recipe_ids_query(
    db: Session,
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
):
    query = db.query(ReceitaIngrediente.recipe_id).join(
        Ingrediente, ReceitaIngrediente.ingredient_id == Ingrediente.id
    )
    if ingredient_id:
        query = query.filter(Ingrediente.id == ingredient_id)
    elif category_id:
        query = query.filter(Ingrediente.category_id == category_id)
    else:
        query = query.filter(Ingrediente.category_id != PRODUCTION_CATEGORY_ID)
    return query.distinct()


@app.get("/api/dashboard/vendas-historico", response_model=list[DashboardHistoryPoint])
def get_dashboard_vendas_historico(
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    days: int = Query(default=90, ge=7, le=730),
    db: Session = Depends(get_db),
):
    reference_date = db.query(func.max(func.date(Venda.date_time))).scalar()
    if reference_date is None:
        return []

    start_date = reference_date - timedelta(days=days - 1)
    date_expr = func.date(Venda.date_time).label("date")
    value_expr = func.coalesce(func.sum(Venda.quantity), 0).label("value")
    query = db.query(date_expr, value_expr).filter(func.date(Venda.date_time) >= start_date)

    if ingredient_id or category_id:
        query = query.filter(
            Venda.recipe_id.in_(
                _filtered_recipe_ids_query(db, ingredient_id=ingredient_id, category_id=category_id)
            )
        )

    rows = query.group_by(date_expr).order_by(date_expr).all()
    return [
        DashboardHistoryPoint(date=row.date, value=_as_float(row.value))
        for row in rows
    ]


@app.get("/api/dashboard/receitas-ranking", response_model=list[DashboardRecipeItem])
def get_dashboard_receitas_ranking(
    ingredient_id: Optional[str] = None,
    category_id: Optional[str] = None,
    days: int = Query(default=90, ge=7, le=730),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    reference_date = db.query(func.max(func.date(Venda.date_time))).scalar()
    if reference_date is None:
        return []

    start_date = reference_date - timedelta(days=days - 1)
    quantity_expr = func.coalesce(func.sum(Venda.quantity), 0).label("quantity")
    revenue_expr = func.coalesce(func.sum(Venda.quantity * Venda.unit_price), 0).label("revenue")
    query = (
        db.query(Receita.id, Receita.name, quantity_expr, revenue_expr)
        .join(Venda, Venda.recipe_id == Receita.id)
        .filter(func.date(Venda.date_time) >= start_date)
    )

    if ingredient_id or category_id:
        query = query.filter(
            Receita.id.in_(
                _filtered_recipe_ids_query(db, ingredient_id=ingredient_id, category_id=category_id)
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
        .order_by(Categoria.name, Ingrediente.name)
    )
    if category:
        query = query.filter(or_(Ingrediente.category_id == category, Categoria.name == category))
    if q:
        query = query.filter(Ingrediente.name.ilike(f"%{q}%"))
    items = query.all()
    if status:
        items = [i for i in items if _compute_status(i) == status]
    return items


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
        .order_by(Categoria.name, Ingrediente.name)
    )
    if category:
        query = query.filter(or_(Ingrediente.category_id == category, Categoria.name == category))
    if q:
        query = query.filter(Ingrediente.name.ilike(f"%{q}%"))
    items = query.all()
    if status:
        items = [i for i in items if _compute_status(i) == status]

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    page_items = items[offset: offset + page_size]

    return EstoquePaginado(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.patch("/api/estoque", response_model=ResultadoLote)
def update_estoque(lote: AtualizacaoLote, db: Session = Depends(get_db)):
    ids = [u.id for u in lote.updates]
    por_id = {
        i.id: i
        for i in db.query(Ingrediente).filter(Ingrediente.id.in_(ids)).all()
    }

    count = 0
    for atualizacao in lote.updates:
        ingrediente = por_id.get(atualizacao.id)
        if ingrediente is None:
            continue

        anterior = float(ingrediente.current_qty)
        if round(atualizacao.new_qty, 3) == round(anterior, 3):
            continue
        db.add(LogContagem(
            ingrediente_id=ingrediente.id,
            quantidade_anterior=anterior,
            quantidade_nova=atualizacao.new_qty,
            delta=round(atualizacao.new_qty - anterior, 3),
            sessao=lote.session_label,
        ))
        if ingrediente.estoque_atual is None:
            ingrediente.estoque_atual = EstoqueAtual(
                id=f"CUR-{ingrediente.id}",
                qtd=atualizacao.new_qty,
                data=date.today(),
            )
        else:
            ingrediente.estoque_atual.qtd = atualizacao.new_qty
            ingrediente.estoque_atual.data = date.today()
        count += 1

    db.commit()
    return ResultadoLote(ok=True, atualizados=count)


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


@app.get("/health")
def health():
    return {"status": "ok"}
