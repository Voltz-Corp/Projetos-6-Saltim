from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


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


class EstoquePaginado(BaseModel):
    items: List[IngredienteOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class AtualizacaoIngrediente(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    min_qty: Optional[float] = None
