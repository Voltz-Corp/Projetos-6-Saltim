from __future__ import annotations

import math
import os
import re
import warnings
from io import StringIO
from collections.abc import Mapping
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-saltim")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    import mlflow
    import mlflow.sklearn
except ImportError:
    mlflow = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATHS = [
    PROJECT_ROOT / "data" / "ml_dataset" / "outputs" / "abt_reposicao_part1.csv",
    PROJECT_ROOT / "data" / "ml_dataset" / "outputs" / "abt_reposicao_part2.csv",
]
MLFLOW_TRACKING_URI = "http://localhost:5000"
SAMPLE_FRAC = 0.25
SAMPLE_RANDOM_STATE = 42
MLFLOW_NOTEBOOK_GROUPS = {
    "01_two_stage_knn": "01_modelos_teste",
    "02_two_stage_linear": "01_modelos_teste",
    "03_two_stage_tree_ensembles": "01_modelos_teste",
    "04_two_stage_model_comparison": "01_modelos_teste",
    "05_random_forest_regressor_threshold_tuning": "02_modelos_finais",
    "06_xgboost_regressor_threshold_tuning": "02_modelos_finais",
    "07_modelos_finais_comparison": "02_modelos_finais",
}

TARGET_ALERT_THRESHOLD = "y_alert_threshold_pct"
TARGET_CRITICAL_THRESHOLD = "y_critical_threshold_pct"
TARGET_CRITICALITY = "y_criticidade_nivel_ajustado"
SPLIT_COLUMN = "split_temporal"
TRAIN_SPLIT = "train"
VALIDATION_SPLIT = "validation"
TEST_SPLIT = "test"

BASE_ALERT_THRESHOLD_PCT = 0.25
CRITICAL_THRESHOLD_GAP_PCT = 0.15
MIN_ALERT_THRESHOLD_PCT = 0.15
MAX_ALERT_THRESHOLD_PCT = 1.0
HISTORY_WINDOW_DAYS = 14
PURCHASE_ALERT_LABEL = "Alerta de compra"
CLASS_LABELS = ["OK", PURCHASE_ALERT_LABEL]

EXPLICIT_FEATURE_EXCLUSIONS = {
    "date",
    "ingredient_id",
    "nome_ingrediente",
    "split_temporal",
    "safety_stock",
    "horizonte_dias",
    "target_horizonte_completo",
    "criticidade_score",
    "lead_time_pedido_no_dia",
    "cobertura_estoque_pct",
    TARGET_ALERT_THRESHOLD,
    TARGET_CRITICAL_THRESHOLD,
    TARGET_CRITICALITY,
}


def ensure_artifact_dirs() -> None:
    """Compat shim: artifacts are stored by MLflow, not in the repository."""
    return None


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _mlflow_tracking_uri() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", MLFLOW_TRACKING_URI)


def _mlflow_notebook_folder(notebook_id: str) -> str:
    return MLFLOW_NOTEBOOK_GROUPS.get(slugify(notebook_id), "deprecated")


def _mlflow_notebook_path(notebook_id: str) -> str:
    return f"notebooks/{_mlflow_notebook_folder(notebook_id)}/{slugify(notebook_id)}"


def _mlflow_experiment_name(notebook_id: str, stage: str) -> str:
    return os.environ.get(
        "MLFLOW_EXPERIMENT_NAME",
        f"{_mlflow_notebook_path(notebook_id)}/{slugify(stage)}",
    )


def _mlflow_registered_model_name(metric_row: Mapping[str, object]) -> str:
    return "saltim_two_stage_{notebook}_{stage}_{model}".format(
        notebook=slugify(str(metric_row["notebook"])),
        stage=slugify(str(metric_row["stage"])),
        model=slugify(str(metric_row["model"])),
    )


def _setup_mlflow_experiment(notebook_id: str, stage: str) -> None:
    if mlflow is None:
        raise RuntimeError(
            "MLflow nao esta instalado. Instale as dependencias de ml/requirements.txt "
            "para registrar os experimentos."
        )
    mlflow.set_tracking_uri(_mlflow_tracking_uri())
    experiment_name = _mlflow_experiment_name(notebook_id, stage)
    client = mlflow.tracking.MlflowClient()
    try:
        experiment = client.get_experiment_by_name(experiment_name)
        if experiment is None:
            client.create_experiment(experiment_name)
    except Exception as exc:
        raise RuntimeError(
            "Nao foi possivel conectar ao MLflow em "
            f"{_mlflow_tracking_uri()}. Suba o servico com: docker compose up -d --build db mlflow"
        ) from exc
    mlflow.set_experiment(experiment_name)


def _safe_mlflow_param_value(value: object) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
    else:
        text = repr(value)
    return text[:500]


def _flatten_summary_params(summary: Mapping[str, object] | None) -> dict[str, object]:
    if not summary:
        return {}

    params: dict[str, object] = {}
    split_counts = summary.get("split_counts", {})
    criticality_rates = summary.get("criticality_rates", {})
    if isinstance(split_counts, Mapping):
        for split_name, count in split_counts.items():
            params[f"split_count_{slugify(str(split_name))}"] = count
    if isinstance(criticality_rates, Mapping):
        for label, rate in criticality_rates.items():
            params[f"criticality_rate_{slugify(str(label))}"] = rate

    for key in [
        "sample_shape",
        "base_alert_threshold_pct",
        "critical_threshold_gap_pct",
        "history_window_days",
        "feature_count",
    ]:
        if key in summary:
            params[key] = summary[key]
    return params


def _model_hyperparams_for_mlflow(model: object) -> dict[str, object]:
    estimator = model
    if isinstance(model, Pipeline) and "model" in model.named_steps:
        estimator = model.named_steps["model"]

    params = {
        "model_class": estimator.__class__.__name__,
        "pipeline_class": model.__class__.__name__,
    }
    if hasattr(estimator, "get_params"):
        for key, value in estimator.get_params(deep=False).items():
            params[f"hyperparam_{key}"] = value
    return params


