from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import Ingrediente, LogContagem
from .schemas import (
    IngredienteOut,
    AtualizacaoLote,
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

@app.get("/api/estoque", response_model=list[IngredienteOut])
def get_estoque(db: Session = Depends(get_db)):
    return (
        db.query(Ingrediente)
        .order_by(Ingrediente.category, Ingrediente.name)
        .all()
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
