"""
Gera fornecedores_ingredientes.csv com mapeamento coerente
entre fornecedores especialistas e ingredientes.

Regras:
- Ingredientes da CAT0015 (Produção) são preparados internamente -> ignorados.
- Cada ingrediente tem 2 ou 3 fornecedores (especialista + generalista).
- Fornecedores especialistas têm preços melhores e descontos mais agressivos.
- Generalistas (FOR0025 - Insumos Gourmet) cobrem várias categorias.
- min_to_discount varia conforme a unidade (KG, L, UND, PORÇÃO).
"""

import csv
import random
from pathlib import Path

random.seed(42)

BASE = Path(__file__).parent

# -------------------------------------------------------------------
# Mapeamento: categoria -> (fornecedor_especialista, [secundários...])
# FOR0025 (Insumos Gourmet) é o fornecedor genérico - aparece em quase tudo
# como opção secundária com preços ligeiramente maiores.
# -------------------------------------------------------------------
CATEGORY_SUPPLIERS = {
    "CAT0001": ["FOR0001", "FOR0022", "FOR0025"],          # Açúcares e Mel
    "CAT0002": ["FOR0011", "FOR0020", "FOR0025"],          # Bebidas e Bases
    "CAT0003": ["FOR0002", "FOR0021", "FOR0014"],          # Chocolates e Cacau
    "CAT0004": ["FOR0003", "FOR0007", "FOR0023"],          # Frutas Frescas
    "CAT0005": ["FOR0013", "FOR0003", "FOR0018"],          # Frutas Secas/Congeladas
    "CAT0006": ["FOR0005", "FOR0016", "FOR0025"],          # Grãos, Farinhas e Massas
    "CAT0007": ["FOR0004", "FOR0019", "FOR0018"],          # Laticínios
    "CAT0008": ["FOR0023", "FOR0007"],                     # Legumes e Verduras
    "CAT0009": ["FOR0012", "FOR0009", "FOR0025"],          # Molhos e Condimentos
    "CAT0010": ["FOR0006", "FOR0016", "FOR0025"],          # Nozes e Sementes
    "CAT0011": ["FOR0008", "FOR0025"],                     # Proteínas
    "CAT0012": ["FOR0014", "FOR0018", "FOR0025"],          # Semi-prontos e Preparados
    "CAT0013": ["FOR0009", "FOR0024", "FOR0025"],          # Temperos e Especiarias
    "CAT0014": ["FOR0010", "FOR0025"],                     # Óleos e Gorduras
}

# -------------------------------------------------------------------
# Overrides por palavra-chave: ajustes finos onde o mapeamento por
# categoria não captura a especialização real do fornecedor.
# -------------------------------------------------------------------
def override_suppliers(ing_id, name, category, default_suppliers):
    """Ajusta fornecedores baseado em palavras-chave do nome."""
    n = name.upper()

    # MEL -> Mel Puro Apiário é especialista
    if "MEL" in n and category == "CAT0001":
        return ["FOR0015", "FOR0001", "FOR0022"]

    # OVOS -> Frigorífico + Hortifruti (ambos vendem)
    if category == "CAT0011" and ("OVO" in n or "CLARA" in n):
        return ["FOR0008", "FOR0007"]

    # SHOYU, SAKÊ, PONZU, VINAGRE DE ARROZ -> Especiarias Orientais é especialista
    if any(k in n for k in ["SHOYU", "SAKÊ", "PONZU", "VINAGRE DE ARROZ", "TAHINE"]):
        return ["FOR0009", "FOR0012", "FOR0025"]

    # MATCHÁ, GOCHUJANG, CUMARU (especiarias raras) -> Especiarias do Oriente
    if any(k in n for k in ["MATCHÁ", "GOCHUJANG"]):
        return ["FOR0009", "FOR0024"]

    # CAFÉ, ESPRESSO -> Bebidas Premium
    if "CAFÉ" in n or "ESPRESSO" in n:
        return ["FOR0011", "FOR0025"]

    # CROISSANT, PÃO CIABATTA, PÃO DE CAIXA -> Confeitaria Insumos + Doçaria
    if any(k in n for k in ["CROISSANT", "PÃO CIABATTA", "PÃO DE CAIXA", "TORRADINHA"]):
        return ["FOR0014", "FOR0018"]

    # PISTACHE, PASTA DE PISTACHE -> Nozes & Castanhas (premium importado)
    if "PISTACHE" in n:
        return ["FOR0006", "FOR0025"]

    # AZEITE DE OLIVA -> Óleos Vitalle + Insumos Gourmet
    if "AZEITE" in n:
        return ["FOR0010", "FOR0025"]

    return default_suppliers


