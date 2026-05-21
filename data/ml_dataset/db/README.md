# DB load

Esta pasta contem o SQL usado para carregar os datasets de ML no Postgres.

## Arquivo

- `load_ml_dataset.sql`: cria o schema `ml`, recria as tabelas `ml.abt_reposicao` e `ml.abt_pedidos_eventos`, importa os CSVs gerados, incluindo as duas partes da ABT e cria indices basicos.

## Execucao no Docker

O servico `db-init` em `docker-compose.yml` espera o Postgres ficar saudavel e executa este SQL via `psql`.
