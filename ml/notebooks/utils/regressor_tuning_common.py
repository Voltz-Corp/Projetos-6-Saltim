from __future__ import annotations

import json
import math
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

from two_stage_common import (
    CLASS_LABELS,
    PURCHASE_ALERT_LABEL,
    TARGET_ALERT_THRESHOLD,
    TARGET_CRITICAL_THRESHOLD,
    TARGET_CRITICALITY,
    TEST_SPLIT,
    TRAIN_SPLIT,
    VALIDATION_SPLIT,
    SPLIT_COLUMN,
    _criticality_metric_row,
    _mlflow_experiment_name,
    _mlflow_notebook_folder,
    _mlflow_notebook_path,
    _mlflow_registered_model_name,
    _mlflow_tracking_uri,
    _safe_mlflow_param_value,
    _setup_mlflow_experiment,
    _threshold_prediction_frame,
    load_abt_full,
    load_abt_sample,
    mlflow,
    pipeline_for,
    select_feature_columns,
    slugify,
)

SCORING = {
    "neg_rmse": "neg_root_mean_squared_error",
    "neg_mae": "neg_mean_absolute_error",
    "r2": "r2",
}

WEIGHT_PROFILE_DESCRIPTIONS = {
    "uniform": "Peso 1 para todas as amostras; usado como controle.",
    "alert_focus": "Aumenta peso de observacoes em Alerta de compra e baixa cobertura.",
    "critical_gap_focus": "Aumenta peso quando cobertura esta abaixo/proxima do limiar critico.",
    "threshold_extreme_focus": "Aumenta peso de limiares de alerta mais distantes da mediana.",
}

FINAL_MODEL_NOTEBOOK_IDS = (
    "05_random_forest_regressor_threshold_tuning",
    "06_xgboost_regressor_threshold_tuning",
)


@dataclass(frozen=True)
class RegressorTuningConfig:
    notebook_id: str
    family: str
    model_name: str
    model_factory: Callable[[], object]
    baseline_factory: Callable[[], object]
    param_distributions: Mapping[str, list[Any]]
    n_iter: int
    cv_splits: int = 4
    random_state: int = 42
    n_jobs: int = -1
    sample_frac: float = 0.25
    use_full_dataset: bool = False
    weight_profiles: tuple[str, ...] = (
        "uniform",
        "alert_focus",
        "critical_gap_focus",
        "threshold_extreme_focus",
    )
    learning_curve_train_sizes: tuple[float, ...] = (0.35, 0.55, 0.75, 1.0)


