"""
Gera vendas sintéticas realistas para a cafeteria Saltim (Boa Viagem, Recife).

Saída principal: data/New/vendas.csv
Colunas: id, date_time, recipe_id, quantity, unit_price
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SEED = 42
START_DATE = "2023-01-01"
END_DATE = "2026-05-19"
OPEN_HOUR = 8
CLOSE_HOUR = 20  # último pedido até 19:59:59
PRICE_FLOOR = 8.0
MAX_PRODUCT_SHARE = 0.12
SATURATION_PENALTY = 0.55

CARNIVAL_TUESDAY = {
    2023: "2023-02-21",
    2024: "2024-02-13",
    2025: "2025-03-04",
    2026: "2026-02-17",
}

YEAR_FACTOR_BASE = {
    2023: 1.00,
    2024: 1.25,
    2025: 1.25 * 0.92,
    2026: 1.25 * 0.92 * 1.12,
}

INFLATION_FACTOR = {
    2023: 1.00,
    2024: 1.07,
    2025: 1.14,
    2026: 1.22,
}

# Base mensal 2023 (+5% vs versão anterior para compensar Poisson)
BASE_2023_MONTHLY = {
    1: int(round(5900 * 1.05)),
    2: int(round(4600 * 1.05)),
    3: int(round(5150 * 1.05)),
    4: int(round(5000 * 1.05)),
    5: int(round(5050 * 1.05)),
    6: int(round(5450 * 1.05)),
    7: int(round(5200 * 1.05)),
    8: int(round(5100 * 1.05)),
    9: int(round(5000 * 1.05)),
    10: int(round(5150 * 1.05)),
    11: int(round(5250 * 1.05)),
    12: int(round(4900 * 1.05)),
}

WEEKDAY_FACTOR = {0: 0.95, 1: 1.00, 2: 1.02, 3: 1.08, 4: 1.20, 5: 1.30, 6: 0.92}

AFFORDABILITY_POWER = {2023: 0.15, 2024: 0.18, 2025: 0.28, 2026: 0.22}

CATEGORY_POPULARITY = {
    "drink_coffee": 2.0,
    "drink_cold": 1.4,
    "breakfast": 1.6,
    "lunch": 1.3,
    "dessert": 1.1,
    "kids": 0.5,
    "other": 1.0,
}

HOURLY_PDF_WEEKDAY = {
    8: 0.025,
    9: 0.045,
    10: 0.060,
    11: 0.085,
    12: 0.155,
    13: 0.165,
    14: 0.115,
    15: 0.045,
    16: 0.075,
    17: 0.085,
    18: 0.045,
    19: 0.100,
}

HOURLY_PDF_WEEKEND = {
    8: 0.030,
    9: 0.110,
    10: 0.150,
    11: 0.135,
    12: 0.105,
    13: 0.090,
    14: 0.060,
    15: 0.045,
    16: 0.060,
    17: 0.060,
    18: 0.060,
    19: 0.095,
}

COLD_TOKENS = ["SHAKE", "SODA", "BOWL", "AÇAÍ", "ACAI", "IOGURTE", "OVERNIGHT", "AFFOGATO"]
HOT_TOKENS = ["ESPRESSO", "CHA", "CHÁ", "CAPPUCCINO", "LATTE", "MOCHA", "AFFOGATO", "TONIC"]
COFFEE_TOKENS = ["ESPRESSO", "AFFOGATO", "CAPPUCCINO", "LATTE", "MOCHA", "TONIC", "CAFÉ", "CAFE"]
KIDS_TOKENS = ["INFANTIL"]
BREAKFAST_TOKENS = [
    "TOAST",
    "RABANADA",
    "PANQUECA",
    "OVERNIGHT",
    "OATS",
    "CUSCUZ",
    "BRIOCHE",
    "CROISSANT",
    "CAFÉ DA MANHÃ",
    "CAFE DA MANHA",
    "GRANOLA",
]
LUNCH_TOKENS = [
    "SUB",
    "KATSU",
    "PF ",
    "LINGUINE",
    "CROQUE",
    "ARROZ",
    "PARMÊ",
    "PARME",
    "EXECUTIVO",
    "BIFUM",
    "COXINHA",
    "TAPIOCA",
    "KLEBINHO",
    "RECIFE É UM OVO",
]
DESSERT_TOKENS = ["BROWNIE", "BLONDIE", "BOLO", "BRIGADEIRO", "CHEESECAKE", "BANNOFFE", "LEMON BAR", "SORVETE"]
DRINK_COLD_TOKENS = ["SHAKE", "SODA", "BOWL", "AÇAÍ", "ACAI", "GINGER", "GREENTEA", "LEMON GRASS", "FRUTAS VERMELHAS"]


def weighted_integer_allocation(total: int, weights: np.ndarray) -> np.ndarray:
    if total <= 0:
        return np.zeros_like(weights, dtype=int)
    w = np.asarray(weights, dtype=float)
    w = np.where(w < 0, 0, w)
    if w.sum() == 0:
        w = np.ones_like(w)
    raw = w / w.sum() * total
    floored = np.floor(raw).astype(int)
    remainder = total - floored.sum()
    if remainder > 0:
        frac = raw - floored
        idx = np.argsort(-frac)[:remainder]
        floored[idx] += 1
    return floored


def _has_token(name: str, tokens: list[str]) -> bool:
    upper = str(name).upper()
    return any(t in upper for t in tokens)


def _normalize_pdf(pdf: dict[int, float]) -> tuple[np.ndarray, np.ndarray]:
    hours = np.array(sorted(pdf.keys()), dtype=int)
    probs = np.array([pdf[h] for h in hours], dtype=float)
    probs = probs / probs.sum()
    return hours, probs


_HOURS_WD, _PROBS_WD = _normalize_pdf(HOURLY_PDF_WEEKDAY)
_HOURS_WE, _PROBS_WE = _normalize_pdf(HOURLY_PDF_WEEKEND)


def inflation_factor(year: int) -> float:
    return INFLATION_FACTOR.get(year, INFLATION_FACTOR[2026])


def classify_product_category(name: str) -> str:
    if _has_token(name, KIDS_TOKENS):
        return "kids"
    if _has_token(name, COFFEE_TOKENS) and not _has_token(name, ["BOWL", "SHAKE", "SODA"]):
        return "drink_coffee"
    if _has_token(name, DRINK_COLD_TOKENS):
        return "drink_cold"
    if _has_token(name, BREAKFAST_TOKENS):
        return "breakfast"
    if _has_token(name, LUNCH_TOKENS):
        return "lunch"
    if _has_token(name, DESSERT_TOKENS):
        return "dessert"
    return "other"


def load_catalog(path: Path, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 200)
    df = pd.read_csv(path)
    catalog = df[df["type"].str.strip().str.upper() == "PRODUTO_FINAL"].copy()
    if catalog.empty:
        raise ValueError("Nenhum PRODUTO_FINAL encontrado em receitas.csv")

    catalog["base_price_raw"] = pd.to_numeric(catalog["sale_price"], errors="coerce")
    median_price = (
        float(catalog["base_price_raw"].dropna().median())
        if catalog["base_price_raw"].notna().any()
        else 25.0
    )
    catalog["base_price_raw"] = catalog["base_price_raw"].fillna(median_price)
    catalog["base_price"] = catalog["base_price_raw"].clip(lower=PRICE_FLOOR)
    catalog["sale_price"] = catalog["base_price"]

    catalog["category"] = catalog["name"].apply(classify_product_category)
    catalog["category_weight"] = catalog["category"].map(CATEGORY_POPULARITY).astype(float)
    catalog["popularity_jitter"] = rng.lognormal(mean=0.0, sigma=0.25, size=len(catalog))

    catalog["is_cold"] = catalog["name"].apply(lambda n: _has_token(n, COLD_TOKENS))
    catalog["is_hot"] = catalog["name"].apply(lambda n: _has_token(n, HOT_TOKENS))
    catalog["is_breakfast"] = catalog["name"].apply(lambda n: _has_token(n, BREAKFAST_TOKENS))
    catalog["is_lunch"] = catalog["name"].apply(lambda n: _has_token(n, LUNCH_TOKENS))
    catalog["is_dessert"] = catalog["name"].apply(lambda n: _has_token(n, DESSERT_TOKENS))
    catalog["is_drink"] = catalog["name"].apply(
        lambda n: _has_token(n, COFFEE_TOKENS) or _has_token(n, DRINK_COLD_TOKENS)
    )

    return catalog.reset_index(drop=True)


def build_year_factors(seed: int) -> dict[int, float]:
    rng = np.random.default_rng(seed + 50)
    factors = {}
    for year, base in YEAR_FACTOR_BASE.items():
        shock = float(rng.lognormal(mean=0.0, sigma=0.04))
        factors[year] = base * shock
    return factors


def holiday_weight_for_row(nome: str, tipo: str) -> float:
    nome_u = str(nome).upper()
    tipo_u = str(tipo).upper()

    if "CARNAVAL" in nome_u or "CINZAS" in nome_u:
        return 1.45
    if "SÃO JOÃO" in nome_u or "SAO JOAO" in nome_u or "SÃO JOAO" in nome_u:
        return 1.30
    if tipo_u in {"NACIONAL", "MUNICIPAL", "ESTADUAL"}:
        return 0.55
    if tipo_u == "FACULTATIVO":
        return 0.85
    return 1.0


def load_holiday_calendar(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de feriados não encontrado: {path}")

    h = pd.read_csv(path)
    h["data"] = pd.to_datetime(h["data"], errors="coerce")
    h = h.dropna(subset=["data"])
    h["peso"] = h.apply(lambda r: holiday_weight_for_row(r["nome"], r["tipo"]), axis=1)

    def pick_weight(group: pd.Series) -> float:
        weights = group.values
        return float(weights[np.argmax(np.abs(weights - 1.0))])

    daily = h.groupby("data")["peso"].apply(pick_weight).reset_index()
    daily.columns = ["date", "holiday_weight"]
    daily["is_holiday"] = 1
    return daily


def build_monthly_targets(end_date: pd.Timestamp, year_factors: dict[int, float]) -> dict[tuple[int, int], int]:
    targets: dict[tuple[int, int], int] = {}
    for year in [2023, 2024, 2025, 2026]:
        factor = year_factors[year]
        for month in range(1, 13):
            if year == 2026 and month > 5:
                continue
            if month not in BASE_2023_MONTHLY:
                continue
            value = int(round(BASE_2023_MONTHLY[month] * factor))
            if year == 2026 and month == 5:
                value = int(round(value * 19 / 31))
            targets[(year, month)] = value
    return targets


def _random_days_in_year(
    rng: np.random.Generator,
    year: int,
    n_days: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> set[pd.Timestamp]:
    year_start = max(pd.Timestamp(f"{year}-01-01"), start)
    year_end = min(pd.Timestamp(f"{year}-12-31"), end)
    if year_start > year_end:
        return set()
    days = pd.date_range(year_start, year_end, freq="D")
    if len(days) == 0:
        return set()
    n_pick = min(n_days, len(days))
    picked = rng.choice(len(days), size=n_pick, replace=False)
    return {pd.Timestamp(days[i]) for i in picked}


def build_daily_calendar(
    start: pd.Timestamp,
    end: pd.Timestamp,
    holidays_df: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    all_days = pd.date_range(start, end, freq="D")
    cal = pd.DataFrame({"date": all_days})
    cal["year"] = cal["date"].dt.year
    cal["month"] = cal["date"].dt.month
    cal["weekday"] = cal["date"].dt.weekday
    cal["is_weekend"] = cal["weekday"].isin([5, 6]).astype(int)
    cal["week_start"] = cal["date"] - pd.to_timedelta(cal["weekday"], unit="D")

    cal = cal.merge(holidays_df, on="date", how="left")
    cal["is_holiday"] = cal["is_holiday"].fillna(0).astype(int)
    cal["holiday_weight"] = cal["holiday_weight"].fillna(1.0)

    cal["is_carnaval_window"] = 0
    for year, tuesday_str in CARNIVAL_TUESDAY.items():
        tuesday = pd.Timestamp(tuesday_str)
        mask = (cal["date"] >= tuesday - pd.Timedelta(days=4)) & (
            cal["date"] <= tuesday + pd.Timedelta(days=2)
        )
        cal.loc[mask, "is_carnaval_window"] = 1

    cal["is_sao_joao"] = (
        (cal["month"] == 6) & (cal["date"].dt.day >= 20) & (cal["date"].dt.day <= 25)
    ).astype(int)

    cal["is_summer"] = cal["month"].isin([12, 1, 2, 3]).astype(int)
    cal["is_school_vacation"] = ((cal["month"] == 1) | (cal["month"] == 7)).astype(int)

    cal["is_payday_window"] = 0
    for dom in [5, 15]:
        mask = (cal["date"].dt.day >= dom - 1) & (cal["date"].dt.day <= dom + 1)
        cal.loc[mask, "is_payday_window"] = 1

    cal["is_promo_day"] = 0
    cal["is_rain_event"] = 0
    cal["is_closure"] = 0

    for year in sorted(cal["year"].unique()):
        promos = _random_days_in_year(rng, year, 18, start, end)
        rains = _random_days_in_year(rng, year, 45, start, end)
        n_closures = int(rng.integers(2, 5))
        closures = _random_days_in_year(rng, year, n_closures, start, end)
        rains -= promos
        rains -= closures

        for d in promos:
            cal.loc[cal["date"] == d, "is_promo_day"] = 1
        for d in rains:
            cal.loc[cal["date"] == d, "is_rain_event"] = 1
        for d in closures:
            cal.loc[cal["date"] == d, "is_closure"] = 1

    return cal


def compute_daily_weights(cal: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = cal.copy()
    out["weight"] = out["weekday"].map(WEEKDAY_FACTOR).astype(float)

    out.loc[out["is_holiday"] == 1, "weight"] *= out.loc[out["is_holiday"] == 1, "holiday_weight"]
    out.loc[out["is_carnaval_window"] == 1, "weight"] *= 1.45
    out.loc[out["is_sao_joao"] == 1, "weight"] *= 1.30
    out.loc[out["is_summer"] == 1, "weight"] *= 1.08
    out.loc[out["is_school_vacation"] == 1, "weight"] *= 1.05
    out.loc[out["is_payday_window"] == 1, "weight"] *= 1.06
    out.loc[out["is_promo_day"] == 1, "weight"] *= 1.20
    out.loc[out["is_rain_event"] == 1, "weight"] *= 0.80
    out.loc[out["is_closure"] == 1, "weight"] = 0.0

    # Ruído empilhado: diário, semanal, mensal
    out["weight"] *= rng.lognormal(mean=0.0, sigma=0.42, size=len(out))

    week_keys = out["week_start"].astype(str)
    week_noise = {k: float(rng.lognormal(0.0, 0.30)) for k in week_keys.unique()}
    out["weight"] *= week_keys.map(week_noise)

    month_keys = list(zip(out["year"], out["month"]))
    month_noise = {k: float(rng.lognormal(0.0, 0.26)) for k in set(month_keys)}
    out["weight"] *= [month_noise[k] for k in month_keys]

    return out


def allocate_daily_sales(
    cal: pd.DataFrame, monthly_targets: dict[tuple[int, int], int], seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    out = cal.copy()
    out["vendas_dia"] = 0

    for (year, month), month_df in out.groupby(["year", "month"]):
        target = monthly_targets.get((int(year), int(month)), 0)
        alloc = weighted_integer_allocation(target, month_df["weight"].values)

        # Re-escala Poisson — sem reajuste exato ao alvo mensal
        lam = np.maximum(alloc.astype(float), 0.0)
        alloc = rng.poisson(lam)

        out.loc[month_df.index, "vendas_dia"] = alloc

    return out


def init_product_drift(n_products: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 99)
    return rng.lognormal(mean=0.0, sigma=0.08, size=n_products)


def update_drift(drift: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    shock = rng.lognormal(mean=0.0, sigma=0.06, size=len(drift))
    updated = drift * shock
    return updated / updated.mean()


def apply_saturation_penalty(
    drift: np.ndarray,
    month_counts: np.ndarray,
    month_total: int,
) -> np.ndarray:
    if month_total <= 0:
        return drift
    shares = month_counts / month_total
    penalty = np.where(shares > MAX_PRODUCT_SHARE, SATURATION_PENALTY, 1.0)
    adjusted = drift * penalty
    return adjusted / adjusted.mean()


def hour_to_block(hour: int) -> str:
    if hour <= 10:
        return "morning"
    if hour <= 14:
        return "lunch"
    if hour <= 17:
        return "afternoon"
    return "evening"


def product_weights_for_day(
    catalog: pd.DataFrame,
    drift: np.ndarray,
    year: int,
    month: int,
    hour_block: str,
) -> np.ndarray:
    w = (
        catalog["category_weight"].to_numpy(dtype=float)
        * catalog["popularity_jitter"].to_numpy(dtype=float)
        * drift
    ).copy()

    if month in [12, 1, 2, 3]:
        w *= np.where(catalog["is_cold"], 1.22, 1.0)
        w *= np.where(catalog["is_hot"], 0.93, 1.0)
    if month in [6, 7, 8]:
        w *= np.where(catalog["is_hot"], 1.10, 1.0)

    aff_power = AFFORDABILITY_POWER.get(year, 0.20)
    prices = catalog["base_price"].to_numpy(dtype=float)
    w *= 1.0 / np.power(np.maximum(prices, PRICE_FLOOR), aff_power)

    if hour_block == "morning":
        w *= np.where(catalog["is_breakfast"] | catalog["is_drink"], 1.25, 1.0)
        w *= np.where(catalog["is_lunch"], 0.85, 1.0)
    elif hour_block == "lunch":
        w *= np.where(catalog["is_lunch"], 1.30, 1.0)
        w *= np.where(catalog["is_dessert"], 0.80, 1.0)
    elif hour_block == "afternoon":
        w *= np.where(catalog["is_dessert"] | catalog["is_drink"], 1.20, 1.0)
    else:
        w *= np.where(catalog["is_lunch"] | catalog["is_dessert"], 1.10, 1.0)

    w = np.where(w <= 0, 1e-9, w)
    return w / w.sum()


def sample_timestamps_batch(
    date_only: pd.Timestamp,
    n: int,
    weekday: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if n == 0:
        return np.array([], dtype="datetime64[ns]")

    if weekday in (5, 6):
        hours, probs = _HOURS_WE, _PROBS_WE
    else:
        hours, probs = _HOURS_WD, _PROBS_WD

    # Jitter diário na distribuição horária
    jittered = probs * rng.lognormal(0.0, 0.07, size=len(probs))
    jittered /= jittered.sum()

    sampled_hours = rng.choice(hours, size=n, p=jittered)
    minutes = rng.integers(0, 60, size=n)
    seconds = rng.integers(0, 60, size=n)

    base = pd.Timestamp(date_only).normalize()
    return np.array(
        [
            base + pd.Timedelta(hours=int(h), minutes=int(m), seconds=int(s))
            for h, m, s in zip(sampled_hours, minutes, seconds)
        ],
        dtype="datetime64[ns]",
    )


def sample_quantities(n: int, rng: np.random.Generator) -> np.ndarray:
    qty = rng.poisson(1.6, size=n) + 1
    return np.clip(qty, 1, 8).astype(int)


def generate_sales(daily_df: pd.DataFrame, catalog: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_products = len(catalog)
    recipe_ids = catalog["id"].values
    base_prices = catalog["base_price"].to_numpy(dtype=float)
    recipe_to_idx = {rid: i for i, rid in enumerate(recipe_ids)}

    drift = init_product_drift(n_products, seed)
    current_month: tuple[int, int] | None = None
    month_counts = np.zeros(n_products, dtype=np.int64)
    month_total = 0

    date_chunks: list[np.ndarray] = []
    recipe_chunks: list[np.ndarray] = []
    qty_chunks: list[np.ndarray] = []
    price_chunks: list[np.ndarray] = []
    year_chunks: list[np.ndarray] = []

    for _, day in daily_df.iterrows():
        n_sales = int(day["vendas_dia"])
        if n_sales <= 0:
            continue

        ym = (int(day["year"]), int(day["month"]))
        if ym != current_month:
            if current_month is not None and month_total > 0:
                drift = apply_saturation_penalty(drift, month_counts, month_total)
            drift = update_drift(drift, rng)
            current_month = ym
            month_counts = np.zeros(n_products, dtype=np.int64)
            month_total = 0

        date_only = pd.Timestamp(day["date"])
        weekday = int(day["weekday"])
        year = int(day["year"])
        month = int(day["month"])
        infl = inflation_factor(year)

        timestamps = sample_timestamps_batch(date_only, n_sales, weekday, rng)
        hours = pd.to_datetime(timestamps).hour
        hour_blocks = np.array([hour_to_block(int(h)) for h in hours])

        products = np.empty(n_sales, dtype=object)
        for block in ("morning", "lunch", "afternoon", "evening"):
            mask = hour_blocks == block
            cnt = int(mask.sum())
            if cnt == 0:
                continue
            w = product_weights_for_day(catalog, drift, year, month, block)
            chosen = rng.choice(recipe_ids, size=cnt, p=w)
            products[mask] = chosen

        quantities = sample_quantities(n_sales, rng)

        idxs = np.array([recipe_to_idx[r] for r in products])
        month_counts[idxs] += 1
        month_total += n_sales

        unit_prices = base_prices[idxs] * infl

        date_chunks.append(timestamps)
        recipe_chunks.append(products)
        qty_chunks.append(quantities)
        price_chunks.append(unit_prices)
        year_chunks.append(np.full(n_sales, year))

    if not date_chunks:
        return pd.DataFrame(columns=["id", "date_time", "recipe_id", "quantity", "unit_price"])

    all_dt = np.concatenate(date_chunks)
    all_recipe = np.concatenate(recipe_chunks)
    all_qty = np.concatenate(qty_chunks)
    all_price = np.concatenate(price_chunks)

    sales = pd.DataFrame(
        {
            "date_time": pd.to_datetime(all_dt),
            "recipe_id": all_recipe,
            "quantity": all_qty.astype(int),
            "unit_price": np.round(all_price, 2),
        }
    )
    sales = sales.sort_values("date_time").reset_index(drop=True)
    sales["id"] = [f"VEN{i:09d}" for i in range(1, len(sales) + 1)]
    return sales[["id", "date_time", "recipe_id", "quantity", "unit_price"]]


def validate_sales(sales: pd.DataFrame, catalog: pd.DataFrame) -> None:
    n = len(sales)
    if not (200_000 <= n <= 300_000):
        raise ValueError(f"Total de vendas fora da faixa 200k-300k: {n}")

    min_dt = sales["date_time"].min()
    max_dt = sales["date_time"].max()
    if min_dt.date() < pd.Timestamp(START_DATE).date():
        raise ValueError(f"Data mínima incorreta: {min_dt}")
    if max_dt.date() > pd.Timestamp(END_DATE).date():
        raise ValueError(f"Data máxima incorreta: {max_dt}")

    hours = sales["date_time"].dt.hour
    if (hours < OPEN_HOUR).any() or (hours >= CLOSE_HOUR).any():
        bad = sales[(hours < OPEN_HOUR) | (hours >= CLOSE_HOUR)].head(3)
        raise ValueError(f"Horários fora de {OPEN_HOUR}h-{CLOSE_HOUR}h:\n{bad}")

    valid_recipes = set(catalog["id"].astype(str))
    used = set(sales["recipe_id"].astype(str))
    invalid = sorted(used - valid_recipes)
    if invalid:
        raise ValueError(f"recipe_id inválidos: {invalid[:5]}")

    if not sales["id"].str.match(r"^VEN\d{9}$").all():
        raise ValueError("Formato de id inválido")

    if sales["id"].duplicated().any():
        raise ValueError("IDs duplicados encontrados")

    qty_mean = float(sales["quantity"].mean())
    if not (2.2 <= qty_mean <= 2.9):
        raise ValueError(f"Média de quantity fora de 2.2-2.9: {qty_mean:.2f}")

    shares = sales["recipe_id"].value_counts(normalize=True)
    max_share = float(shares.iloc[0])
    if max_share > MAX_PRODUCT_SHARE:
        top = shares.index[0]
        raise ValueError(f"Produto {top} com share {max_share:.1%} > {MAX_PRODUCT_SHARE:.0%}")

    if len(shares) >= 2:
        ratio = float(shares.iloc[0] / shares.iloc[1])
        if ratio > 1.8:
            raise ValueError(f"Ratio top1/top2 {ratio:.2f} > 1.8")

    sales_2026 = sales[sales["date_time"].dt.year == 2026]
    if len(sales_2026) > 0:
        # Preço médio unitário do item (com inflação), auditável via unit_price
        ticket_2026 = float(sales_2026["unit_price"].mean())
        if not (24.0 <= ticket_2026 <= 35.0):
            raise ValueError(f"Preço médio unitário 2026 fora de R$24-35: R${ticket_2026:.2f}")


def write_summaries(sales: pd.DataFrame, daily: pd.DataFrame, out_dir: Path) -> None:
    daily_out = daily[
        [
            "date",
            "vendas_dia",
            "is_holiday",
            "is_carnaval_window",
            "is_sao_joao",
            "is_summer",
            "is_promo_day",
            "is_rain_event",
            "is_closure",
        ]
    ].copy()
    daily_out.to_csv(out_dir / "resumo_diario_vendas.csv", index=False)

    sales = sales.copy()
    sales["receita_linha"] = sales["unit_price"] * sales["quantity"]

    monthly = (
        sales.assign(year=sales["date_time"].dt.year, month=sales["date_time"].dt.month)
        .groupby(["year", "month"], as_index=False)
        .agg(
            vendas_mes=("id", "count"),
            unidades_vendidas=("quantity", "sum"),
            receita_total=("receita_linha", "sum"),
        )
    )
    monthly["ticket_medio"] = (monthly["receita_total"] / monthly["unidades_vendidas"]).round(2)
    monthly["receita_por_venda"] = (monthly["receita_total"] / monthly["vendas_mes"]).round(2)
    monthly.to_csv(out_dir / "resumo_mensal_vendas.csv", index=False)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    new_dir = root / "New"

    recipes_path = new_dir / "receitas.csv"
    holidays_path = new_dir / "feriados_recife.csv"
    out_csv = new_dir / "vendas.csv"

    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)

    print("Carregando catálogo e feriados...")
    catalog = load_catalog(recipes_path, seed=SEED)
    holidays = load_holiday_calendar(holidays_path)
    year_factors = build_year_factors(SEED)

    print("Montando calendário e alocando demanda diária...")
    monthly_targets = build_monthly_targets(end, year_factors)
    cal = build_daily_calendar(start, end, holidays, seed=SEED)
    cal = compute_daily_weights(cal, seed=SEED)
    daily = allocate_daily_sales(cal, monthly_targets, seed=SEED)

    print("Gerando vendas (pode levar alguns segundos)...")
    sales = generate_sales(daily, catalog, seed=SEED)

    print("Validando...")
    validate_sales(sales, catalog)

    print(f"Salvando {out_csv}...")
    sales.to_csv(out_csv, index=False)

    print("Gerando resumos...")
    write_summaries(sales, daily, new_dir)

    yearly = sales.assign(year=sales["date_time"].dt.year).groupby("year").agg(
        vendas=("id", "count"),
        ticket_medio=("unit_price", "mean"),
        qty_media=("quantity", "mean"),
    )
    print(f"Vendas geradas: {len(sales):,}")
    print(f"Período: {sales['date_time'].min()} até {sales['date_time'].max()}")
    print(f"Preço médio unitário: R${sales['unit_price'].mean():.2f}")
    print(f"Receita média por linha: R${(sales['unit_price'] * sales['quantity']).mean():.2f}")
    print(f"Quantity média: {sales['quantity'].mean():.2f}")
    top_share = sales["recipe_id"].value_counts(normalize=True).iloc[0]
    print(f"Maior share produto: {top_share:.1%}")
    print(f"Totais por ano:\n{yearly}")
    print("Arquivos:")
    print(f"  - {out_csv}")
    print(f"  - {new_dir / 'resumo_diario_vendas.csv'}")
    print(f"  - {new_dir / 'resumo_mensal_vendas.csv'}")


if __name__ == "__main__":
    main()
