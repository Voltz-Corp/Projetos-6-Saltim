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
    stock_applied_at: Optional[datetime] = None
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


class PedidoEmailResult(BaseModel):
    supplier_id: str
    supplier_name: str
    email: Optional[str] = None
    status: str
    message: str


class PedidoCreateResponse(BaseModel):
    groups: List[PedidoGroupOut]
    created: int
    updated: int
    email_results: List[PedidoEmailResult] = Field(default_factory=list)


class ClienteCreate(BaseModel):
    name: str
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nome do cliente e obrigatorio")
        return value

    @field_validator("document", "email", "phone")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ClienteOut(BaseModel):
    id: str
    name: str
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class VendaProdutoOut(BaseModel):
    id: str
    name: str
    recipe_type: str
    sale_price: float
    yield_qty: Optional[float] = None
    yield_unit: Optional[str] = None
    ingredients_count: int
    available: bool
    max_quantity: Optional[float] = None
    stock_warnings: List[str] = Field(default_factory=list)


class VendaItemCreate(BaseModel):
    recipe_id: str
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    discount_value: float = Field(default=0, ge=0)


class VendaCreateRequest(BaseModel):
    customer_id: Optional[str] = None
    customer: Optional[ClienteCreate] = None
    items: List[VendaItemCreate] = Field(default_factory=list, min_length=1)
    discount_total: float = Field(default=0, ge=0)
    source: str = "balcao"
    notes: Optional[str] = None


class MesaPedidoCreate(BaseModel):
    comanda_id: Optional[str] = None


class MesaVendaOut(BaseModel):
    numero: int
    status: str
    comanda_id: Optional[str] = None
    items_count: int = 0
    items_qty: float = 0
    total: float = 0
    opened_at: Optional[datetime] = None

    @field_serializer("opened_at", when_used="json")
    def serialize_opened_at(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class MesasResponse(BaseModel):
    total_mesas: int
    mesas: List[MesaVendaOut]


class MesaPedidoOut(BaseModel):
    mesa_numero: int
    comanda_id: str


class VendaItensUpdateRequest(BaseModel):
    items: List[VendaItemCreate] = Field(default_factory=list, min_length=1)
    mesa_numero: Optional[int] = None
    customer_name: Optional[str] = None
    cpf_cliente: Optional[str] = None
    notes: Optional[str] = None


class VendaFecharRequest(BaseModel):
    payment_method: str
    paid_amount: Optional[float] = Field(default=None, ge=0)
    cpf_cliente: Optional[str] = None
    customer_name: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Forma de pagamento e obrigatoria")
        return value


class VendaItemOut(BaseModel):
    id: str
    recipe_id: str
    recipe_name: str
    quantity: float
    unit_price: float
    discount_value: float
    total_value: float
    venda_historica_id: Optional[str] = None


class VendaListItem(BaseModel):
    id: str
    comanda_id: Optional[str] = None
    date_time: datetime
    customer_name: Optional[str] = None
    cpf_cliente: Optional[str] = None
    mesa_numero: Optional[int] = None
    status: str
    payment_method: Optional[str] = None
    items_count: int
    items_qty: float
    total: float
    paid_total: float

    @field_serializer("date_time", when_used="json")
    def serialize_date_time(self, value: datetime) -> Optional[str]:
        return _to_recife_datetime(value)


class VendaPaginado(BaseModel):
    items: List[VendaListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    paid_revenue_total: float = 0


class VendaDetailOut(BaseModel):
    id: str
    comanda_id: Optional[str] = None
    date_time: datetime
    customer: Optional[ClienteOut] = None
    customer_name: Optional[str] = None
    cpf_cliente: Optional[str] = None
    mesa_numero: Optional[int] = None
    status: str
    payment_method: Optional[str] = None
    subtotal: float
    discount_total: float
    total: float
    source: str
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    items: List[VendaItemOut] = Field(default_factory=list)

    @field_serializer(
        "date_time",
        "confirmed_at",
        "canceled_at",
        when_used="json",
    )
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class VendaFechamentoDiaOut(BaseModel):
    date: date
    vendas_dia: int
    is_holiday: int
    is_carnaval_window: int
    is_sao_joao: int
    is_summer: int
    is_promo_day: int
    is_rain_event: int
    is_closure: int


class PurchasePlanGenerateRequest(BaseModel):
    contagem_id: Optional[int] = None
    horizon_days: int = Field(default=7, ge=1, le=30)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class PurchasePlanItemUpdateRequest(BaseModel):
    approved_qty: Optional[float] = Field(default=None, ge=0)
    selected_supplier_id: Optional[str] = None
    note: Optional[str] = None


class PurchasePlanSimulationItem(BaseModel):
    ingredient_id: str
    approved_qty: float = Field(ge=0)
    selected_supplier_id: Optional[str] = None


class PurchasePlanSimulationRequest(BaseModel):
    items: List[PurchasePlanSimulationItem] = Field(default_factory=list)


class PurchasePlanSupplierOptionOut(BaseModel):
    id: int
    supplier_id: str
    supplier_name: str
    unit_price: float
    discount_percent: float
    min_to_discount: float
    effective_unit_price: float
    delivery_time_days: int
    delay_risk: float
    score: float
    recommended: bool
    reason: Optional[str] = None


class PurchasePlanItemOut(BaseModel):
    id: int
    ingredient_id: str
    ingredient_name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    current_qty: float
    avg_daily_usage: float
    forecast_qty: float
    in_transit_qty: float
    recommended_qty: float
    approved_qty: float
    selected_supplier_id: Optional[str] = None
    selected_supplier_name: Optional[str] = None
    estimated_unit_price: float
    estimated_total: float
    coverage_days: float
    criticality: str
    criticality_source: str
    justification: Optional[str] = None
    note: Optional[str] = None
    options: List[PurchasePlanSupplierOptionOut] = Field(default_factory=list)


class SupplierQuoteOut(BaseModel):
    id: int
    supplier_id: str
    supplier_name: str
    email: Optional[str] = None
    channel: str
    status: str
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    total_estimated: float
    notes: Optional[str] = None

    @field_serializer("sent_at", "responded_at", "approved_at", when_used="json")
    def serialize_quote_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return _to_recife_datetime(value)


class PurchasePlanOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    status: str
    source: str
    horizon_days: int
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    contagem_id: Optional[int] = None
    total_estimated: float
    approved_total: float
    critical_items_count: int
    avg_coverage_days: float
    savings_potential: float
    items: List[PurchasePlanItemOut] = Field(default_factory=list)
    quotes: List[SupplierQuoteOut] = Field(default_factory=list)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_plan_datetime(self, value: datetime) -> Optional[str]:
        return _to_recife_datetime(value)


class PurchasePlanSimulationOut(BaseModel):
    total_estimated: float
    approved_total: float
    projected_coverage_days: float
    rupture_risk_items: int
    critical_items_count: int
    savings_potential: float
    notes: List[str] = Field(default_factory=list)


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
