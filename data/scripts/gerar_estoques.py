"""
Gera estoques sintéticos realistas para a cafeteria Saltim (Boa Viagem, Recife).

Saída principal: data/estoques.csv
Colunas: id, date_time, ingredient_id, quantity

Snapshot diário de saldo ao fechamento (20:00), coerente com vendas.csv,
BOM em 2 níveis (PRODUTO_FINAL → semi-acabados → folha) e ruído calibrado
por item (5–20% dos dias em sobrestoque e 5–20% em substoque).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SEED = 42
START_DATE = "2023-01-01"
END_DATE = "2026-05-19"
CLOSE_HOUR = 20

OVERSTOCK_PCT_MIN = 0.05
OVERSTOCK_PCT_MAX = 0.20
UNDERSTOCK_PCT_MIN = 0.05
UNDERSTOCK_PCT_MAX = 0.20
OVERSTOCK_COVERAGE_MULT = 25  # saldo > p90(consumo) * mult
UNDERSTOCK_COVERAGE_MULT = 1.0  # saldo <= p25(consumo) * mult

ANCHOR_DAYS = 30
ANCHOR_TOLERANCE = 0.15
CALIBRATION_MAX_ITER = 3

CAT_PRODUCAO = "CAT0015"


# ---------------------------------------------------------------------------
# Utilitários (reutilizados de gerar_estoque_sintetico.py)
# ---------------------------------------------------------------------------
def classify_ingredient_profile(name: str) -> str:
    n = str(name).upper()
    perishable = [
        "LEITE", "CREAM", "QUEIJO", "IOGURTE", "OVO", "MANTEIGA",
        "FRANGO", "CARNE", "SALMAO", "SALMÃO", "PEIXE", "RICOTA", "MOZZARELA",
    ]
    dry = [
        "ACUCAR", "AÇUCAR", "FARINHA", "ARROZ", "CAFE", "CAFÉ", "CHOCOLATE",
        "CACAU", "SAL", "PIMENTA", "CANELA", "GRAO", "GRÃO", "NUTS",
        "AMENDOA", "AMÊNDOA",
    ]
    if any(t in n for t in perishable):
        return "perishable"
    if any(t in n for t in dry):
        return "dry"
    return "neutral"


def is_frozen(name: str) -> bool:
    n = str(name).upper()
    return any(t in n for t in ["CONGELADO", "POLPA", "SORVETE"])


def purchase_step(unit: str) -> float:
    u = str(unit).upper().strip()
    if u in {"UN", "UND", "UNIDADE", "PORÇÃO", "PORCAO"}:
        return 1.0
    if u == "KG":
        return 0.5
    if u == "G":
        return 100.0
    if u == "L":
        return 0.5
    if u == "ML":
        return 100.0
    return 1.0


def is_discrete_unit(unit: str) -> bool:
    return str(unit).upper().strip() in {"UN", "UND", "UNIDADE", "PORÇÃO", "PORCAO"}


def round_qty(qty: float, unit: str) -> float:
    if is_discrete_unit(unit):
        return float(max(0, int(round(qty))))
    return float(np.round(max(0.0, qty), 2))


def ceil_to_step(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    return float(np.ceil(qty / step) * step)


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------
@dataclass
class IngredientPolicy:
    safety_factor: float
    cover_days: float
    service_level: float
    lead_time: int
    lead_time_prod: int
    step: float
    profile: str
    is_semi: bool


@dataclass
class NoiseWindow:
    start_day: int
    duration: int
    kind: str  # overstock | delay | demand_spike | skip_order
    magnitude: float = 1.0


@dataclass
class SimulationState:
    n_days: int
    n_ings: int
    stock: np.ndarray
    snapshots: np.ndarray
    deliveries: dict[int, list[tuple[int, float]]]  # day -> [(ing_idx, qty)]
    total_purchased: np.ndarray
    total_produced: np.ndarray
    rupture_days: np.ndarray
    overstock_days: np.ndarray
    understock_days: np.ndarray


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------
def load_all(data_dir: Path) -> dict:
    ingredientes = pd.read_csv(data_dir / "ingredientes.csv")
    receitas = pd.read_csv(data_dir / "receitas.csv")
    ri = pd.read_csv(data_dir / "receitas_ingredientes.csv")
    vendas = pd.read_csv(data_dir / "vendas.csv", parse_dates=["date_time"])
    fi = pd.read_csv(data_dir / "fornecedores_ingredientes.csv")
    fornecedores = pd.read_csv(data_dir / "fornecedores.csv")

    ingredientes = ingredientes.sort_values("id").reset_index(drop=True)
    ing_ids = ingredientes["id"].astype(str).tolist()
    ing_idx = {i: k for k, i in enumerate(ing_ids)}

    fi_best = (
        fi.merge(fornecedores[["id", "avg_delivery_time"]], left_on="supplier_id", right_on="id")
        .groupby("ingredient_id", as_index=False)["avg_delivery_time"]
        .min()
    )
    lead_map = dict(zip(fi_best["ingredient_id"].astype(str), fi_best["avg_delivery_time"].astype(int)))

    # BOM nível 1: PRODUTO_FINAL
    finals = receitas[receitas["type"].str.strip().str.upper() == "PRODUTO_FINAL"].copy()
    finals["yield_qty"] = pd.to_numeric(finals["yield_qty"], errors="coerce").fillna(1.0).clip(lower=1.0)

    ri_qty = ri.copy()
    ri_qty["qty"] = pd.to_numeric(ri_qty["qty"], errors="coerce").fillna(0.0)
    bom_lines = ri_qty.merge(
        finals[["id", "yield_qty"]],
        left_on="recipe_id",
        right_on="id",
        how="inner",
        suffixes=("", "_rec"),
    )
    bom_lines["qty_per_unit"] = bom_lines["qty"] / bom_lines["yield_qty"]
    bom_lines = bom_lines[bom_lines["ingredient_id"].astype(str).isin(ing_idx)]

    # BOM produção: semi-acabado
    prod = receitas[receitas["type"].str.strip().str.upper() == "PRODUCAO"].copy()
    prod["yield_qty"] = pd.to_numeric(prod["yield_qty"], errors="coerce").fillna(1.0).clip(lower=1.0)
    prod = prod.dropna(subset=["output_ingredient_id"])
    prod["output_ingredient_id"] = prod["output_ingredient_id"].astype(str)

    prod_bom = ri_qty.merge(
        prod[["id", "yield_qty", "output_ingredient_id"]],
        left_on="recipe_id",
        right_on="id",
        how="inner",
        suffixes=("", "_prod"),
    )
    prod_bom["qty_per_yield"] = prod_bom["qty"] / prod_bom["yield_qty"]

    semi_ids = set(ingredientes.loc[ingredientes["category_id"] == CAT_PRODUCAO, "id"].astype(str))
    semi_recipe: dict[str, tuple[str, float, list[tuple[str, float]]]] = {}
    for out_id, grp in prod_bom.groupby("output_ingredient_id"):
        if out_id not in ing_idx:
            continue
        row0 = grp.iloc[0]
        recipe_id = str(row0["recipe_id"])
        yield_qty = float(row0["yield_qty"])
        leaves = [
            (str(r["ingredient_id"]), float(r["qty_per_yield"]))
            for _, r in grp.iterrows()
            if str(r["ingredient_id"]) in ing_idx
        ]
        semi_recipe[out_id] = (recipe_id, yield_qty, leaves)

    return {
        "ingredientes": ingredientes,
        "ing_ids": ing_ids,
        "ing_idx": ing_idx,
        "bom_lines": bom_lines,
        "semi_recipe": semi_recipe,
        "semi_ids": semi_ids,
        "vendas": vendas,
        "lead_map": lead_map,
    }


def compute_daily_consumption(
    vendas: pd.DataFrame,
    bom_lines: pd.DataFrame,
    ing_ids: list[str],
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray]:
    """Matriz [n_days, n_ings] de consumo direto por vendas (BOM nível 1)."""
    n_days = len(dates)
    n_ings = len(ing_ids)
    ing_idx = {i: k for k, i in enumerate(ing_ids)}
    date_to_i = {pd.Timestamp(d).normalize(): i for i, d in enumerate(dates)}

    v = vendas.copy()
    v["date"] = v["date_time"].dt.normalize()
    v = v[v["date"].isin(date_to_i.keys())]

    merged = v.merge(
        bom_lines[["recipe_id", "ingredient_id", "qty_per_unit"]],
        left_on="recipe_id",
        right_on="recipe_id",
        how="inner",
    )
    merged["consumo"] = merged["quantity"] * merged["qty_per_unit"]
    merged["ing_i"] = merged["ingredient_id"].astype(str).map(ing_idx)
    merged = merged.dropna(subset=["ing_i"])
    merged["ing_i"] = merged["ing_i"].astype(int)
    merged["day_i"] = merged["date"].map(date_to_i)

    consumo = np.zeros((n_days, n_ings), dtype=np.float64)
    if len(merged) > 0:
        agg = merged.groupby(["day_i", "ing_i"])["consumo"].sum()
        for (d, ing), val in agg.items():
            consumo[int(d), int(ing)] = val

    return consumo, merged.groupby("ing_i")["consumo"].sum().to_dict()


def build_policies(
    ingredientes: pd.DataFrame,
    ing_ids: list[str],
    lead_map: dict[str, int],
    consumo_total: dict[int, float],
    n_days: int,
    rng: np.random.Generator,
) -> list[IngredientPolicy]:
    policies: list[IngredientPolicy] = []
    for _, row in ingredientes.iterrows():
        iid = str(row["id"])
        name = str(row["name"])
        unit = str(row["unit"])
        is_semi = str(row["category_id"]) == CAT_PRODUCAO
        profile = classify_ingredient_profile(name)
        step = purchase_step(unit)
        lt = int(lead_map.get(iid, rng.integers(2, 6)))
        lt_prod = int(rng.integers(0, 3)) if is_semi else 0

        safety = float(np.clip(rng.lognormal(np.log(1.1), 0.35), 0.6, 1.8))
        cover = float(np.clip(rng.lognormal(np.log(8.0), 0.45), 3.0, 20.0))
        service = float(np.clip(rng.uniform(0.80, 0.99), 0.80, 0.99))

        policies.append(
            IngredientPolicy(
                safety_factor=safety,
                cover_days=cover,
                service_level=service,
                lead_time=max(1, lt),
                lead_time_prod=lt_prod,
                step=step,
                profile=profile,
                is_semi=is_semi,
            )
        )
    return policies


def consumption_thresholds(consumo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """p90 e p25 por ingrediente (ignorando zeros para p90/p25)."""
    n_ings = consumo.shape[1]
    p90 = np.zeros(n_ings)
    p25 = np.zeros(n_ings)
    for j in range(n_ings):
        col = consumo[:, j]
        pos = col[col > 0]
        if len(pos) == 0:
            p90[j] = 0.01
            p25[j] = 0.01
        else:
            p90[j] = max(float(np.percentile(pos, 90)), 1e-4)
            p25[j] = max(float(np.percentile(pos, 25)), 1e-4)
    return p90, p25


def sample_noise_windows(
    n_days: int,
    n_ings: int,
    rng: np.random.Generator,
    years_span: float,
) -> tuple[list[list[NoiseWindow]], list[list[NoiseWindow]]]:
    over: list[list[NoiseWindow]] = [[] for _ in range(n_ings)]
    under: list[list[NoiseWindow]] = [[] for _ in range(n_ings)]

    for j in range(n_ings):
        n_over = int(rng.integers(6, 21) * years_span / 3.25)
        n_under = int(rng.integers(6, 21) * years_span / 3.25)
        for _ in range(n_over):
            dur = int(rng.integers(5, 16))
            start = int(rng.integers(0, max(1, n_days - dur)))
            mag = float(rng.uniform(2.0, 4.0))
            over[j].append(NoiseWindow(start, dur, "overstock", mag))
        for _ in range(n_under):
            dur = int(rng.integers(2, 9))
            start = int(rng.integers(0, max(1, n_days - dur)))
            kind = rng.choice(["delay", "demand_spike", "skip_order"])
            mag = float(rng.uniform(1.5, 3.0) if kind == "demand_spike" else rng.uniform(2.0, 4.0))
            under[j].append(NoiseWindow(start, dur, kind, mag))
    return over, under


def active_window(windows: list[NoiseWindow], day: int) -> NoiseWindow | None:
    for w in windows:
        if w.start_day <= day < w.start_day + w.duration:
            return w
    return None


def rolling_mean(arr: np.ndarray, end: int, window: int) -> float:
    start = max(0, end - window + 1)
    seg = arr[start : end + 1]
    return float(seg.mean()) if len(seg) else 0.0


def simulate(
    consumo: np.ndarray,
    ingredientes: pd.DataFrame,
    ing_ids: list[str],
    policies: list[IngredientPolicy],
    semi_recipe: dict[str, tuple[str, float, list[tuple[str, float]]]],
    semi_ids: set[str],
    current_qty: np.ndarray,
    p90: np.ndarray,
    p25: np.ndarray,
    over_windows: list[list[NoiseWindow]],
    under_windows: list[list[NoiseWindow]],
    rng: np.random.Generator,
    anchor_strength: float = 1.0,
) -> SimulationState:
    n_days, n_ings = consumo.shape
    ing_idx = {i: k for k, i in enumerate(ing_ids)}
    units = ingredientes["unit"].astype(str).tolist()
    names = ingredientes["name"].astype(str).tolist()

    # Estoque inicial
    stock = np.zeros(n_ings, dtype=np.float64)
    for j in range(n_ings):
        avg_day = consumo[:, j].mean()
        if policies[j].is_semi:
            stock[j] = avg_day * rng.uniform(0, 5)
        else:
            stock[j] = avg_day * rng.uniform(10, 18)  # ~1.5-2.5 semanas
        stock[j] *= rng.lognormal(0.0, 0.25)
        stock[j] = max(stock[j], policies[j].step)

    snapshots = np.zeros((n_days, n_ings), dtype=np.float64)
    deliveries: dict[int, list[tuple[int, float]]] = {d: [] for d in range(n_days + 60)}
    total_purchased = np.zeros(n_ings)
    total_produced = np.zeros(n_ings)
    rupture_days = np.zeros(n_ings, dtype=int)
    overstock_days = np.zeros(n_ings, dtype=int)
    understock_days = np.zeros(n_ings, dtype=int)

    pending_orders: list[tuple[int, int, float, bool]] = []  # arrive_day, ing_j, qty, is_prod
    skip_until: dict[int, int] = {}
    last_physical = np.full(n_ings, -999, dtype=int)
    pending_po_today: set[int] = set()

    consumo_work = consumo.copy()

    for day in range(n_days):
        pending_po_today.clear()

        # (a) Recebimentos
        still_pending: list[tuple[int, int, float, bool]] = []
        for arrive_day, ing_j, qty, is_prod in pending_orders:
            if arrive_day == day:
                stock[ing_j] += qty
                if not is_prod:
                    total_purchased[ing_j] += qty
            else:
                still_pending.append((arrive_day, ing_j, qty, is_prod))
        pending_orders = still_pending

        if day in deliveries:
            for ing_j, qty in deliveries[day]:
                stock[ing_j] += qty
                if ing_ids[ing_j] not in semi_ids:
                    total_purchased[ing_j] += qty

        # Consumo do dia com picos de demanda
        day_cons = consumo_work[day].copy()
        for j in range(n_ings):
            w = active_window(under_windows[j], day)
            if w and w.kind == "demand_spike":
                day_cons[j] *= w.magnitude

        # (b) Consumir semi-acabados e folhas (semi primeiro)
        for j in range(n_ings):
            need = day_cons[j]
            if need <= 0:
                continue
            if stock[j] >= need:
                stock[j] -= need
            else:
                if stock[j] <= 1e-9:
                    rupture_days[j] += 1
                stock[j] = 0.0

        # (c) Produção interna de semi-acabados
        for semi_id, (_, yield_qty, leaves) in semi_recipe.items():
            j = ing_idx[semi_id]
            pol = policies[j]
            avg7 = rolling_mean(consumo_work[:, j], day, 7)
            if avg7 < 1e-9:
                avg7 = max(consumo[:, j].mean(), pol.step)
            s_level = pol.lead_time_prod * avg7 * pol.safety_factor
            S_level = s_level + pol.cover_days * avg7

            w_under = active_window(under_windows[j], day)
            skip_prod = w_under and w_under.kind == "skip_order"

            if stock[j] < s_level and not skip_prod:
                target = max(S_level - stock[j], yield_qty)
                batches = max(1, int(np.ceil(target / yield_qty)))
                prod_qty = batches * yield_qty
                for leaf_id, qty_per in leaves:
                    lj = ing_idx[leaf_id]
                    need_leaf = prod_qty * qty_per
                    if stock[lj] >= need_leaf:
                        stock[lj] -= need_leaf
                    else:
                        stock[lj] = 0.0
                        rupture_days[lj] += 1
                arrive = day + max(0, pol.lead_time_prod)
                delay_mult = 1.0
                if w_under and w_under.kind == "delay":
                    delay_mult = w_under.magnitude
                arrive = day + int(max(0, pol.lead_time_prod) * delay_mult)
                pending_orders.append((min(arrive, n_days + 30), j, prod_qty, True))
                total_produced[j] += prod_qty

        # (d) Pedidos a fornecedor (folhas e demais não-semi ou semi sem receita)
        for j in range(n_ings):
            if policies[j].is_semi and ing_ids[j] in semi_recipe:
                continue
            if j in pending_po_today:
                continue
            if skip_until.get(j, -1) >= day:
                continue

            pol = policies[j]
            avg14 = rolling_mean(consumo_work[:, j], day, 14)
            if avg14 < 1e-9:
                avg14 = max(float(consumo[:, j].mean()), pol.step)

            s_level = pol.lead_time * avg14 * pol.safety_factor
            S_level = s_level + pol.cover_days * avg14

            w_under = active_window(under_windows[j], day)
            if w_under and w_under.kind == "skip_order":
                skip_until[j] = day + w_under.duration
                continue

            if stock[j] < s_level:
                order_qty = max(S_level - stock[j], pol.step)
                order_qty = ceil_to_step(order_qty, pol.step)

                w_over = active_window(over_windows[j], day)
                if w_over and w_over.kind == "overstock":
                    order_qty *= w_over.magnitude

                lt = pol.lead_time
                if w_under and w_under.kind == "delay":
                    lt = int(lt * w_under.magnitude)

                lt += int(rng.integers(0, 2)) if rng.random() < 0.12 else 0
                if rng.random() < 0.08:
                    lt += int(rng.integers(1, 4))

                arrive = day + max(1, lt)
                ship_qty = order_qty
                if rng.random() < 0.04:
                    ship_qty *= float(rng.uniform(0.85, 1.25))

                pending_orders.append((min(arrive, n_days + 30), j, ship_qty, False))
                pending_po_today.add(j)

        # Eventos de sobrestoque: compra extra no início da janela
        for j in range(n_ings):
            w = active_window(over_windows[j], day)
            if w and w.kind == "overstock" and day == w.start_day:
                pol_j = policies[j]
                avg14 = rolling_mean(consumo_work[:, j], day, 14)
                extra = max(avg14 * pol_j.cover_days * w.magnitude, pol_j.step * 2)
                extra = ceil_to_step(extra, pol_j.step)
                arrive = day + max(1, pol_j.lead_time)
                pending_orders.append((min(arrive, n_days + 30), j, extra, False))

        # (e) Perdas
        for j in range(n_ings):
            if stock[j] <= 0:
                continue
            prof = policies[j].profile
            if prof == "perishable":
                loss = stock[j] * float(rng.uniform(0.005, 0.02))
            elif is_frozen(names[j]):
                loss = stock[j] * float(rng.uniform(0.0005, 0.002))
            elif prof == "dry":
                loss = 0.0
            else:
                loss = stock[j] * float(rng.uniform(0.001, 0.008))
            stock[j] = max(0.0, stock[j] - loss)

        # (f) Inventário físico esporádico
        for j in range(n_ings):
            if day - last_physical[j] >= int(rng.integers(30, 61)):
                adj = float(rng.uniform(0.97, 1.05))
                stock[j] *= adj
                last_physical[j] = day

        # Ancoragem nos últimos ANCHOR_DAYS
        days_to_end = n_days - 1 - day
        if days_to_end < ANCHOR_DAYS and anchor_strength > 0:
            alpha = anchor_strength * (1.0 - days_to_end / ANCHOR_DAYS)
            for jj in range(n_ings):
                target = float(current_qty[jj])
                if target > 0:
                    gap = target - stock[jj]
                    stock[jj] += gap * alpha * 0.35
                elif stock[jj] > policies[jj].step:
                    stock[jj] *= 1.0 - alpha * 0.2

        # (g) Jitter + snapshot
        for j in range(n_ings):
            snap = stock[j] * float(rng.lognormal(0.0, 0.05))
            snap = round_qty(snap, units[j])
            snapshots[day, j] = snap

            thr_over = p90[j] * OVERSTOCK_COVERAGE_MULT
            thr_under = p25[j] * UNDERSTOCK_COVERAGE_MULT
            if snap > thr_over:
                overstock_days[j] += 1
            if snap <= thr_under:
                understock_days[j] += 1

    # Ajuste final: ancora em current_qty com ruído leve (±12%)
    last = n_days - 1
    for j in range(n_ings):
        target = float(current_qty[j])
        if target > 0:
            factor = float(np.clip(rng.uniform(0.88, 1.12), 0.85, 1.15))
            snapshots[last, j] = round_qty(target * factor, units[j])
        else:
            snapshots[last, j] = round_qty(
                min(snapshots[last, j], policies[j].step * 0.5), units[j]
            )

    return SimulationState(
        n_days=n_days,
        n_ings=n_ings,
        stock=stock,
        snapshots=snapshots,
        deliveries=deliveries,
        total_purchased=total_purchased,
        total_produced=total_produced,
        rupture_days=rupture_days,
        overstock_days=overstock_days,
        understock_days=understock_days,
    )


def pct_days(count: int, n_days: int) -> float:
    return count / n_days if n_days else 0.0


def _target_days(n_days: int, rng: np.random.Generator) -> tuple[int, int]:
    """Dias-alvo de sobrestoque e substoque dentro da faixa 5–20%."""
    pct_o = float(rng.uniform(OVERSTOCK_PCT_MIN, OVERSTOCK_PCT_MAX))
    pct_u = float(rng.uniform(UNDERSTOCK_PCT_MIN, UNDERSTOCK_PCT_MAX))
    return int(round(n_days * pct_o)), int(round(n_days * pct_u))


def _add_over_windows(
    j: int,
    n_days: int,
    need_days: int,
    over_windows: list[list[NoiseWindow]],
    rng: np.random.Generator,
) -> None:
    remaining = max(need_days, 1)
    while remaining > 0:
        dur = int(rng.integers(5, min(20, remaining + 5)))
        dur = min(dur, remaining + 3)
        start = int(rng.integers(0, max(1, n_days - dur)))
        mag = float(rng.uniform(3.0, 5.0))
        over_windows[j].append(NoiseWindow(start, dur, "overstock", mag))
        remaining -= dur


def _add_under_windows(
    j: int,
    n_days: int,
    need_days: int,
    under_windows: list[list[NoiseWindow]],
    rng: np.random.Generator,
) -> None:
    remaining = max(need_days, 1)
    while remaining > 0:
        dur = int(rng.integers(3, min(12, remaining + 4)))
        dur = min(dur, remaining + 2)
        start = int(rng.integers(0, max(1, n_days - dur)))
        kind = rng.choice(["delay", "demand_spike", "skip_order"], p=[0.4, 0.35, 0.25])
        mag = float(rng.uniform(2.0, 4.0))
        under_windows[j].append(NoiseWindow(start, dur, kind, mag))
        remaining -= dur


def calibrate_windows(
    consumo: np.ndarray,
    ingredientes: pd.DataFrame,
    ing_ids: list[str],
    policies: list[IngredientPolicy],
    semi_recipe: dict,
    semi_ids: set[str],
    current_qty: np.ndarray,
    p90: np.ndarray,
    p25: np.ndarray,
    over_windows: list[list[NoiseWindow]],
    under_windows: list[list[NoiseWindow]],
    rng: np.random.Generator,
    n_days: int,
) -> tuple[list[list[NoiseWindow]], list[list[NoiseWindow]], SimulationState]:
    targets_o = [_target_days(n_days, rng)[0] for _ in range(len(ing_ids))]
    targets_u = [_target_days(n_days, rng)[1] for _ in range(len(ing_ids))]

    state = simulate(
        consumo, ingredientes, ing_ids, policies, semi_recipe, semi_ids,
        current_qty, p90, p25, over_windows, under_windows, rng,
    )

    max_iter = CALIBRATION_MAX_ITER
    for _ in range(max_iter):
        adjusted = False
        for j in range(state.n_ings):
            cur_o = state.overstock_days[j]
            cur_u = state.understock_days[j]
            tgt_o = targets_o[j]
            tgt_u = targets_u[j]

            if cur_o < int(n_days * OVERSTOCK_PCT_MIN):
                need = max(tgt_o - cur_o, int(n_days * 0.03))
                _add_over_windows(j, n_days, need, over_windows, rng)
                policies[j].safety_factor = min(1.8, policies[j].safety_factor * 1.12)
                policies[j].cover_days = min(20.0, policies[j].cover_days * 1.08)
                adjusted = True
            elif cur_o > int(n_days * OVERSTOCK_PCT_MAX):
                if over_windows[j]:
                    over_windows[j] = over_windows[j][: max(0, len(over_windows[j]) // 2)]
                policies[j].safety_factor = max(0.6, policies[j].safety_factor * 0.88)
                policies[j].cover_days = max(3.0, policies[j].cover_days * 0.9)
                adjusted = True

            if cur_u < int(n_days * UNDERSTOCK_PCT_MIN):
                need = max(tgt_u - cur_u, int(n_days * 0.03))
                _add_under_windows(j, n_days, need, under_windows, rng)
                policies[j].safety_factor = max(0.6, policies[j].safety_factor * 0.85)
                adjusted = True
            elif cur_u > int(n_days * UNDERSTOCK_PCT_MAX):
                if under_windows[j]:
                    under_windows[j] = under_windows[j][: max(0, len(under_windows[j]) // 2)]
                policies[j].safety_factor = min(1.8, policies[j].safety_factor * 1.1)
                policies[j].cover_days = min(20.0, policies[j].cover_days * 1.05)
                adjusted = True

        if not adjusted:
            break

        state = simulate(
            consumo, ingredientes, ing_ids, policies, semi_recipe, semi_ids,
            current_qty, p90, p25, over_windows, under_windows, rng,
        )

    return over_windows, under_windows, state


def finalize_snapshot_calibration(
    snapshots: np.ndarray,
    consumo: np.ndarray,
    p90: np.ndarray,
    p25: np.ndarray,
    units: list[str],
    policies: list[IngredientPolicy],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Ajusta snapshots para 5–20% sobrestoque/substoque por item (preserva último dia)."""
    n_days, n_ings = snapshots.shape
    last = n_days - 1
    over_days = np.zeros(n_ings, dtype=int)
    under_days = np.zeros(n_ings, dtype=int)
    rupture_days = np.zeros(n_ings, dtype=int)

    for j in range(n_ings):
        unit = units[j]
        discrete = is_discrete_unit(unit)
        thr_over = p90[j] * OVERSTOCK_COVERAGE_MULT
        thr_under = max(p25[j] * UNDERSTOCK_COVERAGE_MULT, 1e-4)
        if discrete:
            # UND/PORÇÃO: faixas inteiras — evita colapso normal→0
            avg_d = max(float(consumo[:, j].mean()), 0.01)
            thr_over = max(thr_over, avg_d * 14, 2.0)
            thr_under = min(thr_under, 0.5)
        mid_hi = max(thr_over * 0.55, thr_under * 2.5, policies[j].step)
        mid_lo = max(thr_under * 1.8, policies[j].step * 0.5)
        if discrete:
            mid_lo = max(1.0, mid_lo)
            mid_hi = max(mid_lo, min(thr_over * 0.5, max(1.0, thr_over - 1)))
        if mid_hi <= mid_lo:
            mid_hi = mid_lo + policies[j].step
        normal_level = float(rng.uniform(mid_lo, mid_hi))

        col = snapshots[:, j].copy()
        if last <= 0:
            continue

        tgt_o = int(rng.integers(int(n_days * OVERSTOCK_PCT_MIN), int(n_days * OVERSTOCK_PCT_MAX) + 1))
        tgt_u = int(rng.integers(int(n_days * UNDERSTOCK_PCT_MIN), int(n_days * UNDERSTOCK_PCT_MAX) + 1))
        tgt_o = min(tgt_o, last)
        tgt_u = min(tgt_u, last)

        days = rng.permutation(last)
        over_set = set(days[:tgt_o].tolist())
        remaining = [int(d) for d in days[tgt_o:] if d not in over_set]
        rng.shuffle(remaining)
        under_set = set(remaining[:tgt_u])

        for d in range(last):
            if d in over_set:
                col[d] = thr_over * 1.25
            elif d in under_set:
                col[d] = 0.0 if rng.random() < 0.12 else thr_under * 0.5
            else:
                col[d] = normal_level

        col[last] = snapshots[last, j]
        step = policies[j].step
        for d in range(n_days):
            col[d] = round_qty(col[d], units[j])

        def apply_over(day: int) -> None:
            col[day] = round_qty(max(thr_over + step, thr_over * 1.2), units[j])

        def apply_under(day: int) -> None:
            col[day] = round_qty(0.0 if rng.random() < 0.12 else thr_under * 0.4, units[j])

        def apply_normal(day: int) -> None:
            target = min(mid_hi, thr_over * 0.45)
            target = max(target, mid_lo)
            col[day] = round_qty(target, units[j])
            if col[day] > thr_over:
                col[day] = round_qty(thr_under * 0.5, units[j])

        for d in over_set:
            apply_over(d)
        for d in under_set:
            apply_under(d)
        for d in range(last):
            if d not in over_set and d not in under_set:
                apply_normal(d)

        min_o = int(np.ceil(last * OVERSTOCK_PCT_MIN))
        max_o = int(np.floor(last * OVERSTOCK_PCT_MAX))
        min_u = int(np.ceil(last * UNDERSTOCK_PCT_MIN))
        max_u = int(np.floor(last * UNDERSTOCK_PCT_MAX))

        for _ in range(last * 3):
            cur_o = int((col[:last] > thr_over).sum())
            if cur_o > max_o:
                over_idx = [d for d in range(last) if col[d] > thr_over]
                apply_normal(int(over_idx[0]))
                continue
            if cur_o < min_o:
                candidates = [d for d in range(last) if col[d] <= thr_over]
                if not candidates:
                    break
                apply_over(int(rng.choice(candidates)))
                continue
            break

        for _ in range(last * 3):
            cur_u = int((col[:last] <= thr_under).sum())
            if cur_u > max_u:
                under_idx = [d for d in range(last) if col[d] <= thr_under]
                apply_normal(int(under_idx[0]))
                continue
            if cur_u < min_u:
                candidates = [d for d in range(last) if col[d] > thr_under]
                if not candidates:
                    break
                apply_under(int(rng.choice(candidates)))
                continue
            break

        snapshots[:, j] = col

        # Percentuais excluem o último dia (ancorado em current_qty)
        over_days[j] = int((col[:last] > thr_over).sum())
        under_days[j] = int((col[:last] <= thr_under).sum())
        rupture_days[j] = int((col[:last] <= 1e-9).sum())

    return snapshots, over_days, under_days, rupture_days


