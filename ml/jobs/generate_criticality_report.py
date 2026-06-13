#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "data" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "data" / "ml_dataset" / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "ml" / "notebooks" / "utils"))

from build_abt_reposicao import build_abt, load_config  # noqa: E402
from gerar_estoque_historico_criticidade import (  # noqa: E402
    backfill_historical_stock_until_cutoff,
)
from gerar_vendas import (  # noqa: E402
    backfill_historical_sales_until_cutoff,
    generate_operational_sales_from_contagem,
)
from two_stage_common import (  # noqa: E402
    CRITICAL_THRESHOLD_GAP_PCT,
    MAX_ALERT_THRESHOLD_PCT,
    MIN_ALERT_THRESHOLD_PCT,
    PURCHASE_ALERT_LABEL,
    TARGET_CRITICAL_THRESHOLD,
    add_criticality_targets,
    select_feature_columns,
    _derive_criticality,
)

try:
    import mlflow
    import mlflow.sklearn
except ImportError:  # pragma: no cover - handled as a runtime failure in the job
    mlflow = None


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://saltim:saltim123@localhost:5432/saltim_db"
)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
DEFAULT_MODEL_URI = os.getenv(
    "CRITICIDADE_MODEL_URI",
    "runs:/58db15b4b9364e6cb1bf7d9ebe65f922/model",
)
DEFAULT_MODEL_NAME = "XGBoost Regressor"
DAILY_MLFLOW_EXPERIMENT = os.getenv(
    "CRITICIDADE_DAILY_MLFLOW_EXPERIMENT",
    "jobs/criticidade/relatorio_diario",
)
EXCLUDED_PURCHASE_CATEGORY_ID = "CAT0015"
RECIFE_TZ = ZoneInfo("America/Recife")


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def today_recife() -> date:
    return datetime.now(RECIFE_TZ).date()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera o relatório diário de criticidade do Saltim."
    )
    parser.add_argument(
        "--reference-date",
        default="today",
        help="Data de referência: today, latest ou YYYY-MM-DD.",
    )
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--model-uri", default=DEFAULT_MODEL_URI)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "data" / "ml_dataset" / "config" / "dataset_config.json",
    )
    return parser.parse_args()


