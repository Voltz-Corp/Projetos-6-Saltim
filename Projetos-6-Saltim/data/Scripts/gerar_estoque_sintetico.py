from pathlib import Path

import numpy as np
import pandas as pd


def shelf_life_days(ingredient_name, unit, rng):
    name = str(ingredient_name).upper()
    unit = str(unit).upper()

    perishable_tokens = [
        "LEITE",
        "CREAM",
        "QUEIJO",
        "IOGURTE",
        "OVO",
        "MANTEIGA",
        "FRANGO",
        "CARNE",
        "SALMAO",
        "PEIXE",
        "RICOTA",
        "MOZZARELA",
        "CREME",
    ]
    dry_tokens = [
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
    frozen_tokens = ["CONGELADO", "POLPA", "SORVETE"]

    if any(t in name for t in frozen_tokens):
        return int(rng.integers(120, 240))

    if any(t in name for t in perishable_tokens):
        # Pereciveis: cerca de 7 a 25 dias.
        return int(rng.integers(7, 26))

    if any(t in name for t in dry_tokens):
        # Secos: validade longa.
        return int(rng.integers(120, 361))

    if unit in {"KG", "G", "L", "ML"}:
        return int(rng.integers(30, 181))

    return int(rng.integers(20, 121))


def classify_ingredient_profile(ingredient_name):
    name = str(ingredient_name).upper()

    perishable_tokens = [
        "LEITE",
        "CREAM",
        "QUEIJO",
        "IOGURTE",
        "OVO",
        "MANTEIGA",
        "FRANGO",
        "CARNE",
        "SALMAO",
        "PEIXE",
        "RICOTA",
        "MOZZARELA",
        "CREME",
    ]
    dry_tokens = [
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

    if any(t in name for t in perishable_tokens):
        return "perishable"
    if any(t in name for t in dry_tokens):
        return "dry"
    return "neutral"


def purchase_step_by_unit(unit):
    unit = str(unit).upper().strip()
    if unit in {"UN", "UND", "UNIDADE"}:
        return 1.0
    if unit == "KG":
        return 0.5
    if unit == "G":
        return 100.0
    if unit == "L":
        return 0.5
    if unit == "ML":
        return 100.0
    return 1.0


def is_discrete_unit(unit):
    return str(unit).upper().strip() in {"UN", "UND", "UNIDADE"}


def min_lot_by_profile(profile, step):
    if profile == "perishable":
        return step * 1
    if profile == "dry":
        return step * 2
    return step * 1


def compute_received_quantity(qtd_semana, unit, profile, rng):
    # Buffer semanal para proteger de ruptura.
    target = float(qtd_semana) * float(rng.uniform(1.10, 1.25))

    step = purchase_step_by_unit(unit)
    min_lot = min_lot_by_profile(profile, step)

    # Compra por multiplo de embalagem/lote minimo.
    qty = max(target, min_lot)
    qty = np.ceil(qty / step) * step

    # Itens por unidade nunca podem ser fracionarios.
    if is_discrete_unit(unit):
        return float(int(np.ceil(qty)))

    # Itens por medida podem ser fracionados conforme passo da embalagem.
    return float(np.round(qty, 2))


def main():
    base_dir = Path(__file__).resolve().parent

    pedidos_path = base_dir / "pedidos_sinteticos_2023_2026_mar.xlsx"
    ficha_path = base_dir / "fichas_tecnicas_ids.xlsx"
    receitas_path = base_dir / "lista_receitas.xlsx"
    ingredientes_path = base_dir / "lista_ingredientes.xlsx"

    output_xlsx = base_dir / "estoque_entradas_sintetico_2023_2026_mar.xlsx"
    output_csv = base_dir / "estoque_entradas_sintetico_2023_2026_mar.csv"
    output_resumo = base_dir / "resumo_mensal_entradas_estoque_2023_2026_mar.xlsx"

    rng = np.random.default_rng(42)

    pedidos = pd.read_excel(pedidos_path)
    ficha = pd.read_excel(ficha_path)
    receitas = pd.read_excel(receitas_path)
    ingredientes = pd.read_excel(ingredientes_path)

    pedidos["data_hora"] = pd.to_datetime(pedidos["data_hora"], errors="coerce")
    pedidos = pedidos.dropna(subset=["data_hora"]).copy()

    # IDs como string para joins e padronizacao.
    pedidos["id_produto"] = pedidos["id_produto"].astype(str)
    receitas["ID_Receita"] = receitas["ID_Receita"].astype(int)
    ficha["ID_Receita"] = ficha["ID_Receita"].astype(int)
    ficha["ID_Ingrediente"] = ficha["ID_Ingrediente"].astype(int)

    receitas["id_produto"] = receitas["ID_Receita"].astype(str)
    receitas["rendimento"] = pd.to_numeric(receitas["rendimento"], errors="coerce").fillna(1.0).clip(lower=1.0)

    # Consumo unitario por ingrediente de cada receita:
    # Qtd_Ingrediente representa o uso por receita inteira; divide por rendimento para obter por unidade vendida.
    comp = ficha.merge(receitas[["ID_Receita", "id_produto", "rendimento"]], on="ID_Receita", how="left")
    comp["consumo_unitario"] = pd.to_numeric(comp["Qtd_Ingrediente"], errors="coerce").fillna(0.0) / comp["rendimento"]

    # Vendas agregadas por dia e produto.
    pedidos["data"] = pedidos["data_hora"].dt.floor("D")
    vendas = (
        pedidos.groupby(["data", "id_produto"], as_index=False)["quantidade"]
        .sum()
        .rename(columns={"quantidade": "qtd_vendida"})
    )

    # Expande vendas para consumo de ingrediente.
    consumo = vendas.merge(
        comp[["id_produto", "ID_Ingrediente", "consumo_unitario"]],
        on="id_produto",
        how="left",
    )
    consumo["qtd_consumida"] = consumo["qtd_vendida"] * consumo["consumo_unitario"]
    consumo = consumo.dropna(subset=["ID_Ingrediente"]).copy()

    # Semana com inicio na segunda-feira para planejamento de entradas semanais.
    consumo["week_start"] = consumo["data"] - pd.to_timedelta(consumo["data"].dt.weekday, unit="D")

    weekly_need = (
        consumo.groupby(["week_start", "ID_Ingrediente"], as_index=False)["qtd_consumida"]
        .sum()
        .rename(columns={"qtd_consumida": "qtd_semana"})
    )

    # Junta detalhes de ingrediente e define validade por lote.
    weekly_need = weekly_need.merge(
        ingredientes[["ID_Ingrediente", "Ingrediente", "Un_Ingrediente"]],
        on="ID_Ingrediente",
        how="left",
    )

    weekly_need["profile"] = weekly_need["Ingrediente"].apply(classify_ingredient_profile)
    weekly_need["qtd_recebida"] = weekly_need.apply(
        lambda row: compute_received_quantity(
            row["qtd_semana"],
            row["Un_Ingrediente"],
            row["profile"],
            rng,
        ),
        axis=1,
    )

    validade_dias = [
        shelf_life_days(row["Ingrediente"], row["Un_Ingrediente"], rng)
        for _, row in weekly_need.iterrows()
    ]

    weekly_need["data_recebimento"] = pd.to_datetime(weekly_need["week_start"])
    weekly_need["data_validade"] = weekly_need["data_recebimento"] + pd.to_timedelta(validade_dias, unit="D")

    # Campos finais no formato solicitado.
    weekly_need = weekly_need.sort_values(["data_recebimento", "ID_Ingrediente"]).reset_index(drop=True)
    weekly_need["id_entrada"] = weekly_need.index.map(lambda i: f"LOTE_{i + 1:06d}")
    weekly_need["id_ingrediente"] = weekly_need["ID_Ingrediente"].astype(int)

    estoque = weekly_need[["id_entrada", "data_recebimento", "id_ingrediente", "qtd_recebida", "data_validade"]].copy()

    # Sanidade: apenas segundas-feiras.
    weekday_receb = estoque["data_recebimento"].dt.weekday
    if not (weekday_receb == 0).all():
        raise ValueError("Foram geradas entradas fora de segunda-feira")

    estoque.to_excel(output_xlsx, index=False)
    estoque.to_csv(output_csv, index=False)

    # Resumo para evidenciar coerencia com vendas.
    resumo_mensal = estoque.copy()
    resumo_mensal["year"] = resumo_mensal["data_recebimento"].dt.year
    resumo_mensal["month"] = resumo_mensal["data_recebimento"].dt.month
    resumo_mensal = resumo_mensal.groupby(["year", "month"], as_index=False)["qtd_recebida"].sum()
    resumo_mensal.to_excel(output_resumo, index=False)

    print(f"Entradas geradas: {len(estoque)}")
    print(f"Periodo: {estoque['data_recebimento'].min().date()} ate {estoque['data_recebimento'].max().date()}")
    print("Arquivos gerados:")
    print(f"- {output_xlsx.name}")
    print(f"- {output_csv.name}")
    print(f"- {output_resumo.name}")


if __name__ == "__main__":
    main()