def _metrics_for_mlflow(metric_row: Mapping[str, object]) -> dict[str, float]:
    metrics = {}
    metric_columns = [
        "accuracy",
        "balanced_accuracy",
        "f1_macro",
        "precision_macro",
        "recall_macro",
        "taxa_ok",
        "taxa_alerta_compra",
        "taxa_necessita_compra",
        "roc_auc",
        "average_precision",
        "rmse",
        "mae",
        "r2",
    ]
    for column in metric_columns:
        value = metric_row.get(column)
        if value is None or pd.isna(value):
            continue
        metrics[column] = float(value)
    return metrics


def _log_two_stage_run_to_mlflow(
    model: object,
    metric_row: Mapping[str, object],
    predictions: pd.DataFrame,
    summary: Mapping[str, object] | None = None,
    run_source: str = "training",
) -> dict[str, str]:
    if mlflow is None:
        _setup_mlflow_experiment(str(metric_row["notebook"]), str(metric_row["stage"]))

    notebook_id = str(metric_row["notebook"])
    stage = str(metric_row["stage"])
    model_name = str(metric_row["model"])
    model_slug = slugify(model_name)
    stage_slug = slugify(stage)
    metric_artifact_path = f"evaluation/{notebook_id}_{model_slug}_{stage_slug}_metrics.csv"
    prediction_artifact_path = f"evaluation/{notebook_id}_{model_slug}_{stage_slug}_predictions.csv"
    summary_artifact_path = f"evaluation/{notebook_id}_run_summary.json"
    _setup_mlflow_experiment(notebook_id, stage)

    params = {
        "notebook": notebook_id,
        "family": metric_row.get("family", ""),
        "stage": stage,
        "model": model_name,
        "registered_model_name": _mlflow_registered_model_name(metric_row),
        "run_source": run_source,
        "sample_frac": SAMPLE_FRAC,
        "sample_random_state": SAMPLE_RANDOM_STATE,
        "target_alert_threshold": TARGET_ALERT_THRESHOLD,
        "target_critical_threshold": TARGET_CRITICAL_THRESHOLD,
        "target_criticality": TARGET_CRITICALITY,
        "purchase_alert_label": PURCHASE_ALERT_LABEL,
        "min_alert_threshold_pct": MIN_ALERT_THRESHOLD_PCT,
        "max_alert_threshold_pct": MAX_ALERT_THRESHOLD_PCT,
        "metric_artifact_path": metric_artifact_path,
        "prediction_artifact_path": prediction_artifact_path,
        "summary_artifact_path": summary_artifact_path,
    }
    params.update(_flatten_summary_params(summary))
    params.update(_model_hyperparams_for_mlflow(model))
    params = {key[:250]: _safe_mlflow_param_value(value) for key, value in params.items()}

    tags = {
        "project": "saltim",
        "problem": "stock_criticality",
        "stage": stage,
        "family": str(metric_row.get("family", "")),
        "notebook": notebook_id,
        "notebook_folder": _mlflow_notebook_folder(notebook_id),
        "notebook_path": _mlflow_notebook_path(notebook_id),
        "experiment_path": _mlflow_experiment_name(notebook_id, stage),
        "registered_model_name": _mlflow_registered_model_name(metric_row),
        "metric_artifact_path": metric_artifact_path,
        "prediction_artifact_path": prediction_artifact_path,
        "summary_artifact_path": summary_artifact_path,
    }
    run_name = f"{notebook_id} - {stage} - {model_name}"

    with mlflow.start_run(run_name=run_name, nested=mlflow.active_run() is not None) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(_metrics_for_mlflow(metric_row))
        mlflow.set_tags(tags)
        mlflow.log_text(pd.DataFrame([metric_row]).to_csv(index=False), metric_artifact_path)
        mlflow.log_text(predictions.to_csv(index=False), prediction_artifact_path)
        if summary:
            mlflow.log_dict(dict(summary), summary_artifact_path)

        mlflow.sklearn.log_model(
            model,
            name="model",
            registered_model_name=_mlflow_registered_model_name(metric_row),
            await_registration_for=120,
        )
        return {
            "run_id": run.info.run_id,
            "model_uri": f"runs:/{run.info.run_id}/model",
            "metric_artifact_path": metric_artifact_path,
            "prediction_artifact_path": prediction_artifact_path,
            "summary_artifact_path": summary_artifact_path,
            "registered_model_name": _mlflow_registered_model_name(metric_row),
        }


