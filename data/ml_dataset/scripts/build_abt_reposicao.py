"""
Build the ML datasets for Saltim Cafe replenishment decisions.

Outputs:
  - data/ml_dataset/outputs/abt_reposicao_part1.csv
  - data/ml_dataset/outputs/abt_reposicao_part2.csv
  - data/ml_dataset/outputs/abt_pedidos_eventos.csv
  - data/ml_dataset/reports/sanity_report.md

The main ABT uses one row per purchasable ingredient per day. Features only use
information known up to that date; future demand is used only to build targets.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    ml_dir = Path(__file__).resolve().parents[1]
    data_dir = ml_dir.parent
    parser = argparse.ArgumentParser(description="Build Saltim replenishment ABT.")
    parser.add_argument("--data-dir", type=Path, default=data_dir)
    parser.add_argument("--ml-dir", type=Path, default=ml_dir)
    parser.add_argument("--config", type=Path, default=ml_dir / "config" / "dataset_config.json")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dirs(ml_dir: Path) -> None:
    for subdir in ["outputs", "reports"]:
        (ml_dir / subdir).mkdir(parents=True, exist_ok=True)


def purchase_step(unit: str) -> float:
    unit_norm = str(unit).upper().strip()
    if unit_norm in {"KG", "L"}:
        return 0.5
    if unit_norm in {"G", "ML"}:
        return 100.0
    if unit_norm in {"UN", "UND", "UNIDADE", "PORCAO", "PORÇÃO"}:
        return 1.0
    return 1.0


def ceil_to_step(qty: float, step: float) -> float:
    if qty <= 0:
        return 0.0
    if step <= 0:
        return float(qty)
    return float(math.ceil(qty / step) * step)


def classify_profile(name: str) -> str:
    text = str(name).upper()
    perishable = [
        "LEITE",
        "CREAM",
        "QUEIJO",
        "IOGURTE",
        "OVO",
        "MANTEIGA",
        "FRANGO",
        "CARNE",
        "SALMAO",
        "SALMÃO",
        "PEIXE",
        "RICOTA",
        "MOZZARELA",
    ]
    dry = [
        "ACUCAR",
        "AÇUCAR",
        "FARINHA",
        "ARROZ",
        "CAFE",
        "CAFÉ",
        "CHOCOLATE",
        "CACAU",
        "SAL",
        "PIMENTA",
        "CANELA",
        "GRAO",
        "GRÃO",
        "NUTS",
        "AMENDOA",
        "AMÊNDOA",
    ]
    if any(token in text for token in perishable):
        return "perecivel"
    if any(token in text for token in dry):
        return "seco"
    return "neutro"


def read_sources(data_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "vendas": pd.read_csv(data_dir / "vendas.csv", parse_dates=["date_time"]),
        "pedidos": pd.read_csv(data_dir / "pedidos.csv", parse_dates=["data_pedido", "data_prevista"]),
        "pedidos_log": pd.read_csv(
            data_dir / "pedidos_log.csv",
            parse_dates=["data_pedido", "data_prevista"],
        ),
        "estoques": pd.read_csv(data_dir / "estoques.csv", parse_dates=["date_time"]),
        "receitas": pd.read_csv(data_dir / "receitas.csv"),
        "receitas_ingredientes": pd.read_csv(data_dir / "receitas_ingredientes.csv"),
        "ingredientes": pd.read_csv(data_dir / "ingredientes.csv"),
        "categorias": pd.read_csv(data_dir / "categorias.csv"),
        "fornecedores": pd.read_csv(data_dir / "fornecedores.csv"),
        "fornecedores_ingredientes": pd.read_csv(data_dir / "fornecedores_ingredientes.csv"),
        "feriados": pd.read_csv(data_dir / "feriados_recife.csv", parse_dates=["data"]),
        "indisponiveis": pd.read_csv(
            data_dir / "produtos_indisponiveis.csv",
            parse_dates=["data_inicio", "data_fim"],
        ),
    }


def add_order_type(pedidos: pd.DataFrame, pedidos_log: pd.DataFrame) -> pd.DataFrame:
    keys = ["data_pedido", "ingredient_id", "data_prevista"]
    orders = pedidos.copy()
    log = pedidos_log.copy()
    orders["_merge_order"] = orders.groupby(keys).cumcount()
    log["_merge_order"] = log.groupby(keys).cumcount()
    out = orders.merge(
        log[keys + ["_merge_order", "order_type"]],
        on=keys + ["_merge_order"],
        how="left",
    )
    out["order_type"] = out["order_type"].fillna("desconhecido")
    return out.drop(columns=["_merge_order"])


def build_recipe_expander(
    receitas: pd.DataFrame,
    receitas_ingredientes: pd.DataFrame,
    ingredientes: pd.DataFrame,
    excluded_category_id: str,
) -> dict[str, dict[str, float]]:
    category_by_ing = dict(zip(ingredientes["id"].astype(str), ingredientes["category_id"].astype(str)))
    ri = receitas_ingredientes.copy()
    ri["recipe_id"] = ri["recipe_id"].astype(str)
    ri["ingredient_id"] = ri["ingredient_id"].astype(str)
    ri["qty"] = pd.to_numeric(ri["qty"], errors="coerce").fillna(0.0)

    rec = receitas.copy()
    rec["id"] = rec["id"].astype(str)
    rec["yield_qty"] = pd.to_numeric(rec["yield_qty"], errors="coerce").fillna(1.0).clip(lower=1.0)

    prod = rec[rec["type"].astype(str).str.upper().str.strip() == "PRODUCAO"].copy()
    prod = prod.dropna(subset=["output_ingredient_id"])
    prod["output_ingredient_id"] = prod["output_ingredient_id"].astype(str)

    production_by_output: dict[str, list[tuple[str, float]]] = {}
    for _, prod_row in prod.iterrows():
        recipe_id = str(prod_row["id"])
        output_id = str(prod_row["output_ingredient_id"])
        yield_qty = float(prod_row["yield_qty"])
        lines = ri[ri["recipe_id"] == recipe_id]
        production_by_output[output_id] = [
            (str(line["ingredient_id"]), float(line["qty"]) / yield_qty)
            for _, line in lines.iterrows()
        ]

    def expand_ingredient(ingredient_id: str, qty: float, visited: set[str] | None = None) -> dict[str, float]:
        if visited is None:
            visited = set()
        if ingredient_id in visited:
            return {}
        visited.add(ingredient_id)

        if category_by_ing.get(ingredient_id) != excluded_category_id:
            return {ingredient_id: float(qty)}

        expanded: dict[str, float] = defaultdict(float)
        for leaf_id, leaf_qty_per_output in production_by_output.get(ingredient_id, []):
            for out_id, out_qty in expand_ingredient(
                leaf_id,
                qty * leaf_qty_per_output,
                visited.copy(),
            ).items():
                expanded[out_id] += out_qty
        return dict(expanded)

    recipe_components: dict[str, dict[str, float]] = {}
    for _, recipe in rec.iterrows():
        recipe_id = str(recipe["id"])
        yield_qty = float(recipe["yield_qty"])
        lines = ri[ri["recipe_id"] == recipe_id]
        components: dict[str, float] = defaultdict(float)
        for _, line in lines.iterrows():
            ing_id = str(line["ingredient_id"])
            qty_per_sale_unit = float(line["qty"]) / yield_qty
            expanded = expand_ingredient(ing_id, qty_per_sale_unit)
            for out_id, out_qty in expanded.items():
                components[out_id] += out_qty
        recipe_components[recipe_id] = dict(components)

    return recipe_components


def build_daily_consumption(
    vendas: pd.DataFrame,
    recipe_components: dict[str, dict[str, float]],
    dates: pd.DatetimeIndex,
    purchasable_ids: list[str],
) -> pd.DataFrame:
    sales = vendas.copy()
    sales["date"] = sales["date_time"].dt.normalize()
    sales["recipe_id"] = sales["recipe_id"].astype(str)
    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce").fillna(0.0)

    rows: list[dict] = []
    for _, sale in sales.iterrows():
        for ingredient_id, qty_per_unit in recipe_components.get(str(sale["recipe_id"]), {}).items():
            rows.append(
                {
                    "date": sale["date"],
                    "ingredient_id": ingredient_id,
                    "consumo_ingrediente_dia": float(sale["quantity"]) * qty_per_unit,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["ingredient_id", "date", "consumo_ingrediente_dia"])

    consumo = pd.DataFrame(rows)
    consumo = consumo[consumo["ingredient_id"].isin(purchasable_ids)]
    consumo = consumo[consumo["date"].isin(dates)]
    return consumo.groupby(["ingredient_id", "date"], as_index=False)["consumo_ingrediente_dia"].sum()


def build_calendar(dates: pd.DatetimeIndex, feriados: pd.DataFrame) -> pd.DataFrame:
    cal = pd.DataFrame({"date": dates})
    cal["dia_da_semana"] = cal["date"].dt.dayofweek
    cal["is_friday"] = (cal["dia_da_semana"] == 4).astype(int)
    cal["dias_ate_sexta"] = (4 - cal["dia_da_semana"]) % 7
    cal["is_weekend"] = cal["dia_da_semana"].isin([5, 6]).astype(int)
    cal["mes"] = cal["date"].dt.month
    cal["semana_do_ano"] = cal["date"].dt.isocalendar().week.astype(int)
    cal["dia_do_mes"] = cal["date"].dt.day
    cal["is_summer"] = cal["mes"].isin([12, 1, 2, 3]).astype(int)
    cal["is_sao_joao"] = ((cal["mes"] == 6) & (cal["dia_do_mes"].between(20, 25))).astype(int)

    holidays = feriados.copy()
    holidays["date"] = holidays["data"].dt.normalize()
    holidays = holidays[["date", "nome", "tipo"]].drop_duplicates("date")
    cal = cal.merge(holidays, on="date", how="left")
    cal["is_holiday"] = cal["nome"].notna().astype(int)
    cal["nome_feriado"] = cal["nome"].fillna("")
    cal["tipo_feriado"] = cal["tipo"].fillna("")
    cal = cal.drop(columns=["nome", "tipo"])

    carnival_dates = holidays[
        holidays["nome"].astype(str).str.upper().str.contains("CARNAVAL", na=False)
    ]["date"]
    cal["is_carnaval_window"] = 0
    for carnival_date in carnival_dates:
        mask = (cal["date"] >= carnival_date - pd.Timedelta(days=2)) & (
            cal["date"] <= carnival_date + pd.Timedelta(days=2)
        )
        cal.loc[mask, "is_carnaval_window"] = 1
    return cal


def build_supplier_features(fornecedores: pd.DataFrame, fornecedores_ingredientes: pd.DataFrame) -> pd.DataFrame:
    fi = fornecedores_ingredientes.copy()
    fi["ingredient_id"] = fi["ingredient_id"].astype(str)
    fi["price"] = pd.to_numeric(fi["price"], errors="coerce")
    fi["discount_percent"] = pd.to_numeric(fi["discount_percent"], errors="coerce").fillna(0.0)
    fi["min_to_discount"] = pd.to_numeric(fi["min_to_discount"], errors="coerce").fillna(0.0)
    sup = fornecedores[["id", "avg_delivery_time"]].copy()
    sup["avg_delivery_time"] = pd.to_numeric(sup["avg_delivery_time"], errors="coerce")
    merged = fi.merge(sup, left_on="supplier_id", right_on="id", how="left")

    features = merged.groupby("ingredient_id").agg(
        menor_preco_disponivel=("price", "min"),
        preco_medio_disponivel=("price", "mean"),
        maior_preco_disponivel=("price", "max"),
        menor_lead_time=("avg_delivery_time", "min"),
        lead_time_medio_fornecedores=("avg_delivery_time", "mean"),
        qtd_fornecedores_disponiveis=("supplier_id", "nunique"),
        maior_desconto_disponivel=("discount_percent", "max"),
        min_to_discount=("min_to_discount", "min"),
    ).reset_index()

    cheapest = (
        merged.sort_values(["ingredient_id", "price", "avg_delivery_time"])
        .drop_duplicates("ingredient_id")[["ingredient_id", "supplier_id"]]
        .rename(columns={"supplier_id": "fornecedor_mais_barato"})
    )
    fastest = (
        merged.sort_values(["ingredient_id", "avg_delivery_time", "price"])
        .drop_duplicates("ingredient_id")[["ingredient_id", "supplier_id"]]
        .rename(columns={"supplier_id": "fornecedor_mais_rapido"})
    )
    features = features.merge(cheapest, on="ingredient_id", how="left")
    features = features.merge(fastest, on="ingredient_id", how="left")
    features["preco_min_max_ratio"] = (
        features["menor_preco_disponivel"] / features["maior_preco_disponivel"]
    ).replace([np.inf, -np.inf], np.nan)
    features["menor_lead_time"] = features["menor_lead_time"].fillna(1).astype(int).clip(lower=1)
    return features


def build_indisponibilidade_features(
    dates: pd.DatetimeIndex,
    purchasable_ids: list[str],
    ingredientes: pd.DataFrame,
    receitas: pd.DataFrame,
    indisponiveis: pd.DataFrame,
    recipe_components: dict[str, dict[str, float]],
) -> pd.DataFrame:
    date_to_i = {date: i for i, date in enumerate(dates)}
    ing_to_i = {ing: i for i, ing in enumerate(purchasable_ids)}
    flags = np.zeros((len(purchasable_ids), len(dates)), dtype=np.int8)
    related: list[list[set[str]]] = [[set() for _ in range(len(dates))] for _ in range(len(purchasable_ids))]

    ingredient_names = ingredientes[["id", "name"]].copy()
    ingredient_names["name_upper"] = ingredient_names["name"].astype(str).str.upper()
    recipes = receitas[["id", "name"]].copy()
    recipes["name_upper"] = recipes["name"].astype(str).str.upper()

    for _, row in indisponiveis.iterrows():
        match = str(row["match"]).upper()
        affected: set[str] = set()
        direct = ingredient_names[ingredient_names["name_upper"].str.contains(match, regex=False, na=False)]
        affected.update(direct["id"].astype(str)[direct["id"].astype(str).isin(purchasable_ids)])
        matching_recipes = recipes[recipes["name_upper"].str.contains(match, regex=False, na=False)]["id"].astype(str)
        for recipe_id in matching_recipes:
            affected.update(recipe_components.get(recipe_id, {}).keys())

        start = pd.Timestamp(row["data_inicio"]).normalize()
        end = pd.Timestamp(row["data_fim"]).normalize()
        period = [date for date in dates if start <= date <= end]
        for ing_id in affected:
            if ing_id not in ing_to_i:
                continue
            ing_i = ing_to_i[ing_id]
            for date in period:
                date_i = date_to_i[date]
                flags[ing_i, date_i] = 1
                related[ing_i][date_i].add(match)

    rows = []
    for ing_id, ing_i in ing_to_i.items():
        current_days = 0
        for date_i, date in enumerate(dates):
            if flags[ing_i, date_i]:
                current_days += 1
            else:
                current_days = 0
            rows.append(
                {
                    "ingredient_id": ing_id,
                    "date": date,
                    "flag_indisponibilidade": int(flags[ing_i, date_i]),
                    "ingrediente_afetado_por_indisponibilidade": int(flags[ing_i, date_i]),
                    "produto_indisponivel_relacionado": ";".join(sorted(related[ing_i][date_i])),
                    "dias_em_indisponibilidade": current_days,
                }
            )
    return pd.DataFrame(rows)


def mode_or_empty(values: pd.Series) -> str:
    clean = values.dropna().astype(str)
    if clean.empty:
        return ""
    return clean.mode().iat[0]


def build_order_daily(orders: pd.DataFrame) -> pd.DataFrame:
    orders = orders.copy()
    orders["lead_time_pedido_no_dia"] = (
        orders["data_prevista"].dt.normalize() - orders["data_pedido"].dt.normalize()
    ).dt.days.clip(lower=0)
    daily = orders.groupby(["ingredient_id", "data_pedido"], as_index=False).agg(
        audit_qtd_pedida_no_dia=("qty", "sum"),
        audit_valor_pedido_no_dia=("valor", "sum"),
        audit_comprou_no_dia=("id", "count"),
        audit_order_type_no_dia=("order_type", mode_or_empty),
        lead_time_pedido_no_dia=("lead_time_pedido_no_dia", "mean"),
    )
    daily = daily.rename(columns={"data_pedido": "date"})
    daily["audit_comprou_no_dia"] = (daily["audit_comprou_no_dia"] > 0).astype(int)
    return daily


def add_historical_order_features(abt: pd.DataFrame) -> pd.DataFrame:
    abt = abt.sort_values(["ingredient_id", "date"]).copy()
    abt["qtd_pedida_no_dia_audit"] = abt["audit_qtd_pedida_no_dia"].fillna(0.0)
    abt["comprou_no_dia_audit"] = abt["audit_comprou_no_dia"].fillna(0).astype(int)
    abt["valor_pedido_no_dia_audit"] = abt["audit_valor_pedido_no_dia"].fillna(0.0)
    abt["order_type_no_dia_audit"] = abt["audit_order_type_no_dia"].fillna("")

    grouped = abt.groupby("ingredient_id", group_keys=False)
    abt["total_pedido_30d"] = grouped["qtd_pedida_no_dia_audit"].transform(
        lambda s: s.shift(1).rolling(30, min_periods=1).sum()
    )
    abt["media_qtd_pedida_30d"] = grouped["qtd_pedida_no_dia_audit"].transform(
        lambda s: s.shift(1).rolling(30, min_periods=1).mean()
    )
    abt["lead_time_medio_realizado"] = grouped["lead_time_pedido_no_dia"].transform(
        lambda s: s.shift(1).expanding(min_periods=1).mean()
    )

    pieces = []
    for _, group in abt.groupby("ingredient_id", sort=False):
        group = group.copy()
        order_mask = group["comprou_no_dia_audit"] == 1
        last_date = group["date"].where(order_mask).ffill().shift(1)
        group["dias_desde_ultimo_pedido"] = (group["date"] - last_date).dt.days
        group["qtd_ultimo_pedido"] = group["qtd_pedida_no_dia_audit"].where(order_mask).ffill().shift(1)
        group["tipo_ultimo_pedido"] = group["order_type_no_dia_audit"].where(order_mask).ffill().shift(1)
        pieces.append(group)

    out = pd.concat(pieces, ignore_index=True)
    out["dias_desde_ultimo_pedido"] = out["dias_desde_ultimo_pedido"].fillna(9999).astype(int)
    out["qtd_ultimo_pedido"] = out["qtd_ultimo_pedido"].fillna(0.0)
    out["tipo_ultimo_pedido"] = out["tipo_ultimo_pedido"].fillna("")
    out["lead_time_medio_realizado"] = out["lead_time_medio_realizado"].fillna(out["lead_time_medio_fornecedores"])
    return out


def add_open_order_features(
    abt: pd.DataFrame,
    orders: pd.DataFrame,
    dates: pd.DatetimeIndex,
    purchasable_ids: list[str],
    review_cycle_days: int,
) -> pd.DataFrame:
    n_rows = len(abt)
    row_index = {
        (row.ingredient_id, row.date): idx
        for idx, row in enumerate(abt[["ingredient_id", "date"]].itertuples(index=False))
    }
    date_to_i = {date: i for i, date in enumerate(dates)}
    date_values = np.array(dates)

    pedidos_em_aberto = np.zeros(n_rows, dtype=np.int16)
    qtd_em_transito = np.zeros(n_rows, dtype=np.float64)
    qtd_em_transito_horizonte = np.zeros(n_rows, dtype=np.float64)
    dias_para_proxima_entrega = np.full(n_rows, np.nan, dtype=np.float64)
    lead_by_ing = (
        abt.drop_duplicates("ingredient_id")
        .set_index("ingredient_id")["menor_lead_time"]
        .fillna(1)
        .astype(int)
        .to_dict()
    )

    relevant_orders = orders[orders["ingredient_id"].isin(purchasable_ids)].copy()
    for _, order in relevant_orders.iterrows():
        ing_id = str(order["ingredient_id"])
        order_date = pd.Timestamp(order["data_pedido"]).normalize()
        delivery_date = pd.Timestamp(order["data_prevista"]).normalize()
        if ing_id not in lead_by_ing:
            continue
        start_i = max(0, date_to_i.get(order_date, -1) + 1)
        end_i = min(date_to_i.get(delivery_date, len(dates)) - 1, len(dates) - 1)
        if end_i < start_i:
            continue

        horizon_days = int(lead_by_ing[ing_id]) + int(review_cycle_days)
        qty = float(order["qty"])
        for date_i in range(start_i, end_i + 1):
            date = pd.Timestamp(date_values[date_i])
            row_pos = row_index.get((ing_id, date))
            if row_pos is None:
                continue
            pedidos_em_aberto[row_pos] += 1
            qtd_em_transito[row_pos] += qty
            days_to_delivery = (delivery_date - date).days
            if np.isnan(dias_para_proxima_entrega[row_pos]):
                dias_para_proxima_entrega[row_pos] = days_to_delivery
            else:
                dias_para_proxima_entrega[row_pos] = min(dias_para_proxima_entrega[row_pos], days_to_delivery)
            if 0 < days_to_delivery <= horizon_days:
                qtd_em_transito_horizonte[row_pos] += qty

    abt = abt.copy()
    abt["pedidos_em_aberto"] = pedidos_em_aberto
    abt["qtd_em_transito"] = qtd_em_transito
    abt["estoque_em_aberto"] = qtd_em_transito
    abt["qtd_em_transito_no_horizonte"] = qtd_em_transito_horizonte
    abt["dias_para_proxima_entrega"] = pd.Series(dias_para_proxima_entrega).fillna(9999).astype(int)
    return abt


def add_stock_and_demand_features(abt: pd.DataFrame) -> pd.DataFrame:
    abt = abt.sort_values(["ingredient_id", "date"]).copy()
    grouped = abt.groupby("ingredient_id", group_keys=False)
    abt["saldo_lag_1"] = grouped["saldo_atual"].shift(1)
    abt["saldo_lag_7"] = grouped["saldo_atual"].shift(7)
    abt["variacao_estoque_1d"] = abt["saldo_atual"] - abt["saldo_lag_1"]
    abt["variacao_estoque_7d"] = abt["saldo_atual"] - abt["saldo_lag_7"]
    abt["flag_ruptura"] = (abt["saldo_atual"] <= 0).astype(int)

    for lag in [1, 7, 14, 28]:
        abt[f"consumo_lag_{lag}d"] = grouped["consumo_ingrediente_dia"].shift(lag)
    for window in [7, 14, 28]:
        abt[f"media_movel_consumo_{window}d"] = grouped["consumo_ingrediente_dia"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).mean()
        )
        abt[f"desvio_consumo_{window}d"] = grouped["consumo_ingrediente_dia"].transform(
            lambda s, w=window: s.rolling(w, min_periods=2).std()
        )
        abt[f"consumo_max_{window}d"] = grouped["consumo_ingrediente_dia"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).max()
        )

    abt["tendencia_consumo_7_vs_28"] = (
        abt["media_movel_consumo_7d"] / abt["media_movel_consumo_28d"].replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    pieces = []
    for _, group in abt.groupby("ingredient_id", sort=False):
        group = group.copy()
        consumption_mask = group["consumo_ingrediente_dia"] > 0
        last_date = group["date"].where(consumption_mask).ffill()
        group["dias_desde_ultimo_consumo"] = (group["date"] - last_date).dt.days
        pieces.append(group)
    abt = pd.concat(pieces, ignore_index=True)
    abt["dias_desde_ultimo_consumo"] = abt["dias_desde_ultimo_consumo"].fillna(9999).astype(int)

    fill_zero_cols = [
        "saldo_lag_1",
        "saldo_lag_7",
        "variacao_estoque_1d",
        "variacao_estoque_7d",
        "consumo_lag_1d",
        "consumo_lag_7d",
        "consumo_lag_14d",
        "consumo_lag_28d",
        "desvio_consumo_7d",
        "desvio_consumo_14d",
        "desvio_consumo_28d",
    ]
    abt[fill_zero_cols] = abt[fill_zero_cols].fillna(0.0)
    return abt


def add_targets_and_baseline(abt: pd.DataFrame, config: dict) -> pd.DataFrame:
    z = float(config["safety_stock_z"])
    review_cycle_days = int(config["review_cycle_days"])
    pieces = []

    for _, group in abt.sort_values(["ingredient_id", "date"]).groupby("ingredient_id", sort=False):
        group = group.copy().reset_index(drop=True)
        demand = group["consumo_ingrediente_dia"].to_numpy(dtype=float)
        prefix = np.concatenate([[0.0], np.cumsum(demand)])
        n = len(group)
        lead_time = int(max(1, group["menor_lead_time"].iloc[0]))
        horizon = lead_time + review_cycle_days

        future_h = np.zeros(n, dtype=float)
        future_lt = np.zeros(n, dtype=float)
        for i in range(n):
            end_h = min(n, i + horizon + 1)
            end_lt = min(n, i + lead_time + 1)
            future_h[i] = prefix[end_h] - prefix[i + 1]
            future_lt[i] = prefix[end_lt] - prefix[i + 1]

        safety_stock = z * group["desvio_consumo_28d"].fillna(0.0).to_numpy(dtype=float) * math.sqrt(lead_time)
        stock_position_target = (
            group["saldo_atual"].to_numpy(dtype=float)
            + group["qtd_em_transito_no_horizonte"].to_numpy(dtype=float)
        )
        raw_qty = np.maximum(0.0, future_h + safety_stock - stock_position_target)
        step = float(group["quantidade_por_unidade_de_compra"].iloc[0])
        group["y_qtd_comprar"] = [ceil_to_step(qty, step) for qty in raw_qty]
        group["y_threshold"] = np.maximum(0.0, future_lt + safety_stock)
        group["y_comprar"] = (group["y_qtd_comprar"] > 0).astype(int)
        group["y_demanda_futura_horizonte"] = future_h
        group["y_demanda_futura_lead_time"] = future_lt
        group["safety_stock"] = safety_stock
        group["horizonte_dias"] = horizon
        group["target_horizonte_completo"] = (
            group["date"] + pd.to_timedelta(horizon, unit="D") <= group["date"].max()
        ).astype(int)

        group["baseline_threshold"] = (group["media_movel_consumo_28d"] * lead_time + safety_stock).clip(lower=0.0)
        group["baseline_order_up_to"] = (
            group["baseline_threshold"] + group["media_movel_consumo_28d"] * review_cycle_days
        ).clip(lower=0.0)
        group["baseline_qtd_comprar"] = np.maximum(0.0, group["baseline_order_up_to"] - group["stock_position"])
        group["baseline_qtd_comprar"] = [ceil_to_step(qty, step) for qty in group["baseline_qtd_comprar"]]
        group["baseline_comprar"] = (group["baseline_qtd_comprar"] > 0).astype(int)

        group["criticidade_score"] = (
            group["stock_position"] / group["baseline_threshold"].replace(0, np.nan)
        ).replace([np.inf, -np.inf], np.nan)
        group["criticidade_score"] = group["criticidade_score"].where(
            group["criticidade_score"].notna(),
            pd.Series(np.where(group["stock_position"] > 0, 999.0, 0.0), index=group.index),
        )
        group["y_criticidade_score"] = (
            stock_position_target / group["y_threshold"].replace(0, np.nan)
        ).replace([np.inf, -np.inf], np.nan)
        group["y_criticidade_score"] = group["y_criticidade_score"].where(
            group["y_criticidade_score"].notna(),
            pd.Series(np.where(stock_position_target > 0, 999.0, 0.0), index=group.index),
        )
        group["y_nivel_criticidade"] = pd.cut(
            group["y_criticidade_score"],
            bins=[-np.inf, 0.5, 1.0, 1.5, np.inf],
            labels=["Emergencial", "Critico", "Atencao", "OK"],
        ).astype(str)
        pieces.append(group)

    return pd.concat(pieces, ignore_index=True)


def assign_split(date: pd.Timestamp, split_dates: dict) -> str:
    if pd.Timestamp(split_dates["train_start"]) <= date <= pd.Timestamp(split_dates["train_end"]):
        return "train"
    if pd.Timestamp(split_dates["validation_start"]) <= date <= pd.Timestamp(split_dates["validation_end"]):
        return "validation"
    if pd.Timestamp(split_dates["test_start"]) <= date <= pd.Timestamp(split_dates["test_end"]):
        return "test"
    return "out_of_split"


def build_pedido_event_dataset(orders: pd.DataFrame, abt: pd.DataFrame) -> pd.DataFrame:
    selected_abt_cols = [
        "ingredient_id",
        "date",
        "nome_ingrediente",
        "categoria",
        "unidade",
        "saldo_atual",
        "stock_position",
        "criticidade_score",
        "baseline_threshold",
        "baseline_qtd_comprar",
        "y_threshold",
        "y_qtd_comprar",
        "y_nivel_criticidade",
        "consumo_ingrediente_dia",
        "media_movel_consumo_7d",
        "media_movel_consumo_14d",
        "media_movel_consumo_28d",
        "pedidos_em_aberto",
        "qtd_em_transito",
        "dias_para_proxima_entrega",
        "lead_time_previsto",
        "menor_preco_disponivel",
        "preco_medio_disponivel",
        "menor_lead_time",
        "qtd_fornecedores_disponiveis",
        "is_holiday",
        "is_friday",
        "flag_indisponibilidade",
        "split_temporal",
    ]
    snapshot = abt[selected_abt_cols].copy()
    orders_out = orders.copy()
    orders_out["date"] = orders_out["data_pedido"].dt.normalize()
    event = orders_out.merge(snapshot, on=["ingredient_id", "date"], how="left")
    event = event.rename(
        columns={
            "id": "pedido_id",
            "qty": "qtd_pedida",
            "valor": "valor_pedido",
            "data_prevista": "data_entrega_prevista",
        }
    )
    first_cols = [
        "pedido_id",
        "supplier_id",
        "ingredient_id",
        "nome_ingrediente",
        "qtd_pedida",
        "valor_pedido",
        "data_pedido",
        "data_entrega_prevista",
        "status",
        "order_type",
    ]
    remaining = [col for col in event.columns if col not in first_cols]
    return event[first_cols + remaining].sort_values(["data_pedido", "ingredient_id"]).reset_index(drop=True)


def build_abt(data: dict[str, pd.DataFrame], config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    excluded_category_id = str(config["excluded_purchase_category_id"])
    start_date = pd.Timestamp(config["start_date"]).normalize()
    end_date = pd.Timestamp(config["end_date"]).normalize()
    dates = pd.date_range(start_date, end_date, freq="D")

    ingredientes = data["ingredientes"].copy()
    ingredientes["id"] = ingredientes["id"].astype(str)
    ingredientes["is_compravel"] = (ingredientes["category_id"] != excluded_category_id).astype(int)
    ingredientes["is_produzido_internamente"] = (ingredientes["category_id"] == excluded_category_id).astype(int)
    purchasable = ingredientes[ingredientes["is_compravel"] == 1].copy()
    purchasable_ids = purchasable["id"].tolist()

    recipe_components = build_recipe_expander(
        data["receitas"],
        data["receitas_ingredientes"],
        ingredientes,
        excluded_category_id,
    )
    consumo = build_daily_consumption(data["vendas"], recipe_components, dates, purchasable_ids)
    calendar = build_calendar(dates, data["feriados"])
    supplier_features = build_supplier_features(data["fornecedores"], data["fornecedores_ingredientes"])
    indisponibilidade = build_indisponibilidade_features(
        dates,
        purchasable_ids,
        ingredientes,
        data["receitas"],
        data["indisponiveis"],
        recipe_components,
    )

    base = pd.MultiIndex.from_product([purchasable_ids, dates], names=["ingredient_id", "date"]).to_frame(index=False)
    abt = base.merge(
        purchasable[["id", "name", "unit", "category_id", "is_compravel", "is_produzido_internamente"]],
        left_on="ingredient_id",
        right_on="id",
        how="left",
    ).drop(columns=["id"])
    abt = abt.rename(columns={"name": "nome_ingrediente", "unit": "unidade", "category_id": "categoria_id"})
    categorias = data["categorias"].rename(columns={"id": "categoria_id", "name": "categoria"})
    abt = abt.merge(categorias, on="categoria_id", how="left")
    abt["perfil_perecivel_estimado"] = abt["nome_ingrediente"].apply(classify_profile)
    abt["quantidade_por_unidade_de_compra"] = abt["unidade"].apply(purchase_step)

    estoque = data["estoques"].copy()
    estoque["date"] = estoque["date_time"].dt.normalize()
    estoque = (
        estoque.sort_values("date_time")
        .groupby(["ingredient_id", "date"], as_index=False)["quantity"]
        .last()
        .rename(columns={"quantity": "saldo_atual"})
    )
    abt = abt.merge(estoque, on=["ingredient_id", "date"], how="left")
    abt["saldo_atual"] = abt["saldo_atual"].fillna(0.0)
    abt = abt.merge(consumo, on=["ingredient_id", "date"], how="left")
    abt["consumo_ingrediente_dia"] = abt["consumo_ingrediente_dia"].fillna(0.0)
    abt = abt.merge(calendar, on="date", how="left")
    abt = abt.merge(supplier_features, on="ingredient_id", how="left")
    abt = abt.merge(indisponibilidade, on=["ingredient_id", "date"], how="left")
    abt["flag_indisponibilidade"] = abt["flag_indisponibilidade"].fillna(0).astype(int)
    abt["ingrediente_afetado_por_indisponibilidade"] = abt["ingrediente_afetado_por_indisponibilidade"].fillna(0).astype(int)
    abt["produto_indisponivel_relacionado"] = abt["produto_indisponivel_relacionado"].fillna("")
    abt["dias_em_indisponibilidade"] = abt["dias_em_indisponibilidade"].fillna(0).astype(int)

    orders = add_order_type(data["pedidos"], data["pedidos_log"])
    order_daily = build_order_daily(orders)
    abt = abt.merge(order_daily, on=["ingredient_id", "date"], how="left")
    abt = add_stock_and_demand_features(abt)
    abt = add_historical_order_features(abt)
    abt = add_open_order_features(abt, orders, dates, purchasable_ids, int(config["review_cycle_days"]))
    abt["stock_position"] = abt["saldo_atual"] + abt["qtd_em_transito"]
    abt["lead_time_previsto"] = abt["menor_lead_time"].fillna(1).astype(int)
    abt["dias_de_cobertura"] = (
        abt["saldo_atual"] / abt["media_movel_consumo_14d"].replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan)
    abt["dias_de_cobertura"] = abt["dias_de_cobertura"].where(
        abt["dias_de_cobertura"].notna(),
        pd.Series(np.where(abt["saldo_atual"] > 0, 999.0, 0.0), index=abt.index),
    )
    abt["flag_subestoque"] = (
        abt["stock_position"] < (abt["media_movel_consumo_28d"] * abt["lead_time_previsto"])
    ).astype(int)
    abt["flag_sobrestoque"] = (abt["dias_de_cobertura"] >= 30).astype(int)

    abt = add_targets_and_baseline(abt, config)
    abt["split_temporal"] = abt["date"].apply(lambda d: assign_split(d, config["split_dates"]))
    abt = abt.sort_values(["date", "ingredient_id"]).reset_index(drop=True)
    pedidos_eventos = build_pedido_event_dataset(orders, abt)
    return abt, pedidos_eventos


def write_report(
    abt: pd.DataFrame,
    pedidos_eventos: pd.DataFrame,
    data: dict[str, pd.DataFrame],
    config: dict,
    report_path: Path,
) -> None:
    excluded = config["excluded_purchase_category_id"]
    ingredientes = data["ingredientes"]
    expected_rows = ((pd.Timestamp(config["end_date"]) - pd.Timestamp(config["start_date"])).days + 1) * int(
        (ingredientes["category_id"] != excluded).sum()
    )
    negative_targets = int((abt[["y_qtd_comprar", "y_threshold"]] < 0).sum().sum())
    cat_target_count = int(abt["categoria_id"].eq(excluded).sum())
    taxa_comprar = float(abt["y_comprar"].mean())

    lines = [
        "# Sanity report - ABT Reposicao",
        "",
        "## Arquivos gerados",
        "",
        "- `outputs/abt_reposicao_part1.csv`",
        "- `outputs/abt_reposicao_part2.csv`",
        "- `outputs/abt_pedidos_eventos.csv`",
        "",
        "## Contagens",
        "",
        f"- Linhas ABT: {len(abt):,}",
        f"- Linhas esperadas: {expected_rows:,}",
        f"- Ingredientes na ABT: {abt['ingredient_id'].nunique():,}",
        f"- Ingredientes compraveis esperados: {(ingredientes['category_id'] != excluded).sum():,}",
        f"- Linhas CAT0015 na ABT: {cat_target_count:,}",
        f"- Eventos de pedido: {len(pedidos_eventos):,}",
        "",
        "## Datas",
        "",
        f"- Inicio ABT: {abt['date'].min().date()}",
        f"- Fim ABT: {abt['date'].max().date()}",
        "",
        "## Targets",
        "",
        f"- Taxa y_comprar: {taxa_comprar:.2%}",
        f"- y_qtd_comprar media: {abt['y_qtd_comprar'].mean():.4f}",
        f"- y_qtd_comprar p95: {abt['y_qtd_comprar'].quantile(0.95):.4f}",
        f"- y_threshold medio: {abt['y_threshold'].mean():.4f}",
        f"- Targets negativos: {negative_targets:,}",
        "",
        "## Splits",
        "",
    ]
    for split, count in abt["split_temporal"].value_counts().sort_index().items():
        lines.append(f"- {split}: {int(count):,}")

    lines.extend(
        [
            "",
            "## Validacoes principais",
            "",
            f"- ABT uma linha por ingredient_id x date: {not abt.duplicated(['ingredient_id', 'date']).any()}",
            f"- Todos os ingredientes da ABT sao compraveis: {cat_target_count == 0}",
            f"- Todos os targets sao nao negativos: {negative_targets == 0}",
            f"- Dataset de eventos preserva order_type: {'order_type' in pedidos_eventos.columns}",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    ensure_dirs(args.ml_dir)
    data = read_sources(args.data_dir)
    abt, pedidos_eventos = build_abt(data, config)

    outputs_dir = args.ml_dir / "outputs"
    reports_dir = args.ml_dir / "reports"
    legacy_abt_path = outputs_dir / "abt_reposicao.csv"
    abt_part1_path = outputs_dir / "abt_reposicao_part1.csv"
    abt_part2_path = outputs_dir / "abt_reposicao_part2.csv"
    abt_sample_path = outputs_dir / "abt_reposicao_sample_100.csv"
    pedidos_path = outputs_dir / "abt_pedidos_eventos.csv"
    report_path = reports_dir / "sanity_report.md"

    split_index = len(abt) // 2
    abt.iloc[:split_index].to_csv(abt_part1_path, index=False)
    abt.iloc[split_index:].to_csv(abt_part2_path, index=False)
    abt.sample(n=min(100, len(abt)), random_state=42).sort_values(
        ["date", "ingredient_id"]
    ).to_csv(abt_sample_path, index=False)
    if legacy_abt_path.exists():
        legacy_abt_path.unlink()

    pedidos_eventos.to_csv(pedidos_path, index=False)
    write_report(abt, pedidos_eventos, data, config, report_path)

    print(f"ABT part 1: {abt_part1_path} ({split_index:,} rows)")
    print(f"ABT part 2: {abt_part2_path} ({len(abt) - split_index:,} rows)")
    print(f"ABT sample: {abt_sample_path} ({min(100, len(abt)):,} rows)")
    print(f"Pedidos eventos: {pedidos_path} ({len(pedidos_eventos):,} rows)")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
