from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List


class IngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    unit: str
    category_id: str
    price: float
    category: str
    min_qty: float
    current_qty: float


class AtualizacaoItem(BaseModel):
    id: str
    new_qty: float


class AtualizacaoLote(BaseModel):
    updates: list[AtualizacaoItem]
    session_label: Optional[str] = None


class LogContagemOut(BaseModel):
    id: int
    ingrediente_id: str
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
    category_id: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    min_qty: Optional[float] = None


class DashboardRankItem(BaseModel):
    id: str
    name: str
    value: float
    unit: Optional[str] = None
    category: Optional[str] = None


class DashboardCategoryItem(BaseModel):
    id: str
    name: str
    value: float
    unit: Optional[str] = None


class DashboardUnitRankGroup(BaseModel):
    unit: str
    items: List[DashboardRankItem]


class DashboardUnitCategoryGroup(BaseModel):
    unit: str
    items: List[DashboardCategoryItem]


class DashboardCards(BaseModel):
    total_items: int
    total_stock_qty: float
    top_categories_by_unit: List[DashboardCategoryItem]
    bottom_categories_by_unit: List[DashboardCategoryItem]
    top_products_by_unit: List[DashboardRankItem]
    bottom_products_by_unit: List[DashboardRankItem]


class DashboardIngredientFilter(BaseModel):
    id: str
    name: str
    category_id: str
    category: str


class DashboardFilters(BaseModel):
    categories: List[DashboardCategoryItem]
    ingredients: List[DashboardIngredientFilter]


class DashboardAlert(BaseModel):
    ingredient_id: str
    name: str
    category: str
    unit: str
    current_qty: float
    avg_daily_output: float
    coverage_days: float
    suggested_qty: float
    severity: str


class DashboardResponse(BaseModel):
    cards: DashboardCards
    top_stock_products_by_unit: List[DashboardUnitRankGroup]
    bottom_stock_products_by_unit: List[DashboardUnitRankGroup]
    top_stock_categories_by_unit: List[DashboardUnitCategoryGroup]
    top_output_products: List[DashboardRankItem]
    bottom_output_products: List[DashboardRankItem]
    top_output_categories: List[DashboardCategoryItem]
    bottom_output_categories: List[DashboardCategoryItem]
    alerts: List[DashboardAlert]
    filters: DashboardFilters


class DashboardHistoryPoint(BaseModel):
    date: date
    value: float


class DashboardRecipeItem(BaseModel):
    id: str
    name: str
    quantity: float
    revenue: float