def _stock_coverage_pct(df: pd.DataFrame) -> pd.Series:
    stock_position = df["stock_position"].fillna(0.0).astype(float)
    baseline_threshold = df["baseline_threshold"].fillna(0.0).astype(float)
    coverage = (stock_position / baseline_threshold.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
    fallback = pd.Series(np.where(stock_position > 0, 1.0, 0.0), index=df.index)
    return coverage.where(coverage.notna(), fallback).clip(lower=0.0, upper=1.0)


def _derive_criticality(
    coverage_pct: pd.Series | np.ndarray,
    alert_threshold_pct: pd.Series | np.ndarray,
    critical_threshold_pct: pd.Series | np.ndarray,
) -> np.ndarray:
    coverage = np.asarray(coverage_pct, dtype=float)
    critical_threshold = np.asarray(critical_threshold_pct, dtype=float)
    return np.select(
        [coverage <= critical_threshold],
        [PURCHASE_ALERT_LABEL],
        default="OK",
    )


def _labels_from_binary(values: pd.Series | np.ndarray) -> np.ndarray:
    numeric = np.asarray(values, dtype=int)
    return np.where(numeric == 1, PURCHASE_ALERT_LABEL, "OK")


def _binary_from_labels(values: pd.Series | np.ndarray) -> np.ndarray:
    return np.asarray(values) == PURCHASE_ALERT_LABEL


def _binary_alert(values: pd.Series | np.ndarray) -> np.ndarray:
    return (np.asarray(values, dtype=object) == PURCHASE_ALERT_LABEL).astype(int)


def _dynamic_alert_thresholds_for_group(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("date").copy()
    dates = pd.to_datetime(group["date"])
    coverage = group["cobertura_estoque_pct"].to_numpy(dtype=float)
    alert_thresholds: list[float] = []
    critical_thresholds: list[float] = []
    classes: list[str] = []

    for idx, current_date in enumerate(dates):
        window_start = current_date - pd.Timedelta(days=HISTORY_WINDOW_DAYS)
        history_mask = (dates.iloc[:idx] >= window_start) & (dates.iloc[:idx] < current_date)
        if history_mask.any():
            history_classes = np.asarray(classes, dtype=object)[history_mask.to_numpy()]
            critical_rate = float((history_classes == PURCHASE_ALERT_LABEL).mean())
        else:
            critical_rate = 0.0

        pressure = 0.50 * critical_rate
        alert_threshold = float(np.clip(BASE_ALERT_THRESHOLD_PCT + pressure, MIN_ALERT_THRESHOLD_PCT, MAX_ALERT_THRESHOLD_PCT))
        critical_threshold = float(max(alert_threshold - CRITICAL_THRESHOLD_GAP_PCT, 0.0))
        criticality = _derive_criticality(
            np.asarray([coverage[idx]]),
            np.asarray([alert_threshold]),
            np.asarray([critical_threshold]),
        )[0]

        alert_thresholds.append(alert_threshold)
        critical_thresholds.append(critical_threshold)
        classes.append(criticality)

    group[TARGET_ALERT_THRESHOLD] = alert_thresholds
    group[TARGET_CRITICAL_THRESHOLD] = critical_thresholds
    group[TARGET_CRITICALITY] = classes
    return group


def add_criticality_targets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["cobertura_estoque_pct"] = _stock_coverage_pct(df)
    adjusted = pd.concat(
        [
            _dynamic_alert_thresholds_for_group(group)
            for _, group in df.sort_values(["ingredient_id", "date"]).groupby("ingredient_id", sort=False)
        ],
        ignore_index=False,
    )
    return adjusted.sort_index()


def load_abt_full() -> pd.DataFrame:
    frames = [pd.read_csv(path, low_memory=False) for path in DATASET_PATHS]
    df = pd.concat(frames, ignore_index=True)
    df = df[df[SPLIT_COLUMN].isin([TRAIN_SPLIT, VALIDATION_SPLIT, TEST_SPLIT])]
    df = add_criticality_targets(df)
    return df.reset_index(drop=True)


def load_abt_sample(sample_frac: float = SAMPLE_FRAC) -> pd.DataFrame:
    if sample_frac <= 0 or sample_frac > 1:
        raise ValueError("sample_frac deve estar no intervalo (0, 1].")
    df = load_abt_full()
    if sample_frac == 1:
        return df.reset_index(drop=True)
    df = df.sample(frac=sample_frac, random_state=SAMPLE_RANDOM_STATE)
    return df.reset_index(drop=True)


def select_feature_columns(df: pd.DataFrame) -> list[str]:
    excluded = set(EXPLICIT_FEATURE_EXCLUSIONS)
    for column in df.columns:
        if column.startswith("y_") or column.startswith("baseline_"):
            excluded.add(column)
        if "audit" in column:
            excluded.add(column)
    return [column for column in df.columns if column not in excluded]


def build_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    numeric_features = X_train.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = [column for column in X_train.columns if column not in numeric_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def build_splits(df: pd.DataFrame) -> dict[str, object]:
    feature_columns = select_feature_columns(df)
    X = df[feature_columns].copy()
    y_threshold = df[TARGET_ALERT_THRESHOLD].astype(float)
    y_purchase_alert = df[TARGET_CRITICALITY].eq(PURCHASE_ALERT_LABEL).astype(int)
    split = df[SPLIT_COLUMN]

    train_mask = split.eq(TRAIN_SPLIT)
    validation_mask = split.eq(VALIDATION_SPLIT)
    test_mask = split.eq(TEST_SPLIT)

    context_columns = [
        "ingredient_id",
        "date",
        "nome_ingrediente",
        "categoria",
        "unidade",
        "stock_position",
        "baseline_threshold",
        "cobertura_estoque_pct",
        TARGET_ALERT_THRESHOLD,
        TARGET_CRITICAL_THRESHOLD,
        TARGET_CRITICALITY,
    ]
    context = df[context_columns].copy()

    return {
        "feature_columns": feature_columns,
        "X_train": X.loc[train_mask],
        "X_validation": X.loc[validation_mask],
        "X_test": X.loc[test_mask],
        "y_threshold_train": y_threshold.loc[train_mask],
        "y_threshold_validation": y_threshold.loc[validation_mask],
        "y_threshold_test": y_threshold.loc[test_mask],
        "y_purchase_alert_train": y_purchase_alert.loc[train_mask],
        "y_purchase_alert_validation": y_purchase_alert.loc[validation_mask],
        "y_purchase_alert_test": y_purchase_alert.loc[test_mask],
        "context_test": context.loc[test_mask].reset_index(drop=True),
        "sample_shape": df.shape,
        "split_counts": split.value_counts().to_dict(),
        "criticality_rates": df[TARGET_CRITICALITY].value_counts(normalize=True).reindex(CLASS_LABELS, fill_value=0.0).to_dict(),
    }


def pipeline_for(model, X_train: pd.DataFrame) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(X_train)),
            ("model", model),
        ]
    )