def prepare_threshold_regression_data(
    sample_frac: float = 0.25,
    use_full_dataset: bool = False,
) -> dict[str, object]:
    df = (
        load_abt_full()
        if use_full_dataset
        else load_abt_sample(sample_frac=sample_frac)
    )

    # Compatibilidade: Cast de colunas StringDtype para object para evitar BrokenProcessPool
    # no joblib durante o processamento paralelo (comum em Python 3.13 + Pandas 2.2+).
    # O Index de colunas também deve ser convertido se for do tipo 'string'.
    for col in df.select_dtypes(include=["string"]).columns:
        df[col] = df[col].astype(object)
    
    if hasattr(df.columns, "dtype") and df.columns.dtype == "string" or str(df.columns.dtype) == "str":
        df.columns = df.columns.astype(object)
    if hasattr(df.index, "dtype") and df.index.dtype == "string" or str(df.index.dtype) == "str":
        df.index = df.index.astype(object)

    df["date"] = pd.to_datetime(df["date"])
    feature_columns = select_feature_columns(df)
    search_mask = df[SPLIT_COLUMN].isin([TRAIN_SPLIT, VALIDATION_SPLIT])
    search_frame = (
        df.loc[search_mask]
        .sort_values(["date", "ingredient_id"])
        .reset_index(drop=True)
    )
    test_frame = (
        df.loc[df[SPLIT_COLUMN].eq(TEST_SPLIT)]
        .sort_values(["date", "ingredient_id"])
        .reset_index(drop=True)
    )

    return {
        "df": df,
        "feature_columns": feature_columns,
        "search_frame": search_frame,
        "test_frame": test_frame,
        "X_search": search_frame[feature_columns].copy(),
        "y_search": search_frame[TARGET_ALERT_THRESHOLD].astype(float).copy(),
        "X_test": test_frame[feature_columns].copy(),
        "y_test": test_frame[TARGET_ALERT_THRESHOLD].astype(float).copy(),
        "context_test": test_frame[
            [
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
        ].copy(),
        "split_counts": df[SPLIT_COLUMN].value_counts().to_dict(),
        "criticality_rates": df[TARGET_CRITICALITY]
        .value_counts(normalize=True)
        .reindex(CLASS_LABELS, fill_value=0.0)
        .to_dict(),
        "sample_shape": df.shape,
    }


def sample_weights(frame: pd.DataFrame, y: pd.Series, profile: str) -> np.ndarray:
    coverage = frame["cobertura_estoque_pct"].astype(float).to_numpy()
    critical_threshold = frame[TARGET_CRITICAL_THRESHOLD].astype(float).to_numpy()
    alert_flag = frame[TARGET_CRITICALITY].eq(PURCHASE_ALERT_LABEL).to_numpy()
    y_values = y.astype(float).to_numpy()
    weights = np.ones(len(frame), dtype=float)

    if profile == "uniform":
        return weights
    if profile == "alert_focus":
        weights += np.where(alert_flag, 2.5, 0.0)
        weights += np.where(coverage <= 0.35, 1.0, 0.0)
    elif profile == "critical_gap_focus":
        gap_pressure = np.maximum(critical_threshold - coverage, 0.0)
        weights += np.where(alert_flag, 2.0, 0.0)
        weights += np.clip(gap_pressure * 12.0, 0.0, 4.0)
    elif profile == "threshold_extreme_focus":
        median = float(np.median(y_values))
        mad = float(np.median(np.abs(y_values - median))) or 1.0
        weights += np.clip(np.abs(y_values - median) / mad, 0.0, 5.0)
    else:
        raise ValueError(f"Perfil de peso desconhecido: {profile}")

    return np.clip(weights, 1.0, 8.0)


def _rmse(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _regression_metrics(
    prefix: str, y_true: pd.Series | np.ndarray, y_pred: np.ndarray
) -> dict[str, float]:
    return {
        f"{prefix}_rmse": _rmse(y_true, y_pred),
        f"{prefix}_mae": float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}_r2": float(r2_score(y_true, y_pred)),
    }


def _fit_pipeline(
    pipeline, X: pd.DataFrame, y: pd.Series, weights: np.ndarray | None = None
) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if weights is None:
            pipeline.fit(X, y)
        else:
            pipeline.fit(X, y, model__sample_weight=weights)
    return [f"{item.category.__name__}: {item.message}" for item in caught]


def cross_validate_estimator(
    estimator,
    data: Mapping[str, object],
    cv_splits: int,
    weight_profile: str,
) -> pd.DataFrame:
    X = data["X_search"]
    y = data["y_search"]
    frame = data["search_frame"]
    pipeline_template = pipeline_for(estimator, X)
    rows = []
    cv = TimeSeriesSplit(n_splits=cv_splits)

    for fold, (train_idx, validation_idx) in enumerate(cv.split(X), start=1):
        pipeline = clone(pipeline_template)
        train_weights = sample_weights(
            frame.iloc[train_idx], y.iloc[train_idx], weight_profile
        )
        warnings_list = _fit_pipeline(
            pipeline, X.iloc[train_idx], y.iloc[train_idx], train_weights
        )
        y_train_pred = pipeline.predict(X.iloc[train_idx])
        y_validation_pred = pipeline.predict(X.iloc[validation_idx])
        rows.append(
            {
                "fold": fold,
                "weight_profile": weight_profile,
                "train_size": len(train_idx),
                "validation_size": len(validation_idx),
                "warnings": " | ".join(warnings_list),
                **_regression_metrics("train", y.iloc[train_idx], y_train_pred),
                **_regression_metrics(
                    "validation", y.iloc[validation_idx], y_validation_pred
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_cv_metrics(
    fold_metrics: pd.DataFrame, prefix: str = "cv"
) -> dict[str, float]:
    return {
        f"{prefix}_train_rmse_mean": float(fold_metrics["train_rmse"].mean()),
        f"{prefix}_train_rmse_std": float(fold_metrics["train_rmse"].std(ddof=0)),
        f"{prefix}_validation_rmse_mean": float(fold_metrics["validation_rmse"].mean()),
        f"{prefix}_validation_rmse_std": float(
            fold_metrics["validation_rmse"].std(ddof=0)
        ),
        f"{prefix}_validation_rmse_var": float(
            fold_metrics["validation_rmse"].var(ddof=0)
        ),
        f"{prefix}_validation_mae_mean": float(fold_metrics["validation_mae"].mean()),
        f"{prefix}_validation_r2_mean": float(fold_metrics["validation_r2"].mean()),
    }


def _tidy_cv_results(search: RandomizedSearchCV, weight_profile: str) -> pd.DataFrame:
    rows = []
    cv_results = pd.DataFrame(search.cv_results_)
    for index, row in cv_results.iterrows():
        params = row["params"]
        item = {
            "candidate_index": int(index),
            "weight_profile": weight_profile,
            "params_json": json.dumps(params, sort_keys=True, default=str),
            "mean_train_rmse": -float(row["mean_train_neg_rmse"]),
            "std_train_rmse": float(row["std_train_neg_rmse"]),
            "mean_validation_rmse": -float(row["mean_test_neg_rmse"]),
            "std_validation_rmse": float(row["std_test_neg_rmse"]),
            "mean_train_mae": -float(row["mean_train_neg_mae"]),
            "mean_validation_mae": -float(row["mean_test_neg_mae"]),
            "mean_train_r2": float(row["mean_train_r2"]),
            "mean_validation_r2": float(row["mean_test_r2"]),
            "rank_validation_rmse": int(row["rank_test_neg_rmse"]),
        }
        for key, value in params.items():
            item[key.replace("model__", "")] = value
        rows.append(item)
    return pd.DataFrame(rows).sort_values("rank_validation_rmse").reset_index(drop=True)


def _best_fold_metrics_from_search(
    search: RandomizedSearchCV, weight_profile: str
) -> pd.DataFrame:
    row = pd.DataFrame(search.cv_results_).iloc[search.best_index_]
    rows = []
    for fold in range(search.cv.n_splits):
        rows.append(
            {
                "fold": fold + 1,
                "weight_profile": weight_profile,
                "train_rmse": -float(row[f"split{fold}_train_neg_rmse"]),
                "validation_rmse": -float(row[f"split{fold}_test_neg_rmse"]),
                "train_mae": -float(row[f"split{fold}_train_neg_mae"]),
                "validation_mae": -float(row[f"split{fold}_test_neg_mae"]),
                "train_r2": float(row[f"split{fold}_train_r2"]),
                "validation_r2": float(row[f"split{fold}_test_r2"]),
            }
        )
    return pd.DataFrame(rows)


def _log_candidate_runs(config: RegressorTuningConfig, cv_table: pd.DataFrame) -> None:
    for _, row in cv_table.iterrows():
        mlflow.autolog()
        with mlflow.start_run(
            run_name=f"{config.model_name} candidate {row['weight_profile']} #{row['candidate_index']}",
            nested=True,
        ):
            mlflow.set_tags(
                {
                    "project": "saltim",
                    "problem": "stock_criticality",
                    "stage": "threshold_regression_tuning_candidate",
                    "notebook": config.notebook_id,
                    "notebook_folder": _mlflow_notebook_folder(config.notebook_id),
                    "notebook_path": _mlflow_notebook_path(config.notebook_id),
                    "experiment_path": _mlflow_experiment_name(
                        config.notebook_id, "threshold_regression"
                    ),
                    "model": config.model_name,
                    "weight_profile": row["weight_profile"],
                }
            )
            mlflow.log_param("candidate_index", int(row["candidate_index"]))
            mlflow.log_param("weight_profile", row["weight_profile"])
            for key, value in json.loads(row["params_json"]).items():
                mlflow.log_param(
                    key.replace("model__", ""), _safe_mlflow_param_value(value)
                )
            mlflow.log_metrics(
                {
                    "mean_validation_rmse": float(row["mean_validation_rmse"]),
                    "std_validation_rmse": float(row["std_validation_rmse"]),
                    "mean_validation_mae": float(row["mean_validation_mae"]),
                    "mean_validation_r2": float(row["mean_validation_r2"]),
                    "mean_train_rmse": float(row["mean_train_rmse"]),
                    "mean_train_r2": float(row["mean_train_r2"]),
                }
            )


def random_search_for_weight_profile(
    config: RegressorTuningConfig,
    data: Mapping[str, object],
    weight_profile: str,
) -> dict[str, object]:
    X = data["X_search"]
    y = data["y_search"]
    frame = data["search_frame"]
    pipeline = pipeline_for(config.model_factory(), X)
    weights = sample_weights(frame, y, weight_profile)
    cv = TimeSeriesSplit(n_splits=config.cv_splits)
    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=dict(config.param_distributions),
        n_iter=config.n_iter,
        scoring=SCORING,
        refit="neg_rmse",
        cv=cv,
        random_state=config.random_state,
        n_jobs=config.n_jobs,
        return_train_score=True,
        verbose=1,
    )

    mlflow.autolog()
    with mlflow.start_run(
        run_name=f"{config.model_name} random search - {weight_profile}", nested=True
    ):
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality",
                "stage": "threshold_regression_random_search",
                "notebook": config.notebook_id,
                "notebook_folder": _mlflow_notebook_folder(config.notebook_id),
                "notebook_path": _mlflow_notebook_path(config.notebook_id),
                "experiment_path": _mlflow_experiment_name(
                    config.notebook_id, "threshold_regression"
                ),
                "model": config.model_name,
                "weight_profile": weight_profile,
            }
        )
        mlflow.log_param("search_method", "RandomizedSearchCV")
        mlflow.log_param("cv_strategy", "TimeSeriesSplit")
        mlflow.log_param("cv_splits", config.cv_splits)
        mlflow.log_param("n_iter", config.n_iter)
        mlflow.log_param("weight_profile", weight_profile)
        mlflow.log_dict(dict(config.param_distributions), "tuning/search_space.json")

        search.fit(X, y, model__sample_weight=weights)
        cv_table = _tidy_cv_results(search, weight_profile)
        best_fold_metrics = _best_fold_metrics_from_search(search, weight_profile)
        fold_summary = summarize_cv_metrics(best_fold_metrics, prefix="best_cv")

        mlflow.log_text(cv_table.to_csv(index=False), "tuning/cv_results.csv")
        mlflow.log_text(
            best_fold_metrics.to_csv(index=False),
            "tuning/best_candidate_fold_metrics.csv",
        )
        mlflow.log_params(
            {
                key.replace("model__", ""): _safe_mlflow_param_value(value)
                for key, value in search.best_params_.items()
            }
        )
        mlflow.log_metrics(
            {
                "best_mean_validation_rmse": -float(search.best_score_),
                **{key: float(value) for key, value in fold_summary.items()},
            }
        )
        _log_candidate_runs(config, cv_table)

    return {
        "weight_profile": weight_profile,
        "search": search,
        "cv_table": cv_table,
        "best_fold_metrics": best_fold_metrics,
        "fold_summary": fold_summary,
        "best_params": search.best_params_,
        "best_cv_rmse": -float(search.best_score_),
    }


def evaluate_baseline(
    config: RegressorTuningConfig, data: Mapping[str, object]
) -> dict[str, object]:
    fold_metrics = cross_validate_estimator(
        config.baseline_factory(),
        data,
        cv_splits=config.cv_splits,
        weight_profile="uniform",
    )
    summary = summarize_cv_metrics(fold_metrics, prefix="baseline_cv")
    pipeline = pipeline_for(config.baseline_factory(), data["X_search"])
    _fit_pipeline(pipeline, data["X_search"], data["y_search"], None)
    y_test_pred = pipeline.predict(data["X_test"])
    test_metrics = _regression_metrics("baseline_test", data["y_test"], y_test_pred)

    mlflow.autolog()
    with mlflow.start_run(run_name=f"{config.model_name} baseline", nested=True):
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality",
                "stage": "threshold_regression_baseline",
                "notebook": config.notebook_id,
                "notebook_folder": _mlflow_notebook_folder(config.notebook_id),
                "notebook_path": _mlflow_notebook_path(config.notebook_id),
                "experiment_path": _mlflow_experiment_name(
                    config.notebook_id, "threshold_regression"
                ),
                "model": config.model_name,
            }
        )
        mlflow.log_param("cv_strategy", "TimeSeriesSplit")
        mlflow.log_param("weight_profile", "uniform")
        mlflow.log_metrics({**summary, **test_metrics})
        mlflow.log_text(fold_metrics.to_csv(index=False), "baseline/fold_metrics.csv")

    return {
        "fold_metrics": fold_metrics,
        "summary": summary,
        "test_metrics": test_metrics,
    }


