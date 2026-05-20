import re
from pathlib import Path

import numpy as np
import pandas as pd


def slugify(text):
    text = str(text).upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "PRODUTO"


def infer_date_column(df):
    for col in df.columns:
        if "data" in str(col).lower():
            return col
    return df.columns[0]


def build_holiday_calendar(path, start_date, end_date):
    holidays_df = pd.read_excel(path, sheet_name=0)
    date_col = infer_date_column(holidays_df)
    holidays_df[date_col] = pd.to_datetime(holidays_df[date_col], errors="coerce")
    holidays_df = holidays_df.dropna(subset=[date_col]).copy()

    holidays_df["month_day"] = holidays_df[date_col].dt.strftime("%m-%d")

    all_days = pd.date_range(start=start_date, end=end_date, freq="D")
    cal = pd.DataFrame({"date": all_days})
    cal["month_day"] = cal["date"].dt.strftime("%m-%d")

    # Replica feriados por dia/mês para cobrir todos os anos do período.
    cal = cal.merge(
        holidays_df[["month_day"]].drop_duplicates().assign(is_holiday=1),
        on="month_day",
        how="left",
    )
    cal["is_holiday"] = cal["is_holiday"].fillna(0).astype(int)

    # Eventos de Recife (além de feriados nacionais):
    # Carnaval (janela mais longa para aumento de fluxo) e Sao Joao.
    cal["is_carnaval"] = 0
    cal["is_sao_joao"] = 0
    cal["is_summer"] = 0

    for year in sorted(cal["date"].dt.year.unique()):
        # Datas aproximadas de Carnaval para sintese de demanda.
        # Segunda e terca de carnaval variam por ano.
        carnival_map = {
            2023: ["2023-02-20", "2023-02-21"],
            2024: ["2024-02-12", "2024-02-13"],
            2025: ["2025-03-03", "2025-03-04"],
            2026: ["2026-02-16", "2026-02-17"],
        }
        if year in carnival_map:
            for d in carnival_map[year]:
                dt = pd.to_datetime(d)
                mask = (cal["date"] >= dt - pd.Timedelta(days=2)) & (
                    cal["date"] <= dt + pd.Timedelta(days=2)
                )
                cal.loc[mask, "is_carnaval"] = 1

        # Sao Joao no Recife: ciclo de junho, com pico ao redor de 23/24.
        sao_joao_start = pd.to_datetime(f"{year}-06-20")
        sao_joao_end = pd.to_datetime(f"{year}-06-25")
        mask_jun = (cal["date"] >= sao_joao_start) & (cal["date"] <= sao_joao_end)
        cal.loc[mask_jun, "is_sao_joao"] = 1

    # Alta de verao no Recife (dezembro a marco).
    cal.loc[cal["date"].dt.month.isin([12, 1, 2, 3]), "is_summer"] = 1

    cal = cal.drop(columns=["month_day"])
    return cal


def build_monthly_targets():
    # Base de 2023 com ancoras obrigatorias fornecidas pelo usuario.
    base_2023 = {
        1: 5900,
        2: 4600,
        3: 5150,
        4: 5000,
        5: 5050,
        6: 5450,
        7: 5200,
        8: 5100,
        9: 5000,
        10: 5150,
        11: 5250,
        12: 4900,
    }

    # Tendencia solicitada:
    # 1) salto alto do 1o para o 2o ano
    # 2) depois ainda cresce, mas em ritmo menor (~10% a.a.)
    # Observacao: 2026 cobre apenas ate marco no periodo final.
    year_factor = {
        2023: 1.00,
        2024: 1.28,      # crescimento forte no 2o ano
        2025: 1.28 * 1.10,
        2026: 1.28 * 1.10 * 1.10,
    }

    targets = {}
    for year in [2023, 2024, 2025, 2026]:
        for month in range(1, 13):
            if year == 2026 and month > 3:
                continue
            value = base_2023[month] * year_factor[year]
            targets[(year, month)] = int(round(value))

    # Garante as ancoras exatas do primeiro ano.
    targets[(2023, 1)] = 5900
    targets[(2023, 2)] = 4600
    targets[(2023, 12)] = 4900
    return targets


def weighted_integer_allocation(total, weights):
    if total <= 0:
        return np.zeros_like(weights, dtype=int)

    w = np.array(weights, dtype=float)
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


