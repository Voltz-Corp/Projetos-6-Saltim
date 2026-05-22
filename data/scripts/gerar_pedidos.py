"""
Gera pedidos.csv a partir do log de decisões de compra produzido pela
simulação de estoque.

Entrada (em data/):
  - pedidos_log.csv          (saída de gerar_estoques.py)
  - fornecedores.csv
  - fornecedores_ingredientes.csv

Saída:
  - pedidos.csv com colunas:
      id, supplier_id, ingredient_id, qty, valor,
      data_pedido, status, data_prevista

Cada linha do log vira 1 pedido. Este script é responsável apenas pelo
enriquecimento — selecionar fornecedor, calcular valor e adicionar ruído —
sem refazer a simulação de estoque. Assim, estoques.csv e pedidos.csv ficam
100% congruentes via o log intermediário.

Princípio: pedidos NÃO são otimizados. A operação real escolhe nem sempre o
mais barato, recebe entregas parciais, paga preços diferentes da tabela.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SEED = 4242
END_DATE = "2026-05-19"

# Ruído na escolha do fornecedor — operação não é perfeitamente otimizada
SECOND_SUPPLIER_PROB = 0.32   # chance de pegar o 2º da lista ordenada
THIRD_SUPPLIER_PROB = 0.10    # chance de pegar o 3º (acumulativa)

# Ruído de preço: variação por lote (frete, negociação, sazonalidade do mercado)
PRICE_NOISE_LOW = 0.86
PRICE_NOISE_HIGH = 1.18

# Ruído de quantidade: entrega parcial ou excesso ocasional
QTY_NOISE_PROB = 0.20
QTY_NOISE_LOW = 0.82
QTY_NOISE_HIGH = 1.22

# Aplicação de desconto da tabela quando qty >= min_to_discount
APPLY_DISCOUNT_PROB = 0.75    # nem sempre se aplica (esquecimento, regra negocial)


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------
def load_supplier_options(
    fornecedores_path: Path, fi_path: Path
) -> dict[str, list[dict]]:
    """Para cada ingrediente, retorna lista de opções de fornecedor.

    Cada opção: {supplier_id, price, delivery_time, discount_pct, min_to_discount}
    """
    fornecedores = pd.read_csv(fornecedores_path)
    fi = pd.read_csv(fi_path)
    merged = fi.merge(
        fornecedores[["id", "avg_delivery_time"]],
        left_on="supplier_id",
        right_on="id",
        suffixes=("", "_sup"),
    )
    options: dict[str, list[dict]] = {}
    for ing_id, grp in merged.groupby("ingredient_id"):
        options[str(ing_id)] = [
            {
                "supplier_id": str(r["supplier_id"]),
                "price": float(r["price"]),
                "delivery_time": int(r["avg_delivery_time"]),
                "discount_pct": float(r.get("discount_percent", 0.0) or 0.0),
                "min_to_discount": float(r.get("min_to_discount", 0.0) or 0.0),
            }
            for _, r in grp.iterrows()
        ]
    return options


# ---------------------------------------------------------------------------
# Seleção de fornecedor e cálculo do valor
# ---------------------------------------------------------------------------
def pick_supplier(
    opts: list[dict],
    order_type: str,
    rng: np.random.Generator,
) -> dict:
    """Sexta → mais barato; emergencial → mais rápido. Com ruído de escolha."""
    if order_type == "emergencial":
        opts_sorted = sorted(opts, key=lambda o: (o["delivery_time"], o["price"]))
    else:
        opts_sorted = sorted(opts, key=lambda o: (o["price"], o["delivery_time"]))

    pick = 0
    if len(opts_sorted) > 1:
        r = rng.random()
        if r < THIRD_SUPPLIER_PROB and len(opts_sorted) > 2:
            pick = 2
        elif r < THIRD_SUPPLIER_PROB + SECOND_SUPPLIER_PROB:
            pick = 1
    return opts_sorted[pick]


def compute_valor(
    qty: float,
    supplier: dict,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """Retorna (qty_efetiva_recebida, valor_total) com ruídos aplicados."""
    received_qty = qty
    if rng.random() < QTY_NOISE_PROB:
        received_qty = qty * float(rng.uniform(QTY_NOISE_LOW, QTY_NOISE_HIGH))
    received_qty = round(received_qty, 2)

    base_price = supplier["price"] * float(rng.uniform(PRICE_NOISE_LOW, PRICE_NOISE_HIGH))

    # Desconto progressivo quando qty atinge min_to_discount (nem sempre aplicado)
    discount = 0.0
    if (
        supplier["min_to_discount"] > 0
        and received_qty >= supplier["min_to_discount"]
        and rng.random() < APPLY_DISCOUNT_PROB
    ):
        discount = supplier["discount_pct"]
    eff_price = base_price * (1.0 - discount)

    valor = round(received_qty * eff_price, 2)
    return received_qty, valor


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    root = Path(__file__).resolve().parents[1]
    log_path = root / "pedidos_log.csv"
    out_path = root / "pedidos.csv"

    if not log_path.exists():
        raise FileNotFoundError(
            f"Log não encontrado: {log_path}. "
            "Execute data/scripts/gerar_estoques.py primeiro."
        )

    print(f"Lendo log: {log_path}")
    log = pd.read_csv(log_path, parse_dates=["data_pedido", "data_prevista"])
    if log.empty:
        print("Log vazio — nada a gerar.")
        return

    print("Carregando opções de fornecedor...")
    sup_opts = load_supplier_options(
        root / "fornecedores.csv",
        root / "fornecedores_ingredientes.csv",
    )

    rng = np.random.default_rng(SEED)
    end_ts = pd.Timestamp(END_DATE)

    print(f"Processando {len(log):,} eventos de compra...")
    rows: list[dict] = []
    skipped = 0
    for _, r in log.iterrows():
        ing_id = str(r["ingredient_id"])
        opts = sup_opts.get(ing_id, [])
        if not opts:
            skipped += 1
            continue

        order_type = str(r["order_type"])
        supplier = pick_supplier(opts, order_type, rng)
        qty_efetiva, valor = compute_valor(float(r["qty"]), supplier, rng)

        status = "entregue" if r["data_prevista"] <= end_ts else "em_transito"

        rows.append(
            {
                "supplier_id": supplier["supplier_id"],
                "ingredient_id": ing_id,
                "qty": qty_efetiva,
                "valor": valor,
                "data_pedido": r["data_pedido"].date(),
                "status": status,
                "data_prevista": r["data_prevista"].date(),
            }
        )

    if skipped:
        print(f"  - {skipped} pedido(s) sem fornecedor cadastrado (ignorados)")

    if not rows:
        print("Nenhum pedido produzido — verifique pedidos_log.csv.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["data_pedido", "ingredient_id", "supplier_id"]
    ).reset_index(drop=True)
    df.insert(0, "id", [f"PED{i:012d}" for i in range(1, len(df) + 1)])
    df = df[
        [
            "id",
            "supplier_id",
            "ingredient_id",
            "qty",
            "valor",
            "data_pedido",
            "status",
            "data_prevista",
        ]
    ]

    df.to_csv(out_path, index=False)

    # ---------------- Resumo ----------------
    n_entregue = int((df["status"] == "entregue").sum())
    n_transito = int((df["status"] == "em_transito").sum())
    valor_total = float(df["valor"].sum())
    log_dow = log["data_pedido"].dt.day_name()
    sexta_share = float((log["order_type"] == "sexta").mean()) if len(log) else 0.0

    print(f"Pedidos gerados: {len(df):,}")
    print(f"  - Entregues: {n_entregue:,}")
    print(f"  - Em trânsito: {n_transito:,}")
    print(f"  - Fornecedores únicos: {df['supplier_id'].nunique()}")
    print(f"  - Ingredientes únicos: {df['ingredient_id'].nunique()}")
    print(f"  - Valor total: R$ {valor_total:,.2f}")
    print(f"  - % pedidos rotina de sexta: {sexta_share:.1%}")
    print(f"  - Distribuição por dia da semana:")
    for dow, n in log_dow.value_counts().items():
        print(f"      {dow:<10}: {int(n):,}")
    print(f"Arquivo: {out_path}")


if __name__ == "__main__":
    main()