# -------------------------------------------------------------------
# Tabela de preço base (R$ por unidade) por palavra-chave.
# A primeira regra que casar é usada; senão cai no fallback por categoria.
# -------------------------------------------------------------------
KEYWORD_PRICES = [
    # (keyword, preco_base, unit_hint)
    ("AÇÚCAR CRISTAL", 6.50),
    ("AÇÚCAR REFINADO", 7.20),
    ("AÇÚCAR GRANULADO", 8.50),
    ("AÇÚCAR DEMERARA", 12.00),
    ("AÇÚCAR DE CONFEITEIRO", 14.50),
    ("AÇÚCAR IMPALPÁVEL", 15.80),
    ("XAROPE DE DEMERARA", 28.00),
    ("MEL DE AROEIRA", 95.00),
    ("MEL", 38.00),
    ("CAFÉ COADO", 4.20),
    ("ESPRESSO", 5.50),
    ("CHÁ VERDE", 110.00),
    ("CITRUS MIX", 32.00),
    ("ESSÊNCIA DE BAUNILHA", 95.00),
    ("EXTRATO DE BAUNILHA", 110.00),
    ("ÁGUA COM GÁS", 5.20),
    ("ÁGUA FILTRADA", 3.50),
    ("ÁGUA TÔNICA", 7.80),
    ("GELO", 4.00),
    ("GUARNIÇÃO", 1.80),
    ("BRIGADEIRO MOLE", 42.00),
    ("CACAU EM PÓ", 78.00),
    ("CHOCOLATE AMARGO 70%", 95.00),
    ("CHOCOLATE AMARGO", 78.00),
    ("CHOCOLATE BRANCO", 88.00),
    ("CHOCOLATE MEIO AMARGO", 82.00),
    ("ABACATE CONGELADO", 22.00),
    ("BANANA CONGELADA", 18.00),
    ("MANGA CONGELADA", 16.00),
    ("ABACATE", 12.00),
    ("BANANA PRATA", 8.50),
    ("KIWI", 18.00),
    ("LIMÃO SICILIANO", 14.00),
    ("LIMÃO TAHITI", 6.50),
    ("MANGA", 8.00),
    ("MAÇÃ VERMELHA", 9.50),
    ("MORANGO", 22.00),
    ("RASPAS DE LIMÃO SICILIANO", 38.00),
    ("RASPAS DE LIMÃO", 28.00),
    ("SUMO DE LARANJA", 14.00),
    ("SUMO DE LIMÃO SICILIANO", 24.00),
    ("SUMO DE LIMÃO TAHITI", 12.00),
    ("SUMO DE LIMÃO", 11.00),
    ("TOMATE CEREJA", 18.00),
    ("CRANBERRY SECO", 68.00),
    ("DAMASCO SECO", 72.00),
    ("FRUTAS CORTADAS", 14.00),
    ("HIBISCO SECO", 85.00),
    ("MIX DE FRUTAS VERMELHAS CONGELADAS", 55.00),
    ("MIX DE FRUTAS VERMELHAS", 78.00),
    ("POLPA DE AÇAÍ", 22.00),
    ("SALADA DE FRUTAS", 12.00),
    ("UVA PASSA BRANCA", 42.00),
    ("AMIDO DE MILHO", 12.00),
    ("ARROZ PARBOILIZADO", 8.50),
    ("AVEIA EM FLOCOS", 14.00),
    ("BIFUM", 18.00),
    ("ESPAGUETE", 12.00),
    ("FARELO DE AVEIA", 13.00),
    ("FARINHA DE GRÃO DE BICO", 18.00),
    ("FARINHA DE TRIGO", 7.50),
    ("FARINHA PANKO", 22.00),
    ("FERMENTO BIOLÓGICO SECO", 58.00),
    ("FERMENTO QUÍMICO", 32.00),
    ("LINGUINE", 16.00),
    ("MASSA DE TAPIOCA", 18.00),
    ("MASSA PARA PASTEL", 22.00),
    ("POLVILHO AZEDO", 12.00),
    ("POLVILHO DOCE", 11.00),
    ("CHANTILLY", 32.00),
    ("CREAM CHEESE", 48.00),
    ("CREME DE LEITE FRESCO", 38.00),
    ("CREME DE LEITE", 22.00),
    ("DOCE DE LEITE", 32.00),
    ("GORGONZOLA", 95.00),
    ("IOGURTE GREGO", 35.00),
    ("IOGURTE", 18.00),
    ("LEITE CONDENSADO", 22.00),
    ("LEITE EM PÓ", 48.00),
    ("LEITE INTEGRAL", 7.50),
    ("MANTEIGA DE GARRAFA", 68.00),
    ("MANTEIGA SEM SAL", 82.00),
    ("MANTEIGA", 75.00),
    ("MUSSARELA", 52.00),
    ("PARMESÃO", 110.00),
    ("QUEIJO BOURSIN", 130.00),
    ("QUEIJO DE COALHO", 62.00),
    ("REQUEIJÃO", 38.00),
    ("RICOTA", 32.00),
    ("ACELGA", 8.50),
    ("BATATA DOCE", 7.50),
    ("BERINJELA", 8.00),
    ("BETERRABA", 6.50),
    ("CEBOLA BRANCA", 6.80),
    ("CEBOLA ROXA", 10.50),
    ("CEBOLA", 5.50),
    ("CEBOLINHA", 24.00),
    ("CENOURA EM FIOS", 18.00),
    ("CENOURA", 6.50),
    ("COENTRO", 22.00),
    ("COUVE", 18.00),
    ("MIX DE COGUMELOS", 62.00),
    ("MIX DE FOLHAS", 38.00),
    ("PEPINO JAPONÊS", 12.00),
    ("REPOLHO ROXO EM FIOS", 18.00),
    ("REPOLHO BRANCO", 6.00),
    ("REPOLHO ROXO", 7.50),
    ("RÚCULA", 22.00),
    ("SALSINHA", 24.00),
    ("MOLHO BÉCHAMEL", 28.00),
    ("MOLHO DE TOMATE ASSADO", 22.00),
    ("PESTO DE MANJERICÃO", 78.00),
    ("SAKÊ MIRIM", 48.00),
    ("SHOYU", 32.00),
    ("TAHINE", 65.00),
    ("VINAGRE DE ARROZ", 35.00),
    ("AMENDOIM TORRADO SEM SAL", 38.00),
    ("AMENDOIM SEM SAL", 35.00),
    ("AMENDOIM", 28.00),
    ("AMÊNDOAS LAMINADAS", 115.00),
    ("CASTANHA DE CAJU", 95.00),
    ("CASTANHA DO PARÁ", 110.00),
    ("COCO DESIDRATADO EM FITAS", 68.00),
    ("GERGELIM PRETO TORRADO", 58.00),
    ("GERGELIM PRETO", 52.00),
    ("GERGELIM BRANCO", 45.00),
    ("MIX DE GERGELIM", 55.00),
    ("PASTA DE PISTACHE", 320.00),
    ("PISTACHE", 280.00),
    ("SEMENTE DE ABÓBORA", 42.00),
    ("SEMENTE DE CHIA", 38.00),
    ("SEMENTE DE COENTRO", 65.00),
    ("SEMENTE DE GIRASSOL", 32.00),
    ("SEMENTE DE MOSTARDA", 48.00),
    ("APARAS DE FRANGO", 22.00),
    ("APARAS DE SALMÃO", 75.00),
    ("BACON", 52.00),
    ("CAMARÃO", 110.00),
    ("CHARQUE DESFIADA", 78.00),
    ("CHATEAUBRIAND DE MIGNON", 165.00),
    ("CLARA DE OVO", 1.20),
    ("FILÉ DE PEITO DE FRANGO", 32.00),
    ("FRANGO DESFIADO", 38.00),
    ("OVO", 0.85),
    ("PRESUNTO DE PERU", 55.00),
    ("PRESUNTO SERRANO", 210.00),
    ("SALMÃO DEFUMADO", 145.00),
    ("TOFU FIRME", 32.00),
    ("APARAS DE PÃO", 8.00),
    ("ARROZ PARBOILIZADO COZIDO", 12.00),
    ("BASE DE BISCOITO", 28.00),
    ("BATATA ASSADA", 14.00),
    ("BISCOITO MAISENA", 22.00),
    ("BISCOITO NEGRESCO", 32.00),
    ("BOLINHA DE RICOTA MARINADA", 1.20),
    ("CALDA DE CARAMELO", 28.00),
    ("CHIPS DE PARMESÃO", 85.00),
    ("CROISSANT", 5.50),
    ("CRUMBLE", 32.00),
    ("CUSCUZ", 12.00),
    ("EMPANAMENTO MOLHADO", 22.00),
    ("EMPANAMENTO SECO", 18.00),
    ("GELATINA EM PÓ INCOLOR", 85.00),
    ("GELATINA EM PÓ SEM SABOR", 95.00),
    ("GRÃO DE BICO COZIDO", 18.00),
    ("MERENGUE", 35.00),
    ("MIX DE CHIPS", 38.00),
    ("MIX DE GRÃOS", 22.00),
    ("MIX DE VEGETAIS ESCALFADOS", 28.00),
    ("MOUSSE DE LIMÃO SICILIANO", 38.00),
    ("NUGGETS DE FRANGO", 42.00),
    ("PARMÊ DE FRANGO KATSU", 8.50),
    ("PÃO CIABATTA", 4.20),
    ("PÃO DE CAIXA", 22.00),
    ("SORVETE DE CHOCOLATE", 38.00),
    ("SORVETE DE CREME", 32.00),
    ("TORRADINHA DE CIABATTA", 28.00),
    ("ALECRIM", 28.00),
    ("ALHO", 24.00),
    ("CANELA", 85.00),
    ("CAPIM SANTO", 42.00),
    ("CUMARU", 320.00),
    ("FLOR DE SAL", 110.00),
    ("GENGIBRE", 22.00),
    ("MATCHÁ", 280.00),
    ("NOZ MOSCADA", 95.00),
    ("PASTA DE ALHO COM GENGIBRE", 48.00),
    ("PASTA DE ALHO", 42.00),
    ("PASTA DE GOCHUJANG", 85.00),
    ("PASTA DE TEMPERO", 52.00),
    ("PIMENTA DO REINO", 110.00),
    ("PIMENTA SÍRIA", 78.00),
    ("PÁPRICA DOCE", 62.00),
    ("PÁPRICA PICANTE", 68.00),
    ("SAL DE COZINHA", 4.50),
    ("ÁCIDO CÍTRICO", 55.00),
    ("AZEITE DE OLIVA", 42.00),
    ("GORDURA DE PALMA", 22.00),
    ("ÓLEO DE CANOLA", 14.00),
    ("ÓLEO DE GERGELIM", 95.00),
    ("ÓLEO DE SOJA", 9.50),
]

