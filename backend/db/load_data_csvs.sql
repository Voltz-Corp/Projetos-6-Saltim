-- Loads the source CSV files from data/ into PostgreSQL.
-- The tables live in the public schema and preserve the CSV business IDs.

DROP SCHEMA IF EXISTS dados CASCADE;
DROP TABLE IF EXISTS
    venda_documentos_fiscais,
    estoque_movimentos,
    venda_pagamentos,
    venda_itens,
    venda_transacoes,
    clientes,
    contagem_log,
    contagens,
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

CREATE SCHEMA IF NOT EXISTS ml;

CREATE TABLE IF NOT EXISTS ml.job_status (
    id BIGSERIAL PRIMARY KEY,
    dia DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    inicio_em TIMESTAMPTZ,
    fim_em TIMESTAMPTZ,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_message TEXT,
    CONSTRAINT uq_job_status_dia UNIQUE (dia),
    CONSTRAINT ck_job_status_status CHECK (status IN ('running', 'pending', 'success', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_job_status_dia ON ml.job_status (dia);

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

CREATE TABLE contagens (
    id BIGSERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    data_contagem DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'em_andamento',
    estoque_snapshot_data DATE,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizada_em TIMESTAMPTZ,
    UNIQUE (data_contagem)
);

CREATE TABLE contagem_log (
    id BIGSERIAL PRIMARY KEY,
    contagem_id BIGINT NOT NULL REFERENCES contagens (id),
    ingrediente_id TEXT NOT NULL REFERENCES ingredientes (id),
    estoque_id TEXT,
    estoque_data DATE,
    estoque_quantidade NUMERIC(14, 4),
    category_id TEXT NOT NULL REFERENCES categorias (id),
    categoria TEXT NOT NULL,
    quantidade_anterior NUMERIC(14, 4) NOT NULL,
    quantidade_nova NUMERIC(14, 4) NOT NULL,
    delta NUMERIC(14, 4) NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (contagem_id, ingrediente_id)
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
    unit_price NUMERIC(14, 4) NOT NULL,
    comanda_id TEXT,
    mesa_numero INTEGER,
    status TEXT NOT NULL DEFAULT 'paga',
    cpf_cliente TEXT,
    customer_name TEXT,
    payment_method TEXT,
    paid_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
    change_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(14, 4) NOT NULL DEFAULT 0,
    total NUMERIC(14, 4) NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'historico',
    fiscal_status TEXT NOT NULL DEFAULT 'pendente_preparacao',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ
);

CREATE TABLE clientes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    document TEXT,
    email TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE venda_transacoes (
    id TEXT PRIMARY KEY,
    date_time TIMESTAMPTZ NOT NULL,
    cliente_id TEXT REFERENCES clientes (id),
    status TEXT NOT NULL DEFAULT 'aberta',
    subtotal NUMERIC(14, 4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(14, 4) NOT NULL DEFAULT 0,
    total NUMERIC(14, 4) NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'balcao',
    fiscal_status TEXT NOT NULL DEFAULT 'pendente_preparacao',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ
);

CREATE TABLE venda_itens (
    id TEXT PRIMARY KEY,
    venda_id TEXT NOT NULL REFERENCES venda_transacoes (id) ON DELETE CASCADE,
    recipe_id TEXT NOT NULL REFERENCES receitas (id),
    recipe_name TEXT NOT NULL,
    quantity NUMERIC(14, 4) NOT NULL,
    unit_price NUMERIC(14, 4) NOT NULL,
    discount_value NUMERIC(14, 4) NOT NULL DEFAULT 0,
    total_value NUMERIC(14, 4) NOT NULL,
    venda_historica_id TEXT REFERENCES vendas (id)
);

CREATE TABLE venda_pagamentos (
    id TEXT PRIMARY KEY,
    venda_id TEXT NOT NULL REFERENCES venda_transacoes (id) ON DELETE CASCADE,
    method TEXT NOT NULL,
    amount NUMERIC(14, 4) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pago',
    paid_at TIMESTAMPTZ,
    change_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
    external_reference TEXT
);

CREATE TABLE estoque_movimentos (
    id TEXT PRIMARY KEY,
    ingredient_id TEXT NOT NULL REFERENCES ingredientes (id),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    delta_qty NUMERIC(14, 4) NOT NULL,
    previous_qty NUMERIC(14, 4) NOT NULL,
    new_qty NUMERIC(14, 4) NOT NULL,
    unit TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE venda_documentos_fiscais (
    id TEXT PRIMARY KEY,
    venda_id TEXT NOT NULL REFERENCES venda_transacoes (id) ON DELETE CASCADE,
    document_type TEXT NOT NULL DEFAULT 'NFC-e',
    status TEXT NOT NULL DEFAULT 'pendente_preparacao',
    provider TEXT,
    access_key TEXT,
    protocol TEXT,
    issued_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    payload JSON,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
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

ALTER TABLE contagem_log
    ADD CONSTRAINT fk_contagem_log_estoque
    FOREIGN KEY (estoque_id)
    REFERENCES estoques (id);

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

UPDATE vendas
SET
    comanda_id = id,
    total = quantity * unit_price,
    paid_amount = quantity * unit_price,
    confirmed_at = date_time;

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

CREATE INDEX idx_contagens_criada_em
    ON contagens (criada_em);

CREATE INDEX idx_contagens_status
    ON contagens (status);

CREATE INDEX idx_contagens_data_contagem
    ON contagens (data_contagem);

CREATE INDEX idx_contagens_estoque_snapshot_data
    ON contagens (estoque_snapshot_data);

CREATE INDEX idx_contagem_log_contagem_categoria
    ON contagem_log (contagem_id, category_id);

CREATE INDEX idx_contagem_log_ingredient
    ON contagem_log (ingrediente_id);

CREATE INDEX idx_contagem_log_estoque
    ON contagem_log (estoque_id);

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

CREATE INDEX idx_vendas_comanda
    ON vendas (comanda_id);

CREATE INDEX idx_vendas_mesa_status
    ON vendas (mesa_numero, status);

CREATE INDEX idx_clientes_name
    ON clientes (name);

CREATE INDEX idx_clientes_document
    ON clientes (document);

CREATE INDEX idx_venda_transacoes_date
    ON venda_transacoes (date_time);

CREATE INDEX idx_venda_transacoes_status
    ON venda_transacoes (status);

CREATE INDEX idx_venda_transacoes_cliente
    ON venda_transacoes (cliente_id);

CREATE INDEX idx_venda_transacoes_fiscal_status
    ON venda_transacoes (fiscal_status);

CREATE INDEX idx_venda_itens_venda
    ON venda_itens (venda_id);

CREATE INDEX idx_venda_itens_recipe
    ON venda_itens (recipe_id);

CREATE INDEX idx_venda_itens_historical
    ON venda_itens (venda_historica_id);

CREATE INDEX idx_venda_pagamentos_venda
    ON venda_pagamentos (venda_id);

CREATE INDEX idx_venda_pagamentos_status
    ON venda_pagamentos (status);

CREATE INDEX idx_estoque_movimentos_ingredient_date
    ON estoque_movimentos (ingredient_id, created_at);

CREATE INDEX idx_estoque_movimentos_source
    ON estoque_movimentos (source_type, source_id);

CREATE INDEX idx_venda_documentos_fiscais_venda
    ON venda_documentos_fiscais (venda_id);

CREATE INDEX idx_venda_documentos_fiscais_status
    ON venda_documentos_fiscais (status);

CREATE INDEX idx_pedidos_supplier_date
    ON pedidos (supplier_id, data_pedido);

CREATE INDEX idx_pedidos_ingredient_date
    ON pedidos (ingredient_id, data_pedido);

CREATE INDEX idx_pedidos_log_ingredient_date
    ON pedidos_log (ingredient_id, data_pedido);

ANALYZE categorias;
ANALYZE ingredientes;
ANALYZE contagens;
ANALYZE contagem_log;
ANALYZE estoque_atual;
ANALYZE estoques;
ANALYZE feriados_recife;
ANALYZE fornecedores;
ANALYZE fornecedores_ingredientes;
ANALYZE produtos_indisponiveis;
ANALYZE receitas;
ANALYZE receitas_ingredientes;
ANALYZE vendas;
ANALYZE clientes;
ANALYZE venda_transacoes;
ANALYZE venda_itens;
ANALYZE venda_pagamentos;
ANALYZE estoque_movimentos;
ANALYZE venda_documentos_fiscais;
ANALYZE pedidos;
ANALYZE pedidos_log;
ANALYZE resumo_diario_estoques;
ANALYZE resumo_diario_vendas;
ANALYZE resumo_mensal_estoques;
ANALYZE resumo_mensal_vendas;
