# Desenvolvimento, Avaliação e Comparação dos Modelos de Machine Learning

## Contextualização do Problema

Esta etapa teve como objetivo identificar quais famílias de modelos de Machine Learning apresentavam maior aderência ao problema de gestão preditiva de estoque da cafeteria. O foco dos notebooks analisados foi a previsão da criticidade de estoque e da necessidade de compra, isto é, a classificação de ingredientes entre as classes `OK` e `Alerta de compra`, além da estimação de limiares quantitativos de alerta para apoiar decisões de reposição.

Essa abordagem está alinhada à proposta de transformar o processo atual, manual e reativo, em um processo preditivo. Ao antecipar ingredientes com risco de ruptura, a solução reduz a urgência operacional, melhora o planejamento de compras e cria condições para que os gestores tenham mais tempo para cotar fornecedores.

## Estratégia Experimental

Foram desenvolvidos três notebooks de treinamento inicial e um notebook de comparação consolidada:

- `01_two_stage_knn.ipynb`: modelos baseados em distância, com KNN como abordagem principal.
- `02_two_stage_linear.ipynb`: modelos lineares, com Regressão Linear e Regressão Logística.
- `03_two_stage_tree_ensembles.ipynb`: modelos baseados em árvores, com Random Forest como abordagem principal.
- `04_two_stage_model_comparison.ipynb`: consolidação, comparação e visualização dos resultados.

Nas execuções registradas, foi utilizada uma amostra de 25% da base completa. A base completa possui 247.000 registros e 105 colunas após a geração dos alvos de criticidade; a amostra utilizada nos experimentos possui 61.750 registros. A divisão temporal da amostra foi composta por 45.480 registros de treino, 9.275 de validação e 6.995 de teste. A taxa observada das classes foi de 84,43% para `OK` e 15,57% para `Alerta de compra`, com 73 atributos utilizados como variáveis explicativas.

A utilização da amostra reduzida teve caráter exploratório: permitiu testar diferentes famílias de algoritmos com menor custo computacional antes da execução em escala completa. Essa decisão é adequada para a fase inicial do projeto, pois reduz tempo de experimentação e permite identificar rapidamente quais abordagens justificam maior investimento de treinamento e ajuste fino.

## Metodologia de Treinamento

Os notebooks utilizaram um pipeline em duas etapas. Na primeira, modelos de regressão estimaram o limiar percentual de alerta de estoque (`y_alert_threshold_pct`). A partir desse limiar previsto, foi derivada a criticidade predita do ingrediente. Na segunda, modelos de classificação aprenderam diretamente a prever a classe binária de criticidade, distinguindo `OK` de `Alerta de compra`.

O pré-processamento foi padronizado entre os experimentos. Variáveis numéricas receberam imputação por mediana e padronização com `StandardScaler`; variáveis categóricas receberam imputação pelo valor mais frequente e codificação `OneHotEncoder`. Esse desenho garante comparação mais justa entre modelos, pois mantém a mesma engenharia de dados e altera apenas a família algorítmica.

## Modelos Avaliados

Foram avaliadas três famílias principais:

- Modelos baseados em distância: `KNN Regressor` e `KNN Classifier`.
- Modelos lineares: `Linear Regression` e `Logistic Regression`.
- Modelos baseados em árvores e ensembles: `Random Forest`, `XGBoost` e `Gradient Boosting`, em versões de regressão e classificação.

Os modelos lineares oferecem maior interpretabilidade e menor complexidade computacional, mas tendem a capturar pior relações não lineares. O KNN é simples e intuitivo, porém mais sensível à escala, dimensionalidade e custo de inferência. Os modelos baseados em árvores, especialmente Random Forest e XGBoost, apresentam maior capacidade de capturar interações não lineares, com custo computacional mais elevado e menor interpretabilidade direta.

## Métricas Utilizadas

Para os modelos de classificação, foram utilizadas `accuracy`, `balanced_accuracy`, `f1_macro`, `precision_macro`, `recall_macro`, `ROC AUC` e `average_precision`. A métrica `f1_macro` é especialmente relevante porque considera o desempenho médio entre as classes, evitando que a classe majoritária `OK` domine a avaliação.

Para os modelos de regressão, foram utilizadas `RMSE`, `MAE` e `R²`, além das métricas derivadas da criticidade resultante, como `accuracy`, `balanced_accuracy` e `f1_macro`.

## Resultados dos Modelos de Regressão

