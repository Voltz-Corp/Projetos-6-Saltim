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


class FornecedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avg_delivery_time: Optional[int] = None


class FornecedorListItem(FornecedorOut):
    item_count: int = 0
    avg_price: Optional[float] = None


class FornecedorKpis(BaseModel):
    supplier_count: int
    avg_delivery_time: float
    avg_items_per_supplier: float
    best_value_supplier_id: Optional[str] = None
    best_value_supplier_name: Optional[str] = None
    best_value_detail: str


class FornecedorListResponse(BaseModel):
    kpis: FornecedorKpis
    items: List[FornecedorListItem]


class FornecedorProductOut(BaseModel):
    ingredient_id: str
    name: str
    category: str
    current_qty: float
    unit: str
    unit_price: float


class FornecedorOrderOut(BaseModel):
    id: str
    order_date: date
    items_qty: float
    total_value: float
    status: str


class FornecedorProfileKpis(BaseModel):
    avg_lead_time: float
    orders_count: int
    delivery_rate: float


class FornecedorProfileResponse(BaseModel):
    supplier: FornecedorOut
    kpis: FornecedorProfileKpis
    products: List[FornecedorProductOut]
    orders: List[FornecedorOrderOut]


class PedidoOut(BaseModel):
    id: str
    supplier_id: str
    supplier_name: str
    ingredient_id: str
    ingredient_name: str
    order_date: date
    items_qty: float
    total_value: float
    status: str
    expected_date: date


class PedidoPaginado(BaseModel):
    items: List[PedidoOut]
    total: int
    page: int
    page_size: int
    total_pages: int


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


class DashboardKpi(BaseModel):
    id: str
    label: str
    value: str
    detail: str
    trend_value: Optional[float] = None
    trend_label: str
    trend_direction: str


class DashboardCards(BaseModel):
    items: List[DashboardKpi]


class DashboardIngredientFilter(BaseModel):
    id: str
    name: str
    category_id: str
    category: str


class DashboardHolidayFilter(BaseModel):
    date: date
    name: str
    type: str


class DashboardMonthFilter(BaseModel):
    key: str
    label: str


class DashboardFilters(BaseModel):
    categories: List[DashboardCategoryItem]
    ingredients: List[DashboardIngredientFilter]
    holidays: List[DashboardHolidayFilter]
    months: List[DashboardMonthFilter]


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
    bottom_stock_categories_by_unit: List[DashboardUnitCategoryGroup]
    top_output_products_by_unit: List[DashboardUnitRankGroup]
    bottom_output_products_by_unit: List[DashboardUnitRankGroup]
    top_output_categories_by_unit: List[DashboardUnitCategoryGroup]
    bottom_output_categories_by_unit: List[DashboardUnitCategoryGroup]
    alerts: List[DashboardAlert]
    filters: DashboardFilters


class DashboardHistoryPoint(BaseModel):
    date: date
    value: float


class DashboardNamedMetric(BaseModel):
    key: str
    label: str
    value: float


class DashboardRevenueSummary(BaseModel):
    monthly: List[DashboardNamedMetric]
    quarterly: List[DashboardNamedMetric]


class DashboardRecipeItem(BaseModel):
    id: str
    name: str
    quantity: float
    revenue: float
