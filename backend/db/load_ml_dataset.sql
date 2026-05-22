-- Loads the Saltim ML datasets into PostgreSQL.
-- This file is executed by the backend startup loader.

CREATE SCHEMA IF NOT EXISTS ml;

DROP TABLE IF EXISTS ml.abt_reposicao_sample_100;
DROP TABLE IF EXISTS ml.abt_reposicao;
CREATE TABLE ml.abt_reposicao (
    "ingredient_id" TEXT,
    "date" DATE,
    "nome_ingrediente" TEXT,
    "unidade" TEXT,
    "categoria_id" TEXT,
    "is_compravel" INTEGER,
    "is_produzido_internamente" INTEGER,
    "categoria" TEXT,
    "perfil_perecivel_estimado" TEXT,
    "quantidade_por_unidade_de_compra" DOUBLE PRECISION,
    "saldo_atual" DOUBLE PRECISION,
    "consumo_ingrediente_dia" DOUBLE PRECISION,
    "dia_da_semana" INTEGER,
    "is_friday" INTEGER,
    "dias_ate_sexta" INTEGER,
    "is_weekend" INTEGER,
    "mes" INTEGER,
    "semana_do_ano" INTEGER,
    "dia_do_mes" INTEGER,
    "is_summer" INTEGER,
    "is_sao_joao" INTEGER,
    "is_holiday" INTEGER,
    "nome_feriado" TEXT,
    "tipo_feriado" TEXT,
    "is_carnaval_window" INTEGER,
    "menor_preco_disponivel" DOUBLE PRECISION,
    "preco_medio_disponivel" DOUBLE PRECISION,
    "maior_preco_disponivel" DOUBLE PRECISION,
    "menor_lead_time" INTEGER,
    "lead_time_medio_fornecedores" DOUBLE PRECISION,
    "qtd_fornecedores_disponiveis" INTEGER,
    "maior_desconto_disponivel" DOUBLE PRECISION,
    "min_to_discount" INTEGER,
    "fornecedor_mais_barato" TEXT,
    "fornecedor_mais_rapido" TEXT,
    "preco_min_max_ratio" DOUBLE PRECISION,
    "flag_indisponibilidade" INTEGER,
    "ingrediente_afetado_por_indisponibilidade" INTEGER,
    "produto_indisponivel_relacionado" TEXT,
    "dias_em_indisponibilidade" INTEGER,
    "audit_qtd_pedida_no_dia" DOUBLE PRECISION,
    "audit_valor_pedido_no_dia" DOUBLE PRECISION,
    "audit_comprou_no_dia" DOUBLE PRECISION,
    "audit_order_type_no_dia" TEXT,
    "lead_time_pedido_no_dia" DOUBLE PRECISION,
    "saldo_lag_1" DOUBLE PRECISION,
    "saldo_lag_7" DOUBLE PRECISION,
    "variacao_estoque_1d" DOUBLE PRECISION,
    "variacao_estoque_7d" DOUBLE PRECISION,
    "flag_ruptura" INTEGER,
    "consumo_lag_1d" DOUBLE PRECISION,
    "consumo_lag_7d" DOUBLE PRECISION,
    "consumo_lag_14d" DOUBLE PRECISION,
    "consumo_lag_28d" DOUBLE PRECISION,
    "media_movel_consumo_7d" DOUBLE PRECISION,
    "desvio_consumo_7d" DOUBLE PRECISION,
    "consumo_max_7d" DOUBLE PRECISION,
    "media_movel_consumo_14d" DOUBLE PRECISION,
    "desvio_consumo_14d" DOUBLE PRECISION,
    "consumo_max_14d" DOUBLE PRECISION,
    "media_movel_consumo_28d" DOUBLE PRECISION,
    "desvio_consumo_28d" DOUBLE PRECISION,
    "consumo_max_28d" DOUBLE PRECISION,
    "tendencia_consumo_7_vs_28" DOUBLE PRECISION,
    "dias_desde_ultimo_consumo" INTEGER,
    "qtd_pedida_no_dia_audit" DOUBLE PRECISION,
    "comprou_no_dia_audit" INTEGER,
    "valor_pedido_no_dia_audit" DOUBLE PRECISION,
    "order_type_no_dia_audit" TEXT,
    "total_pedido_30d" DOUBLE PRECISION,
    "media_qtd_pedida_30d" DOUBLE PRECISION,
    "lead_time_medio_realizado" DOUBLE PRECISION,
    "dias_desde_ultimo_pedido" INTEGER,
    "qtd_ultimo_pedido" DOUBLE PRECISION,
    "tipo_ultimo_pedido" TEXT,
    "pedidos_em_aberto" INTEGER,
    "qtd_em_transito" DOUBLE PRECISION,
    "estoque_em_aberto" DOUBLE PRECISION,
    "qtd_em_transito_no_horizonte" DOUBLE PRECISION,
    "dias_para_proxima_entrega" INTEGER,
    "stock_position" DOUBLE PRECISION,
    "lead_time_previsto" INTEGER,
    "dias_de_cobertura" DOUBLE PRECISION,
    "flag_subestoque" INTEGER,
    "flag_sobrestoque" INTEGER,
    "y_qtd_comprar" DOUBLE PRECISION,
    "y_threshold" DOUBLE PRECISION,
    "y_comprar" INTEGER,
    "y_demanda_futura_horizonte" DOUBLE PRECISION,
    "y_demanda_futura_lead_time" DOUBLE PRECISION,
    "safety_stock" DOUBLE PRECISION,
    "horizonte_dias" INTEGER,
    "target_horizonte_completo" INTEGER,
    "baseline_threshold" DOUBLE PRECISION,
    "baseline_order_up_to" DOUBLE PRECISION,
    "baseline_qtd_comprar" DOUBLE PRECISION,
    "baseline_comprar" INTEGER,
    "criticidade_score" DOUBLE PRECISION,
    "y_criticidade_score" DOUBLE PRECISION,
    "y_nivel_criticidade" TEXT,
    "split_temporal" TEXT
);