def json_dump(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(key): normalize(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(val) for val in item]
        if isinstance(item, (np.integer,)):
            return int(item)
        if isinstance(item, (np.floating,)):
            return float(item)
        if isinstance(item, (pd.Timestamp, datetime)):
            return item.isoformat()
        if isinstance(item, date):
            return item.isoformat()
        if pd.isna(item):
            return None
        return item

    return json.dumps(normalize(value), ensure_ascii=False)


def ensure_schema(engine) -> None:
    statements = [
        "CREATE SCHEMA IF NOT EXISTS ml",
        "ALTER TABLE contagens ADD COLUMN IF NOT EXISTS data_contagem DATE",
        "UPDATE contagens SET data_contagem = date(criada_em) WHERE data_contagem IS NULL",
        "ALTER TABLE contagens ALTER COLUMN data_contagem SET NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_contagens_data_contagem ON contagens (data_contagem)",
        """
        CREATE TABLE IF NOT EXISTS ml.criticidade_report_runs (
            id BIGSERIAL PRIMARY KEY,
            reference_date DATE NOT NULL,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status TEXT NOT NULL,
            contagem_id BIGINT,
            contagem_status TEXT,
            model_name TEXT NOT NULL,
            model_uri TEXT NOT NULL,
            model_run_id TEXT,
            total_items INTEGER NOT NULL DEFAULT 0,
            ok_count INTEGER NOT NULL DEFAULT 0,
            alert_count INTEGER NOT NULL DEFAULT 0,
            alert_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            metrics JSONB,
            stability JSONB,
            error_message TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ml.criticidade_report_items (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT NOT NULL REFERENCES ml.criticidade_report_runs (id) ON DELETE CASCADE,
            ingredient_id TEXT NOT NULL,
            ingredient_name TEXT NOT NULL,
            category_id TEXT,
            category TEXT,
            unit TEXT,
            estoque_atual DOUBLE PRECISION NOT NULL DEFAULT 0,
            stock_position DOUBLE PRECISION NOT NULL DEFAULT 0,
            baseline_threshold DOUBLE PRECISION NOT NULL DEFAULT 0,
            cobertura_estoque_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
            limiar_alerta_predito_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
            limiar_critico_predito_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
            criticidade_predita TEXT NOT NULL,
            necessita_compra INTEGER NOT NULL DEFAULT 0,
            score_alerta_compra DOUBLE PRECISION NOT NULL DEFAULT 0,
            rank_position INTEGER NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_criticidade_report_runs_reference_date ON ml.criticidade_report_runs (reference_date)",
        "CREATE INDEX IF NOT EXISTS idx_criticidade_report_runs_generated_at ON ml.criticidade_report_runs (generated_at)",
        "CREATE INDEX IF NOT EXISTS idx_criticidade_report_items_run_rank ON ml.criticidade_report_items (run_id, rank_position)",
        "CREATE INDEX IF NOT EXISTS idx_criticidade_report_items_run_criticality ON ml.criticidade_report_items (run_id, criticidade_predita)",
        """
        CREATE TABLE IF NOT EXISTS ml.job_status (
            id BIGSERIAL PRIMARY KEY,
            dia DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            inicio_em TIMESTAMPTZ,
            fim_em TIMESTAMPTZ,
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
            error_message TEXT,
            CONSTRAINT uq_job_status_dia UNIQUE (dia),
            CONSTRAINT ck_job_status_status CHECK (status IN ('running', 'pending', 'success', 'failed'))
        )
        """,
        "ALTER TABLE ml.job_status ADD COLUMN IF NOT EXISTS inicio_em TIMESTAMPTZ",
        "ALTER TABLE ml.job_status ADD COLUMN IF NOT EXISTS fim_em TIMESTAMPTZ",
        "CREATE INDEX IF NOT EXISTS idx_job_status_dia ON ml.job_status (dia)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def resolve_reference_date(engine, value: str) -> date:
    normalized = value.strip().lower()
    if normalized == "today":
        return today_recife()
    if normalized == "latest":
        with engine.begin() as conn:
            latest = conn.execute(
                text("SELECT max(data_contagem) FROM contagens")
            ).scalar()
            if latest is None:
                latest = conn.execute(
                    text("SELECT max(data) FROM estoque_atual")
                ).scalar()
        return latest or today_recife()
    return date.fromisoformat(value)


def upsert_job_status(
    engine,
    dia: date,
    status: str,
    error_message: str | None = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO ml.job_status (
                    dia,
                    status,
                    inicio_em,
                    fim_em,
                    atualizado_em,
                    error_message
                )
                VALUES (
                    :dia,
                    :status,
                    CASE WHEN :status = 'running' THEN now() ELSE NULL END,
                    CASE WHEN :status IN ('pending', 'success', 'failed') THEN now() ELSE NULL END,
                    now(),
                    :error_message
                )
                ON CONFLICT (dia)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    inicio_em = CASE
                        WHEN EXCLUDED.status = 'running' THEN now()
                        ELSE COALESCE(ml.job_status.inicio_em, EXCLUDED.inicio_em)
                    END,
                    fim_em = CASE
                        WHEN EXCLUDED.status = 'running' THEN NULL
                        WHEN EXCLUDED.status IN ('pending', 'success', 'failed') THEN now()
                        ELSE ml.job_status.fim_em
                    END,
                    atualizado_em = now(),
                    error_message = EXCLUDED.error_message
                """),
            {"dia": dia, "status": status, "error_message": error_message},
        )


def model_run_id_from_uri(model_uri: str) -> str | None:
    match = re.match(r"runs:/([^/]+)/", model_uri)
    if match:
        return match.group(1)
    return os.getenv("CRITICIDADE_MODEL_RUN_ID")


