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
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
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

TARGET_CLASSIFICATION = "y_comprar"
TARGET_REGRESSION = "y_qtd_comprar"
SPLIT_COLUMN = "split_temporal"
TRAIN_SPLIT = "train"
VALIDATION_SPLIT = "validation"
TEST_SPLIT = "test"

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
}


def ensure_artifact_dirs() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_abt_sample() -> pd.DataFrame:
    frames = [pd.read_csv(path, low_memory=False) for path in DATASET_PATHS]
    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=SAMPLE_FRAC, random_state=SAMPLE_RANDOM_STATE)
    df = df[df[SPLIT_COLUMN].isin([TRAIN_SPLIT, VALIDATION_SPLIT, TEST_SPLIT])]
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
    y_classification = df[TARGET_CLASSIFICATION].astype(int)
    y_regression = df[TARGET_REGRESSION].astype(float)
    split = df[SPLIT_COLUMN]

    train_mask = split.eq(TRAIN_SPLIT)
    validation_mask = split.eq(VALIDATION_SPLIT)
    test_mask = split.eq(TEST_SPLIT)
    regression_train_mask = train_mask & y_classification.eq(1)
    regression_validation_mask = validation_mask & y_classification.eq(1)
    regression_test_mask = test_mask & y_classification.eq(1)

    return {
        "feature_columns": feature_columns,
        "X_train": X.loc[train_mask],
        "X_validation": X.loc[validation_mask],
        "X_test": X.loc[test_mask],
        "y_classification_train": y_classification.loc[train_mask],
        "y_classification_validation": y_classification.loc[validation_mask],
        "y_classification_test": y_classification.loc[test_mask],
        "X_regression_train": X.loc[regression_train_mask],
        "X_regression_validation": X.loc[regression_validation_mask],
        "X_regression_test": X.loc[regression_test_mask],
        "y_regression_train": y_regression.loc[regression_train_mask],
        "y_regression_validation": y_regression.loc[regression_validation_mask],
        "y_regression_test": y_regression.loc[regression_test_mask],
        "sample_shape": df.shape,
        "split_counts": split.value_counts().to_dict(),
        "positive_rate": float(y_classification.mean()),
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


def train_classifiers(
    notebook_id: str,
    family: str,
    models: dict[str, object],
    splits: dict[str, object],
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_train"]
    X_test = splits["X_test"]
    y_train = splits["y_classification_train"]
    y_test = splits["y_classification_test"]

    for model_name, model in models.items():
        model_slug = slugify(model_name)
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_proba = _prediction_probability(pipeline, X_test)

        roc_auc = np.nan
        if not np.isnan(y_proba).all() and y_test.nunique() == 2:
            roc_auc = float(roc_auc_score(y_test, y_proba))

        metrics = {
            "notebook": notebook_id,
            "family": family,
            "stage": "classification",
            "model": model_name,
            "artifact_path": str((ARTIFACT_DIR / f"{notebook_id}_{model_slug}_classifier.pkl").relative_to(PROJECT_ROOT)),
            "prediction_path": str((METRICS_DIR / f"{notebook_id}_{model_slug}_classification_predictions.csv").relative_to(PROJECT_ROOT)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "roc_auc": roc_auc,
            "warnings": " | ".join(fit_warnings),
        }
        rows.append(metrics)

        predictions = pd.DataFrame(
            {
                "notebook": notebook_id,
                "family": family,
                "model": model_name,
                "y_true": y_test.to_numpy(),
                "y_pred": y_pred,
                "y_proba": y_proba,
            }
        )
        predictions.to_csv(METRICS_DIR / f"{notebook_id}_{model_slug}_classification_predictions.csv", index=False)
        joblib.dump(pipeline, ARTIFACT_DIR / f"{notebook_id}_{model_slug}_classifier.pkl")

    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(METRICS_DIR / f"{notebook_id}_classification_metrics.csv", index=False)
    return metrics_df


def train_regressors(
    notebook_id: str,
    family: str,
    models: dict[str, object],
    splits: dict[str, object],
) -> pd.DataFrame:
    rows = []
    X_train = splits["X_regression_train"]
    X_test = splits["X_regression_test"]
    y_train = splits["y_regression_train"]
    y_test = splits["y_regression_test"]

    for model_name, model in models.items():
        model_slug = slugify(model_name)
        pipeline = pipeline_for(model, X_train)
        fit_warnings = _fit_with_warnings(pipeline, X_train, y_train)
        y_pred = pipeline.predict(X_test)
        residual = y_test.to_numpy() - y_pred

        metrics = {
            "notebook": notebook_id,
            "family": family,
            "stage": "regression",
            "model": model_name,
            "artifact_path": str((ARTIFACT_DIR / f"{notebook_id}_{model_slug}_regressor.pkl").relative_to(PROJECT_ROOT)),
            "prediction_path": str((METRICS_DIR / f"{notebook_id}_{model_slug}_regression_predictions.csv").relative_to(PROJECT_ROOT)),
            "rmse": float(math.sqrt(mean_squared_error(y_test, y_pred))),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "r2": float(r2_score(y_test, y_pred)),
            "warnings": " | ".join(fit_warnings),
        }
        rows.append(metrics)

        predictions = pd.DataFrame(
            {
                "notebook": notebook_id,
                "family": family,
                "model": model_name,
                "y_true": y_test.to_numpy(),
                "y_pred": y_pred,
                "residual": residual,
            }
        )
        predictions.to_csv(METRICS_DIR / f"{notebook_id}_{model_slug}_regression_predictions.csv", index=False)
        joblib.dump(pipeline, ARTIFACT_DIR / f"{notebook_id}_{model_slug}_regressor.pkl")

    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(METRICS_DIR / f"{notebook_id}_regression_metrics.csv", index=False)
    return metrics_df


def run_training_notebook(
    notebook_id: str,
    family: str,
    classifiers: dict[str, object],
    regressors: dict[str, object],
) -> dict[str, pd.DataFrame]:
    ensure_artifact_dirs()
    df = load_abt_sample()
    splits = build_splits(df)
    classification_metrics = train_classifiers(notebook_id, family, classifiers, splits)
    regression_metrics = train_regressors(notebook_id, family, regressors, splits)

    summary = {
        "notebook": notebook_id,
        "family": family,
        "sample_shape": list(splits["sample_shape"]),
        "split_counts": splits["split_counts"],
        "positive_rate": splits["positive_rate"],
        "feature_count": len(splits["feature_columns"]),
        "feature_columns": splits["feature_columns"],
    }
    with open(METRICS_DIR / f"{notebook_id}_run_summary.json", "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2, ensure_ascii=False)

    return {
        "classification_metrics": classification_metrics,
        "regression_metrics": regression_metrics,
        "summary": pd.DataFrame([summary]),
    }


def _read_metric_files(pattern: str) -> pd.DataFrame:
    files = sorted(METRICS_DIR.glob(pattern))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)


def load_all_metrics() -> tuple[pd.DataFrame, pd.DataFrame]:
    classification = _read_metric_files("*_classification_metrics.csv")
    regression = _read_metric_files("*_regression_metrics.csv")
    return classification, regression


def load_all_models() -> dict[str, object]:
    models = {}
    for path in sorted(ARTIFACT_DIR.glob("*.pkl")):
        models[path.name] = joblib.load(path)
    return models


def build_decision_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    classification, regression = load_all_metrics()
    classification_rank = classification.sort_values(
        ["f1_score", "precision", "recall", "accuracy"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    regression_rank = regression.sort_values(
        ["rmse", "mae", "r2"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    classification_rank.insert(0, "rank", range(1, len(classification_rank) + 1))
    regression_rank.insert(0, "rank", range(1, len(regression_rank) + 1))
    classification_rank.to_csv(METRICS_DIR / "classification_decision_table.csv", index=False)
    regression_rank.to_csv(METRICS_DIR / "regression_decision_table.csv", index=False)
    return classification_rank, regression_rank


def build_combined_decision_table(
    classification_rank: pd.DataFrame,
    regression_rank: pd.DataFrame,
) -> pd.DataFrame:
    classification = classification_rank.copy()
    classification["stage_rank"] = classification["rank"]
    classification["sort_metric"] = classification["f1_score"]

    regression = regression_rank.copy()
    regression["stage_rank"] = regression["rank"]
    regression["sort_metric"] = regression["rmse"]

    common_columns = [
        "stage",
        "stage_rank",
        "family",
        "model",
        "f1_score",
        "precision",
        "recall",
        "accuracy",
        "roc_auc",
        "rmse",
        "mae",
        "r2",
        "sort_metric",
        "artifact_path",
        "prediction_path",
        "warnings",
    ]
    combined = pd.concat(
        [classification.reindex(columns=common_columns), regression.reindex(columns=common_columns)],
        ignore_index=True,
    )
    combined = combined.sort_values(["stage", "stage_rank"]).reset_index(drop=True)
    combined.insert(0, "decision_rank", range(1, len(combined) + 1))
    combined.to_csv(METRICS_DIR / "model_decision_table.csv", index=False)
    return combined


def _load_predictions(metric_row: pd.Series) -> pd.DataFrame:
    return pd.read_csv(PROJECT_ROOT / metric_row["prediction_path"])


def plot_confusion_matrices(classification_rank: pd.DataFrame) -> plt.Figure:
    n_models = len(classification_rank)
    n_cols = 3
    n_rows = math.ceil(n_models / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    axes = np.array(axes).reshape(-1)

    for ax, (_, row) in zip(axes, classification_rank.iterrows()):
        predictions = _load_predictions(row)
        matrix = confusion_matrix(predictions["y_true"], predictions["y_pred"], labels=[0, 1])
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            xticklabels=["Nao compra", "Compra"],
            yticklabels=["Nao compra", "Compra"],
            ax=ax,
        )
        ax.set_title(f"{row['family']} - {row['model']}")
        ax.set_xlabel("Predito")
        ax.set_ylabel("Real")

    for ax in axes[n_models:]:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "classification_confusion_matrices.png", dpi=160, bbox_inches="tight")
    return fig


def plot_roc_curves(classification_rank: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 7))
    for _, row in classification_rank.iterrows():
        predictions = _load_predictions(row).dropna(subset=["y_proba"])
        if predictions.empty or predictions["y_true"].nunique() < 2:
            continue
        fpr, tpr, _ = roc_curve(predictions["y_true"], predictions["y_proba"])
        label = f"{row['family']} - {row['model']} (AUC={row['roc_auc']:.3f})"
        ax.plot(fpr, tpr, linewidth=2, label=label)

    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_title("Curvas ROC - classificadores")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "classification_roc_curves.png", dpi=160, bbox_inches="tight")
    return fig


def plot_regression_metric_bars(regression_rank: pd.DataFrame) -> plt.Figure:
    metrics = ["rmse", "mae", "r2"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    labels = regression_rank["family"] + " - " + regression_rank["model"]

    for ax, metric in zip(axes, metrics):
        sns.barplot(x=regression_rank[metric], y=labels, ax=ax, color="#4C78A8")
        ax.set_title(metric.upper())
        ax.set_xlabel(metric.upper())
        ax.set_ylabel("")
        ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "regression_metric_bars.png", dpi=160, bbox_inches="tight")
    return fig


def plot_top_regression_residuals(regression_rank: pd.DataFrame, top_n: int = 2) -> plt.Figure:
    top = regression_rank.head(top_n)
    fig, axes = plt.subplots(1, len(top), figsize=(8 * len(top), 6))
    axes = np.array(axes).reshape(-1)

    for ax, (_, row) in zip(axes, top.iterrows()):
        predictions = _load_predictions(row)
        sns.scatterplot(
            data=predictions,
            x="y_pred",
            y="residual",
            alpha=0.35,
            edgecolor=None,
            ax=ax,
        )
        ax.axhline(0, color="black", linestyle="--", linewidth=1)
        ax.set_title(f"{row['family']} - {row['model']} | RMSE={row['rmse']:.3f}")
        ax.set_xlabel("Quantidade predita")
        ax.set_ylabel("Residuo")
        ax.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "regression_top2_residuals.png", dpi=160, bbox_inches="tight")
    return fig


def _model_pair_key(model_name: str) -> str:
    normalized = model_name.lower()
    if "gradient boosting" in normalized:
        return "gradient_boosting"
    if "xgboost" in normalized:
        return "xgboost"
    if "random forest" in normalized:
        return "random_forest"
    if "knn" in normalized:
        return "knn"
    if "logistic" in normalized or "linear regression" in normalized:
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
        "qtd_pedida_no_dia_audit",
        "comprou_no_dia_audit",
        "preco_medio_disponivel",
        TARGET_REGRESSION,
        TARGET_CLASSIFICATION,
    ]
    context = test[context_columns].copy()
    context["qtd_real_comprada"] = context["qtd_pedida_no_dia_audit"].fillna(0.0).astype(float)
    context["comprou_real"] = context["comprou_no_dia_audit"].fillna(0).astype(int)
    context["preco_medio_disponivel"] = context["preco_medio_disponivel"].fillna(0.0).astype(float)
    context["qtd_alvo_abt"] = context[TARGET_REGRESSION].fillna(0.0).astype(float)
    context["comprar_alvo_abt"] = context[TARGET_CLASSIFICATION].fillna(0).astype(int)
    context["valor_real_comprado"] = context["qtd_real_comprada"] * context["preco_medio_disponivel"]
    return context, X_test


def _build_operational_pairs(
    classification_rank: pd.DataFrame,
    regression_rank: pd.DataFrame,
) -> list[dict[str, object]]:
    classifiers = classification_rank.copy()
    regressors = regression_rank.copy()
    classifiers["pair_key"] = classifiers["model"].apply(_model_pair_key)
    regressors["pair_key"] = regressors["model"].apply(_model_pair_key)

    pairs = []
    for _, classifier in classifiers.iterrows():
        candidates = regressors[
            regressors["notebook"].eq(classifier["notebook"])
            & regressors["pair_key"].eq(classifier["pair_key"])
        ]
        if candidates.empty:
            continue
        regressor = candidates.iloc[0]
        pairs.append(
            {
                "notebook": classifier["notebook"],
                "family": classifier["family"],
                "pair_key": classifier["pair_key"],
                "pipeline": f"{classifier['family']} - {classifier['pair_key'].replace('_', ' ').title()}",
                "classifier_model": classifier["model"],
                "regressor_model": regressor["model"],
                "classifier_artifact_path": classifier["artifact_path"],
                "regressor_artifact_path": regressor["artifact_path"],
                "f1_score": classifier.get("f1_score", np.nan),
                "classification_accuracy": classifier.get("accuracy", np.nan),
                "target_rmse": regressor.get("rmse", np.nan),
                "target_mae": regressor.get("mae", np.nan),
                "target_r2": regressor.get("r2", np.nan),
            }
        )
    return pairs


def _evaluate_operational_pair(pair: dict[str, object], context: pd.DataFrame, X_test: pd.DataFrame) -> pd.DataFrame:
    classifier = joblib.load(PROJECT_ROOT / str(pair["classifier_artifact_path"]))
    regressor = joblib.load(PROJECT_ROOT / str(pair["regressor_artifact_path"]))

    class_pred = classifier.predict(X_test).astype(int)
    class_proba = _prediction_probability(classifier, X_test)
    raw_quantity_pred = regressor.predict(X_test)
    clipped_quantity_pred = np.maximum(0.0, raw_quantity_pred)
    indicated_quantity = np.where(class_pred == 1, clipped_quantity_pred, 0.0)

    recommendations = context.copy()
    recommendations.insert(0, "pipeline", pair["pipeline"])
    recommendations.insert(1, "notebook", pair["notebook"])
    recommendations.insert(2, "family", pair["family"])
    recommendations.insert(3, "pair_key", pair["pair_key"])
    recommendations["classifier_model"] = pair["classifier_model"]
    recommendations["regressor_model"] = pair["regressor_model"]
    recommendations["classificador_indicou_compra"] = class_pred
    recommendations["probabilidade_compra"] = class_proba
    recommendations["qtd_regressor_bruta"] = raw_quantity_pred
    recommendations["qtd_modelo_indicada"] = indicated_quantity
    recommendations["diferenca_modelo_menos_real"] = (
        recommendations["qtd_modelo_indicada"] - recommendations["qtd_real_comprada"]
    )
    recommendations["diferenca_abs"] = recommendations["diferenca_modelo_menos_real"].abs()
    recommendations["valor_modelo_indicado"] = (
        recommendations["qtd_modelo_indicada"] * recommendations["preco_medio_disponivel"]
    )
    recommendations["diferenca_valor_modelo_menos_real"] = (
        recommendations["valor_modelo_indicado"] - recommendations["valor_real_comprado"]
    )
    recommendations["diferenca_modelo_menos_alvo_abt"] = (
        recommendations["qtd_modelo_indicada"] - recommendations["qtd_alvo_abt"]
    )
    return recommendations


def _operational_metric_row(pair: dict[str, object], recommendations: pd.DataFrame) -> dict[str, object]:
    y_real = recommendations["qtd_real_comprada"].to_numpy(dtype=float)
    y_model = recommendations["qtd_modelo_indicada"].to_numpy(dtype=float)
    y_target = recommendations["qtd_alvo_abt"].to_numpy(dtype=float)
    diff = y_model - y_real
    abs_diff = np.abs(diff)
    total_real = float(y_real.sum())
    total_model = float(y_model.sum())
    total_value_real = float(recommendations["valor_real_comprado"].sum())
    total_value_model = float(recommendations["valor_modelo_indicado"].sum())

    return {
        "notebook": pair["notebook"],
        "family": pair["family"],
        "pair_key": pair["pair_key"],
        "pipeline": pair["pipeline"],
        "classifier_model": pair["classifier_model"],
        "regressor_model": pair["regressor_model"],
        "mae_vs_real": float(mean_absolute_error(y_real, y_model)),
        "rmse_vs_real": float(math.sqrt(mean_squared_error(y_real, y_model))),
        "bias_medio": float(diff.mean()),
        "abs_bias_medio": float(abs(diff.mean())),
        "wape_vs_real": float(abs_diff.sum() / total_real) if total_real else np.nan,
        "total_real_comprado": total_real,
        "total_modelo_indicado": total_model,
        "gap_total_quantidade": total_model - total_real,
        "gap_total_percentual": float((total_model - total_real) / total_real) if total_real else np.nan,
        "valor_real_comprado": total_value_real,
        "valor_modelo_indicado": total_value_model,
        "gap_total_valor": total_value_model - total_value_real,
        "taxa_itens_com_recomendacao": float((y_model > 0).mean()),
        "taxa_itens_com_compra_real": float((y_real > 0).mean()),
        "over_recommendation_rate": float((diff > 0).mean()),
        "under_recommendation_rate": float((diff < 0).mean()),
        "mae_vs_alvo_abt": float(mean_absolute_error(y_target, y_model)),
        "rmse_vs_alvo_abt": float(math.sqrt(mean_squared_error(y_target, y_model))),
        "r2_vs_alvo_abt": float(r2_score(y_target, y_model)),
        "f1_score": pair["f1_score"],
        "classification_accuracy": pair["classification_accuracy"],
        "target_rmse": pair["target_rmse"],
        "target_mae": pair["target_mae"],
        "target_r2": pair["target_r2"],
    }


def build_operational_recommendations(
    classification_rank: pd.DataFrame,
    regression_rank: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    context, X_test = _load_test_context_and_features()
    pairs = _build_operational_pairs(classification_rank, regression_rank)
    recommendation_frames = []
    metric_rows = []

    for pair in pairs:
        recommendations = _evaluate_operational_pair(pair, context, X_test)
        recommendation_frames.append(recommendations)
        metric_rows.append(_operational_metric_row(pair, recommendations))

    all_recommendations = pd.concat(recommendation_frames, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    metrics = metrics.sort_values(
        ["wape_vs_real", "rmse_vs_real", "abs_bias_medio"],
        ascending=[True, True, True],
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
            qtd_real_comprada=("qtd_real_comprada", "sum"),
            qtd_modelo_indicada=("qtd_modelo_indicada", "sum"),
            diferenca_abs=("diferenca_abs", "sum"),
            valor_real_comprado=("valor_real_comprado", "sum"),
            valor_modelo_indicado=("valor_modelo_indicado", "sum"),
        )
    )
    by_ingredient["diferenca_modelo_menos_real"] = (
        by_ingredient["qtd_modelo_indicada"] - by_ingredient["qtd_real_comprada"]
    )
    by_ingredient["diferenca_valor_modelo_menos_real"] = (
        by_ingredient["valor_modelo_indicado"] - by_ingredient["valor_real_comprado"]
    )
    by_ingredient = by_ingredient.sort_values("diferenca_abs", ascending=False).reset_index(drop=True)

    all_recommendations.to_csv(METRICS_DIR / "two_stage_operational_recommendations.csv", index=False)
    metrics.to_csv(METRICS_DIR / "two_stage_operational_metrics.csv", index=False)
    by_ingredient.to_csv(METRICS_DIR / "two_stage_operational_by_ingredient.csv", index=False)
    return metrics, all_recommendations, by_ingredient


def plot_operational_total_quantity(operational_metrics: pd.DataFrame) -> plt.Figure:
    plot_df = operational_metrics.melt(
        id_vars=["pipeline"],
        value_vars=["total_real_comprado", "total_modelo_indicado"],
        var_name="serie",
        value_name="quantidade",
    )
    fig, ax = plt.subplots(figsize=(13, 7))
    sns.barplot(data=plot_df, y="pipeline", x="quantidade", hue="serie", ax=ax)
    ax.set_title("Total comprado real vs total indicado pelo modelo")
    ax.set_xlabel("Quantidade total")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "operational_total_quantity_real_vs_model.png", dpi=160, bbox_inches="tight")
    return fig


def plot_operational_total_value_gap(operational_metrics: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(13, 7))
    sns.barplot(data=operational_metrics, y="pipeline", x="gap_total_valor", color="#E45756", ax=ax)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Gap financeiro: valor indicado pelo modelo menos valor comprado real")
    ax.set_xlabel("Gap de valor")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "operational_total_value_gap.png", dpi=160, bbox_inches="tight")
    return fig


def plot_operational_best_models_scatter(
    operational_metrics: pd.DataFrame,
    recommendations: pd.DataFrame,
    top_n: int = 2,
) -> plt.Figure:
    top_pipelines = operational_metrics.head(top_n)["pipeline"].tolist()
    plot_df = recommendations[recommendations["pipeline"].isin(top_pipelines)].copy()
    fig, axes = plt.subplots(1, len(top_pipelines), figsize=(8 * len(top_pipelines), 6))
    axes = np.array(axes).reshape(-1)

    max_axis = float(max(plot_df["qtd_real_comprada"].max(), plot_df["qtd_modelo_indicada"].max()))
    for ax, pipeline_name in zip(axes, top_pipelines):
        data = plot_df[plot_df["pipeline"].eq(pipeline_name)]
        sns.scatterplot(
            data=data,
            x="qtd_real_comprada",
            y="qtd_modelo_indicada",
            alpha=0.35,
            edgecolor=None,
            ax=ax,
        )
        ax.plot([0, max_axis], [0, max_axis], linestyle="--", color="black", linewidth=1)
        ax.set_title(pipeline_name)
        ax.set_xlabel("Quantidade comprada real")
        ax.set_ylabel("Quantidade indicada pelo modelo")
        ax.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "operational_best_models_scatter.png", dpi=160, bbox_inches="tight")
    return fig


