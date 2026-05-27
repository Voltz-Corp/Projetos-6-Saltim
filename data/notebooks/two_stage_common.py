from __future__ import annotations

import json
import math
import os
import re
import warnings
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-saltim")

import joblib
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATHS = [
    PROJECT_ROOT / "data" / "ml_dataset" / "outputs" / "abt_reposicao_part1.csv",
    PROJECT_ROOT / "data" / "ml_dataset" / "outputs" / "abt_reposicao_part2.csv",
]
ARTIFACT_DIR = PROJECT_ROOT / "ml" / "artifacts" / "two_stage"
METRICS_DIR = ARTIFACT_DIR / "metrics"
PLOTS_DIR = ARTIFACT_DIR / "plots"
SAMPLE_FRAC = 0.25
SAMPLE_RANDOM_STATE = 42

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
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


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


def load_abt_sample() -> pd.DataFrame:
    frames = [pd.read_csv(path, low_memory=False) for path in DATASET_PATHS]
    df = pd.concat(frames, ignore_index=True)
    df = df[df[SPLIT_COLUMN].isin([TRAIN_SPLIT, VALIDATION_SPLIT, TEST_SPLIT])]
    df = add_criticality_targets(df)
    df = df.sample(frac=SAMPLE_FRAC, random_state=SAMPLE_RANDOM_STATE)
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
    artifact_path: Path,
    prediction_path: Path,
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
        "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
        "prediction_path": str(prediction_path.relative_to(PROJECT_ROOT)),
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
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train = splits["y_threshold_train"]
    y_test = splits["y_threshold_test"]
    context_test = splits["context_test"]

    for model_name, model in models.items():
        model_slug = slugify(model_name)
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test)

        artifact_path = ARTIFACT_DIR / f"{notebook_id}_{model_slug}_threshold_model.pkl"
        prediction_path = METRICS_DIR / f"{notebook_id}_{model_slug}_threshold_predictions.csv"
        metrics_path = METRICS_DIR / f"{notebook_id}_{model_slug}_threshold_metrics.csv"

        predictions = _threshold_prediction_frame(notebook_id, family, model_name, context_test, y_test, y_pred)
        metrics = _criticality_metric_row(
            notebook_id,
            family,
            "threshold_regression",
            model_name,
            artifact_path,
            prediction_path,
            predictions,
            fit_warnings,
        )
        rows.append(metrics)

        predictions.to_csv(prediction_path, index=False)
        pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
        joblib.dump(pipeline, artifact_path)

    return pd.DataFrame(rows)


def train_purchase_alert_classifiers(
    notebook_id: str,
    family: str,
    models: dict[str, object],
    splits: dict[str, object],
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train = splits["y_purchase_alert_train"]
    context_test = splits["context_test"]

    for model_name, model in models.items():
        model_slug = slugify(model_name)
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test).astype(int)
        y_proba = _prediction_probability(pipeline, X_test)

        artifact_path = ARTIFACT_DIR / f"{notebook_id}_{model_slug}_purchase_alert_classifier.pkl"
        prediction_path = METRICS_DIR / f"{notebook_id}_{model_slug}_purchase_alert_predictions.csv"
        metrics_path = METRICS_DIR / f"{notebook_id}_{model_slug}_purchase_alert_metrics.csv"

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
            artifact_path,
            prediction_path,
            predictions,
            fit_warnings,
        )
        rows.append(metrics)

        predictions.to_csv(prediction_path, index=False)
        pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
        joblib.dump(pipeline, artifact_path)

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
    threshold_metrics = train_threshold_models(notebook_id, family, threshold_models, splits)
    purchase_alert_metrics = train_purchase_alert_classifiers(notebook_id, family, purchase_alert_models, splits)
    criticality_metrics = pd.concat([threshold_metrics, purchase_alert_metrics], ignore_index=True)

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
    with open(METRICS_DIR / f"{notebook_id}_run_summary.json", "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2, ensure_ascii=False)

    return {
        "threshold_metrics": threshold_metrics,
        "purchase_alert_metrics": purchase_alert_metrics,
        "criticality_metrics": criticality_metrics,
        "summary": pd.DataFrame([summary]),
    }


def _read_metric_files(pattern: str) -> pd.DataFrame:
    files = sorted(METRICS_DIR.glob(pattern))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)


def _add_analysis_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = metrics.copy()
    for column in ["balanced_accuracy", "roc_auc", "average_precision"]:
        if column not in metrics.columns:
            metrics[column] = np.nan

    for index, row in metrics.iterrows():
        prediction_path = row.get("prediction_path")
        if not isinstance(prediction_path, str) or not prediction_path:
            continue
        path = PROJECT_ROOT / prediction_path
        if not path.exists():
            continue

        predictions = pd.read_csv(path)
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
    threshold = _read_metric_files("*_threshold_metrics.csv")
    purchase_alert = _read_metric_files("*_purchase_alert_metrics.csv")
    return _add_analysis_metrics(pd.concat([threshold, purchase_alert], ignore_index=True))


def load_all_models() -> dict[str, object]:
    models = {}
    artifact_patterns = ["*_threshold_model.pkl", "*_purchase_alert_classifier.pkl"]
    for pattern in artifact_patterns:
        for path in sorted(ARTIFACT_DIR.glob(pattern)):
            models[path.name] = joblib.load(path)
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
    rank.to_csv(METRICS_DIR / "criticality_decision_table.csv", index=False)
    rank.to_csv(METRICS_DIR / "model_decision_table.csv", index=False)
    return rank


def _load_predictions(metric_row: pd.Series) -> pd.DataFrame:
    return pd.read_csv(PROJECT_ROOT / metric_row["prediction_path"])


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
    model = joblib.load(PROJECT_ROOT / str(metric_row["artifact_path"]))
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

    all_recommendations.to_csv(METRICS_DIR / "criticality_operational_recommendations.csv", index=False)
    metrics.to_csv(METRICS_DIR / "criticality_operational_metrics.csv", index=False)
    by_ingredient.to_csv(METRICS_DIR / "criticality_operational_by_ingredient.csv", index=False)
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
    fig.savefig(PLOTS_DIR / "criticality_distribution_by_model.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "criticality_metric_bars.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "purchase_alert_classifier_metric_bars.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "purchase_alert_roc_curves.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "purchase_alert_precision_recall_curves.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "criticality_threshold_scatter.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "criticality_confusion_matrices.png", dpi=160, bbox_inches="tight")
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
    fig.savefig(PLOTS_DIR / "criticality_top_critical_ingredients.png", dpi=160, bbox_inches="tight")
    return fig


def run_comparison_notebook() -> dict[str, object]:
    ensure_artifact_dirs()
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
    rows = []
    artifact_patterns = ["*_threshold_model.pkl", "*_purchase_alert_classifier.pkl"]
    for pattern in artifact_patterns:
        for path in sorted(ARTIFACT_DIR.glob(pattern)):
            rows.append({"artifact": path.name, "size_mb": path.stat().st_size / 1024 / 1024})
    return pd.DataFrame(rows)
