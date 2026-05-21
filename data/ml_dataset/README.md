# Dataset de ML para Reposicao

Esta pasta concentra os artefatos usados para construir, carregar e compartilhar os datasets de Machine Learning de reposicao de ingredientes do Saltim Cafe.

## Objetivo

Organizar a criacao da ABT principal e dos datasets auxiliares para treinar modelos que respondam, para cada ingrediente e data:

- se e necessario comprar;
- quanto deve ser comprado;
- qual e o threshold de criticidade ou ponto de reordem.

## Estrutura

- `scripts/`: scripts de construcao dos datasets.
- `outputs/`: CSVs gerados pelo pipeline.
- `reports/`: relatorios de validacao e qualidade.
- `config/`: parametros do pipeline.
- `db/`: SQL de carga dos datasets no Postgres.

## Como gerar os CSVs

Execute a partir da raiz do repositorio:

```bash
python data/ml_dataset/scripts/build_abt_reposicao.py
```

Saidas principais:

- `data/ml_dataset/outputs/abt_reposicao_part1.csv`
- `data/ml_dataset/outputs/abt_reposicao_part2.csv`
- `data/ml_dataset/outputs/abt_pedidos_eventos.csv`
- `data/ml_dataset/outputs/abt_reposicao_sample_100.csv`
- `data/ml_dataset/reports/sanity_report.md`

## Carga no banco

Ao subir o Docker Compose, o servico `db-init` executa `data/ml_dataset/db/load_ml_dataset.sql` e carrega os CSVs particionados da ABT e o dataset de pedidos no schema `ml`.