| Modelo | Accuracy | F1 macro | RMSE | MAE | R² |
|---|---:|---:|---:|---:|---:|
| Random Forest Regressor | 0,998856 | 0,997815 | 0,046589 | 0,035292 | 0,778663 |
| XGBoost Regressor | 0,997999 | 0,996182 | 0,046804 | 0,035411 | 0,776620 |
| Gradient Boosting Regressor | 0,997856 | 0,995898 | 0,051189 | 0,038615 | 0,732801 |
| Linear Regression | 0,995568 | 0,991523 | 0,083430 | 0,057833 | 0,290209 |
| KNN Regressor | 0,993567 | 0,987667 | 0,071022 | 0,048211 | 0,485638 |

O melhor desempenho regressivo foi obtido pelo `Random Forest Regressor`, com o menor RMSE e MAE e o maior R². O `XGBoost Regressor` apresentou desempenho muito próximo, indicando boa capacidade de generalização. Já a Regressão Linear e o KNN ficaram abaixo, principalmente em R², sugerindo menor aderência ao padrão não linear do problema.

## Resultados dos Modelos de Classificação

| Modelo | Accuracy | Balanced accuracy | F1 macro | ROC AUC | Average precision |
|---|---:|---:|---:|---:|---:|
| Random Forest Classifier | 0,997856 | 0,995711 | 0,995898 | 0,999948 | 0,999708 |
| Gradient Boosting Classifier | 0,997570 | 0,996297 | 0,995362 | 0,999796 | 0,994169 |
| XGBoost Classifier | 0,997570 | 0,994409 | 0,995345 | 0,999960 | 0,999782 |
| Logistic Regression | 0,985132 | 0,980257 | 0,972056 | 0,998877 | 0,992742 |
| KNN Classifier | 0,982988 | 0,959356 | 0,966934 | 0,990533 | 0,969034 |

Entre os classificadores, o `Random Forest Classifier` obteve o melhor `f1_macro` e manteve métricas de ranking probabilístico muito elevadas. O `XGBoost Classifier` apresentou o maior `average_precision`, mas com `f1_macro` ligeiramente inferior ao Random Forest. Os modelos lineares e KNN tiveram desempenho inferior, embora ainda apresentem resultados razoáveis.

## Comparação Consolidada no Notebook 04

O notebook `04_two_stage_model_comparison.ipynb` carregou 18 modelos registrados e consolidou a comparação técnica e operacional. A análise incluiu ranking dos modelos, métricas operacionais, recomendações por ingrediente e visualizações comparativas.

As visualizações utilizadas foram:

- Distribuição de criticidade predita por modelo.
- Gráficos de barras para métricas dos modelos de regressão (`RMSE`, `MAE`, `F1 macro`).
- Gráficos de barras para métricas dos classificadores (`ROC AUC`, `average_precision`, `balanced_accuracy`, `F1 macro`).
- Curvas ROC dos classificadores.
- Curvas Precision-Recall dos classificadores.
- Gráficos de dispersão entre limiar real e limiar predito.
- Matrizes de confusão para os 18 modelos avaliados.
- Ranking dos ingredientes com mais dias preditos em alerta de compra.

## Seleção dos Modelos Mais Promissores

Considerando a etapa seguinte do projeto, os dois modelos mais promissores para avanço em escala completa foram o `Random Forest Regressor` e o `XGBoost Regressor`. A escolha se justifica porque ambos apresentaram os melhores resultados na tarefa de estimação dos limiares de alerta, que é central para transformar a gestão de estoque em um processo preditivo.

O `Random Forest Regressor` teve o melhor resultado geral, com `RMSE = 0,046589`, `MAE = 0,035292` e `R² = 0,778663`. O `XGBoost Regressor` apresentou desempenho praticamente equivalente, com `RMSE = 0,046804`, `MAE = 0,035411` e `R² = 0,776620`. Essa proximidade indica que ambos são candidatos fortes para tuning e avaliação em base completa.

## Conclusão

Os experimentos iniciais atendem aos critérios da disciplina ao treinar múltiplos modelos de Machine Learning, comparar pelo menos duas famílias algorítmicas distintas e apresentar métricas quantitativas e visualizações para análise comparativa. A etapa demonstrou que modelos baseados em árvores capturam melhor os padrões do problema do que abordagens lineares ou baseadas em distância.

Assim, os resultados sustentam a escolha de Random Forest e XGBoost para a próxima fase, pois combinam alto desempenho preditivo, boa capacidade de generalização e aderência operacional ao problema de antecipação de compras. Esses modelos oferecem uma base sólida para evoluir o projeto em direção a uma solução de gestão de estoque mais preditiva, reduzindo o risco de ruptura e melhorando o tempo disponível para tomada de decisão e negociação com fornecedores.