def diagnose_fit(
    final_metrics: Mapping[str, float],
    best_cv_summary: Mapping[str, float],
    baseline_summary: Mapping[str, float],
) -> dict[str, object]:
    train_rmse = float(final_metrics["train_rmse"])
    validation_rmse = float(best_cv_summary["best_cv_validation_rmse_mean"])
    validation_std = float(best_cv_summary["best_cv_validation_rmse_std"])
    baseline_validation_rmse = float(
        baseline_summary["baseline_cv_validation_rmse_mean"]
    )
    gap = validation_rmse - train_rmse
    gap_ratio = gap / max(train_rmse, 1e-9)

    if gap_ratio > 0.30 and gap > 0.015:
        label = "overfitting"
        explanation = (
            "RMSE de validacao ficou muito acima do RMSE de treino nas dobras."
        )
    elif (
        validation_rmse >= baseline_validation_rmse * 0.98
        and train_rmse >= baseline_validation_rmse * 0.90
    ):
        label = "underfitting"
        explanation = (
            "O tuning nao melhorou o baseline e o erro de treino permanece alto."
        )
    elif validation_std > validation_rmse * 0.20:
        label = "unstable"
        explanation = "A media e boa, mas a variancia entre dobras e alta."
    else:
        label = "adequate"
        explanation = (
            "Nao ha sinal forte de sobreajuste/subajuste nos criterios adotados."
        )

    return {
        "fit_status": label,
        "fit_explanation": explanation,
        "train_validation_rmse_gap": float(gap),
        "train_validation_rmse_gap_ratio": float(gap_ratio),
        "validation_rmse_std": validation_std,
    }