def plot_operational_best_model_top_ingredient_gaps(by_ingredient: pd.DataFrame, top_n: int = 20) -> plt.Figure:
    plot_df = by_ingredient.head(top_n).copy()
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.barplot(
        data=plot_df,
        y="nome_ingrediente",
        x="diferenca_modelo_menos_real",
        color="#4C78A8",
        ax=ax,
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Top divergencias por ingrediente - melhor modelo operacional")
    ax.set_xlabel("Quantidade indicada menos quantidade real")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "operational_best_model_top_ingredient_gaps.png", dpi=160, bbox_inches="tight")
    return fig


def plot_operational_best_models_difference_distribution(
    operational_metrics: pd.DataFrame,
    recommendations: pd.DataFrame,
    top_n: int = 2,
) -> plt.Figure:
    top_pipelines = operational_metrics.head(top_n)["pipeline"].tolist()
    plot_df = recommendations[recommendations["pipeline"].isin(top_pipelines)].copy()
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.histplot(
        data=plot_df,
        x="diferenca_modelo_menos_real",
        hue="pipeline",
        bins=60,
        element="step",
        stat="density",
        common_norm=False,
        ax=axes[0],
    )
    axes[0].axvline(0, color="black", linewidth=1)
    axes[0].set_title("Distribuicao do gap de quantidade")
    axes[0].set_xlabel("Quantidade indicada menos quantidade real")
    axes[0].grid(alpha=0.25)

    sns.boxplot(
        data=plot_df,
        x="diferenca_modelo_menos_real",
        y="pipeline",
        ax=axes[1],
    )
    axes[1].axvline(0, color="black", linewidth=1)
    axes[1].set_title("Variancia do gap nos melhores modelos")
    axes[1].set_xlabel("Quantidade indicada menos quantidade real")
    axes[1].set_ylabel("")
    axes[1].grid(axis="x", alpha=0.25)

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "operational_best_models_gap_distribution.png", dpi=160, bbox_inches="tight")
    return fig