COPY ml.abt_reposicao ("ingredient_id", "date", "nome_ingrediente", "unidade", "categoria_id", "is_compravel", "is_produzido_internamente", "categoria", "perfil_perecivel_estimado", "quantidade_por_unidade_de_compra", "saldo_atual", "consumo_ingrediente_dia", "dia_da_semana", "is_friday", "dias_ate_sexta", "is_weekend", "mes", "semana_do_ano", "dia_do_mes", "is_summer", "is_sao_joao", "is_holiday", "nome_feriado", "tipo_feriado", "is_carnaval_window", "menor_preco_disponivel", "preco_medio_disponivel", "maior_preco_disponivel", "menor_lead_time", "lead_time_medio_fornecedores", "qtd_fornecedores_disponiveis", "maior_desconto_disponivel", "min_to_discount", "fornecedor_mais_barato", "fornecedor_mais_rapido", "preco_min_max_ratio", "flag_indisponibilidade", "ingrediente_afetado_por_indisponibilidade", "produto_indisponivel_relacionado", "dias_em_indisponibilidade", "audit_qtd_pedida_no_dia", "audit_valor_pedido_no_dia", "audit_comprou_no_dia", "audit_order_type_no_dia", "lead_time_pedido_no_dia", "saldo_lag_1", "saldo_lag_7", "variacao_estoque_1d", "variacao_estoque_7d", "flag_ruptura", "consumo_lag_1d", "consumo_lag_7d", "consumo_lag_14d", "consumo_lag_28d", "media_movel_consumo_7d", "desvio_consumo_7d", "consumo_max_7d", "media_movel_consumo_14d", "desvio_consumo_14d", "consumo_max_14d", "media_movel_consumo_28d", "desvio_consumo_28d", "consumo_max_28d", "tendencia_consumo_7_vs_28", "dias_desde_ultimo_consumo", "qtd_pedida_no_dia_audit", "comprou_no_dia_audit", "valor_pedido_no_dia_audit", "order_type_no_dia_audit", "total_pedido_30d", "media_qtd_pedida_30d", "lead_time_medio_realizado", "dias_desde_ultimo_pedido", "qtd_ultimo_pedido", "tipo_ultimo_pedido", "pedidos_em_aberto", "qtd_em_transito", "estoque_em_aberto", "qtd_em_transito_no_horizonte", "dias_para_proxima_entrega", "stock_position", "lead_time_previsto", "dias_de_cobertura", "flag_subestoque", "flag_sobrestoque", "y_qtd_comprar", "y_threshold", "y_comprar", "y_demanda_futura_horizonte", "y_demanda_futura_lead_time", "safety_stock", "horizonte_dias", "target_horizonte_completo", "baseline_threshold", "baseline_order_up_to", "baseline_qtd_comprar", "baseline_comprar", "criticidade_score", "y_criticidade_score", "y_nivel_criticidade", "split_temporal")
FROM '/ml_dataset_outputs/abt_reposicao_part1.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