def insert_run(
    engine,
    *,
    reference_date: date,
    status: str,
    model_name: str,
    model_uri: str,
    model_run_id: str | None,
    contagem_id: int | None = None,
    contagem_status: str | None = None,
    total_items: int = 0,
    ok_count: int = 0,
    alert_count: int = 0,
    alert_rate: float = 0.0,
    metrics: dict[str, Any] | None = None,
    stability: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> int:
    sql = text("""
        INSERT INTO ml.criticidade_report_runs (
            reference_date,
            status,
            contagem_id,
            contagem_status,
            model_name,
            model_uri,
            model_run_id,
            total_items,
            ok_count,
            alert_count,
            alert_rate,
            metrics,
            stability,
            error_message
        )
        VALUES (
            :reference_date,
            :status,
            :contagem_id,
            :contagem_status,
            :model_name,
            :model_uri,
            :model_run_id,
            :total_items,
            :ok_count,
            :alert_count,
            :alert_rate,
            CAST(:metrics AS jsonb),
            CAST(:stability AS jsonb),
            :error_message
        )
        RETURNING id
        """)
    params = {
        "reference_date": reference_date,
        "status": status,
        "contagem_id": contagem_id,
        "contagem_status": contagem_status,
        "model_name": model_name,
        "model_uri": model_uri,
        "model_run_id": model_run_id,
        "total_items": total_items,
        "ok_count": ok_count,
        "alert_count": alert_count,
        "alert_rate": alert_rate,
        "metrics": json_dump(metrics or {}),
        "stability": json_dump(stability or {}),
        "error_message": error_message,
    }
    with engine.begin() as conn:
        return int(conn.execute(sql, params).scalar_one())


def update_run_payload(
    engine,
    run_id: int,
    *,
    metrics: dict[str, Any] | None = None,
    stability: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    assignments = []
    params: dict[str, Any] = {"run_id": run_id}
    if metrics is not None:
        assignments.append("metrics = CAST(:metrics AS jsonb)")
        params["metrics"] = json_dump(metrics)
    if stability is not None:
        assignments.append("stability = CAST(:stability AS jsonb)")
        params["stability"] = json_dump(stability)
    if error_message is not None:
        assignments.append("error_message = :error_message")
        params["error_message"] = error_message
    if not assignments:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                f"UPDATE ml.criticidade_report_runs SET {', '.join(assignments)} WHERE id = :run_id"
            ),
            params,
        )


def validate_contagem(
    engine, reference_date: date
) -> tuple[int | None, str | None, str | None]:
    with engine.begin() as conn:
        contagem = (
            conn.execute(
                text("""
                    SELECT id, status
                    FROM contagens
                    WHERE data_contagem = :reference_date
                    ORDER BY id DESC
                    LIMIT 1
                    """),
                {"reference_date": reference_date},
            )
            .mappings()
            .first()
        )
        if contagem is None:
            return None, None, "Nenhuma contagem encontrada para a data de referência."

        total_items = int(
            conn.execute(
                text(
                    "SELECT count(*) FROM ingredientes WHERE category_id != :category_id"
                ),
                {"category_id": EXCLUDED_PURCHASE_CATEGORY_ID},
            ).scalar()
            or 0
        )
        counted_items = int(
            conn.execute(
                text(
                    "SELECT count(DISTINCT ingrediente_id) FROM contagem_log WHERE contagem_id = :contagem_id"
                ),
                {"contagem_id": contagem["id"]},
            ).scalar()
            or 0
        )

    if contagem["status"] != "finalizada":
        return (
            int(contagem["id"]),
            str(contagem["status"]),
            "A contagem do dia ainda não foi finalizada.",
        )
    if counted_items < total_items:
        return (
            int(contagem["id"]),
            str(contagem["status"]),
            f"A contagem está finalizada, mas possui {total_items - counted_items} item(ns) pendente(s).",
        )
    return int(contagem["id"]), str(contagem["status"]), None