def _fit_with_warnings(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pipeline.fit(X, y)
    return [f"{item.category.__name__}: {item.message}" for item in caught]


def _prediction_probability(pipeline: Pipeline, X: pd.DataFrame) -> np.ndarray:
    if not hasattr(pipeline, "predict_proba"):
        return np.full(len(X), np.nan)
    probabilities = pipeline.predict_proba(X)
    if probabilities.ndim == 2 and probabilities.shape[1] > 1:
        return probabilities[:, 1]
    return np.full(len(X), np.nan)


def _threshold_prediction_frame(
    notebook_id: str,
    family: str,
    model_name: str,
    context: pd.DataFrame,
    y_true_threshold: pd.Series,
    y_pred_threshold: np.ndarray,
) -> pd.DataFrame:
    predictions = context.reset_index(drop=True).copy()
    alert_real = y_true_threshold.reset_index(drop=True).astype(float)
    alert_pred = pd.Series(y_pred_threshold, index=predictions.index).astype(float).clip(
        lower=MIN_ALERT_THRESHOLD_PCT,
        upper=MAX_ALERT_THRESHOLD_PCT,
    )
    critical_pred = (alert_pred - CRITICAL_THRESHOLD_GAP_PCT).clip(lower=0.0)

    predictions.insert(0, "notebook", notebook_id)
    predictions.insert(1, "family", family)
    predictions.insert(2, "model", model_name)
    predictions["limiar_alerta_real_pct"] = alert_real
    predictions["limiar_alerta_predito_pct"] = alert_pred
    predictions["limiar_critico_predito_pct"] = critical_pred
    predictions["criticidade_real"] = _derive_criticality(
        predictions["cobertura_estoque_pct"],
        predictions["limiar_alerta_real_pct"],
        predictions[TARGET_CRITICAL_THRESHOLD],
    )
    predictions["criticidade_predita"] = _derive_criticality(
        predictions["cobertura_estoque_pct"],
        predictions["limiar_alerta_predito_pct"],
        predictions["limiar_critico_predito_pct"],
    )
    predictions["probabilidade_alerta_compra"] = np.nan
    predictions["score_alerta_compra"] = predictions["limiar_critico_predito_pct"] - predictions["cobertura_estoque_pct"]
    predictions["necessita_compra"] = predictions["criticidade_predita"].eq(PURCHASE_ALERT_LABEL)
    predictions["erro_limiar_alerta_pct"] = predictions["limiar_alerta_predito_pct"] - predictions["limiar_alerta_real_pct"]
    return predictions


def _classifier_prediction_frame(
    notebook_id: str,
    family: str,
    model_name: str,
    context: pd.DataFrame,
    y_pred_class: np.ndarray,
    y_proba: np.ndarray,
) -> pd.DataFrame:
    predictions = context.reset_index(drop=True).copy()
    predictions.insert(0, "notebook", notebook_id)
    predictions.insert(1, "family", family)
    predictions.insert(2, "model", model_name)
    predictions["limiar_alerta_real_pct"] = predictions[TARGET_ALERT_THRESHOLD].astype(float)
    predictions["limiar_alerta_predito_pct"] = np.nan
    predictions["limiar_critico_predito_pct"] = np.nan
    predictions["criticidade_real"] = predictions[TARGET_CRITICALITY]
    predictions["criticidade_predita"] = y_pred_class
    predictions["probabilidade_alerta_compra"] = y_proba
    predictions["score_alerta_compra"] = pd.Series(y_proba, index=predictions.index).where(
        ~np.isnan(y_proba),
        _binary_alert(predictions["criticidade_predita"]),
    )
    predictions["necessita_compra"] = predictions["criticidade_predita"].eq(PURCHASE_ALERT_LABEL)
    predictions["erro_limiar_alerta_pct"] = np.nan
    return predictions


def _criticality_metric_row(
    notebook_id: str,
    family: str,
    stage: str,
    model_name: str,
    predictions: pd.DataFrame,
    fit_warnings: list[str],
) -> dict[str, object]:
    y_true_class = predictions["criticidade_real"]
    y_pred_class = predictions["criticidade_predita"]
    class_rates = predictions["criticidade_predita"].value_counts(normalize=True).reindex(CLASS_LABELS, fill_value=0.0)
    y_true_binary = _binary_from_labels(y_true_class)
    y_pred_binary = _binary_from_labels(y_pred_class)
    y_score = predictions["probabilidade_alerta_compra"].to_numpy(dtype=float)

    row = {
        "notebook": notebook_id,
        "family": family,
        "stage": stage,
        "model": model_name,
        "accuracy": float(accuracy_score(y_true_class, y_pred_class)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true_class, y_pred_class)),
        "f1_macro": float(f1_score(y_true_class, y_pred_class, labels=CLASS_LABELS, average="macro", zero_division=0)),
        "precision_macro": float(
            precision_score(y_true_class, y_pred_class, labels=CLASS_LABELS, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true_class, y_pred_class, labels=CLASS_LABELS, average="macro", zero_division=0)
        ),
        "taxa_ok": float(class_rates["OK"]),
        "taxa_alerta_compra": float(class_rates[PURCHASE_ALERT_LABEL]),
        "taxa_necessita_compra": float(predictions["necessita_compra"].mean()),
        "warnings": " | ".join(fit_warnings),
    }
    if not np.isnan(y_score).all() and len(np.unique(y_true_binary)) == 2:
        row["roc_auc"] = float(roc_auc_score(y_true_binary, y_score))
        row["average_precision"] = float(average_precision_score(y_true_binary, y_score))
    else:
        row["roc_auc"] = np.nan
        row["average_precision"] = np.nan
    if predictions["limiar_alerta_predito_pct"].notna().any():
        y_true_threshold = predictions["limiar_alerta_real_pct"].to_numpy(dtype=float)
        y_pred_threshold = predictions["limiar_alerta_predito_pct"].to_numpy(dtype=float)
        row["rmse"] = float(math.sqrt(mean_squared_error(y_true_threshold, y_pred_threshold)))
        row["mae"] = float(mean_absolute_error(y_true_threshold, y_pred_threshold))
        row["r2"] = float(r2_score(y_true_threshold, y_pred_threshold))
    else:
        row["rmse"] = np.nan
        row["mae"] = np.nan
        row["r2"] = np.nan
    return row