def build_residual_plot(predictions: pd.DataFrame) -> plt.Figure:
    residuals = (
        predictions["limiar_alerta_real_pct"] - predictions["limiar_alerta_predito_pct"]
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.scatterplot(
        x=predictions["limiar_alerta_predito_pct"],
        y=residuals,
        hue=predictions["criticidade_real"],
        hue_order=CLASS_LABELS,
        alpha=0.45,
        ax=axes[0],
    )
    axes[0].axhline(0.0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Residuos por previsao")
    axes[0].set_xlabel("Limiar de alerta predito")
    axes[0].set_ylabel("Residual")
    sns.histplot(residuals, bins=30, kde=True, ax=axes[1], color="#4C78A8")
    axes[1].set_title("Distribuicao dos residuos")
    axes[1].set_xlabel("Residual")
    fig.tight_layout()
    return fig


def learning_curve_frame(
    final_pipeline,
    data: Mapping[str, object],
    weight_profile: str,
    train_sizes: tuple[float, ...],
    cv_splits: int,
) -> pd.DataFrame:
    X = data["X_search"]
    y = data["y_search"]
    frame = data["search_frame"]
    rows = []
    cv = TimeSeriesSplit(n_splits=cv_splits)

    for fold, (train_idx, validation_idx) in enumerate(cv.split(X), start=1):
        for fraction in train_sizes:
            size = max(25, int(len(train_idx) * fraction))
            size = min(size, len(train_idx))
            selected_train_idx = train_idx[:size]
            pipeline = clone(final_pipeline)
            weights = sample_weights(
                frame.iloc[selected_train_idx],
                y.iloc[selected_train_idx],
                weight_profile,
            )
            _fit_pipeline(
                pipeline,
                X.iloc[selected_train_idx],
                y.iloc[selected_train_idx],
                weights,
            )
            train_pred = pipeline.predict(X.iloc[selected_train_idx])
            validation_pred = pipeline.predict(X.iloc[validation_idx])
            rows.append(
                {
                    "fold": fold,
                    "train_fraction": fraction,
                    "train_size": size,
                    "train_rmse": _rmse(y.iloc[selected_train_idx], train_pred),
                    "validation_rmse": _rmse(y.iloc[validation_idx], validation_pred),
                }
            )
    return pd.DataFrame(rows)


def build_learning_curve_plot(learning_curve: pd.DataFrame) -> plt.Figure:
    plot_df = (
        learning_curve.groupby("train_size", as_index=False)
        .agg(
            train_rmse_mean=("train_rmse", "mean"),
            train_rmse_std=("train_rmse", "std"),
            validation_rmse_mean=("validation_rmse", "mean"),
            validation_rmse_std=("validation_rmse", "std"),
        )
        .fillna(0.0)
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        plot_df["train_size"], plot_df["train_rmse_mean"], marker="o", label="Treino"
    )
    ax.fill_between(
        plot_df["train_size"],
        plot_df["train_rmse_mean"] - plot_df["train_rmse_std"],
        plot_df["train_rmse_mean"] + plot_df["train_rmse_std"],
        alpha=0.15,
    )
    ax.plot(
        plot_df["train_size"],
        plot_df["validation_rmse_mean"],
        marker="o",
        label="Validacao",
    )
    ax.fill_between(
        plot_df["train_size"],
        plot_df["validation_rmse_mean"] - plot_df["validation_rmse_std"],
        plot_df["validation_rmse_mean"] + plot_df["validation_rmse_std"],
        alpha=0.15,
    )
    ax.set_title("Curva de aprendizado")
    ax.set_xlabel("Tamanho do treino")
    ax.set_ylabel("RMSE")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return fig


def _log_final_model_run(
    config: RegressorTuningConfig,
    final_pipeline,
    metrics: dict[str, object],
    predictions: pd.DataFrame,
    summary: dict[str, object],
    residual_figure: plt.Figure,
    learning_curve: pd.DataFrame,
    learning_figure: plt.Figure,
) -> dict[str, str]:
    metric_row = {
        key: value
        for key, value in metrics.items()
        if not isinstance(value, (dict, list, tuple))
    }
    metric_artifact_path = f"evaluation/{config.notebook_id}_{slugify(config.model_name)}_threshold_regression_metrics.csv"
    prediction_artifact_path = f"evaluation/{config.notebook_id}_{slugify(config.model_name)}_threshold_regression_predictions.csv"
    summary_artifact_path = f"evaluation/{config.notebook_id}_tuning_summary.json"
    registered_model_name = _mlflow_registered_model_name(
        {
            "notebook": config.notebook_id,
            "stage": "threshold_regression",
            "model": config.model_name,
        }
    )

    mlflow.autolog()
    with mlflow.start_run(run_name=f"{config.model_name} champion", nested=True) as run:
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality",
                "stage": "threshold_regression",
                "family": config.family,
                "notebook": config.notebook_id,
                "notebook_folder": _mlflow_notebook_folder(config.notebook_id),
                "notebook_path": _mlflow_notebook_path(config.notebook_id),
                "experiment_path": _mlflow_experiment_name(
                    config.notebook_id, "threshold_regression"
                ),
                "model": config.model_name,
                "registered_model_name": registered_model_name,
                "metric_artifact_path": metric_artifact_path,
                "prediction_artifact_path": prediction_artifact_path,
                "summary_artifact_path": summary_artifact_path,
            }
        )
        mlflow.log_params(
            {
                "notebook": config.notebook_id,
                "family": config.family,
                "stage": "threshold_regression",
                "model": config.model_name,
                "registered_model_name": registered_model_name,
                "run_source": "random_search_tuning",
                "dataset_mode": summary.get("dataset_mode", ""),
                "sample_frac": summary.get("sample_frac", ""),
                "metric_artifact_path": metric_artifact_path,
                "prediction_artifact_path": prediction_artifact_path,
                "summary_artifact_path": summary_artifact_path,
                **{
                    key: _safe_mlflow_param_value(value)
                    for key, value in summary.get("best_params", {}).items()
                },
            }
        )
        numeric_metrics = {
            key: float(value)
            for key, value in metric_row.items()
            if isinstance(value, (int, float, np.integer, np.floating))
            and not pd.isna(value)
        }
        mlflow.log_metrics(numeric_metrics)
        mlflow.log_text(
            pd.DataFrame([metric_row]).to_csv(index=False), metric_artifact_path
        )
        mlflow.log_text(predictions.to_csv(index=False), prediction_artifact_path)
        mlflow.log_dict(summary, summary_artifact_path)
        mlflow.log_text(
            learning_curve.to_csv(index=False), "diagnostics/learning_curve.csv"
        )
        mlflow.log_figure(residual_figure, "diagnostics/residual_analysis.png")
        mlflow.log_figure(learning_figure, "diagnostics/learning_curve.png")
        mlflow.sklearn.log_model(
            final_pipeline,
            name="model",
            registered_model_name=registered_model_name,
            await_registration_for=120,
        )
        return {
            "run_id": run.info.run_id,
            "model_uri": f"runs:/{run.info.run_id}/model",
            "registered_model_name": registered_model_name,
            "metric_artifact_path": metric_artifact_path,
            "prediction_artifact_path": prediction_artifact_path,
            "summary_artifact_path": summary_artifact_path,
        }


