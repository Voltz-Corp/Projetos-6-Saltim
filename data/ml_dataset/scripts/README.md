# Scripts

Esta pasta guarda scripts de geracao da ABT e datasets auxiliares.

## Script disponivel

- `build_abt_reposicao.py`: gera a ABT `ingredient_id x date`, o dataset auxiliar pedido-a-pedido e um relatorio de sanidade.

O script le as bases originais em `data/` e salva resultados em `data/ml_dataset/outputs/`.

## Comando

```bash
python data/ml_dataset/scripts/build_abt_reposicao.py
```