COPY ml.abt_reposicao ("ingredient_id", "date", "nome_ingrediente", "unidade", "categoria_id", "is_compravel", "is_produzido_internamente", "categoria", "perfil_perecivel_estimado", "quantidade_por_unidade_de_compra", "saldo_atual", "consumo_ingrediente_dia", "dia_da_semana", "is_friday", "dias_ate_sexta", "is_weekend", "mes", "semana_do_ano", "dia_do_mes", "is_summer", "is_sao_joao", "is_holiday", "nome_feriado", "tipo_feriado", "is_carnaval_window", "menor_preco_disponivel", "preco_medio_disponivel", "maior_preco_disponivel", "menor_lead_time", "lead_time_medio_fornecedores", "qtd_fornecedores_disponiveis", "maior_desconto_disponivel", "min_to_discount", "fornecedor_mais_barato", "fornecedor_mais_rapido", "preco_min_max_ratio", "flag_indisponibilidade", "ingrediente_afetado_por_indisponibilidade", "produto_indisponivel_relacionado", "dias_em_indisponibilidade", "audit_qtd_pedida_no_dia", "audit_valor_pedido_no_dia", "audit_comprou_no_dia", "audit_order_type_no_dia", "lead_time_pedido_no_dia", "saldo_lag_1", "saldo_lag_7", "variacao_estoque_1d", "variacao_estoque_7d", "flag_ruptura", "consumo_lag_1d", "consumo_lag_7d", "consumo_lag_14d", "consumo_lag_28d", "media_movel_consumo_7d", "desvio_consumo_7d", "consumo_max_7d", "media_movel_consumo_14d", "desvio_consumo_14d", "consumo_max_14d", "media_movel_consumo_28d", "desvio_consumo_28d", "consumo_max_28d", "tendencia_consumo_7_vs_28", "dias_desde_ultimo_consumo", "qtd_pedida_no_dia_audit", "comprou_no_dia_audit", "valor_pedido_no_dia_audit", "order_type_no_dia_audit", "total_pedido_30d", "media_qtd_pedida_30d", "lead_time_medio_realizado", "dias_desde_ultimo_pedido", "qtd_ultimo_pedido", "tipo_ultimo_pedido", "pedidos_em_aberto", "qtd_em_transito", "estoque_em_aberto", "qtd_em_transito_no_horizonte", "dias_para_proxima_entrega", "stock_position", "lead_time_previsto", "dias_de_cobertura", "flag_subestoque", "flag_sobrestoque", "y_qtd_comprar", "y_threshold", "y_comprar", "y_demanda_futura_horizonte", "y_demanda_futura_lead_time", "safety_stock", "horizonte_dias", "target_horizonte_completo", "baseline_threshold", "baseline_order_up_to", "baseline_qtd_comprar", "baseline_comprar", "criticidade_score", "y_criticidade_score", "y_nivel_criticidade", "split_temporal")
FROM '/ml_dataset_outputs/abt_reposicao_part2.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