CATEGORY_FALLBACK_PRICE = {
    "CAT0001": 10.00,
    "CAT0002": 15.00,
    "CAT0003": 80.00,
    "CAT0004": 12.00,
    "CAT0005": 50.00,
    "CAT0006": 12.00,
    "CAT0007": 35.00,
    "CAT0008": 12.00,
    "CAT0009": 35.00,
    "CAT0010": 55.00,
    "CAT0011": 45.00,
    "CAT0012": 25.00,
    "CAT0013": 65.00,
    "CAT0014": 18.00,
}


def base_price(name, category):
    upper = name.upper()
    for keyword, price in KEYWORD_PRICES:
        if keyword in upper:
            return price
    return CATEGORY_FALLBACK_PRICE.get(category, 20.00)


# -------------------------------------------------------------------
# Geração das linhas
# -------------------------------------------------------------------
def min_to_discount(unit, bp):
    """
    Define quantidade mínima para desconto conforme a UNIDADE do ingrediente
    e ajustada pelo preço base: ingredientes caros têm mínimos menores
    para não exigir compras absurdamente grandes (ex.: 50 kg de pistache).
    """
    if unit == "KG":
        if bp > 250:                # pistache, cumaru, matchá, pasta de pistache
            choices = [2, 3, 5]
        elif bp > 100:              # parmesão, boursin, salmão, presunto serrano
            choices = [5, 8, 10, 15]
        elif bp > 40:               # frutas secas, nozes, queijos
            choices = [10, 15, 20, 25]
        else:                       # açúcar, farinha, legumes, frutas comuns
            choices = [15, 20, 25, 30, 40, 50]
        return random.choice(choices)

    if unit == "L":
        if bp > 60:                 # óleo de gergelim, essência de baunilha
            choices = [3, 5, 8, 10]
        elif bp > 25:               # azeite, shoyu, sakê, sumos especiais
            choices = [8, 10, 12, 15, 20]
        else:                       # água, leite, óleos comuns, sumos básicos
            choices = [10, 15, 20, 25, 30]
        return random.choice(choices)

    if unit == "UND":
        if bp > 50:                 # parmê de frango katsu (R$ 8.5/un cluster)
            choices = [20, 30, 50]
        elif bp > 5:                # croissant, pão ciabatta, pão de caixa
            choices = [30, 50, 80, 100]
        else:                       # ovos, água com gás, café coado
            choices = [100, 150, 200, 250, 300]
        return random.choice(choices)

    if unit == "PORÇÃO":
        return random.choice([20, 30, 50, 75])

    return 15


