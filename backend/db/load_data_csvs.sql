-- Loads the source CSV files from data/ into PostgreSQL.
-- The tables live in the public schema and preserve the CSV business IDs.

DROP SCHEMA IF EXISTS dados CASCADE;
DROP TABLE IF EXISTS
    log_contagem,
    resumo_mensal_vendas,
    resumo_mensal_estoques,
    resumo_diario_vendas,
    resumo_diario_estoques,
    pedidos_log,
    pedidos,
    vendas,
    receitas_ingredientes,
    receitas,
    produtos_indisponiveis,
    fornecedores_ingredientes,
    fornecedores,
    feriados_recife,
    estoques,
    estoque_atual,
    ingredientes,
    categorias
CASCADE;

CREATE TABLE categorias (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE ingredientes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    category_id TEXT NOT NULL REFERENCES categorias (id)
);

CREATE TABLE estoque_atual (
    id TEXT PRIMARY KEY,
    ingrediente TEXT NOT NULL UNIQUE REFERENCES ingredientes (id),
    qtd NUMERIC(14, 4) NOT NULL,
    data DATE NOT NULL
);

CREATE TABLE estoques (
    id TEXT PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,
    ingredient_id TEXT NOT NULL REFERENCES ingredientes (id),
    quantity NUMERIC(14, 4) NOT NULL
);

CREATE TABLE feriados_recife (
    data DATE PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL
);

CREATE TABLE fornecedores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cnpj TEXT,
    email TEXT,
    phone TEXT,
    avg_delivery_time INTEGER
);

CREATE TABLE fornecedores_ingredientes (
    supplier_id TEXT NOT NULL REFERENCES fornecedores (id),
    ingredient_id TEXT NOT NULL REFERENCES ingredientes (id),
    price NUMERIC(14, 4) NOT NULL,
    discount_percent NUMERIC(8, 4) NOT NULL DEFAULT 0,
    min_to_discount NUMERIC(14, 4) NOT NULL DEFAULT 0,
    PRIMARY KEY (supplier_id, ingredient_id)
);

CREATE TABLE produtos_indisponiveis (
    "match" TEXT NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    PRIMARY KEY ("match", data_inicio, data_fim)
);

CREATE TABLE receitas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    "type" TEXT NOT NULL,
    yield_qty NUMERIC(14, 4),
    yield_unit TEXT,
    output_ingredient_id TEXT REFERENCES ingredientes (id),
    sale_price NUMERIC(14, 4)
);