def read_sources(engine) -> dict[str, pd.DataFrame]:
    queries = {
        "vendas": "SELECT id, date_time, recipe_id, quantity, unit_price FROM vendas",
        "pedidos": "SELECT id, supplier_id, ingredient_id, qty, valor, data_pedido, status, data_prevista FROM pedidos",
        "pedidos_log": "SELECT id, data_pedido, ingredient_id, qty, data_prevista, order_type FROM pedidos_log",
        "estoques": "SELECT id, date_time, ingredient_id, quantity FROM estoques",
        "receitas": 'SELECT id, name, "type", yield_qty, yield_unit, output_ingredient_id, sale_price FROM receitas',
        "receitas_ingredientes": "SELECT recipe_id, ingredient_id, qty, unit FROM receitas_ingredientes",
        "ingredientes": "SELECT id, name, unit, category_id FROM ingredientes",
        "categorias": "SELECT id, name FROM categorias",
        "fornecedores": "SELECT id, name, cnpj, email, phone, avg_delivery_time FROM fornecedores",
        "fornecedores_ingredientes": "SELECT supplier_id, ingredient_id, price, discount_percent, min_to_discount FROM fornecedores_ingredientes",
        "feriados": "SELECT data, nome, tipo FROM feriados_recife",
        "indisponiveis": 'SELECT "match", data_inicio, data_fim FROM produtos_indisponiveis',
        "estoque_atual": "SELECT ingrediente, qtd, data FROM estoque_atual",
    }
    with engine.begin() as conn:
        data = {
            name: pd.read_sql_query(text(query), conn)
            for name, query in queries.items()
        }

    date_columns = {
        "vendas": ["date_time"],
        "pedidos": ["data_pedido", "data_prevista"],
        "pedidos_log": ["data_pedido", "data_prevista"],
        "estoques": ["date_time"],
        "feriados": ["data"],
        "indisponiveis": ["data_inicio", "data_fim"],
        "estoque_atual": ["data"],
    }
    for frame_name, columns in date_columns.items():
        for column in columns:
            if column in data[frame_name].columns:
                data[frame_name][column] = pd.to_datetime(data[frame_name][column])
    return data


def append_operational_stock(
    data: dict[str, pd.DataFrame], reference_date: date
) -> dict[str, pd.DataFrame]:
    current = data["estoque_atual"].copy()
    if current.empty:
        raise RuntimeError(
            "estoque_atual está vazio; não é possível gerar criticidade operacional."
        )

    historical = data["estoques"].copy()
    if historical.empty:
        start_date = reference_date
    else:
        latest_history_date = historical["date_time"].dt.date.max()
        start_date = min(reference_date, latest_history_date + timedelta(days=1))

    dates = pd.date_range(start_date, reference_date, freq="D")
    if dates.empty:
        dates = pd.DatetimeIndex([pd.Timestamp(reference_date)])

    rows = []
    for current_row in current.itertuples(index=False):
        ingredient_id = str(current_row.ingrediente)
        qty = float(current_row.qtd or 0.0)
        for current_date in dates:
            stock_date = current_date.date()
            rows.append(
                {
                    "id": f"CRIT-{stock_date:%Y%m%d}-{ingredient_id}",
                    "date_time": pd.Timestamp.combine(stock_date, time(23, 59, 0)),
                    "ingredient_id": ingredient_id,
                    "quantity": qty,
                }
            )

    data = data.copy()
    data["estoques"] = pd.concat([historical, pd.DataFrame(rows)], ignore_index=True)
    return data


def build_operational_frame(
    engine, config_path: Path, reference_date: date
) -> pd.DataFrame:
    config = load_config(config_path)
    if pd.Timestamp(reference_date) > pd.Timestamp(config["end_date"]):
        config["end_date"] = reference_date.isoformat()
        config["split_dates"]["test_end"] = reference_date.isoformat()

    data = append_operational_stock(read_sources(engine), reference_date)
    abt, _ = build_abt(data, config)
    abt = add_criticality_targets(abt)
    abt["date"] = pd.to_datetime(abt["date"])
    current = abt[abt["date"].dt.date == reference_date].copy()
    if current.empty:
        raise RuntimeError(
            f"Nenhuma linha operacional foi montada para {reference_date.isoformat()}."
        )
    return current.reset_index(drop=True)