def build_daily_demand(calendar_df, monthly_targets, seed=42):
    rng = np.random.default_rng(seed)
    cal = calendar_df.copy()
    cal["year"] = cal["date"].dt.year
    cal["month"] = cal["date"].dt.month
    cal["weekday"] = cal["date"].dt.weekday

    weekday_factor = {
        0: 0.95,
        1: 1.00,
        2: 1.02,
        3: 1.08,
        4: 1.20,
        5: 1.30,
        6: 0.92,
    }

    cal["weight"] = cal["weekday"].map(weekday_factor).astype(float)
    cal["weight"] *= np.where(cal["is_holiday"] == 1, 1.10, 1.00)
    cal["weight"] *= np.where(cal["is_carnaval"] == 1, 1.35, 1.00)
    cal["weight"] *= np.where(cal["is_sao_joao"] == 1, 1.20, 1.00)
    cal["weight"] *= np.where(cal["is_summer"] == 1, 1.08, 1.00)

    # Ruido controlado para nao ficar artificial demais.
    cal["weight"] *= rng.lognormal(mean=0.0, sigma=0.08, size=len(cal))

    cal["pedidos_dia"] = 0

    for (year, month), month_df in cal.groupby(["year", "month"]):
        month_target = monthly_targets.get((year, month), 0)
        alloc = weighted_integer_allocation(month_target, month_df["weight"].values)
        cal.loc[month_df.index, "pedidos_dia"] = alloc

    return cal


def classify_temperature_bias(name):
    text = str(name).upper()
    cold_tokens = [
        "GELADO",
        "SHAKE",
        "SUCO",
        "LIMONADA",
        "SORVETE",
        "ICED",
        "FRAPPE",
        "SMOOTHIE",
    ]
    hot_tokens = [
        "CAFE",
        "CAPPUCCINO",
        "ESPRESSO",
        "CHA",
        "LATTE",
        "MOCHA",
        "CHOCOLATE QUENTE",
    ]

    is_cold = any(t in text for t in cold_tokens)
    is_hot = any(t in text for t in hot_tokens)

    if is_cold and not is_hot:
        return "cold"
    if is_hot and not is_cold:
        return "hot"
    return "neutral"


def build_product_catalog(path):
    df = pd.read_excel(path)
    if "ID_Receita" not in df.columns:
        raise ValueError("Arquivo de receitas sem coluna ID_Receita")

    catalog = df[["ID_Receita", "Receita", "Preco_Venda_Produto"]].copy()
    catalog = catalog.drop_duplicates(subset=["ID_Receita"]).reset_index(drop=True)

    # ID de produto alinhado ao ID da receita para nao vender itens fora do cadastro.
    catalog["id_produto"] = catalog["ID_Receita"].astype(int).astype(str)
    catalog["slug"] = catalog["Receita"].apply(slugify)

    price = pd.to_numeric(catalog["Preco_Venda_Produto"], errors="coerce")
    if price.notna().any():
        median_price = float(price.dropna().median())
    else:
        median_price = 27.99
    catalog["price"] = price.fillna(median_price)

    # Base de preferencia por acessibilidade (substituicao em periodos de alta de preco).
    catalog["base_weight"] = 1 / np.sqrt(np.maximum(catalog["price"], 1.0))
    catalog["temp_bias"] = catalog["Receita"].apply(classify_temperature_bias)

    return catalog


def validate_product_ids(orders_df, catalog_df):
    valid_ids = set(catalog_df["id_produto"].astype(str).unique())
    used_ids = set(orders_df["id_produto"].astype(str).unique())
    invalid = sorted(used_ids - valid_ids)
    if invalid:
        raise ValueError(
            f"Foram encontrados id_produto fora de receitas: {invalid[:10]}"
        )


def sample_hour(rng):
    # Mistura de picos: manha, tarde e inicio da noite.
    block = rng.choice(["morning", "afternoon", "evening"], p=[0.58, 0.30, 0.12])

    if block == "morning":
        hour = int(np.clip(round(rng.normal(8.5, 1.1)), 6, 12))
    elif block == "afternoon":
        hour = int(np.clip(round(rng.normal(15.5, 1.3)), 12, 18))
    else:
        hour = int(np.clip(round(rng.normal(19.0, 0.8)), 17, 22))

    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return hour, minute, second


