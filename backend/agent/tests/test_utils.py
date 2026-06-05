from __future__ import annotations

from pathlib import Path
import sys

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.utils import extrair_tabelas, validar_sql


ALLOWED_TABLES = {
    "ingredientes",
    "public.ingredientes",
    "estoque_atual",
    "public.estoque_atual",
    "ml.criticidade_report_items",
    "ml.criticidade_report_runs",
}


def test_validar_sql_adiciona_limit_default():
    sql = validar_sql("SELECT id, name FROM ingredientes", ALLOWED_TABLES)

    assert sql.endswith("LIMIT 50;")


def test_validar_sql_limita_resultados_acima_de_100():
    sql = validar_sql("SELECT id, name FROM ingredientes LIMIT 500", ALLOWED_TABLES)

    assert "LIMIT 100" in sql


def test_validar_sql_bloqueia_operacao_destrutiva():
    with pytest.raises(ValueError, match="Operacao proibida"):
        validar_sql("DELETE FROM ingredientes", ALLOWED_TABLES)


def test_validar_sql_bloqueia_multiplas_queries():
    with pytest.raises(ValueError, match="Multiplas queries"):
        validar_sql("SELECT * FROM ingredientes; SELECT * FROM estoque_atual", ALLOWED_TABLES)


def test_validar_sql_bloqueia_tabela_fora_do_escopo():
    with pytest.raises(ValueError, match="Tabelas nao permitidas"):
        validar_sql("SELECT * FROM users", ALLOWED_TABLES)


def test_validar_sql_permite_tabela_ml_qualificada_com_cte():
    sql = validar_sql(
        """
        WITH latest AS (
          SELECT run_id, ingredient_id
          FROM ml.criticidade_report_items
          LIMIT 10
        )
        SELECT ingredient_id FROM latest
        """,
        ALLOWED_TABLES,
    )

    assert "ml.criticidade_report_items" in sql


def test_extrair_tabelas_ignora_nome_de_cte():
    tables = extrair_tabelas(
        """
        WITH latest AS (
          SELECT run_id FROM ml.criticidade_report_items
        )
        SELECT * FROM latest
        """
    )

    assert tables == {"ml.criticidade_report_items"}