def load_model(model_uri: str):
    if mlflow is None:
        raise RuntimeError(
            "MLflow não está instalado. Instale as dependências de ml/requirements.txt."
        )
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    return mlflow.sklearn.load_model(model_uri)


def mlflow_metrics(model_run_id: str | None) -> dict[str, float]:
    if mlflow is None or not model_run_id:
        return {}
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    run = mlflow.tracking.MlflowClient().get_run(model_run_id)
    return {key: float(value) for key, value in run.data.metrics.items()}


def setup_daily_mlflow_experiment() -> None:
    if mlflow is None:
        raise RuntimeError(
            "MLflow não está instalado. Instale as dependências de ml/requirements.txt."
        )
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    if client.get_experiment_by_name(DAILY_MLFLOW_EXPERIMENT) is None:
        client.create_experiment(DAILY_MLFLOW_EXPERIMENT)
    mlflow.set_experiment(DAILY_MLFLOW_EXPERIMENT)


def flatten_numeric(prefix: str, payload: dict[str, Any] | None) -> dict[str, float]:
    values: dict[str, float] = {}
    if not payload:
        return values
    for key, value in payload.items():
        metric_name = f"{prefix}_{key}" if prefix else str(key)
        if isinstance(value, dict):
            values.update(flatten_numeric(metric_name, value))
            continue
        if isinstance(value, (int, float, np.integer, np.floating)) and not pd.isna(value):
            values[metric_name[:250]] = float(value)
    return values


def log_daily_mlflow_run(
    *,
    reference_date: date,
    status: str,
    model_name: str,
    source_model_uri: str,
    source_model_run_id: str | None,
    contagem_id: int | None,
    contagem_status: str | None,
    db_run_id: int,
    metrics: dict[str, Any] | None = None,
    stability: dict[str, Any] | None = None,
    scored: pd.DataFrame | None = None,
    model: Any | None = None,
    error_message: str | None = None,
) -> dict[str, str]:
    setup_daily_mlflow_experiment()
    run_name = f"criticidade_diaria_{reference_date.isoformat()}_{status}"
    with mlflow.start_run(run_name=run_name, nested=mlflow.active_run() is not None) as run:
        mlflow.set_tags(
            {
                "project": "saltim",
                "job": "generate_criticality_report",
                "problem": "stock_criticality",
                "stage": "daily_inference",
                "status": status,
                "reference_date": reference_date.isoformat(),
                "model_name": model_name,
                "source_model_uri": source_model_uri,
                "source_model_run_id": source_model_run_id or "",
                "contagem_id": str(contagem_id or ""),
                "contagem_status": contagem_status or "",
                "db_report_run_id": str(db_run_id),
            }
        )
        mlflow.log_params(
            {
                "reference_date": reference_date.isoformat(),
                "status": status,
                "model_name": model_name,
                "source_model_uri": source_model_uri,
                "source_model_run_id": source_model_run_id or "",
                "contagem_id": contagem_id or "",
                "contagem_status": contagem_status or "",
                "db_report_run_id": db_run_id,
                "run_source": "daily_operational_inference",
            }
        )
        numeric_metrics = {
            **flatten_numeric("", metrics),
            **flatten_numeric("stability", stability),
        }
        if numeric_metrics:
            mlflow.log_metrics(numeric_metrics)
        mlflow.log_dict(metrics or {}, "report/metrics.json")
        mlflow.log_dict(stability or {}, "report/stability.json")
        if error_message:
            mlflow.log_text(error_message, "report/error.txt")
        if scored is not None:
            mlflow.log_text(scored.to_csv(index=False), "report/predictions.csv")
            summary = (
                scored.groupby(["categoria", "criticidade_predita"], dropna=False)
                .size()
                .reset_index(name="total")
            )
            mlflow.log_text(summary.to_csv(index=False), "report/category_summary.csv")
        daily_model_uri = ""
        if model is not None:
            mlflow.sklearn.log_model(model, name="model")
            daily_model_uri = f"runs:/{run.info.run_id}/model"
        return {
            "daily_mlflow_run_id": run.info.run_id,
            "daily_model_uri": daily_model_uri,
            "daily_mlflow_experiment": DAILY_MLFLOW_EXPERIMENT,
        }