def _artifact_size_bytes(model_uri: str) -> int | None:
    try:
        local_path = mlflow.artifacts.download_artifacts(model_uri)
    except Exception:
        return None

    root = Path(local_path)
    if root.is_file():
        return root.stat().st_size

    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _final_model_experiments() -> list[object]:
    if mlflow is None:
        raise RuntimeError("MLflow nao esta instalado no ambiente do notebook.")

    mlflow.set_tracking_uri(_mlflow_tracking_uri())
    client = mlflow.tracking.MlflowClient()
    experiments = client.search_experiments()
    return [
        experiment
        for experiment in experiments
        if experiment.name.startswith("notebooks/02_modelos_finais/")
        and experiment.name.endswith("/threshold_regression")
    ]


def _latest_final_champion_run(client: object, experiment_id: str) -> object | None:
    runs = client.search_runs(
        [experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=1000,
    )
    for run in runs:
        if (
            run.data.tags.get("stage") == "threshold_regression"
            and run.data.tags.get("notebook") in FINAL_MODEL_NOTEBOOK_IDS
            and run.data.params.get("registered_model_name")
        ):
            return run
    return None


def compare_final_model_runs() -> pd.DataFrame:
    if mlflow is None:
        raise RuntimeError("MLflow nao esta instalado no ambiente do notebook.")

    mlflow.set_tracking_uri(_mlflow_tracking_uri())
    client = mlflow.tracking.MlflowClient()
    rows: list[dict[str, object]] = []

    for experiment in _final_model_experiments():
        run = _latest_final_champion_run(client, experiment.experiment_id)
        if run is None:
            continue

        params = run.data.params
        metrics = run.data.metrics
        tags = run.data.tags
        model_uri = f"runs:/{run.info.run_id}/model"
        size_bytes = _artifact_size_bytes(model_uri)
        rows.append(
            {
                "notebook": params.get("notebook", tags.get("notebook", "")),
                "experiment": experiment.name,
                "run_id": run.info.run_id,
                "model": params.get("model", ""),
                "registered_model_name": params.get("registered_model_name", ""),
                "dataset_mode": params.get("dataset_mode", ""),
                "sample_frac": params.get("sample_frac", ""),
                "test_rmse": metrics.get("test_rmse", metrics.get("rmse")),
                "test_mae": metrics.get("test_mae", metrics.get("mae")),
                "test_r2": metrics.get("test_r2", metrics.get("r2")),
                "best_cv_rmse": metrics.get("best_cv_rmse"),
                "baseline_test_rmse": metrics.get("baseline_test_rmse"),
                "test_rmse_gain_vs_baseline": metrics.get("test_rmse_gain_vs_baseline"),
                "model_size_bytes": size_bytes,
                "model_size_mb": (
                    None if size_bytes is None else size_bytes / (1024 * 1024)
                ),
                "model_uri": model_uri,
            }
        )

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values(["test_rmse", "model_size_bytes"], ascending=[True, True])
        .reset_index(drop=True)
    )


