from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    ingredientes = relationship("Ingrediente", back_populates="categoria")


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    category_id = Column(
        String, ForeignKey("categorias.id"), nullable=False, index=True
    )

    categoria = relationship("Categoria", back_populates="ingredientes")
    estoque_atual = relationship(
        "EstoqueAtual",
        back_populates="ingrediente_ref",
        uselist=False,
        cascade="all, delete-orphan",
    )
    estoques = relationship("Estoque", back_populates="ingrediente_ref")
    fornecedores_opcoes = relationship(
        "FornecedorIngrediente", back_populates="ingrediente_ref"
    )
    receitas_como_saida = relationship("Receita", back_populates="output_ingredient")
    receitas_ingredientes = relationship(
        "ReceitaIngrediente", back_populates="ingrediente_ref"
    )
    pedidos_log = relationship("PedidoLog", back_populates="ingrediente_ref")
    historico = relationship(
        "LogContagem", back_populates="ingrediente", lazy="dynamic"
    )

    @property
    def current_qty(self) -> float:
        if self.estoque_atual is None:
            return 0.0
        return float(self.estoque_atual.qtd)

    @property
    def category(self) -> str:
        if self.categoria is None:
            return self.category_id
        return self.categoria.name

    @property
    def price(self) -> float:
        prices = [
            float(option.price)
            for option in self.fornecedores_opcoes
            if option.price is not None
        ]
        return min(prices) if prices else 0.0

    @property
    def min_qty(self) -> float:
        return 0.0


class EstoqueAtual(Base):
    __tablename__ = "estoque_atual"

    id = Column(String, primary_key=True)
    ingrediente = Column(
        String, ForeignKey("ingredientes.id"), nullable=False, unique=True, index=True
    )
    qtd = Column(Numeric(14, 4), nullable=False)
    data = Column(Date, nullable=False)

    ingrediente_ref = relationship("Ingrediente", back_populates="estoque_atual")


class Estoque(Base):
    __tablename__ = "estoques"
    __table_args__ = (
        Index("idx_estoques_ingredient_date", "ingredient_id", "date_time"),
    )

    id = Column(String, primary_key=True)
    date_time = Column(DateTime, nullable=False)
    ingredient_id = Column(String, ForeignKey("ingredientes.id"), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)

    ingrediente_ref = relationship("Ingrediente", back_populates="estoques")


class FeriadoRecife(Base):
    __tablename__ = "feriados_recife"

    data = Column(Date, primary_key=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    cnpj = Column(String)
    email = Column(String)
    phone = Column(String)
    avg_delivery_time = Column(Integer)

    ingredientes_opcoes = relationship(
        "FornecedorIngrediente", back_populates="fornecedor"
    )


class FornecedorIngrediente(Base):
    __tablename__ = "fornecedores_ingredientes"
    __table_args__ = (
        Index("idx_fornecedores_ingredientes_ingredient", "ingredient_id"),
    )

    supplier_id = Column(String, ForeignKey("fornecedores.id"), primary_key=True)
    ingredient_id = Column(String, ForeignKey("ingredientes.id"), primary_key=True)
    price = Column(Numeric(14, 4), nullable=False)
    discount_percent = Column(Numeric(8, 4), nullable=False, default=0)
    min_to_discount = Column(Numeric(14, 4), nullable=False, default=0)

    fornecedor = relationship("Fornecedor", back_populates="ingredientes_opcoes")
    ingrediente_ref = relationship("Ingrediente", back_populates="fornecedores_opcoes")
    pedidos = relationship("Pedido", back_populates="fornecedor_ingrediente")


class ProdutoIndisponivel(Base):
    __tablename__ = "produtos_indisponiveis"

    match = Column("match", String, primary_key=True)
    data_inicio = Column(Date, primary_key=True)
    data_fim = Column(Date, primary_key=True)


class Receita(Base):
    __tablename__ = "receitas"
    __table_args__ = (Index("idx_receitas_output_ingredient", "output_ingredient_id"),)

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    recipe_type = Column("type", String, nullable=False)
    yield_qty = Column(Numeric(14, 4))
    yield_unit = Column(String)
    output_ingredient_id = Column(String, ForeignKey("ingredientes.id"))
    sale_price = Column(Numeric(14, 4))

    output_ingredient = relationship(
        "Ingrediente", back_populates="receitas_como_saida"
    )
    ingredientes = relationship("ReceitaIngrediente", back_populates="receita")
    vendas = relationship("Venda", back_populates="receita")


class ReceitaIngrediente(Base):
    __tablename__ = "receitas_ingredientes"
    __table_args__ = (Index("idx_receitas_ingredientes_ingredient", "ingredient_id"),)

    recipe_id = Column(String, ForeignKey("receitas.id"), primary_key=True)
    ingredient_id = Column(String, ForeignKey("ingredientes.id"), primary_key=True)
    qty = Column(Numeric(14, 4), nullable=False)
    unit = Column(String, nullable=False)

    receita = relationship("Receita", back_populates="ingredientes")
    ingrediente_ref = relationship(
        "Ingrediente", back_populates="receitas_ingredientes"
    )


class Venda(Base):
    __tablename__ = "vendas"
    __table_args__ = (Index("idx_vendas_recipe_date", "recipe_id", "date_time"),)

    id = Column(String, primary_key=True)
    date_time = Column(DateTime, nullable=False)
    recipe_id = Column(String, ForeignKey("receitas.id"), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit_price = Column(Numeric(14, 4), nullable=False)

    receita = relationship("Receita", back_populates="vendas")


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supplier_id", "ingredient_id"],
            [
                "fornecedores_ingredientes.supplier_id",
                "fornecedores_ingredientes.ingredient_id",
            ],
        ),
        Index("idx_pedidos_supplier_date", "supplier_id", "data_pedido"),
        Index("idx_pedidos_ingredient_date", "ingredient_id", "data_pedido"),
    )

    id = Column(String, primary_key=True)
    supplier_id = Column(String, nullable=False)
    ingredient_id = Column(String, nullable=False)
    qty = Column(Numeric(14, 4), nullable=False)
    valor = Column(Numeric(14, 4), nullable=False)
    data_pedido = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    data_prevista = Column(Date, nullable=False)

    fornecedor_ingrediente = relationship(
        "FornecedorIngrediente", back_populates="pedidos"
    )