def pick_discount(role_index):
    """
    Desconto normalizado em [0, 1].
    Especialista costuma ter faixa por volume; secundário e generalista
    frequentemente vendem só a preço de tabela (0.00).
    """
    if role_index == 0:
        if random.random() < 0.12:
            return 0.0
        return random.choice([0.05, 0.07, 0.08, 0.10, 0.12, 0.15])
    if role_index == 1:
        if random.random() < 0.45:
            return 0.0
        return random.choice([0.03, 0.05, 0.07, 0.08, 0.10])
    if random.random() < 0.62:
        return 0.0
    return random.choice([0.03, 0.05, 0.07])


def supplier_variation(role_index):
    """Retorna (multiplicador_preço, desconto_decimal)."""
    if role_index == 0:
        return random.uniform(0.92, 1.00), pick_discount(0)
    if role_index == 1:
        return random.uniform(0.98, 1.08), pick_discount(1)
    return random.uniform(1.05, 1.15), pick_discount(2)


def main():
    rows_out = []

    with open(BASE / "ingredientes.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ingredients = list(reader)

    for ing in ingredients:
        ing_id = ing["id"]
        name = ing["name"]
        unit = ing["unit"]
        category = ing["category_id"]

        # Pula itens de produção interna
        if category == "CAT0015":
            continue

        default_suppliers = CATEGORY_SUPPLIERS.get(category, [])
        suppliers = override_suppliers(ing_id, name, category, default_suppliers)
        if not suppliers:
            continue

        bp = base_price(name, category)

        batch = []
        for idx, sup in enumerate(suppliers):
            mult, disc = supplier_variation(idx)
            price = round(bp * mult, 2)
            # Sem desconto => sem mínimo (0.00 em ambos); mínimo só com desconto por volume.
            mtd = min_to_discount(unit, bp) if disc > 0 else 0
            batch.append({
                "supplier_id": sup,
                "ingredient_id": ing_id,
                "price": f"{price:.2f}",
                "discount_percent": f"{disc:.2f}",
                "min_to_discount": mtd,
            })

        # Garante ao menos um fornecedor com faixa de desconto por ingrediente.
        if batch and all(float(r["discount_percent"]) == 0 for r in batch):
            batch[0]["discount_percent"] = random.choice(["0.05", "0.07", "0.08", "0.10"])
            batch[0]["min_to_discount"] = min_to_discount(unit, bp)

        rows_out.extend(batch)

    out_path = BASE / "fornecedores_ingredientes.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["supplier_id", "ingredient_id", "price",
                        "discount_percent", "min_to_discount"],
        )
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Linhas geradas: {len(rows_out)}")
    print(f"Arquivo: {out_path}")


if __name__ == "__main__":
    main()