def plot_final_model_comparison(comparison: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    if comparison.empty:
        axes[0].text(
            0.5, 0.5, "Nenhum run champion encontrado", ha="center", va="center"
        )
        axes[1].axis("off")
        return fig

    plot_df = comparison.copy()
    sns.barplot(data=plot_df, y="model", x="test_rmse", color="#4C78A8", ax=axes[0])
    axes[0].set_title("Erro no teste")
    axes[0].set_xlabel("RMSE")
    axes[0].set_ylabel("")
    axes[0].grid(axis="x", alpha=0.25)

    sns.barplot(data=plot_df, y="model", x="model_size_mb", color="#F58518", ax=axes[1])
    axes[1].set_title("Tamanho do modelo")
    axes[1].set_xlabel("MB")
    axes[1].set_ylabel("")
    axes[1].grid(axis="x", alpha=0.25)

    fig.tight_layout()
    return fig


def log_final_model_comparison(
    comparison: pd.DataFrame, figure: plt.Figure | None = None
) -> dict[str, str]:
    if mlflow is None:
        raise RuntimeError("MLflow nao esta instalado no ambiente do notebook.")

    _setup_mlflow_experiment("07_modelos_finais_comparison", "analysis")
    mlflow.autolog()
    with mlflow.start_run(
        run_name="07_modelos_finais_comparison - analysis",
        nested=mlflow.active_run() is not None,
    ) as run:
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality_final_model_comparison",
                "stage": "analysis",
                "notebook": "07_modelos_finais_comparison",
                "notebook_folder": _mlflow_notebook_folder(
                    "07_modelos_finais_comparison"
                ),
                "notebook_path": _mlflow_notebook_path("07_modelos_finais_comparison"),
                "experiment_path": _mlflow_experiment_name(
                    "07_modelos_finais_comparison", "analysis"
                ),
            }
        )
        mlflow.log_text(
            comparison.to_csv(index=False), "comparison/final_model_comparison.csv"
        )
        if not comparison.empty:
            mlflow.log_metric("best_test_rmse", float(comparison["test_rmse"].min()))
            if comparison["model_size_mb"].notna().any():
                mlflow.log_metric(
                    "smallest_model_size_mb", float(comparison["model_size_mb"].min())
                )
        if figure is not None:
            mlflow.log_figure(figure, "comparison/final_model_comparison.png")

        return {
            "run_id": run.info.run_id,
            "comparison_artifact_path": "comparison/final_model_comparison.csv",
        }