class PedidoLog(Base):
    __tablename__ = "pedidos_log"
    __table_args__ = (
        Index("idx_pedidos_log_ingredient_date", "ingredient_id", "data_pedido"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_pedido = Column(Date, nullable=False)
    ingredient_id = Column(String, ForeignKey("ingredientes.id"), nullable=False)
    qty = Column(Numeric(14, 4), nullable=False)
    data_prevista = Column(Date, nullable=False)
    order_type = Column(String, nullable=False)

    ingrediente_ref = relationship("Ingrediente", back_populates="pedidos_log")


class ResumoDiarioEstoque(Base):
    __tablename__ = "resumo_diario_estoques"

    date = Column(Date, primary_key=True)
    saldo_medio = Column(Float, nullable=False)
    itens_sobrestoque = Column(Integer, nullable=False)
    itens_substoque = Column(Integer, nullable=False)
    itens_ruptura = Column(Integer, nullable=False)
    consumo_total = Column(Float, nullable=False)


class ResumoDiarioVenda(Base):
    __tablename__ = "resumo_diario_vendas"

    date = Column(Date, primary_key=True)
    vendas_dia = Column(Integer, nullable=False)
    is_holiday = Column(Integer, nullable=False)
    is_carnaval_window = Column(Integer, nullable=False)
    is_sao_joao = Column(Integer, nullable=False)
    is_summer = Column(Integer, nullable=False)
    is_promo_day = Column(Integer, nullable=False)
    is_rain_event = Column(Integer, nullable=False)
    is_closure = Column(Integer, nullable=False)


class ResumoMensalEstoque(Base):
    __tablename__ = "resumo_mensal_estoques"
    __table_args__ = (
        CheckConstraint(
            "month BETWEEN 1 AND 12", name="resumo_mensal_estoques_month_check"
        ),
    )

    year = Column(Integer, primary_key=True)
    month = Column(Integer, primary_key=True)
    saldo_medio = Column(Float, nullable=False)
    saldo_max = Column(Float, nullable=False)
    registros = Column(Integer, nullable=False)


class ResumoMensalVenda(Base):
    __tablename__ = "resumo_mensal_vendas"
    __table_args__ = (
        CheckConstraint(
            "month BETWEEN 1 AND 12", name="resumo_mensal_vendas_month_check"
        ),
    )

    year = Column(Integer, primary_key=True)
    month = Column(Integer, primary_key=True)
    vendas_mes = Column(Integer, nullable=False)
    unidades_vendidas = Column(Integer, nullable=False)
    receita_total = Column(Numeric(14, 4), nullable=False)
    ticket_medio = Column(Numeric(14, 4), nullable=False)
    receita_por_venda = Column(Numeric(14, 4), nullable=False)


class LogContagem(Base):
    __tablename__ = "log_contagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingrediente_id = Column(
        String, ForeignKey("ingredientes.id"), nullable=False, index=True
    )
    quantidade_anterior = Column(Numeric(14, 4), nullable=False)
    quantidade_nova = Column(Numeric(14, 4), nullable=False)
    delta = Column(Numeric(14, 4), nullable=False)
    sessao = Column(String)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    ingrediente = relationship("Ingrediente", back_populates="historico")


class Contagem(Base):
    __tablename__ = "contagens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False)
    status = Column(String, nullable=False, default="em_andamento", index=True)
    criada_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    finalizada_em = Column(DateTime(timezone=True))

    logs = relationship("ContagemLog", back_populates="contagem")


class ContagemLog(Base):
    __tablename__ = "contagem_log"
    __table_args__ = (
        Index("idx_contagem_log_contagem_categoria", "contagem_id", "category_id"),
        Index("idx_contagem_log_ingredient", "ingrediente_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    contagem_id = Column(Integer, ForeignKey("contagens.id"), nullable=False)
    ingrediente_id = Column(String, ForeignKey("ingredientes.id"), nullable=False)
    category_id = Column(String, ForeignKey("categorias.id"), nullable=False)
    categoria = Column(String, nullable=False)
    quantidade_anterior = Column(Numeric(14, 4), nullable=False)
    quantidade_nova = Column(Numeric(14, 4), nullable=False)
    delta = Column(Numeric(14, 4), nullable=False)
    criado_em = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    contagem = relationship("Contagem", back_populates="logs")
    ingrediente = relationship("Ingrediente")