# Complemento: Ajuste Fino, Comparação Final e Escolha do XGBoost

## Continuidade a Partir dos Modelos de Teste

Após a etapa inicial de experimentação, os modelos `Random Forest Regressor` e `XGBoost Regressor` avançaram para a seleção final por terem apresentado os melhores resultados na tarefa de regressão do limiar de alerta de compra. Essa decisão foi operacionalmente coerente com o problema do projeto, pois a previsão do limiar de criticidade é a base para transformar os dados históricos de estoque em recomendações objetivas de reposição.

A etapa final foi materializada nos notebooks `05_random_forest_regressor_threshold_tuning.ipynb`, `06_xgboost_regressor_threshold_tuning.ipynb` e `07_modelos_finais_comparison.ipynb`. Diferentemente da etapa exploratória, os dois notebooks de tuning foram configurados com `use_full_dataset=True`, isto é, executaram o pipeline de ajuste fino sobre a base completa disponível, preservando a separação temporal entre dados de treino, validação e teste.

## Estratégia de Validação e Ajuste de Hiperparâmetros

Para o ajuste dos modelos finais foi utilizada a técnica `RandomizedSearchCV`, e não Grid Search ou Optuna. Essa escolha é justificável porque o espaço de busca dos dois modelos contém múltiplas combinações possíveis de hiperparâmetros; nesse cenário, a busca aleatória reduz o custo computacional e permite explorar regiões diferentes do espaço de parâmetros sem testar exaustivamente todas as combinações.

A validação cruzada foi realizada com `TimeSeriesSplit(k=3)`. Essa estratégia é mais adequada do que um k-fold aleatório tradicional porque os dados possuem estrutura temporal. Em problemas de estoque e consumo, misturar observações futuras no treino de folds anteriores poderia gerar vazamento temporal e superestimar o desempenho do modelo. Por esse mesmo motivo, Leave-One-Out não foi aplicado: além de ser computacionalmente caro para a base completa, não preservaria de forma adequada a lógica temporal necessária para o problema.

Além da validação cruzada, os notebooks mantiveram avaliação em holdout por meio do conjunto de teste temporal. Assim, a comparação final utilizou duas camadas de validação: o desempenho médio nos folds de validação temporal e as métricas finais em teste.

## Espaços de Busca Avaliados

No notebook `05_random_forest_regressor_threshold_tuning.ipynb`, o Random Forest foi ajustado com `n_iter = 6`, `cv_splits = 3`, `random_state = 42`, `use_full_dataset = True` e dois perfis de peso: `uniform` e `alert_focus`.

| Hiperparâmetro | Valores avaliados |
|---|---|
| `model__n_estimators` | `[80, 120, 180]` |
| `model__max_depth` | `[6, 10, 14]` |
| `model__min_samples_split` | `[5, 10, 20]` |
| `model__min_samples_leaf` | `[2, 4, 8]` |
| `model__max_features` | `["sqrt", 0.5, 0.8]` |
| `model__bootstrap` | `[True]` |

O melhor perfil de peso do Random Forest foi `uniform`, com os seguintes hiperparâmetros: `n_estimators = 120`, `max_depth = 14`, `min_samples_split = 10`, `min_samples_leaf = 8`, `max_features = 0.8` e `bootstrap = True`.

No notebook `06_xgboost_regressor_threshold_tuning.ipynb`, o XGBoost foi ajustado com `n_iter = 8`, `cv_splits = 3`, `random_state = 42`, `use_full_dataset = True` e os mesmos perfis de peso: `uniform` e `alert_focus`.

| Hiperparâmetro | Valores avaliados |
|---|---|
| `model__n_estimators` | `[100, 180, 260]` |
| `model__max_depth` | `[2, 3, 4]` |
| `model__learning_rate` | `[0.03, 0.05, 0.08]` |
| `model__subsample` | `[0.85, 1.0]` |
| `model__colsample_bytree` | `[0.85, 1.0]` |
| `model__min_child_weight` | `[1, 3, 5]` |
| `model__gamma` | `[0.0, 0.1]` |
| `model__reg_alpha` | `[0.0, 0.1]` |
| `model__reg_lambda` | `[1.0, 2.0]` |

O melhor perfil de peso do XGBoost também foi `uniform`, com os seguintes hiperparâmetros: `n_estimators = 260`, `max_depth = 4`, `learning_rate = 0.08`, `subsample = 0.85`, `colsample_bytree = 0.85`, `min_child_weight = 5`, `gamma = 0.1`, `reg_alpha = 0.1` e `reg_lambda = 2.0`.