def run_regressor_tuning(config: RegressorTuningConfig) -> dict[str, object]:
    if mlflow is None:
        raise RuntimeError("MLflow nao esta instalado no ambiente do notebook.")

    _setup_mlflow_experiment(config.notebook_id, "threshold_regression")
    data = prepare_threshold_regression_data(
        sample_frac=config.sample_frac,
        use_full_dataset=config.use_full_dataset,
    )
    all_candidate_tables = []
    search_outputs = []
    mlflow.autolog()
    with mlflow.start_run(
        run_name=f"{config.model_name} tuning parent",
        nested=mlflow.active_run() is not None,
    ):
        mlflow.set_tags(
            {
                "project": "saltim",
                "problem": "stock_criticality",
                "stage": "threshold_regression_tuning",
                "notebook": config.notebook_id,
                "notebook_folder": _mlflow_notebook_folder(config.notebook_id),
                "notebook_path": _mlflow_notebook_path(config.notebook_id),
                "experiment_path": _mlflow_experiment_name(
                    config.notebook_id, "threshold_regression"
                ),
                "model": config.model_name,
            }
        )
        mlflow.log_params(
            {
                "validation_strategy": "TimeSeriesSplit",
                "cv_splits": config.cv_splits,
                "search_method": "RandomizedSearchCV",
                "n_iter_per_weight_profile": config.n_iter,
                "dataset_mode": "full" if config.use_full_dataset else "sample",
                "sample_frac": 1.0 if config.use_full_dataset else config.sample_frac,
                "weight_profiles": ",".join(config.weight_profiles),
                "feature_count": len(data["feature_columns"]),
            }
        )
        mlflow.log_dict(dict(config.param_distributions), "tuning/search_space.json")
        mlflow.log_dict(
            {
                "sample_shape": list(data["sample_shape"]),
                "split_counts": data["split_counts"],
                "criticality_rates": data["criticality_rates"],
                "weight_profile_descriptions": WEIGHT_PROFILE_DESCRIPTIONS,
            },
            "tuning/data_and_weight_summary.json",
        )

        baseline = evaluate_baseline(config, data)
        for profile in config.weight_profiles:
            output = random_search_for_weight_profile(config, data, profile)
            search_outputs.append(output)
            all_candidate_tables.append(output["cv_table"])

        candidate_results = pd.concat(
            all_candidate_tables, ignore_index=True
        ).sort_values(
            ["mean_validation_rmse", "std_validation_rmse"],
            ascending=[True, True],
        )
        champion_output = min(search_outputs, key=lambda item: item["best_cv_rmse"])
        best_params = champion_output["best_params"]
        best_weight_profile = champion_output["weight_profile"]

        final_pipeline = pipeline_for(config.model_factory(), data["X_search"])
        final_pipeline.set_params(**best_params)
        final_weights = sample_weights(
            data["search_frame"], data["y_search"], best_weight_profile
        )
        fit_warnings = _fit_pipeline(
            final_pipeline, data["X_search"], data["y_search"], final_weights
        )

        y_train_pred = final_pipeline.predict(data["X_search"])
        y_test_pred = final_pipeline.predict(data["X_test"])
        predictions = _threshold_prediction_frame(
            config.notebook_id,
            config.family,
            config.model_name,
            data["context_test"],
            data["y_test"],
            y_test_pred,
        )
        criticality_metrics = _criticality_metric_row(
            config.notebook_id,
            config.family,
            "threshold_regression",
            config.model_name,
            predictions,
            fit_warnings,
        )
        final_metrics = {
            **criticality_metrics,
            **_regression_metrics("train", data["y_search"], y_train_pred),
            **_regression_metrics("test", data["y_test"], y_test_pred),
            **champion_output["fold_summary"],
            "best_cv_rmse": champion_output["best_cv_rmse"],
            "best_weight_profile": best_weight_profile,
            "baseline_cv_rmse": baseline["summary"]["baseline_cv_validation_rmse_mean"],
            "baseline_test_rmse": baseline["test_metrics"]["baseline_test_rmse"],
            "test_rmse_gain_vs_baseline": baseline["test_metrics"]["baseline_test_rmse"]
            - _rmse(data["y_test"], y_test_pred),
        }
        fit_diagnosis = diagnose_fit(
            final_metrics, champion_output["fold_summary"], baseline["summary"]
        )
        final_metrics.update(fit_diagnosis)

        learning_curve = learning_curve_frame(
            final_pipeline,
            data,
            best_weight_profile,
            config.learning_curve_train_sizes,
            config.cv_splits,
        )
        residual_figure = build_residual_plot(predictions)
        learning_figure = build_learning_curve_plot(learning_curve)
        summary = {
            "validation_strategy": "TimeSeriesSplit",
            "search_method": "RandomizedSearchCV",
            "dataset_mode": "full" if config.use_full_dataset else "sample",
            "sample_frac": 1.0 if config.use_full_dataset else config.sample_frac,
            "best_params": best_params,
            "best_weight_profile": best_weight_profile,
            "fit_diagnosis": fit_diagnosis,
            "baseline_summary": baseline["summary"],
            "baseline_test_metrics": baseline["test_metrics"],
            "best_cv_fold_summary": champion_output["fold_summary"],
            "search_space": dict(config.param_distributions),
            "weight_profiles": {
                profile: WEIGHT_PROFILE_DESCRIPTIONS[profile]
                for profile in config.weight_profiles
            },
        }
        final_mlflow_info = _log_final_model_run(
            config,
            final_pipeline,
            final_metrics,
            predictions,
            summary,
            residual_figure,
            learning_curve,
            learning_figure,
        )
        final_metrics.update(final_mlflow_info)
        mlflow.log_text(
            candidate_results.to_csv(index=False), "tuning/all_candidate_results.csv"
        )

    return {
        "data_summary": pd.DataFrame(
            [
                {
                    "dataset_mode": "full" if config.use_full_dataset else "sample",
                    "sample_frac": (
                        1.0 if config.use_full_dataset else config.sample_frac
                    ),
                    "sample_shape": data["sample_shape"],
                    "split_counts": data["split_counts"],
                    "criticality_rates": data["criticality_rates"],
                    "feature_count": len(data["feature_columns"]),
                }
            ]
        ),
        "baseline_fold_metrics": baseline["fold_metrics"],
        "baseline_summary": pd.DataFrame(
            [{**baseline["summary"], **baseline["test_metrics"]}]
        ),
        "candidate_results": candidate_results,
        "best_fold_metrics": champion_output["best_fold_metrics"],
        "test_predictions": predictions,
        "final_metrics": pd.DataFrame([final_metrics]),
        "learning_curve": learning_curve,
        "figures": {
            "residual_analysis": residual_figure,
            "learning_curve": learning_figure,
        },
        "best_params": best_params,
        "best_weight_profile": best_weight_profile,
        "fit_diagnosis": fit_diagnosis,
    }