def generate_orders(daily_df, catalog, seed=42):
    rng = np.random.default_rng(seed)

    rows = []
    order_seq = 1

    base_w = catalog["base_weight"].to_numpy(dtype=float)

    for _, day in daily_df.iterrows():
        n_orders = int(day["pedidos_dia"])
        if n_orders <= 0:
            continue

        month = int(day["month"])
        year = int(day["year"])

        # Ajusta mix por estacao e mudanca de comportamento por preco ao longo dos anos.
        season_w = np.ones(len(catalog), dtype=float)

        # Verao: mais bebidas frias.
        if month in [12, 1, 2, 3]:
            season_w *= np.where(catalog["temp_bias"] == "cold", 1.22, 1.0)
            season_w *= np.where(catalog["temp_bias"] == "hot", 0.93, 1.0)

        # Periodo mais ameno/chuvoso: quentes sobem.
        if month in [6, 7, 8]:
            season_w *= np.where(catalog["temp_bias"] == "hot", 1.12, 1.0)

        # Em anos de pressao de preco, sobe peso de itens mais acessiveis.
        affordability_power = {2023: 0.50, 2024: 0.58, 2025: 0.66, 2026: 0.72}.get(year, 0.60)
        affordability_w = 1 / np.power(np.maximum(catalog["price"].to_numpy(), 1.0), affordability_power)

        w = base_w * season_w * affordability_w
        if np.all(w <= 0):
            w = np.ones(len(catalog), dtype=float)
        w = w / w.sum()

        product_idx = rng.choice(len(catalog), size=n_orders, p=w)
        qty = rng.choice([1, 2, 3], size=n_orders, p=[0.83, 0.14, 0.03])

        date_only = pd.Timestamp(day["date"])

        for i in range(n_orders):
            hour, minute, second = sample_hour(rng)
            dt = date_only + pd.Timedelta(hours=hour, minutes=minute, seconds=second)

            rows.append(
                {
                    "id_pedido": f"PED{order_seq:08d}",
                    "data_hora": dt,
                    "id_produto": catalog.iloc[product_idx[i]]["id_produto"],
                    "quantidade": int(qty[i]),
                }
            )
            order_seq += 1

    orders = pd.DataFrame(rows)
    orders = orders.sort_values("data_hora").reset_index(drop=True)
    return orders


def main():
    base_dir = Path(__file__).resolve().parent

    recipes_path = base_dir / "lista_receitas.xlsx"
    holidays_path = base_dir / "feriados_nacionais.xls"

    out_xlsx = base_dir / "pedidos_sinteticos_2023_2026_mar.xlsx"
    out_csv = base_dir / "pedidos_sinteticos_2023_2026_mar.csv"
    out_daily = base_dir / "resumo_diario_pedidos_2023_2026_mar.xlsx"
    out_month = base_dir / "resumo_mensal_pedidos_2023_2026_mar.xlsx"

    start_date = "2023-01-01"
    end_date = "2026-03-31"

    catalog = build_product_catalog(recipes_path)
    calendar = build_holiday_calendar(holidays_path, start_date, end_date)
    monthly_targets = build_monthly_targets()
    daily = build_daily_demand(calendar, monthly_targets, seed=42)
    orders = generate_orders(daily, catalog, seed=42)
    validate_product_ids(orders, catalog)

    orders.to_excel(out_xlsx, index=False)
    orders.to_csv(out_csv, index=False)

    resumo_diario = daily[["date", "pedidos_dia", "is_holiday", "is_carnaval", "is_sao_joao", "is_summer"]].copy()
    resumo_diario.to_excel(out_daily, index=False)

    resumo_mensal = (
        daily.assign(year=daily["date"].dt.year, month=daily["date"].dt.month)
        .groupby(["year", "month"], as_index=False)["pedidos_dia"]
        .sum()
        .rename(columns={"pedidos_dia": "pedidos_mes"})
    )
    resumo_mensal.to_excel(out_month, index=False)

    print(f"Pedidos gerados: {len(orders)}")
    print(f"Periodo: {orders['data_hora'].min()} ate {orders['data_hora'].max()}")
    print("Arquivos gerados:")
    print(f"- {out_xlsx.name}")
    print(f"- {out_csv.name}")
    print(f"- {out_daily.name}")
    print(f"- {out_month.name}")

    # Validacao das ancoras de 2023.
    anc = resumo_mensal[resumo_mensal["year"] == 2023].set_index("month")["pedidos_mes"].to_dict()
    print("Anchors 2023 -> jan/feb/dez:", anc.get(1), anc.get(2), anc.get(12))


if __name__ == "__main__":
    main()