def train_threshold_models(
    notebook_id: str,
    family: str,
    models: dict[str, object],
    splits: dict[str, object],
    summary: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train = splits["y_threshold_train"]
    y_test = splits["y_threshold_test"]
    context_test = splits["context_test"]

    for model_name, model in models.items():
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test)

        predictions = _threshold_prediction_frame(notebook_id, family, model_name, context_test, y_test, y_pred)
        metrics = _criticality_metric_row(
            notebook_id,
            family,
            "threshold_regression",
            model_name,
            predictions,
            fit_warnings,
        )
        mlflow_info = _log_two_stage_run_to_mlflow(
            pipeline,
            metrics,
            predictions,
            summary=summary,
            run_source="training",
        )
        metrics.update(mlflow_info)
        rows.append(metrics)

    return pd.DataFrame(rows)


def train_purchase_alert_classifiers(
    notebook_id: str,
    family: str,
    models: dict[str, object],
    splits: dict[str, object],
    summary: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train = splits["y_purchase_alert_train"]
    context_test = splits["context_test"]

    for model_name, model in models.items():
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test).astype(int)
        y_proba = _prediction_probability(pipeline, X_test)

        predictions = _classifier_prediction_frame(
            notebook_id,
            family,
            model_name,
            context_test,
            _labels_from_binary(y_pred),
            y_proba,
        )
        metrics = _criticality_metric_row(
            notebook_id,
            family,
            "purchase_alert_classification",
            model_name,
            predictions,
            fit_warnings,
        )
        mlflow_info = _log_two_stage_run_to_mlflow(
            pipeline,
            metrics,
            predictions,
            summary=summary,
            run_source="training",
        )
        metrics.update(mlflow_info)
        rows.append(metrics)

    return pd.DataFrame(rows)


def run_training_notebook(
    notebook_id: str,
    family: str,
    threshold_models: dict[str, object],
    purchase_alert_models: dict[str, object],
) -> dict[str, pd.DataFrame]:
    ensure_artifact_dirs()
    df = load_abt_sample()
    splits = build_splits(df)
    summary = {
        "notebook": notebook_id,
        "family": family,
        "sample_shape": list(splits["sample_shape"]),
        "split_counts": splits["split_counts"],
        "criticality_rates": splits["criticality_rates"],
        "base_alert_threshold_pct": BASE_ALERT_THRESHOLD_PCT,
        "critical_threshold_gap_pct": CRITICAL_THRESHOLD_GAP_PCT,
        "history_window_days": HISTORY_WINDOW_DAYS,
        "feature_count": len(splits["feature_columns"]),
        "feature_columns": splits["feature_columns"],
    }

    threshold_metrics = train_threshold_models(notebook_id, family, threshold_models, splits, summary=summary)
    purchase_alert_metrics = train_purchase_alert_classifiers(
        notebook_id,
        family,
        purchase_alert_models,
        splits,
        summary=summary,
    )
    criticality_metrics = pd.concat([threshold_metrics, purchase_alert_metrics], ignore_index=True)

    return {
        "threshold_metrics": threshold_metrics,
        "purchase_alert_metrics": purchase_alert_metrics,
        "criticality_metrics": criticality_metrics,
        "summary": pd.DataFrame([summary]),
    }


def _two_stage_experiments() -> list[object]:
    if mlflow is None:
        _setup_mlflow_experiment("two_stage", "missing_mlflow")

    mlflow.set_tracking_uri(_mlflow_tracking_uri())
    client = mlflow.tracking.MlflowClient()
    try:
        experiments = client.search_experiments()
    except Exception as exc:
        raise RuntimeError(
            "Nao foi possivel buscar experimentos no MLflow. "
            "Suba o servico com: docker compose up -d --build db mlflow"
        ) from exc
    return [
        experiment
        for experiment in experiments
        if experiment.name.startswith("notebooks/") or experiment.name.startswith("saltim_two_stage_")
    ]


def _metric_row_from_mlflow_run(run: object) -> dict[str, object]:
    params = run.data.params
    metrics = run.data.metrics
    row: dict[str, object] = {
        "notebook": params.get("notebook", ""),
        "family": params.get("family", ""),
        "stage": params.get("stage", ""),
        "model": params.get("model", ""),
        "warnings": "",
        "run_id": run.info.run_id,
        "model_uri": f"runs:/{run.info.run_id}/model",
        "registered_model_name": params.get("registered_model_name", ""),
        "metric_artifact_path": params.get("metric_artifact_path", run.data.tags.get("metric_artifact_path", "")),
        "prediction_artifact_path": params.get(
            "prediction_artifact_path",
            run.data.tags.get("prediction_artifact_path", ""),
        ),
        "summary_artifact_path": params.get("summary_artifact_path", run.data.tags.get("summary_artifact_path", "")),
    }
    row.update({key: float(value) for key, value in metrics.items()})
    return row


def _load_metric_artifact_from_run(run: object) -> pd.DataFrame:
    metric_artifact_path = run.data.params.get("metric_artifact_path") or run.data.tags.get("metric_artifact_path")
    if not metric_artifact_path:
        return pd.DataFrame([_metric_row_from_mlflow_run(run)])

    try:
        text = mlflow.artifacts.load_text(f"runs:/{run.info.run_id}/{metric_artifact_path}")
        metrics = pd.read_csv(StringIO(text))
    except Exception:
        metrics = pd.DataFrame([_metric_row_from_mlflow_run(run)])

    metrics["run_id"] = run.info.run_id
    metrics["model_uri"] = f"runs:/{run.info.run_id}/model"
    metrics["registered_model_name"] = run.data.params.get("registered_model_name", "")
    metrics["metric_artifact_path"] = metric_artifact_path
    metrics["prediction_artifact_path"] = run.data.params.get("prediction_artifact_path") or run.data.tags.get(
        "prediction_artifact_path",
        "",
    )
    metrics["summary_artifact_path"] = run.data.params.get("summary_artifact_path") or run.data.tags.get(
        "summary_artifact_path",
        "",
    )
    return metrics