## Resultados do Tuning

| Modelo | Baseline test RMSE | Test RMSE final | Ganho vs. baseline | Test MAE | Test R² |
|---|---:|---:|---:|---:|---:|
| Random Forest Regressor | 0,046108 | 0,045343 | 0,000764 | 0,034145 | 0,801977 |
| XGBoost Regressor | 0,051662 | 0,046962 | 0,004700 | 0,035402 | 0,787586 |

Em desempenho bruto no holdout de teste, o Random Forest apresentou melhor resultado, com `test_rmse = 0,045343`, `test_mae = 0,034145` e `test_r² = 0,801977`. O XGBoost ficou ligeiramente atrás nesse critério, com `test_rmse = 0,046962`, `test_mae = 0,035402` e `test_r² = 0,787586`.

Entretanto, a análise não se limitou ao menor erro em teste. O XGBoost apresentou maior ganho em relação ao seu baseline, reduzindo o RMSE de `0,051662` para `0,046962`, uma melhora de `0,004700`. Isso indica que o processo de tuning teve impacto mais expressivo no XGBoost do que no Random Forest, cujo ganho frente ao baseline foi de `0,000764`.

## Validação Cruzada, Variância e Diagnóstico de Ajuste

| Modelo | CV RMSE médio | CV RMSE desvio | Coeficiente de variação | Estabilidade |
|---|---:|---:|---:|---|
| Random Forest Regressor | 0,053637 | 0,002765 | 0,051545 | moderada |
| XGBoost Regressor | 0,054655 | 0,002616 | 0,047870 | alta |

Na validação cruzada temporal, o Random Forest manteve menor RMSE médio de validação (`0,053637`) em comparação ao XGBoost (`0,054655`). Porém, o XGBoost apresentou menor dispersão relativa entre folds, com coeficiente de variação `0,047870`, classificado como estabilidade alta no notebook de comparação. O Random Forest teve coeficiente de variação `0,051545`, classificado como estabilidade moderada.

O notebook 07 também comparou o risco de overfitting por meio da diferença entre erro de treino e erro de validação:

| Modelo | Train RMSE | CV validation RMSE | Gap treino-validação | Gap ratio | Diagnóstico |
|---|---:|---:|---:|---:|---|
| Random Forest Regressor | 0,039623 | 0,053637 | 0,014014 | 0,353693 | adequate |
| XGBoost Regressor | 0,047679 | 0,054655 | 0,006977 | 0,146332 | adequate |

Ambos os modelos foram classificados como `adequate`, com a explicação de que não houve sinal forte de sobreajuste ou subajuste pelos critérios adotados. Ainda assim, o XGBoost apresentou uma diferença menor entre treino e validação, sugerindo comportamento mais equilibrado entre ajuste e generalização. O Random Forest obteve menor erro absoluto, mas com gap relativo mais alto, o que indica maior distância entre desempenho de treino e validação.

As visualizações de apoio geradas nos notebooks finais incluíram curvas de aprendizado e análise de resíduos. Essas visualizações foram usadas para complementar a leitura das métricas, verificando a evolução do erro com diferentes tamanhos de treino e a distribuição dos resíduos no conjunto de teste.

## Comparação Multicritério do Notebook 07

O notebook `07_modelos_finais_comparison.ipynb` consolidou a decisão com base em múltiplos critérios: precisão, generalização, robustez e complexidade. Essa análise é importante porque, em um produto operacional, o menor erro bruto nem sempre representa a melhor escolha final se outro modelo oferece comportamento mais estável e menor complexidade relativa.

| Modelo | Rank precisão | Rank generalização | Rank robustez | Rank complexidade | Score geral |
|---|---:|---:|---:|---:|---:|
| XGBoost Regressor | 2,0 | 1,6 | 1,0 | 1,0 | 0,8 |
| Random Forest Regressor | 1,0 | 1,4 | 2,0 | 2,0 | 0,7 |

O Random Forest foi identificado como o melhor modelo em desempenho bruto, pois teve menor `test_rmse` e menor `test_mae`. Também foi apontado como melhor em generalização quando considerado apenas o menor RMSE médio nos folds já executados. No entanto, o XGBoost foi classificado como melhor custo-benefício, modelo mais robusto, modelo mais simples pelo proxy disponível e modelo recomendado para produção.

