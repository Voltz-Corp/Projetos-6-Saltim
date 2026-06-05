import re

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any, Optional, List


RECIFE_TZ = ZoneInfo("America/Recife")


def _to_recife_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=RECIFE_TZ)
    return value.astimezone(RECIFE_TZ).isoformat()


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
    status: str = "OK"
    criticidade_predita: Optional[str] = None
    criticidade_report_id: Optional[int] = None
    criticidade_reference_date: Optional[date] = None


class AtualizacaoItem(BaseModel):
    id: str
    new_qty: float


class AtualizacaoLote(BaseModel):
    updates: list[AtualizacaoItem]
    session_label: Optional[str] = None
    contagem_id: Optional[int] = None


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

    @field_serializer("criado_em", when_used="json")
    def serialize_criado_em(self, value: datetime) -> Optional[str]:
        return _to_recife_datetime(value)


class ResultadoLote(BaseModel):
    ok: bool
    atualizados: int
    contagem_id: Optional[int] = None


class ContagemCreate(BaseModel):
    label: Optional[str] = None


class ContagemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    data_contagem: date
    status: str
    estoque_snapshot_data: Optional[date] = None
    criada_em: datetime
    finalizada_em: Optional[datetime] = None

    @field_serializer("criada_em", "finalizada_em", when_used="json")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class ContagemListItem(ContagemOut):
    total_itens: int
    itens_contados: int
    itens_alterados: int
    itens_sem_alteracao: int
    itens_nao_contados: int


class ContagemDetalheItem(BaseModel):
    ingrediente_id: str
    ingrediente_nome: str
    unit: str
    quantidade_atual: float
    estoque_id: Optional[str] = None
    estoque_data: Optional[date] = None
    estoque_quantidade: Optional[float] = None
    quantidade_anterior: Optional[float] = None
    quantidade_nova: Optional[float] = None
    delta: Optional[float] = None
    status: str
    contado_em: Optional[datetime] = None

    @field_serializer("contado_em", when_used="json")
    def serialize_contado_em(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class ContagemDetalheCategoria(BaseModel):
    category_id: str
    categoria: str
    total_itens: int
    itens_contados: int
    itens_alterados: int
    itens_sem_alteracao: int
    itens_nao_contados: int
    items: List[ContagemDetalheItem]


class ContagemDetalheOut(ContagemOut):
    total_itens: int
    itens_contados: int
    itens_alterados: int
    itens_sem_alteracao: int
    itens_nao_contados: int
    categorias: List[ContagemDetalheCategoria]


class EstoquePaginado(BaseModel):
    items: List[IngredienteOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class CriticidadeReportRunOut(BaseModel):
    id: Optional[int] = None
    reference_date: Optional[date] = None
    generated_at: Optional[datetime] = None
    status: str
    contagem_id: Optional[int] = None
    contagem_status: Optional[str] = None
    model_name: Optional[str] = None
    model_uri: Optional[str] = None
    model_run_id: Optional[str] = None
    total_items: int = 0
    ok_count: int = 0
    alert_count: int = 0
    alert_rate: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict)
    stability: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class CriticidadeReportItemOut(BaseModel):
    ingredient_id: str
    ingredient_name: str
    category_id: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    estoque_atual: float
    stock_position: float
    baseline_threshold: float
    cobertura_estoque_pct: float
    limiar_alerta_predito_pct: float
    limiar_critico_predito_pct: float
    criticidade_predita: str
    necessita_compra: bool
    score_alerta_compra: float
    rank_position: int


class CriticidadeReportCategoryOut(BaseModel):
    category: str
    total_items: int
    ok_count: int
    alert_count: int
    alert_rate: float


class CriticidadeReportLatestOut(BaseModel):
    run: CriticidadeReportRunOut
    distribution: list[dict[str, Any]]
    categories: list[CriticidadeReportCategoryOut]
    critical_items: list[CriticidadeReportItemOut]
    zero_items: list[CriticidadeReportItemOut] = Field(default_factory=list)
    examples_critical: list[CriticidadeReportItemOut]
    examples_ok: list[CriticidadeReportItemOut]


class JobStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dia: date
    status: str
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    error_message: Optional[str] = None

    @field_serializer("inicio_em", "fim_em", "atualizado_em", when_used="json")
    def serialize_job_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


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


class FornecedorIngredientCreate(BaseModel):
    ingredient_id: str
    price: float
    discount_percent: float = 0
    min_to_discount: float = 0


class FornecedorCreate(BaseModel):
    name: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avg_delivery_time: Optional[int] = None
    ingredients: List[FornecedorIngredientCreate] = []

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos")
        return digits

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) not in (10, 11):
            raise ValueError("Telefone deve conter 10 ou 11 dígitos")
        return digits


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


class PedidoGroupOut(BaseModel):
    group_key: str
    supplier_id: str
    supplier_name: str
    order_date: date
    expected_date: date
    status: str
    ingredients_count: int
    items_qty: float
    total_value: float


class PedidoPaginado(BaseModel):
    items: List[PedidoGroupOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PedidoDetailItem(BaseModel):
    ingredient_id: str
    ingredient_name: str
    category: str
    unit: str
    qty: float
    unit_price: float
    total_value: float


class PedidoDetailResponse(BaseModel):
    id: str
    group_key: Optional[str] = None
    supplier_id: str
    supplier_name: str
    order_date: date
    expected_date: date
    status: str
    items_qty: float
    total_value: float
    items: List[PedidoDetailItem]


class PedidoRequestItem(BaseModel):
    ingredient_id: str
    qty: float

    @field_validator("qty")
    @classmethod
    def validate_qty(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return value


class PedidoCreateItem(PedidoRequestItem):
    supplier_id: str


class PedidoRecommendationRequest(BaseModel):
    items: List[PedidoRequestItem]


class SupplierOption(BaseModel):
    supplier_id: str
    supplier_name: str
    unit_price: float
    discount_percent: float
    min_to_discount: float
    discount_applied: bool
    effective_unit_price: float
    total_value: float
    delivery_time_days: int
    expected_date: date
    detractors: List[str] = []
    recommended: bool = False


class PedidoRecommendationItem(BaseModel):
    ingredient_id: str
    ingredient_name: str
    category: str
    unit: str
    qty: float
    recommended_supplier_id: Optional[str] = None
    options: List[SupplierOption]


class RecommendedOrderItem(BaseModel):
    ingredient_id: str
    ingredient_name: str
    qty: float
    unit: str
    total_value: float
    expected_date: date


class RecommendedOrderGroup(BaseModel):
    supplier_id: str
    supplier_name: str
    expected_date: date
    total_value: float
    items: List[RecommendedOrderItem]


class PedidoRecommendationResponse(BaseModel):
    items: List[PedidoRecommendationItem]
    groups: List[RecommendedOrderGroup]


class PedidoCreateRequest(BaseModel):
    items: List[PedidoCreateItem]


class PedidoCreateResponse(BaseModel):
    groups: List[PedidoGroupOut]
    created: int
    updated: int


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


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class AgentChatResponse(BaseModel):
    session_id: str
    answer: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    is_valid: bool
    error_type: Optional[str] = None
