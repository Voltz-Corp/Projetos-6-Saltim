import math
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Ingrediente, LogContagem
from .schemas import (
    IngredienteOut,
    EstoquePaginado,
    AtualizacaoLote,
    AtualizacaoIngrediente,
    LogContagemOut,
    ResultadoLote,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/api/estoque", response_model=list[IngredienteOut])
def get_estoque(
    category: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Ingrediente)
        .order_by(Ingrediente.category, Ingrediente.name)
    )
    if category:
        query = query.filter(Ingrediente.category == category)
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
        .order_by(Ingrediente.category, Ingrediente.name)
    )
    if category:
        query = query.filter(Ingrediente.category == category)
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
        ingrediente.current_qty = atualizacao.new_qty
        count += 1

    db.commit()
    return ResultadoLote(ok=True, atualizados=count)


@app.patch("/api/ingredientes/{ingrediente_id}", response_model=IngredienteOut)
def update_ingrediente(
    ingrediente_id: int,
    dados: AtualizacaoIngrediente,
    db: Session = Depends(get_db),
):
    ingrediente = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado")
    for field, value in dados.model_dump(exclude_none=True).items():
        setattr(ingrediente, field, value)
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
def get_log_ingrediente(ingrediente_id: int, db: Session = Depends(get_db)):
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
