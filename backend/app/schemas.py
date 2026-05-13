from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class IngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit: str
    price: float
    category: str
    min_qty: float
    current_qty: float


class AtualizacaoItem(BaseModel):
    id: int
    new_qty: float


class AtualizacaoLote(BaseModel):
    updates: list[AtualizacaoItem]
    session_label: Optional[str] = None


class LogContagemOut(BaseModel):
    id: int
    ingrediente_id: int
    ingrediente_nome: str
    unit: str
    quantidade_anterior: float
    quantidade_nova: float
    delta: float
    sessao: Optional[str]
    criado_em: datetime


class ResultadoLote(BaseModel):
    ok: bool
    atualizados: int