def safe_log_daily_mlflow_run(**kwargs: Any) -> dict[str, str]:
    try:
        return log_daily_mlflow_run(**kwargs)
    except Exception as exc:
        return {"daily_mlflow_error": str(exc)}


def score_current_stock(current: pd.DataFrame, model) -> pd.DataFrame:
    feature_columns = select_feature_columns(current)
    X_current = current[feature_columns].copy()
    alert_pred = (
        pd.Series(model.predict(X_current), index=current.index)
        .astype(float)
        .clip(
            lower=MIN_ALERT_THRESHOLD_PCT,
            upper=MAX_ALERT_THRESHOLD_PCT,
        )
    )
    critical_pred = (alert_pred - CRITICAL_THRESHOLD_GAP_PCT).clip(lower=0.0)
    criticality = _derive_criticality(
        current["cobertura_estoque_pct"],
        alert_pred,
        critical_pred,
    )

    scored = current[
        [
            "ingredient_id",
            "nome_ingrediente",
            "categoria_id",
            "categoria",
            "unidade",
            "saldo_atual",
            "stock_position",
            "baseline_threshold",
            "cobertura_estoque_pct",
            TARGET_CRITICAL_THRESHOLD,
        ]
    ].copy()
    scored["limiar_alerta_predito_pct"] = alert_pred
    scored["limiar_critico_predito_pct"] = critical_pred
    scored["criticidade_predita"] = criticality
    scored["necessita_compra"] = scored["criticidade_predita"].eq(PURCHASE_ALERT_LABEL)
    scored["score_alerta_compra"] = (
        scored["limiar_critico_predito_pct"] - scored["cobertura_estoque_pct"]
    )
    scored = scored.sort_values(
        ["necessita_compra", "score_alerta_compra", "cobertura_estoque_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    scored["rank_position"] = np.arange(1, len(scored) + 1)
    return scored


def stability_payload(
    engine, alert_rate: float, metrics: dict[str, Any]
) -> dict[str, Any]:
    with engine.begin() as conn:
        previous = pd.read_sql_query(
            text("""
                SELECT alert_rate
                FROM ml.criticidade_report_runs
                WHERE status = 'success'
                ORDER BY generated_at DESC, id DESC
                LIMIT 30
                """),
            conn,
        )

    training_alert_rate = metrics.get("taxa_alerta_compra") or metrics.get(
        "taxa_necessita_compra"
    )
    payload: dict[str, Any] = {
        "current_alert_rate": alert_rate,
        "training_alert_rate": training_alert_rate,
    }
    if training_alert_rate is not None:
        payload["delta_vs_training_alert_rate"] = alert_rate - float(
            training_alert_rate
        )

    if previous.empty:
        payload["status"] = "sem_historico_operacional"
        payload["previous_runs"] = 0
        return payload

    mean_rate = float(previous["alert_rate"].mean())
    std_rate = float(previous["alert_rate"].std(ddof=0))
    payload.update(
        {
            "previous_runs": int(len(previous)),
            "previous_alert_rate_mean": mean_rate,
            "previous_alert_rate_std": std_rate,
            "delta_vs_previous_mean": alert_rate - mean_rate,
            "coefficient_of_variation": (std_rate / mean_rate if mean_rate else None),
        }
    )
    payload["status"] = (
        "estavel"
        if abs(alert_rate - mean_rate) <= max(0.05, 2 * std_rate)
        else "atencao"
    )
    return payload


def insert_items(engine, run_id: int, scored: pd.DataFrame) -> None:
    sql = text("""
        INSERT INTO ml.criticidade_report_items (
            run_id,
            ingredient_id,
            ingredient_name,
            category_id,
            category,
            unit,
            estoque_atual,
            stock_position,
            baseline_threshold,
            cobertura_estoque_pct,
            limiar_alerta_predito_pct,
            limiar_critico_predito_pct,
            criticidade_predita,
            necessita_compra,
            score_alerta_compra,
            rank_position
        )
        VALUES (
            :run_id,
            :ingredient_id,
            :ingredient_name,
            :category_id,
            :category,
            :unit,
            :estoque_atual,
            :stock_position,
            :baseline_threshold,
            :cobertura_estoque_pct,
            :limiar_alerta_predito_pct,
            :limiar_critico_predito_pct,
            :criticidade_predita,
            :necessita_compra,
            :score_alerta_compra,
            :rank_position
        )
        """)
    records = []
    for row in scored.itertuples(index=False):
        records.append(
            {
                "run_id": run_id,
                "ingredient_id": str(row.ingredient_id),
                "ingredient_name": str(row.nome_ingrediente),
                "category_id": str(row.categoria_id),
                "category": str(row.categoria),
                "unit": str(row.unidade),
                "estoque_atual": float(row.saldo_atual),
                "stock_position": float(row.stock_position),
                "baseline_threshold": float(row.baseline_threshold),
                "cobertura_estoque_pct": float(row.cobertura_estoque_pct),
                "limiar_alerta_predito_pct": float(row.limiar_alerta_predito_pct),
                "limiar_critico_predito_pct": float(row.limiar_critico_predito_pct),
                "criticidade_predita": str(row.criticidade_predita),
                "necessita_compra": int(bool(row.necessita_compra)),
                "score_alerta_compra": float(row.score_alerta_compra),
                "rank_position": int(row.rank_position),
            }
        )
    if records:
        with engine.begin() as conn:
            conn.execute(sql, records)


def run_job(args: argparse.Namespace) -> int:
    engine = create_engine(normalize_database_url(args.database_url))
    ensure_schema(engine)
    reference_date = resolve_reference_date(engine, args.reference_date)
    model_run_id = model_run_id_from_uri(args.model_uri)
    upsert_job_status(engine, reference_date, "running")
    try:
        historical_sales_payload = backfill_historical_sales_until_cutoff(
            engine, reference_date
        )
        historical_stock_payload = backfill_historical_stock_until_cutoff(
            engine, reference_date
        )
    except Exception as exc:
        detail = f"{exc}\n{traceback.format_exc(limit=8)}"
        upsert_job_status(engine, reference_date, "failed", detail[:4000])
        metrics = {
            "model": args.model_name,
            "model_uri": args.model_uri,
            "status": "failed",
            "vendas_historicas": {
                "status": "failed",
                "error": str(exc),
            },
            "estoques_historicos": {
                "status": "failed",
                "error": str(exc),
            },
        }
        run_id = insert_run(
            engine,
            reference_date=reference_date,
            status="failed",
            model_name=args.model_name,
            model_uri=args.model_uri,
            model_run_id=model_run_id,
            metrics=metrics,
            error_message=detail[:4000],
        )
        print(f"Falha registrada no run {run_id}: {exc}")
        return 1

    contagem_id, contagem_status, validation_error = validate_contagem(
        engine, reference_date
    )
    if validation_error:
        upsert_job_status(engine, reference_date, "pending", validation_error)
        metrics = {
            "model": args.model_name,
            "model_uri": args.model_uri,
            "status": "pending_contagem",
            "vendas_historicas": historical_sales_payload,
            "estoques_historicos": historical_stock_payload,
        }
        run_id = insert_run(
            engine,
            reference_date=reference_date,
            status="pending_contagem",
            model_name=args.model_name,
            model_uri=args.model_uri,
            model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            metrics=metrics,
            error_message=validation_error,
        )
        daily_mlflow = safe_log_daily_mlflow_run(
            reference_date=reference_date,
            status="pending_contagem",
            model_name=args.model_name,
            source_model_uri=args.model_uri,
            source_model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            db_run_id=run_id,
            metrics=metrics,
            stability={},
            error_message=validation_error,
        )
        metrics["daily_mlflow"] = daily_mlflow
        update_run_payload(engine, run_id, metrics=metrics)
        print(f"Relatório pendente registrado no run {run_id}: {validation_error}")
        return 0

    try:
        operational_sales_payload = generate_operational_sales_from_contagem(
            engine, reference_date, int(contagem_id)
        )
        current = build_operational_frame(engine, args.config, reference_date)
        model = load_model(args.model_uri)
        scored = score_current_stock(current, model)
        total_items = int(len(scored))
        alert_count = int(scored["necessita_compra"].sum())
        ok_count = total_items - alert_count
        alert_rate = alert_count / total_items if total_items else 0.0
        model_metrics = mlflow_metrics(model_run_id)
        metrics = {
            "model": args.model_name,
            "model_uri": args.model_uri,
            "total_items": total_items,
            "ok_count": ok_count,
            "alert_count": alert_count,
            "alert_rate": alert_rate,
            "mlflow": model_metrics,
            "vendas_historicas": historical_sales_payload,
            "estoques_historicos": historical_stock_payload,
            "vendas_geradas": operational_sales_payload,
        }
        stability = stability_payload(engine, alert_rate, model_metrics)
        run_id = insert_run(
            engine,
            reference_date=reference_date,
            status="success",
            model_name=args.model_name,
            model_uri=args.model_uri,
            model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            total_items=total_items,
            ok_count=ok_count,
            alert_count=alert_count,
            alert_rate=alert_rate,
            metrics=metrics,
            stability=stability,
        )
        insert_items(engine, run_id, scored)
        daily_mlflow = safe_log_daily_mlflow_run(
            reference_date=reference_date,
            status="success",
            model_name=args.model_name,
            source_model_uri=args.model_uri,
            source_model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            db_run_id=run_id,
            metrics=metrics,
            stability=stability,
            scored=scored,
            model=model,
        )
        metrics["daily_mlflow"] = daily_mlflow
        update_run_payload(engine, run_id, metrics=metrics, stability=stability)
        upsert_job_status(engine, reference_date, "success")
        print(
            "Relatório de criticidade gerado: "
            f"run={run_id}, data={reference_date.isoformat()}, "
            f"alertas={alert_count}/{total_items} ({alert_rate:.2%})."
        )
        return 0
    except Exception as exc:
        detail = f"{exc}\n{traceback.format_exc(limit=8)}"
        upsert_job_status(engine, reference_date, "failed", detail[:4000])
        metrics = {
            "model": args.model_name,
            "model_uri": args.model_uri,
            "status": "failed",
        }
        run_id = insert_run(
            engine,
            reference_date=reference_date,
            status="failed",
            model_name=args.model_name,
            model_uri=args.model_uri,
            model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            metrics=metrics,
            error_message=detail[:4000],
        )
        daily_mlflow = safe_log_daily_mlflow_run(
            reference_date=reference_date,
            status="failed",
            model_name=args.model_name,
            source_model_uri=args.model_uri,
            source_model_run_id=model_run_id,
            contagem_id=contagem_id,
            contagem_status=contagem_status,
            db_run_id=run_id,
            metrics=metrics,
            stability={},
            error_message=detail[:4000],
        )
        metrics["daily_mlflow"] = daily_mlflow
        update_run_payload(engine, run_id, metrics=metrics)
        print(f"Falha registrada no run {run_id}: {exc}")
        return 1


def main() -> None:
    raise SystemExit(run_job(parse_args()))


if __name__ == "__main__":
    main()
