# Decisoes de modelagem e validacao

Este documento registra as escolhas feitas para os notebooks:

- `05_random_forest_regressor_threshold_tuning.ipynb`
- `06_xgboost_regressor_threshold_tuning.ipynb`

Os dois notebooks treinam regressores para prever `y_alert_threshold_pct`, o limiar dinamico de alerta de compra. Nenhum modelo e salvo como `.pkl` local; todos os modelos, metricas, resultados de busca, predicoes e graficos sao registrados no MLflow.

## 1. Estrategia de validacao

Escolha: `TimeSeriesSplit`, uma variacao temporal de validacao cruzada K-Fold.

Justificativa teorica:

- O problema usa historico de estoque e compras, entao existe dependencia temporal.
- K-Fold aleatorio tradicional mistura passado e futuro entre treino e validacao, criando vazamento temporal.
- Stratified K-Fold e apropriado para classificacao; aqui o alvo principal e regressao.
- Leave-One-Out e caro, instavel para series temporais e tambem nao preserva a estrutura passado -> futuro.
- Holdout simples ja existe no dataset (`train`, `validation`, `test`), mas fornece apenas uma estimativa pontual e nao permite analisar variancia entre dobras.

Justificativa pratica:

- `TimeSeriesSplit` permite medir a estabilidade por fold sem usar dados futuros para prever o passado.
- O conjunto `test` e mantido fora do tuning e usado apenas na avaliacao final do modelo campeao.
- `train` e `validation` sao combinados e ordenados por `date` para a busca de hiperparametros. O `test` continua como holdout final.

## 2. Pesos das amostras

Foram definidos quatro perfis de peso para testar como o modelo se comporta quando alguns tipos de erro ficam mais caros:

- `uniform`: peso 1 para todas as linhas. Serve como controle.
- `alert_focus`: aumenta o peso de casos em `Alerta de compra` e baixa cobertura de estoque.
- `critical_gap_focus`: aumenta o peso quando a cobertura esta abaixo ou muito proxima do limiar critico.
- `threshold_extreme_focus`: aumenta o peso de limiares de alerta mais distantes da mediana, para reduzir erro em casos extremos.

Cada perfil roda um `RandomizedSearchCV` completo. Assim, a comparacao nao varia apenas hiperparametros do estimador; ela tambem avalia custos de erro diferentes.

## 3. Hyperparameter tuning

Escolha: `RandomizedSearchCV`.

Motivo:

- Grid Search completo ficaria caro porque cada candidato passa por pipeline com imputacao, escala, one-hot encoding e validacao temporal.
- Random Search cobre melhor regioes amplas do espaco de busca com orcamento controlado.
- Cada candidato, cada perfil de peso e o modelo campeao sao registrados no MLflow.

Metricas de selecao:

- Principal: RMSE medio nas dobras de validacao temporal.
- Secundarias: MAE, R2, desvio padrao do RMSE entre folds e metricas operacionais de criticidade derivadas do limiar previsto.

## 4. Espacos de busca

### Random Forest Regressor

Parametros avaliados:

- `n_estimators`: quantidade de arvores.
- `max_depth`: controle de complexidade.
- `min_samples_split`: tamanho minimo para dividir um no.
- `min_samples_leaf`: tamanho minimo de folha.
- `max_features`: quantidade de atributos considerados por split.
- `bootstrap`: amostragem com reposicao.

O espaco privilegia combinacoes que testam desde arvores rasas e conservadoras ate florestas mais profundas. Isso ajuda a identificar overfitting via diferenca entre RMSE de treino e validacao.

### XGBoost Regressor

Parametros avaliados:

- `n_estimators`: numero de arvores boosting.
- `max_depth`: profundidade das arvores fracas.
- `learning_rate`: tamanho do passo.
- `subsample`: amostragem de linhas.
- `colsample_bytree`: amostragem de colunas.
- `min_child_weight`: regularizacao estrutural.
- `gamma`: ganho minimo para split.
- `reg_alpha` e `reg_lambda`: regularizacao L1/L2.

XGBoost foi mantido como segunda opcao recomendada porque tende a capturar interacoes nao lineares com bom controle de regularizacao, especialmente quando comparado a modelos lineares.

## 5. Diagnostico de ajuste

Os notebooks calculam:

- Media, desvio padrao e variancia do RMSE entre folds.
- RMSE/MAE/R2 em treino, validacao cruzada e teste final.
- Ganho de RMSE contra baseline.
- Diagnostico automatico:
  - `overfitting`: validacao muito pior que treino.
  - `underfitting`: tuning nao melhora o baseline e erro de treino segue alto.
  - `unstable`: variancia alta entre folds.
  - `adequate`: sem sinal forte dos problemas acima.

## 6. Visualizacoes

Cada notebook gera e envia ao MLflow:

- Curva de aprendizado: RMSE de treino e validacao por tamanho crescente de treino.
- Analise de residuos: dispersao dos residuos contra previsoes e distribuicao dos residuos.

Para regressao nao foi usada matriz de confusao como diagnostico principal. A matriz de confusao e mais adequada para classificacao; aqui a avaliacao central e o erro do limiar previsto. Ainda assim, o pipeline calcula metricas operacionais de criticidade derivadas desse limiar.

## 7. Dataset completo nos modelos finais

Os notebooks em `02_modelos_finais` usam `load_abt_full()` por meio de `use_full_dataset=True` no `RegressorTuningConfig`.

Essa escolha separa explicitamente os experimentos rapidos, que podem usar `load_abt_sample()`, dos modelos finais, que precisam aproveitar 100% das linhas disponiveis nos splits `train`, `validation` e `test`.

O notebook `07_modelos_finais_comparison.ipynb` compara os champions finais registrados no MLflow. Alem de RMSE, MAE, R2 e ganho contra baseline, ele calcula `model_size_mb` baixando o artefato `model` de cada run e somando o tamanho dos arquivos serializados.