def _add_analysis_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = metrics.copy()
    for column in ["balanced_accuracy", "roc_auc", "average_precision"]:
        if column not in metrics.columns:
            metrics[column] = np.nan

    for index, row in metrics.iterrows():
        try:
            predictions = _load_predictions(row)
        except Exception:
            continue

        if {"criticidade_real", "criticidade_predita"}.issubset(predictions.columns):
            y_true = predictions["criticidade_real"]
            y_pred = predictions["criticidade_predita"]
            metrics.at[index, "balanced_accuracy"] = float(balanced_accuracy_score(y_true, y_pred))

        if "probabilidade_alerta_compra" not in predictions.columns:
            continue
        y_score = predictions["probabilidade_alerta_compra"].to_numpy(dtype=float)
        if np.isnan(y_score).all():
            continue

        y_true_binary = _binary_from_labels(predictions["criticidade_real"])
        if len(np.unique(y_true_binary)) != 2:
            continue
        metrics.at[index, "roc_auc"] = float(roc_auc_score(y_true_binary, y_score))
        metrics.at[index, "average_precision"] = float(average_precision_score(y_true_binary, y_score))

    return metrics


def load_all_metrics() -> pd.DataFrame:
    experiments = _two_stage_experiments()
    if not experiments:
        return pd.DataFrame()

    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        [experiment.experiment_id for experiment in experiments],
        filter_string="tags.project = 'saltim' and tags.problem = 'stock_criticality'",
        max_results=5000,
        order_by=["attributes.start_time ASC"],
    )
    frames = [_load_metric_artifact_from_run(run) for run in runs]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return _add_analysis_metrics(pd.concat(frames, ignore_index=True))


def load_all_models() -> dict[str, object]:
    metrics = load_all_metrics()
    if metrics.empty:
        return {}
    metrics = metrics.drop_duplicates(subset=["stage", "notebook", "family", "model"], keep="last")
    models = {}
    for _, row in metrics.iterrows():
        key = f"{row['notebook']}_{slugify(str(row['stage']))}_{slugify(str(row['model']))}"
        models[key] = mlflow.sklearn.load_model(str(row["model_uri"]))
    return models


def build_decision_table() -> pd.DataFrame:
    criticality = load_all_metrics()
    if criticality.empty:
        return criticality
    criticality = criticality.drop_duplicates(subset=["stage", "notebook", "family", "model"], keep="last")
    rank = criticality.sort_values(
        ["stage", "f1_macro", "roc_auc", "average_precision", "accuracy", "rmse", "mae"],
        ascending=[True, False, False, False, False, True, True],
    ).reset_index(drop=True)
    rank.insert(0, "rank", range(1, len(rank) + 1))
    return rank


def _load_predictions(metric_row: pd.Series) -> pd.DataFrame:
    artifact_path = metric_row.get("prediction_artifact_path")
    run_id = metric_row.get("run_id")
    if not isinstance(artifact_path, str) or not artifact_path or not isinstance(run_id, str) or not run_id:
        raise ValueError("Linha de metrica sem run_id/prediction_artifact_path do MLflow.")
    text = mlflow.artifacts.load_text(f"runs:/{run_id}/{artifact_path}")
    return pd.read_csv(StringIO(text))


def _criticality_model_key(model_name: str) -> str:
    normalized = model_name.lower()
    if "gradient boosting" in normalized:
        return "gradient_boosting"
    if "xgboost" in normalized:
        return "xgboost"
    if "random forest" in normalized:
        return "random_forest"
    if "knn" in normalized:
        return "knn"
    if "linear regression" in normalized:
        return "linear"
    if "logistic" in normalized:
        return "linear"
    return slugify(model_name)


def _load_test_context_and_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_abt_sample()
    feature_columns = select_feature_columns(df)
    test = df[df[SPLIT_COLUMN].eq(TEST_SPLIT)].copy().reset_index(drop=True)
    X_test = test[feature_columns].copy()
    context_columns = [
        "ingredient_id",
        "date",
        "nome_ingrediente",
        "categoria",
        "unidade",
        "stock_position",
        "baseline_threshold",
        "cobertura_estoque_pct",
        TARGET_ALERT_THRESHOLD,
        TARGET_CRITICAL_THRESHOLD,
        TARGET_CRITICALITY,
    ]
    return test[context_columns].copy(), X_test


def _evaluate_operational_model(metric_row: pd.Series, context: pd.DataFrame, X_test: pd.DataFrame) -> pd.DataFrame:
    model = mlflow.sklearn.load_model(str(metric_row["model_uri"]))
    if metric_row["stage"] == "threshold_regression":
        y_pred = model.predict(X_test)
        predictions = _threshold_prediction_frame(
            metric_row["notebook"],
            metric_row["family"],
            metric_row["model"],
            context,
            context[TARGET_ALERT_THRESHOLD],
            y_pred,
        )
    else:
        y_pred = model.predict(X_test).astype(int)
        y_proba = _prediction_probability(model, X_test)
        predictions = _classifier_prediction_frame(
            metric_row["notebook"],
            metric_row["family"],
            metric_row["model"],
            context,
            _labels_from_binary(y_pred),
            y_proba,
        )
    pipeline_name = f"{metric_row['family']} - {metric_row['stage']} - {_criticality_model_key(metric_row['model']).replace('_', ' ').title()}"
    predictions.insert(0, "pipeline", pipeline_name)
    predictions.insert(1, "stage", metric_row["stage"])
    return predictions


def _operational_metric_row(metric_row: pd.Series, recommendations: pd.DataFrame) -> dict[str, object]:
    class_rates = recommendations["criticidade_predita"].value_counts(normalize=True).reindex(CLASS_LABELS, fill_value=0.0)
    return {
        "notebook": metric_row["notebook"],
        "family": metric_row["family"],
        "stage": metric_row["stage"],
        "pipeline": recommendations["pipeline"].iloc[0],
        "model": metric_row["model"],
        "rmse": metric_row["rmse"],
        "mae": metric_row["mae"],
        "r2": metric_row["r2"],
        "accuracy": metric_row["accuracy"],
        "balanced_accuracy": metric_row.get("balanced_accuracy", np.nan),
        "roc_auc": metric_row.get("roc_auc", np.nan),
        "average_precision": metric_row.get("average_precision", np.nan),
        "f1_macro": metric_row["f1_macro"],
        "precision_macro": metric_row["precision_macro"],
        "recall_macro": metric_row["recall_macro"],
        "taxa_ok": float(class_rates["OK"]),
        "taxa_alerta_compra": float(class_rates[PURCHASE_ALERT_LABEL]),
        "taxa_necessita_compra": float(recommendations["necessita_compra"].mean()),
        "limiar_alerta_predito_medio": float(recommendations["limiar_alerta_predito_pct"].mean()),
        "limiar_critico_predito_medio": float(recommendations["limiar_critico_predito_pct"].mean()),
    }