O critério de complexidade utilizou como proxy o produto entre número de estimadores e profundidade máxima configurada. O Random Forest apresentou proxy `1680` (`120 x 14`), enquanto o XGBoost apresentou proxy `1040` (`260 x 4`). Embora essa métrica não substitua medições reais de tempo, CPU, RAM ou tamanho do modelo, ela sugere uma estrutura menos profunda para o XGBoost, com potencial de melhor custo operacional.

Na robustez, o notebook utilizou a razão `RMSE/MAE` em teste. O XGBoost apresentou `1,326535`, ligeiramente menor que o Random Forest (`1,327954`), sendo classificado como mais robusto pelo indicador disponível. A diferença é pequena, mas reforça a decisão multicritério quando combinada à menor variância relativa na validação cruzada e ao menor proxy de complexidade.

## Avaliação Estatística Disponível

O notebook 07 incluiu testes estatísticos sobre o `validation_rmse` por fold. O teste t pareado entre Random Forest e XGBoost resultou em `p_value = 0,162020`, enquanto o Wilcoxon resultou em `p_value = 0,250000`. O próprio notebook registra que esses testes têm baixo poder estatístico, pois há apenas três folds disponíveis. Portanto, não há evidência estatística forte para afirmar superioridade absoluta de um modelo sobre o outro apenas pelos folds.

Essa limitação reforça a escolha por uma decisão multicritério: como a diferença de erro entre os modelos é pequena e estatisticamente pouco conclusiva, a escolha final considera também estabilidade, robustez, complexidade e integração ao produto.

## Estrutura de Inferência e Integração ao Produto

A entrega de integração foi materializada no job `ml/jobs/generate_criticality_report.py`. Esse job carrega o modelo final pelo MLflow, monta a base operacional do dia, executa inferência com `model.predict`, calcula os limiares previstos e deriva a criticidade final de cada ingrediente.

O modelo padrão configurado no job é o XGBoost champion:

- `DEFAULT_MODEL_NAME = "XGBoost Regressor"`
- `DEFAULT_MODEL_URI = "runs:/58db15b4b9364e6cb1bf7d9ebe65f922/model"`

A função `score_current_stock` aplica o modelo ao conjunto operacional atual, calcula `limiar_alerta_predito_pct`, `limiar_critico_predito_pct`, `criticidade_predita`, `necessita_compra`, `score_alerta_compra` e `rank_position`. Em seguida, o pipeline persiste os resultados nas tabelas `ml.criticidade_report_runs` e `ml.criticidade_report_items`.

Além disso, o backend expõe uma estrutura mínima de integração por endpoints:

- `GET /api/ml/criticidade/job-status/latest`: consulta o status mais recente do job de criticidade.
- `GET /api/ml/criticidade/relatorio/latest`: consulta o relatório de criticidade mais recente.
- `POST /api/ml/criticidade/relatorio/run`: executa o job de criticidade para a data atual e retorna o relatório gerado.

Essa estrutura atende ao requisito de disponibilizar uma função de inferência ou integração mínima do modelo treinado ao produto, pois conecta o modelo final registrado no MLflow ao fluxo operacional do sistema.

## Execução do Pipeline Completo e Evidências de Estabilidade

O pipeline final executa as seguintes etapas: leitura dos dados operacionais, atualização de históricos até a data de referência, construção da ABT de reposição, geração dos alvos de criticidade, carregamento do modelo final via MLflow, inferência dos limiares de alerta, derivação da criticidade, persistência dos resultados em banco e registro de métricas no MLflow.

As métricas finais consolidadas para o XGBoost foram:

| Métrica | Valor |
|---|---:|
| `test_rmse` | 0,046962 |
| `test_mae` | 0,035402 |
| `test_r²` | 0,787586 |
| `accuracy` | 0,998165 |
| `balanced_accuracy` | 0,997126 |
| `f1_macro` | 0,996518 |
| `precision_macro` | 0,995913 |
| `recall_macro` | 0,997126 |
| `best_cv_validation_rmse_mean` | 0,054655 |
| `best_cv_validation_rmse_std` | 0,002136 |
| `best_cv_validation_r²_mean` | 0,720535 |

Essas métricas indicam que o modelo final mantém bom desempenho no conjunto de teste e comportamento estável na validação cruzada temporal. A escolha do XGBoost, portanto, não se baseia exclusivamente em menor erro absoluto, mas em uma leitura mais ampla dos critérios de avaliação do notebook 07: desempenho competitivo, estabilidade alta, menor gap relativo entre treino e validação, menor proxy de complexidade, robustez ligeiramente superior e integração operacional já configurada como modelo padrão do pipeline de criticidade.
