from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    category = Column(String(100), nullable=False, index=True)
    min_qty = Column(Numeric(10, 3), nullable=False, default=0)
    current_qty = Column(Numeric(10, 3), nullable=False, default=0)

    historico = relationship("LogContagem", back_populates="ingrediente", lazy="dynamic")


class LogContagem(Base):
    """Registro imutável de cada alteração de estoque. Um log por item por contagem."""

    __tablename__ = "log_contagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingrediente_id = Column(Integer, ForeignKey("ingredientes.id"), nullable=False, index=True)
    quantidade_anterior = Column(Numeric(10, 3), nullable=False)
    quantidade_nova = Column(Numeric(10, 3), nullable=False)
    delta = Column(Numeric(10, 3), nullable=False)          # quantidade_nova - quantidade_anterior
    sessao = Column(String(255))                             # ex: "Laticínios", "manual"
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    ingrediente = relationship("Ingrediente", back_populates="historico")