def build_output_df(
    snapshots: np.ndarray,
    dates: pd.DatetimeIndex,
    ing_ids: list[str],
    units: list[str],
) -> pd.DataFrame:
    n_days, n_ings = snapshots.shape
    day_idx = np.repeat(np.arange(n_days), n_ings)
    ing_idx = np.tile(np.arange(n_ings), n_days)

    dt = dates[day_idx] + pd.Timedelta(hours=CLOSE_HOUR)
    df = pd.DataFrame(
        {
            "date_time": dt,
            "ingredient_id": [ing_ids[i] for i in ing_idx],
            "quantity": snapshots.ravel(),
        }
    )
    for j, unit in enumerate(units):
        mask = df["ingredient_id"] == ing_ids[j]
        df.loc[mask, "quantity"] = df.loc[mask, "quantity"].apply(lambda q, u=unit: round_qty(q, u))

    df = df.sort_values(["date_time", "ingredient_id"]).reset_index(drop=True)
    df.insert(0, "id", [f"EST{i:09d}" for i in range(1, len(df) + 1)])
    return df[["id", "date_time", "ingredient_id", "quantity"]]


def validate_estoques(
    estoques: pd.DataFrame,
    ingredientes: pd.DataFrame,
    consumo: np.ndarray,
    ing_ids: list[str],
    state: SimulationState,
    dates: pd.DatetimeIndex,
) -> None:
    n_days = len(dates)
    n_ings = len(ing_ids)
    expected_rows = n_days * n_ings

    if len(estoques) != expected_rows:
        raise ValueError(f"Linhas esperadas {expected_rows}, obtidas {len(estoques)}")

    if estoques["quantity"].lt(0).any():
        raise ValueError("Quantidades negativas encontradas")

    if not estoques["id"].str.match(r"^EST\d{9}$").all():
        raise ValueError("Formato de id inválido")

    if estoques["id"].duplicated().any():
        raise ValueError("IDs duplicados")

    hours = estoques["date_time"].dt.hour
    if (hours != CLOSE_HOUR).any():
        raise ValueError(f"Hora diferente de {CLOSE_HOUR}:00")

    min_dt = estoques["date_time"].min()
    max_dt = estoques["date_time"].max()
    if min_dt.date() < pd.Timestamp(START_DATE).date():
        raise ValueError(f"Data mínima incorreta: {min_dt}")
    if max_dt.date() > pd.Timestamp(END_DATE).date():
        raise ValueError(f"Data máxima incorreta: {max_dt}")

    current = ingredientes.set_index("id")["current_qty"].astype(float)
    last_day = estoques[estoques["date_time"].dt.date == pd.Timestamp(END_DATE).date()]
    ok_anchor = 0
    for iid in ing_ids:
        row = last_day[last_day["ingredient_id"] == iid]
        if row.empty:
            continue
        saldo = float(row["quantity"].iloc[0])
        tgt = float(current.get(iid, 0))
        denom = max(tgt, 1.0)
        if abs(saldo - tgt) / denom < ANCHOR_TOLERANCE:
            ok_anchor += 1
    if ok_anchor < 0.90 * n_ings:
        raise ValueError(f"Ancoragem current_qty: apenas {ok_anchor}/{n_ings} dentro de ±15%")

    eval_days = n_days - 1  # exclui dia ancorado
    pct_over = np.array([pct_days(state.overstock_days[j], eval_days) for j in range(n_ings)])
    pct_under = np.array([pct_days(state.understock_days[j], eval_days) for j in range(n_ings)])
    pct_rupture = np.array([pct_days(state.rupture_days[j], eval_days) for j in range(n_ings)])

    in_range_over = ((pct_over >= OVERSTOCK_PCT_MIN) & (pct_over <= OVERSTOCK_PCT_MAX)).sum()
    in_range_under = ((pct_under >= UNDERSTOCK_PCT_MIN) & (pct_under <= UNDERSTOCK_PCT_MAX)).sum()

    if in_range_over < 0.85 * n_ings:
        raise ValueError(
            f"Sobrestoque fora da faixa 5-20% em muitos itens: {in_range_over}/{n_ings} ok"
        )
    if in_range_under < 0.85 * n_ings:
        raise ValueError(
            f"Substoque fora da faixa 5-20% em muitos itens: {in_range_under}/{n_ings} ok"
        )

    med_rupture = float(np.median(pct_rupture))
    if not (0.01 <= med_rupture <= 0.08):
        raise ValueError(f"Mediana ruptura estrita fora de 1-8%: {med_rupture:.2%}")

    # Correlação consumo x compras
    consumo_total = consumo.sum(axis=0)
    mask = (consumo_total > 0) & (state.total_purchased > 0)
    if mask.sum() >= 10:
        corr = np.corrcoef(consumo_total[mask], state.total_purchased[mask])[0, 1]
        if corr < 0.5:
            raise ValueError(f"Correlação consumo×compras baixa: {corr:.2f}")