CREATE TABLE receitas_ingredientes (
    recipe_id TEXT NOT NULL REFERENCES receitas (id),
    ingredient_id TEXT NOT NULL REFERENCES ingredientes (id),
    qty NUMERIC(14, 4) NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE vendas (
    id TEXT PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,
    recipe_id TEXT NOT NULL REFERENCES receitas (id),
    quantity NUMERIC(14, 4) NOT NULL,
    unit_price NUMERIC(14, 4) NOT NULL
);

CREATE TABLE pedidos (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    qty NUMERIC(14, 4) NOT NULL,
    valor NUMERIC(14, 4) NOT NULL,
    data_pedido DATE NOT NULL,
    status TEXT NOT NULL,
    data_prevista DATE NOT NULL,
    FOREIGN KEY (supplier_id, ingredient_id)
        REFERENCES fornecedores_ingredientes (supplier_id, ingredient_id)
);

CREATE TABLE pedidos_log (
    id BIGSERIAL PRIMARY KEY,
    data_pedido DATE NOT NULL,
    ingredient_id TEXT NOT NULL REFERENCES ingredientes (id),
    qty NUMERIC(14, 4) NOT NULL,
    data_prevista DATE NOT NULL,
    order_type TEXT NOT NULL
);

CREATE TABLE resumo_diario_estoques (
    date DATE PRIMARY KEY,
    saldo_medio DOUBLE PRECISION NOT NULL,
    itens_sobrestoque INTEGER NOT NULL,
    itens_substoque INTEGER NOT NULL,
    itens_ruptura INTEGER NOT NULL,
    consumo_total DOUBLE PRECISION NOT NULL
);

CREATE TABLE resumo_diario_vendas (
    date DATE PRIMARY KEY,
    vendas_dia INTEGER NOT NULL,
    is_holiday INTEGER NOT NULL,
    is_carnaval_window INTEGER NOT NULL,
    is_sao_joao INTEGER NOT NULL,
    is_summer INTEGER NOT NULL,
    is_promo_day INTEGER NOT NULL,
    is_rain_event INTEGER NOT NULL,
    is_closure INTEGER NOT NULL
);

CREATE TABLE resumo_mensal_estoques (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    saldo_medio DOUBLE PRECISION NOT NULL,
    saldo_max DOUBLE PRECISION NOT NULL,
    registros INTEGER NOT NULL,
    PRIMARY KEY (year, month)
);

CREATE TABLE resumo_mensal_vendas (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    vendas_mes INTEGER NOT NULL,
    unidades_vendidas INTEGER NOT NULL,
    receita_total NUMERIC(14, 4) NOT NULL,
    ticket_medio NUMERIC(14, 4) NOT NULL,
    receita_por_venda NUMERIC(14, 4) NOT NULL,
    PRIMARY KEY (year, month)
);

COPY categorias (id, name)
FROM '/data/categorias.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY ingredientes (id, name, unit, category_id)
FROM '/data/ingredientes.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY estoque_atual (id, ingrediente, qtd, data)
FROM '/data/estoque_atual.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY estoques (id, date_time, ingredient_id, quantity)
FROM '/data/estoques.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY feriados_recife (data, nome, tipo)
FROM '/data/feriados_recife.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY fornecedores (id, name, cnpj, email, phone, avg_delivery_time)
FROM '/data/fornecedores.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY fornecedores_ingredientes (
    supplier_id,
    ingredient_id,
    price,
    discount_percent,
    min_to_discount
)
FROM '/data/fornecedores_ingredientes.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY produtos_indisponiveis ("match", data_inicio, data_fim)
FROM '/data/produtos_indisponiveis.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY receitas (
    id,
    name,
    "type",
    yield_qty,
    yield_unit,
    output_ingredient_id,
    sale_price
)
FROM '/data/receitas.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY receitas_ingredientes (recipe_id, ingredient_id, qty, unit)
FROM '/data/receitas_ingredientes.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY vendas (id, date_time, recipe_id, quantity, unit_price)
FROM '/data/vendas.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY pedidos (
    id,
    supplier_id,
    ingredient_id,
    qty,
    valor,
    data_pedido,
    status,
    data_prevista
)
FROM '/data/pedidos.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY pedidos_log (data_pedido, ingredient_id, qty, data_prevista, order_type)
FROM '/data/pedidos_log.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY resumo_diario_estoques (
    date,
    saldo_medio,
    itens_sobrestoque,
    itens_substoque,
    itens_ruptura,
    consumo_total
)
FROM '/data/resumo_diario_estoques.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY resumo_diario_vendas (
    date,
    vendas_dia,
    is_holiday,
    is_carnaval_window,
    is_sao_joao,
    is_summer,
    is_promo_day,
    is_rain_event,
    is_closure
)
FROM '/data/resumo_diario_vendas.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY resumo_mensal_estoques (
    year,
    month,
    saldo_medio,
    saldo_max,
    registros
)
FROM '/data/resumo_mensal_estoques.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY resumo_mensal_vendas (
    year,
    month,
    vendas_mes,
    unidades_vendidas,
    receita_total,
    ticket_medio,
    receita_por_venda
)
FROM '/data/resumo_mensal_vendas.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

CREATE INDEX idx_ingredientes_category_id
    ON ingredientes (category_id);

CREATE INDEX idx_estoque_atual_ingrediente
    ON estoque_atual (ingrediente);

CREATE INDEX idx_estoques_ingredient_date
    ON estoques (ingredient_id, date_time);

CREATE INDEX idx_fornecedores_ingredientes_ingredient
    ON fornecedores_ingredientes (ingredient_id);

CREATE INDEX idx_receitas_output_ingredient
    ON receitas (output_ingredient_id);

CREATE INDEX idx_receitas_ingredientes_ingredient
    ON receitas_ingredientes (ingredient_id);

CREATE INDEX idx_vendas_recipe_date
    ON vendas (recipe_id, date_time);

CREATE INDEX idx_pedidos_supplier_date
    ON pedidos (supplier_id, data_pedido);

CREATE INDEX idx_pedidos_ingredient_date
    ON pedidos (ingredient_id, data_pedido);

CREATE INDEX idx_pedidos_log_ingredient_date
    ON pedidos_log (ingredient_id, data_pedido);

ANALYZE categorias;
ANALYZE ingredientes;
ANALYZE estoque_atual;
ANALYZE estoques;
ANALYZE feriados_recife;
ANALYZE fornecedores;
ANALYZE fornecedores_ingredientes;
ANALYZE produtos_indisponiveis;
ANALYZE receitas;
ANALYZE receitas_ingredientes;
ANALYZE vendas;
ANALYZE pedidos;
ANALYZE pedidos_log;
ANALYZE resumo_diario_estoques;
ANALYZE resumo_diario_vendas;
ANALYZE resumo_mensal_estoques;
ANALYZE resumo_mensal_vendas;
