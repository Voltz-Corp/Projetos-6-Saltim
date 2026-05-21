# Sanity report - ABT Reposicao

## Arquivos gerados

- `outputs/abt_reposicao_part1.csv`
- `outputs/abt_reposicao_part2.csv`
- `outputs/abt_pedidos_eventos.csv`

## Contagens

- Linhas ABT: 247,000
- Linhas esperadas: 247,000
- Ingredientes na ABT: 200
- Ingredientes compraveis esperados: 200
- Linhas CAT0015 na ABT: 0
- Eventos de pedido: 15,647

## Datas

- Inicio ABT: 2023-01-01
- Fim ABT: 2026-05-19

## Targets

- Taxa y_comprar: 25.41%
- y_qtd_comprar media: 8.6062
- y_qtd_comprar p95: 19.0000
- y_threshold medio: 16.6598
- Targets negativos: 0

## Splits

- test: 27,800
- train: 182,400
- validation: 36,800

## Validacoes principais

- ABT uma linha por ingredient_id x date: True
- Todos os ingredientes da ABT sao compraveis: True
- Todos os targets sao nao negativos: True
- Dataset de eventos preserva order_type: True