CREATE TABLE ml.abt_reposicao_sample_100 (
    LIKE ml.abt_reposicao INCLUDING DEFAULTS
);

COPY ml.abt_reposicao_sample_100
FROM '/ml_dataset_outputs/abt_reposicao_sample_100.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

DROP TABLE IF EXISTS ml.abt_pedidos_eventos;
CREATE TABLE ml.abt_pedidos_eventos (
    "pedido_id" TEXT,
    "supplier_id" TEXT,
    "ingredient_id" TEXT,
    "nome_ingrediente" TEXT,
    "qtd_pedida" DOUBLE PRECISION,
    "valor_pedido" DOUBLE PRECISION,
    "data_pedido" DATE,
    "data_entrega_prevista" DATE,
    "status" TEXT,
    "order_type" TEXT,
    "date" DATE,
    "categoria" TEXT,
    "unidade" TEXT,
    "saldo_atual" DOUBLE PRECISION,
    "stock_position" DOUBLE PRECISION,
    "criticidade_score" DOUBLE PRECISION,
    "baseline_threshold" DOUBLE PRECISION,
    "baseline_qtd_comprar" DOUBLE PRECISION,
    "y_threshold" DOUBLE PRECISION,
    "y_qtd_comprar" DOUBLE PRECISION,
    "y_nivel_criticidade" TEXT,
    "consumo_ingrediente_dia" DOUBLE PRECISION,
    "media_movel_consumo_7d" DOUBLE PRECISION,
    "media_movel_consumo_14d" DOUBLE PRECISION,
    "media_movel_consumo_28d" DOUBLE PRECISION,
    "pedidos_em_aberto" INTEGER,
    "qtd_em_transito" DOUBLE PRECISION,
    "dias_para_proxima_entrega" INTEGER,
    "lead_time_previsto" INTEGER,
    "menor_preco_disponivel" DOUBLE PRECISION,
    "preco_medio_disponivel" DOUBLE PRECISION,
    "menor_lead_time" INTEGER,
    "qtd_fornecedores_disponiveis" INTEGER,
    "is_holiday" INTEGER,
    "is_friday" INTEGER,
    "flag_indisponibilidade" INTEGER,
    "split_temporal" TEXT
);

COPY ml.abt_pedidos_eventos ("pedido_id", "supplier_id", "ingredient_id", "nome_ingrediente", "qtd_pedida", "valor_pedido", "data_pedido", "data_entrega_prevista", "status", "order_type", "date", "categoria", "unidade", "saldo_atual", "stock_position", "criticidade_score", "baseline_threshold", "baseline_qtd_comprar", "y_threshold", "y_qtd_comprar", "y_nivel_criticidade", "consumo_ingrediente_dia", "media_movel_consumo_7d", "media_movel_consumo_14d", "media_movel_consumo_28d", "pedidos_em_aberto", "qtd_em_transito", "dias_para_proxima_entrega", "lead_time_previsto", "menor_preco_disponivel", "preco_medio_disponivel", "menor_lead_time", "qtd_fornecedores_disponiveis", "is_holiday", "is_friday", "flag_indisponibilidade", "split_temporal")
FROM '/ml_dataset_outputs/abt_pedidos_eventos.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

CREATE INDEX IF NOT EXISTS idx_ml_abt_reposicao_ingredient_date
    ON ml.abt_reposicao ("ingredient_id", "date");

CREATE INDEX IF NOT EXISTS idx_ml_abt_reposicao_split
    ON ml.abt_reposicao ("split_temporal");

CREATE INDEX IF NOT EXISTS idx_ml_abt_reposicao_sample_ingredient_date
    ON ml.abt_reposicao_sample_100 ("ingredient_id", "date");

CREATE INDEX IF NOT EXISTS idx_ml_pedidos_eventos_ingredient_date
    ON ml.abt_pedidos_eventos ("ingredient_id", "data_pedido");

ANALYZE ml.abt_reposicao;
ANALYZE ml.abt_reposicao_sample_100;
ANALYZE ml.abt_pedidos_eventos;