def run_comparison_notebook() -> dict[str, object]:
    ensure_artifact_dirs()
    models = load_all_models()
    classification_rank, regression_rank = build_decision_tables()
    decision_table = build_combined_decision_table(classification_rank, regression_rank)
    operational_metrics, operational_recommendations, operational_by_ingredient = build_operational_recommendations(
        classification_rank,
        regression_rank,
    )
    figures = {
        "operational_total_quantity": plot_operational_total_quantity(operational_metrics),
        "operational_total_value_gap": plot_operational_total_value_gap(operational_metrics),
        "operational_best_models_scatter": plot_operational_best_models_scatter(
            operational_metrics,
            operational_recommendations,
        ),
        "operational_best_model_top_ingredient_gaps": plot_operational_best_model_top_ingredient_gaps(
            operational_by_ingredient
        ),
        "operational_best_models_gap_distribution": plot_operational_best_models_difference_distribution(
            operational_metrics,
            operational_recommendations,
        ),
        "confusion_matrices": plot_confusion_matrices(classification_rank),
        "roc_curves": plot_roc_curves(classification_rank),
        "regression_metric_bars": plot_regression_metric_bars(regression_rank),
        "top_regression_residuals": plot_top_regression_residuals(regression_rank),
    }
    return {
        "models_loaded": len(models),
        "operational_metrics": operational_metrics,
        "operational_recommendations": operational_recommendations,
        "operational_by_ingredient": operational_by_ingredient,
        "decision_table": decision_table,
        "classification_rank": classification_rank,
        "regression_rank": regression_rank,
        "figures": figures,
    }


def list_expected_artifacts() -> pd.DataFrame:
    rows = []
    for path in sorted(ARTIFACT_DIR.glob("*.pkl")):
        rows.append({"artifact": path.name, "size_mb": path.stat().st_size / 1024 / 1024})
    return pd.DataFrame(rows)