def build_operational_recommendations(
    criticality_rank: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if criticality_rank.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    context, X_test = _load_test_context_and_features()
    recommendation_frames = []
    metric_rows = []

    for _, row in criticality_rank.iterrows():
        recommendations = _evaluate_operational_model(row, context, X_test)
        recommendation_frames.append(recommendations)
        metric_rows.append(_operational_metric_row(row, recommendations))

    all_recommendations = pd.concat(recommendation_frames, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    metrics = metrics.sort_values(
        ["stage", "f1_macro", "accuracy", "rmse", "mae"],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)
    metrics.insert(0, "rank_estrategico", range(1, len(metrics) + 1))

    best_pipeline = metrics.loc[0, "pipeline"]
    best_recommendations = all_recommendations[all_recommendations["pipeline"].eq(best_pipeline)]
    by_ingredient = (
        best_recommendations.groupby(
            ["pipeline", "ingredient_id", "nome_ingrediente", "categoria", "unidade"],
            as_index=False,
        )
        .agg(
            observacoes=("criticidade_predita", "size"),
            dias_ok_preditos=("criticidade_predita", lambda s: int((s == "OK").sum())),
            dias_alerta_compra_preditos=("criticidade_predita", lambda s: int((s == PURCHASE_ALERT_LABEL).sum())),
            dias_necessita_compra=("necessita_compra", "sum"),
            cobertura_estoque_pct_min=("cobertura_estoque_pct", "min"),
            cobertura_estoque_pct_media=("cobertura_estoque_pct", "mean"),
            limiar_alerta_predito_pct_medio=("limiar_alerta_predito_pct", "mean"),
            limiar_critico_predito_pct_medio=("limiar_critico_predito_pct", "mean"),
        )
    )
    by_ingredient["taxa_necessita_compra"] = by_ingredient["dias_necessita_compra"] / by_ingredient["observacoes"]
    by_ingredient = by_ingredient.sort_values(
        ["dias_alerta_compra_preditos", "taxa_necessita_compra", "cobertura_estoque_pct_min"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return metrics, all_recommendations, by_ingredient


def plot_criticality_distribution(operational_metrics: pd.DataFrame) -> plt.Figure:
    plot_df = operational_metrics.melt(
        id_vars=["pipeline"],
        value_vars=["taxa_ok", "taxa_alerta_compra"],
        var_name="criticidade",
        value_name="taxa",
    )
    fig, ax = plt.subplots(figsize=(13, 7))
    sns.barplot(data=plot_df, y="pipeline", x="taxa", hue="criticidade", ax=ax)
    ax.set_title("Distribuicao de criticidade predita por modelo")
    ax.set_xlabel("Taxa")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


def plot_threshold_metric_bars(criticality_rank: pd.DataFrame) -> plt.Figure:
    criticality_rank = criticality_rank[criticality_rank["stage"].eq("threshold_regression")].copy()
    metrics = ["rmse", "mae", "f1_macro"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    labels = criticality_rank["family"] + " - " + criticality_rank["model"]

    for ax, metric in zip(axes, metrics):
        sns.barplot(x=criticality_rank[metric], y=labels, ax=ax, color="#4C78A8")
        ax.set_title(metric.upper())
        ax.set_xlabel(metric.upper())
        ax.set_ylabel("")
        ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    return fig


def plot_classifier_metric_bars(criticality_rank: pd.DataFrame) -> plt.Figure:
    classifiers = criticality_rank[criticality_rank["stage"].eq("purchase_alert_classification")].copy()
    metrics = ["roc_auc", "average_precision", "balanced_accuracy", "f1_macro"]
    fig, axes = plt.subplots(1, 4, figsize=(22, 6))
    labels = classifiers["family"] + " - " + classifiers["model"]

    for ax, metric in zip(axes, metrics):
        sns.barplot(x=classifiers[metric], y=labels, ax=ax, color="#59A14F")
        ax.set_title(metric.upper())
        ax.set_xlabel(metric.upper())
        ax.set_ylabel("")
        ax.set_xlim(0, 1)
        ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    return fig


def plot_purchase_alert_roc_curves(criticality_rank: pd.DataFrame) -> plt.Figure:
    classifiers = criticality_rank[criticality_rank["stage"].eq("purchase_alert_classification")]
    fig, ax = plt.subplots(figsize=(9, 7))

    for _, row in classifiers.iterrows():
        predictions = _load_predictions(row)
        y_score = predictions["probabilidade_alerta_compra"].to_numpy(dtype=float)
        if np.isnan(y_score).all():
            continue
        y_true = _binary_from_labels(predictions["criticidade_real"])
        if len(np.unique(y_true)) != 2:
            continue
        fpr, tpr, _ = roc_curve(y_true, y_score)
        label = f"{row['family']} - {row['model']} (AUC={row['roc_auc']:.3f})"
        ax.plot(fpr, tpr, linewidth=2, label=label)

    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_title("Curvas ROC - alerta de compra")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_purchase_alert_precision_recall_curves(criticality_rank: pd.DataFrame) -> plt.Figure:
    classifiers = criticality_rank[criticality_rank["stage"].eq("purchase_alert_classification")]
    fig, ax = plt.subplots(figsize=(9, 7))

    for _, row in classifiers.iterrows():
        predictions = _load_predictions(row)
        y_score = predictions["probabilidade_alerta_compra"].to_numpy(dtype=float)
        if np.isnan(y_score).all():
            continue
        y_true = _binary_from_labels(predictions["criticidade_real"])
        if len(np.unique(y_true)) != 2:
            continue
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        label = f"{row['family']} - {row['model']} (AP={row['average_precision']:.3f})"
        ax.plot(recall, precision, linewidth=2, label=label)

    ax.set_title("Curvas Precision-Recall - alerta de compra")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_threshold_scatter(
    operational_metrics: pd.DataFrame,
    recommendations: pd.DataFrame,
    top_n: int = 2,
) -> plt.Figure:
    threshold_metrics = operational_metrics[operational_metrics["stage"].eq("threshold_regression")]
    top_pipelines = threshold_metrics.head(top_n)["pipeline"].tolist()
    plot_df = recommendations[recommendations["pipeline"].isin(top_pipelines)].copy()
    fig, axes = plt.subplots(1, len(top_pipelines), figsize=(8 * len(top_pipelines), 6))
    axes = np.array(axes).reshape(-1)

    for ax, pipeline_name in zip(axes, top_pipelines):
        data = plot_df[plot_df["pipeline"].eq(pipeline_name)]
        sns.scatterplot(
            data=data,
            x="limiar_alerta_real_pct",
            y="limiar_alerta_predito_pct",
            hue="criticidade_predita",
            hue_order=CLASS_LABELS,
            alpha=0.35,
            edgecolor=None,
            ax=ax,
        )
        ax.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1)
        ax.set_title(pipeline_name)
        ax.set_xlabel("Limiar de alerta real")
        ax.set_ylabel("Limiar de alerta predito")
        ax.grid(alpha=0.25)

    fig.tight_layout()
    return fig


def plot_confusion_matrices(criticality_rank: pd.DataFrame) -> plt.Figure:
    n_models = len(criticality_rank)
    n_cols = 3
    n_rows = math.ceil(n_models / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    axes = np.array(axes).reshape(-1)

    for ax, (_, row) in zip(axes, criticality_rank.iterrows()):
        predictions = _load_predictions(row)
        matrix = confusion_matrix(predictions["criticidade_real"], predictions["criticidade_predita"], labels=CLASS_LABELS)
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            xticklabels=CLASS_LABELS,
            yticklabels=CLASS_LABELS,
            ax=ax,
        )
        ax.set_title(f"{row['family']} - {row['model']}")
        ax.set_xlabel("Predito")
        ax.set_ylabel("Real")

    for ax in axes[n_models:]:
        ax.axis("off")

    fig.tight_layout()
    return fig


def plot_best_model_top_critical_ingredients(by_ingredient: pd.DataFrame, top_n: int = 20) -> plt.Figure:
    plot_df = by_ingredient.head(top_n).copy()
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.barplot(
        data=plot_df,
        y="nome_ingrediente",
        x="dias_alerta_compra_preditos",
        color="#E45756",
        ax=ax,
    )
    ax.set_title("Ingredientes com mais dias em alerta de compra preditos")
    ax.set_xlabel("Dias em alerta de compra preditos")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


def run_comparison_notebook() -> dict[str, object]:
    ensure_artifact_dirs()
    _setup_mlflow_experiment("04_two_stage_model_comparison", "analysis")
    with mlflow.start_run(run_name="04_two_stage_model_comparison - analysis", nested=mlflow.active_run() is not None):
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality_comparison",
                "stage": "analysis",
                "notebook": "04_two_stage_model_comparison",
                "notebook_folder": _mlflow_notebook_folder("04_two_stage_model_comparison"),
                "notebook_path": _mlflow_notebook_path("04_two_stage_model_comparison"),
                "experiment_path": _mlflow_experiment_name("04_two_stage_model_comparison", "analysis"),
            }
        )
        models = load_all_models()
        criticality_rank = build_decision_table()
        operational_metrics, operational_recommendations, operational_by_ingredient = build_operational_recommendations(
            criticality_rank
        )
        figures = {}
        if not criticality_rank.empty:
            figures = {
                "criticality_distribution": plot_criticality_distribution(operational_metrics),
                "threshold_metric_bars": plot_threshold_metric_bars(criticality_rank),
                "classifier_metric_bars": plot_classifier_metric_bars(criticality_rank),
                "purchase_alert_roc_curves": plot_purchase_alert_roc_curves(criticality_rank),
                "purchase_alert_precision_recall_curves": plot_purchase_alert_precision_recall_curves(criticality_rank),
                "threshold_scatter": plot_threshold_scatter(operational_metrics, operational_recommendations),
                "confusion_matrices": plot_confusion_matrices(criticality_rank),
                "top_critical_ingredients": plot_best_model_top_critical_ingredients(operational_by_ingredient),
            }
            mlflow.log_text(criticality_rank.to_csv(index=False), "comparison/criticality_decision_table.csv")
            mlflow.log_text(criticality_rank.to_csv(index=False), "comparison/model_decision_table.csv")
            mlflow.log_text(
                operational_metrics.to_csv(index=False),
                "comparison/criticality_operational_metrics.csv",
            )
            mlflow.log_text(
                operational_recommendations.to_csv(index=False),
                "comparison/criticality_operational_recommendations.csv",
            )
            mlflow.log_text(
                operational_by_ingredient.to_csv(index=False),
                "comparison/criticality_operational_by_ingredient.csv",
            )
            for name, figure in figures.items():
                mlflow.log_figure(figure, f"plots/{name}.png")
    return {
        "models_loaded": len(models),
        "operational_metrics": operational_metrics,
        "operational_recommendations": operational_recommendations,
        "operational_by_ingredient": operational_by_ingredient,
        "decision_table": criticality_rank,
        "criticality_rank": criticality_rank,
        "figures": figures,
    }


def list_expected_artifacts() -> pd.DataFrame:
    metrics = load_all_metrics()
    if metrics.empty:
        return pd.DataFrame(columns=["model_uri", "registered_model_name", "run_id"])
    return metrics[["model_uri", "registered_model_name", "run_id"]].drop_duplicates().reset_index(drop=True)