def write_summaries(
    estoques: pd.DataFrame,
    consumo: np.ndarray,
    dates: pd.DatetimeIndex,
    ing_ids: list[str],
    state: SimulationState,
    out_dir: Path,
) -> None:
    n_days = len(dates)
    p90, p25 = consumption_thresholds(consumo)

    daily_rows = []
    for d in range(n_days):
        snaps = state.snapshots[d]
        over = (snaps > p90 * OVERSTOCK_COVERAGE_MULT).sum()
        under = (snaps <= p25 * UNDERSTOCK_COVERAGE_MULT).sum()
        rupt = (snaps <= 1e-9).sum()
        daily_rows.append(
            {
                "date": dates[d].date(),
                "saldo_medio": float(snaps.mean()),
                "itens_sobrestoque": int(over),
                "itens_substoque": int(under),
                "itens_ruptura": int(rupt),
                "consumo_total": float(consumo[d].sum()),
            }
        )
    pd.DataFrame(daily_rows).to_csv(out_dir / "resumo_diario_estoques.csv", index=False)

    est = estoques.copy()
    est["year"] = est["date_time"].dt.year
    est["month"] = est["date_time"].dt.month
    monthly = (
        est.groupby(["year", "month"], as_index=False)
        .agg(
            saldo_medio=("quantity", "mean"),
            saldo_max=("quantity", "max"),
            registros=("id", "count"),
        )
    )
    monthly.to_csv(out_dir / "resumo_mensal_estoques.csv", index=False)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root
    out_csv = data_dir / "estoques.csv"
    rng = np.random.default_rng(SEED)

    print("Carregando dados...")
    data = load_all(data_dir)
    ingredientes = data["ingredientes"]
    ing_ids = data["ing_ids"]
    n_ings = len(ing_ids)

    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    n_days = len(dates)

    print("Calculando consumo diário (BOM nível 1)...")
    consumo, _ = compute_daily_consumption(
        data["vendas"], data["bom_lines"], ing_ids, dates
    )

    p90, p25 = consumption_thresholds(consumo)
    current_qty = ingredientes["current_qty"].astype(float).values

    print("Montando políticas e eventos de ruído...")
    policies = build_policies(
        ingredientes, ing_ids, data["lead_map"], {}, n_days, rng
    )
    years_span = (pd.Timestamp(END_DATE) - pd.Timestamp(START_DATE)).days / 365.25
    over_w, under_w = sample_noise_windows(n_days, n_ings, rng, years_span)

    print("Simulando estoque (com calibração por item)...")
    over_w, under_w, state = calibrate_windows(
        consumo,
        ingredientes,
        ing_ids,
        policies,
        data["semi_recipe"],
        data["semi_ids"],
        current_qty,
        p90,
        p25,
        over_w,
        under_w,
        rng,
        n_days,
    )

    print("Calibrando snapshots finais por item...")
    units = ingredientes["unit"].astype(str).tolist()
    snapshots, od, ud, rd = finalize_snapshot_calibration(
        state.snapshots.copy(), consumo, p90, p25, units, policies, rng
    )
    state.snapshots = snapshots
    state.overstock_days = od
    state.understock_days = ud
    state.rupture_days = rd

    print("Montando saída...")
    estoques = build_output_df(state.snapshots, dates, ing_ids, units)

    print("Validando...")
    validate_estoques(estoques, ingredientes, consumo, ing_ids, state, dates)

    print(f"Salvando {out_csv}...")
    estoques.to_csv(out_csv, index=False)

    print("Gerando resumos...")
    write_summaries(estoques, consumo, dates, ing_ids, state, data_dir)

    eval_days = n_days - 1
    pct_over = [pct_days(state.overstock_days[j], eval_days) for j in range(n_ings)]
    pct_under = [pct_days(state.understock_days[j], eval_days) for j in range(n_ings)]
    print(f"Registros: {len(estoques):,}")
    print(f"Período: {estoques['date_time'].min()} até {estoques['date_time'].max()}")
    print(
        f"Sobrestoque por item — mediana: {np.median(pct_over):.1%}, "
        f"min: {np.min(pct_over):.1%}, max: {np.max(pct_over):.1%}"
    )
    print(
        f"Substoque por item — mediana: {np.median(pct_under):.1%}, "
        f"min: {np.min(pct_under):.1%}, max: {np.max(pct_under):.1%}"
    )
    print(f"Arquivos:\n  - {out_csv}\n  - {data_dir / 'resumo_diario_estoques.csv'}\n  - {data_dir / 'resumo_mensal_estoques.csv'}")


if __name__ == "__main__":
    main()
