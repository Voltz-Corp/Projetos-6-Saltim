<p align="center">
  <img src="frontend/public/images/saltim_logo.jpg" alt="Saltim Cafe" width="220" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Em%20desenvolvimento-green?style=for-the-badge&logo=github" alt="Status" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi" alt="Backend" />
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react" alt="Frontend" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-316192?style=for-the-badge&logo=postgresql" alt="Database" />
  <img src="https://img.shields.io/badge/MLflow-Tracking%20%2B%20Registry-0194E2?style=for-the-badge" alt="MLflow" />
</p>

<p align="center">
  <a href="#sobre-o-projeto">Sobre</a> |
  <a href="#funcionalidades-principais">Funcionalidades</a> |
  <a href="#arquitetura-e-tecnologias">Arquitetura</a> |
  <a href="#como-executar">Como executar</a> |
  <a href="#apis-por-dominio">APIs</a> |
  <a href="#aprendizado-de-maquina">ML</a> |
  <a href="#entregaveis">Entregáveis</a> |
  <a href="#equipe">Equipe</a>
</p>

<a id="sobre-o-projeto"></a>
## Sobre o Projeto

O **Saltim Cafe** é uma aplicação de gestão operacional para uma cafeteria, com foco em estoque, vendas, compras, fornecedores e apoio à decisão. O produto evoluiu de um controle de estoque para uma plataforma integrada: registra contagens, acompanha pedidos, opera mesas/comandas, gera planos de compra, exporta relatórios e usa aprendizado de máquina para apoiar a criticidade de reposição.

O repositório reúne três frentes principais:

- **Aplicação web** em React + Vite, com dashboard, estoque, vendas, compras, fornecedores, pedidos, criticidade, aparência, chat e acessibilidade.
- **Backend FastAPI** com PostgreSQL, SQLAlchemy, carga automática de CSVs, exportações, envio local de emails e endpoints operacionais.
- **Camada analítica/ML** com ABT de reposição, notebooks de comparação/tuning, MLflow e job de inferência de criticidade.

<a id="funcionalidades-principais"></a>
## Funcionalidades Principais

### Dashboard executivo

- KPIs de estoque, consumo, cobertura, vendas e criticidade.
- Filtros globais por período, categoria, ingrediente, mês e eventos/feriados.
- Séries históricas alinhadas de estoque e vendas, ranking de receitas, faturamento mensal/trimestral e pedidos por dia da semana.
- Rankings por unidade (`KG`, `UND`, `L`) para maiores/menores saldos, saídas e categorias.
- Exportação do dashboard em PDF ou Excel, respeitando o tema visual selecionado.

### Estoque e contagem

- Consulta de estoque com busca, filtros, paginação e status operacional.
- Edição individual de ingredientes, unidade, categoria e metadados de cadastro.
- Fluxo guiado de contagem por categoria, com progresso, ajuste por item e finalização.
- Histórico de contagens com detalhe por categoria, delta e rastreabilidade de alterações.
- Integração com criticidade do modelo quando há relatório de ML disponível.

### Fornecedores

- Listagem de fornecedores com KPIs, busca e exportação.
- Cadastro de fornecedores com CNPJ, telefone, email, prazo médio e itens fornecidos.
- Perfil do fornecedor com produtos, preços, descontos, prazo e histórico de pedidos.
- Base de fornecedores usada pelos módulos de pedidos, compras e recomendações.

### Pedidos

- Histórico paginado de pedidos agrupados por fornecedor e data.
- Filtros por status, fornecedor e período.
- Criação de pedidos com recomendação automática de fornecedor por preço efetivo, desconto, prazo e detratores.
- Pedidos em trânsito, detalhe por grupo e marcação de entrega.
- Entrega de pedido aplica entrada no estoque e atualiza dashboard/criticidade.
- Envio de emails por fornecedor via SMTP local ou real, com retorno por status (`sent`, `missing_email`, `disabled`, `failed`).

### Compras e Plano Maestro

- Tela `/compras/planejamento` para gerar plano de compra com horizonte configurável.
- Sugestões baseadas no consumo recente do horizonte escolhido, estoque atual, itens em trânsito, fornecedores e criticidade.
- Ajuste automático de quantidades aprovadas, fornecedor selecionado e observações.
- Remoção de itens antes da aprovação, simulação de cenários e recálculo de totais.
- Envio de cotações, aprovação do plano e geração de pedidos agrupados.
- Exportação do plano em PDF ou Excel.

A criticidade exibida no plano segue esta precedência: relatório do modelo (`model_report`), fallback por ingrediente em `ml.abt_reposicao` e, por último, regra operacional.

### Vendas, mesas e comandas

- Área de vendas em `/vendas`, com layout próprio para operação de salão.
- Painel de mesas livres/ocupadas, abertura de comanda e edição dos itens da conta.
- Busca de receitas/produtos vendáveis, validação de disponibilidade e avisos de estoque.
- Fechamento de mesa com forma de pagamento, valor pago, troco, CPF/nome do cliente e observações.
- Cancelamento de vendas e fechamento diário para atualizar resumos usados pelo dashboard.

### Criticidade e ML operacional

- Tela `/ml/criticidade` para rodar o modelo, consultar status do job e visualizar relatório.
- KPIs de itens em alerta, distribuição por categoria, itens zerados e ranking de criticidade.
- Relatório persistido em `ml.criticidade_report_runs` e `ml.criticidade_report_items`.
- O estoque e o plano de compras consomem a criticidade mais recente quando disponível.

### Agente Saltim

- Botão flutuante persistente em todas as páginas, incluindo a área de vendas.
- Chat arrastável com sugestões iniciais e prévia tabular dos resultados.
- Endpoint público `POST /api/agent/chat`, que retorna texto amigável, colunas e linhas de prévia, sem expor SQL ao usuário final.
- Agente Text-to-SQL com Gemini, memória de sessão, enriquecimento de contexto e guardrails somente leitura.
- Fallback para perguntas de compra quando os relatórios de criticidade ainda estão vazios, usando a ABT mais recente.

### Aparência e acessibilidade

- Configuração de aparência em `/configuracoes/aparencia` e alias `/aparencia`.
- Temas clássicos, modo claro/escuro e temas especiais de seleções.
- Exportações em PDF/Excel acompanham a identidade visual selecionada.
- Widget VLibras montado no shell da aplicação.

<a id="arquitetura-e-tecnologias"></a>
## Arquitetura e Tecnologias

### Frontend

- React 19, TypeScript e Vite.
- TanStack Router para rotas e TanStack Query para dados assíncronos.
- TanStack Table, Recharts, MUI, React Select, React Day Picker e lucide-react.
- Tailwind CSS 4 com tema runtime via `frontend/src/theme/appearance.tsx`.
- Shell principal com sidebar, chat e VLibras; área de vendas com layout próprio.

### Backend

- FastAPI, Pydantic, SQLAlchemy e Uvicorn.
- PostgreSQL 16 em Docker Compose.
- Carga de CSVs de `data/` para o schema `public`.
- Carga dos datasets analíticos de `data/ml_dataset/outputs/` para o schema `ml`.
- Exportações em CSV, JSON, XML, YAML, Excel e PDF.
- Mailpit para captura local de emails de pedidos/cotações.
- Agente Text-to-SQL em `backend/agent/`, com `google-genai` e `sqlglot`.

### Dados, ML e operação local

- `data/`: bases CSV e scripts geradores de dados sintéticos.
- `data/ml_dataset/`: construção da ABT de reposição e relatório de sanidade.
- `ml/notebooks/`: exploração, comparação de modelos, tuning e decisão final.
- `ml/jobs/generate_criticality_report.py`: job operacional de inferência.
- `mlflow/`: imagem Docker para MLflow Tracking Server e Model Registry.
- `docker-compose.yml`: Postgres, MLflow e Mailpit.

<a id="como-executar"></a>
## Como Executar

### Pré-requisitos

- Bun para o frontend.
- Python 3.11+ para backend, ML e notebooks.
- Docker e Docker Compose para Postgres, MLflow e Mailpit.
- Bash para o script único:
  - Linux/WSL: terminal normal.
  - Windows: Git Bash ou WSL2.

### 1. Configurar variáveis de ambiente

Copie `.env.example` para `.env` e ajuste quando necessário:

```env
GOOGLE_API_KEY= # Gerar chave no Google AI Studio
SMTP_ENABLED=1
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM_EMAIL=pedidos@saltim.local
SMTP_FROM_NAME=Saltim Cafe
SMTP_USE_TLS=0
```

Variáveis importantes:

- `GOOGLE_API_KEY`: habilita o agente Text-to-SQL com Gemini.
- `GOOGLE_MODEL`: opcional; por padrão o agente usa `gemini-3.1-flash-lite-preview`.
- `VITE_API_URL`: URL do backend para o frontend; padrão `http://localhost:8000`.
- `DATABASE_URL`: URL do Postgres; padrão `postgresql://saltim:saltim123@localhost:5432/saltim_db`.
- `MLFLOW_TRACKING_URI`: URL do MLflow; padrão `http://localhost:5000`.
- `CRITICIDADE_MODEL_URI`: URI do modelo de criticidade; por padrão aponta para o champion XGBoost.
- `CRITICIDADE_DAILY_MLFLOW_EXPERIMENT`: experimento do job diário; padrão `jobs/criticidade/relatorio_diario`.
- `SMTP_*`: configura o envio de emails; por padrão aponta para o Mailpit local.

### 2. Executar em modo desenvolvimento

```bash
./scripts/start-all.sh
```

O script sobe Postgres, MLflow e Mailpit, cria/usa o virtualenv do backend, instala dependências quando necessário, inicia a API em `http://localhost:8000` e o frontend em `http://localhost:5173`.

Também é possível chamar diretamente:

```bash
./scripts/run-dev.sh
```

Ao iniciar, o backend executa os SQLs de `backend/db/` e carrega os CSVs no banco. Para iniciar sem recarregar os CSVs:

```bash
LOAD_CSV_DATA_ON_STARTUP=0 ./scripts/run-dev.sh
```

Serviços opcionais:

```bash
START_MLFLOW=0 ./scripts/run-dev.sh
START_MAILPIT=0 ./scripts/run-dev.sh
START_DB=0 ./scripts/run-dev.sh
```

### 3. Executar manualmente o backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app --reload-dir agent --reload-dir db --reload-exclude ".venv/*" --port 8000
```

Em Linux/WSL/macOS, ative o virtualenv com:

```bash
source .venv/bin/activate
```

### 4. Executar manualmente o frontend

```bash
cd frontend
bun install
bun run dev
```

### 5. Acessar serviços locais

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Mailpit inbox: `http://localhost:8025`
- SMTP local: `localhost:1025`
- MLflow UI: `http://localhost:5000`
- Aparência: `http://localhost:5173/configuracoes/aparencia`
- Criticidade: `http://localhost:5173/ml/criticidade`
- Compras: `http://localhost:5173/compras/planejamento`
- Vendas: `http://localhost:5173/vendas`

<a id="apis-por-dominio"></a>
## APIs por Domínio

### Dashboard e exportações

- `GET /api/dashboard`: KPIs, rankings, alertas e filtros.
- `GET /api/dashboard/estoque-historico`: série histórica de estoque.
- `GET /api/dashboard/vendas-historico`: série histórica de vendas.
- `GET /api/dashboard/faturamento-resumo`: resumo mensal e trimestral.
- `GET /api/dashboard/pedidos-semana`: pedidos por dia da semana.
- `GET /api/dashboard/receitas-ranking`: ranking de receitas.
- `GET /api/export/dashboard`: exportação em PDF ou Excel.

### Estoque e contagem

- `GET /api/estoque` e `GET /api/estoque/paginado`: consulta de estoque.
- `PATCH /api/estoque`: atualização em lote.
- `PATCH /api/ingredientes/{ingrediente_id}`: edição de ingrediente.
- `POST /api/contagens`: inicia contagem.
- `GET /api/contagens` e `GET /api/contagens/{id}/detalhe`: histórico e detalhe.
- `PATCH /api/contagens/{id}/finalizar`: finaliza contagem.
- `GET /api/log` e `GET /api/log/{ingrediente_id}`: rastreabilidade de alterações.
- `GET /api/export/estoque`: exportação do histórico.

### Fornecedores

- `GET /api/fornecedores`: lista fornecedores, KPIs e itens.
- `POST /api/fornecedores`: cadastra fornecedor.
- `GET /api/fornecedores/{fornecedor_id}`: perfil, produtos e pedidos.
- `GET /api/export/fornecedores`: exportação.

### Pedidos

- `POST /api/pedidos/recomendacao`: recomenda fornecedor por item.
- `POST /api/pedidos`: cria pedidos e tenta enviar emails por fornecedor.
- `GET /api/pedidos`: histórico agrupado por fornecedor e data.
- `GET /api/pedidos/em-transito`: pedidos em aberto.
- `GET /api/pedidos/grupos/{supplier_id}/{order_date}`: detalhe do grupo.
- `PATCH /api/pedidos/grupos/{supplier_id}/{order_date}/entregar`: marca entrega e aplica estoque.
- `GET /api/export/pedidos`: exportação.

### Vendas

- `GET /api/vendas/produtos`: produtos/receitas disponíveis para venda.
- `GET /api/vendas/mesas`: status das mesas.
- `POST /api/vendas/mesas/{mesa_numero}/pedido`: abre comanda.
- `PATCH /api/vendas/{venda_id}/itens`: atualiza itens da conta.
- `POST /api/vendas/{venda_id}/fechar`: fecha venda/mesa.
- `PATCH /api/vendas/{venda_id}/cancelar`: cancela venda.
- `GET /api/vendas`: histórico paginado.
- `POST /api/vendas/fechamento-dia`: consolida o dia.

### Compras

- `POST /api/compras/planos/gerar`: gera plano de compra.
- `GET /api/compras/planos/latest`: plano mais recente.
- `GET /api/compras/planos/{plan_id}`: detalhe do plano.
- `PATCH /api/compras/planos/{plan_id}/items/{ingredient_id}`: ajusta item.
- `DELETE /api/compras/planos/{plan_id}/items/{ingredient_id}`: remove item antes da aprovação.
- `POST /api/compras/planos/{plan_id}/simular`: simula cenário.
- `POST /api/compras/planos/{plan_id}/cotacoes/enviar`: envia cotações.
- `POST /api/compras/planos/{plan_id}/aprovar`: aprova e gera pedidos.
- `GET /api/export/compras/planos/{plan_id}`: exportação em PDF ou Excel.

### Criticidade ML e agente

- `GET /api/ml/criticidade/job-status/latest`: status do job.
- `GET /api/ml/criticidade/relatorio/latest`: relatório mais recente.
- `POST /api/ml/criticidade/relatorio/run`: executa inferência para o dia atual.
- `POST /api/agent/chat`: conversa com o agente Saltim.

### Formatos de exportação

As exportações simples aceitam `pdf`, `excel`, `csv`, `json`, `xml` e `yaml`.

- `excel` gera `.xlsx` com abas de capa, resumo, dados e gráficos quando aplicável.
- `pdf` gera relatório visual com identidade do tema selecionado.
- Dashboard e plano de compra aceitam apenas `pdf` e `excel`.

<a id="aprendizado-de-maquina"></a>
## Aprendizado de Máquina

### Objetivo

A frente de ML estima a criticidade de reposição de ingredientes. O modelo prevê um limiar percentual de alerta de estoque por ingrediente; a aplicação compara esse limiar com a cobertura atual para decidir se o item está `OK` ou em `Alerta de compra`.

Essa abordagem transforma histórico de estoque, vendas, pedidos, fornecedores e eventos operacionais em uma recomendação objetiva para antecipar rupturas e apoiar compras.

### ABT de reposição

A base analítica é gerada por `data/ml_dataset/scripts/build_abt_reposicao.py` e materializada em:

- `data/ml_dataset/outputs/abt_reposicao_part1.csv`
- `data/ml_dataset/outputs/abt_reposicao_part2.csv`
- `data/ml_dataset/outputs/abt_pedidos_eventos.csv`
- `data/ml_dataset/reports/sanity_report.md`

Dados principais do relatório de sanidade:

| Item | Valor |
|---|---:|
| Linhas da ABT | 247.000 |
| Ingredientes compráveis | 200 |
| Período | 2023-01-01 a 2026-05-19 |
| Eventos de pedido | 15.647 |
| Taxa `y_comprar` | 25,41% |
| Split treino | 182.400 linhas |
| Split validação | 36.800 linhas |
| Split teste | 27.800 linhas |

Targets e variáveis relevantes:

- `y_alert_threshold_pct`: limiar de alerta previsto pelo modelo.
- `y_critical_threshold_pct`: limiar crítico derivado do limiar de alerta.
- `criticidade_predita`: classe final derivada da cobertura atual contra os limiares.
- `necessita_compra`: indicador operacional usado no relatório e no plano de compra.
- `score_alerta_compra`: distância entre limiar crítico previsto e cobertura atual.

### Experimentos e comparação inicial

Os notebooks em `ml/notebooks/01_modelos_teste/` comparam famílias de modelos em um pipeline de duas etapas:

- `01_two_stage_knn.ipynb`: modelos baseados em distância.
- `02_two_stage_linear.ipynb`: modelos lineares.
- `03_two_stage_tree_ensembles.ipynb`: Random Forest, XGBoost e Gradient Boosting.
- `04_two_stage_model_comparison.ipynb`: consolidação de métricas e visualizações.

Foram avaliados modelos de regressão para prever o limiar e modelos de classificação para prever diretamente `OK` vs. `Alerta de compra`. As métricas principais incluem `RMSE`, `MAE`, `R²`, `accuracy`, `balanced_accuracy`, `f1_macro`, `ROC AUC` e `average_precision`.

Na fase inicial, Random Forest e XGBoost foram os candidatos mais fortes para a etapa final:

| Modelo exploratório | Accuracy | F1 macro | RMSE | MAE | R² |
|---|---:|---:|---:|---:|---:|
| Random Forest Regressor | 0,998856 | 0,997815 | 0,046589 | 0,035292 | 0,778663 |
| XGBoost Regressor | 0,997999 | 0,996182 | 0,046804 | 0,035411 | 0,776620 |

### Tuning final

Os notebooks finais ficam em `ml/notebooks/02_modelos_finais/`:

- `05_random_forest_regressor_threshold_tuning.ipynb`
- `06_xgboost_regressor_threshold_tuning.ipynb`
- `07_modelos_finais_comparison.ipynb`

Decisões de treinamento:

- Uso da base completa com `use_full_dataset=True`.
- Tuning com `RandomizedSearchCV`.
- Validação temporal com `TimeSeriesSplit(k=3)`.
- Avaliação final em holdout temporal.
- Perfis de peso avaliados: `uniform` e `alert_focus`.

Melhores hiperparâmetros encontrados:

| Modelo | Parâmetros principais |
|---|---|
| Random Forest | `n_estimators=120`, `max_depth=14`, `min_samples_split=10`, `min_samples_leaf=8`, `max_features=0.8`, `bootstrap=True` |
| XGBoost | `n_estimators=260`, `max_depth=4`, `learning_rate=0.08`, `subsample=0.85`, `colsample_bytree=0.85`, `min_child_weight=5`, `gamma=0.1`, `reg_alpha=0.1`, `reg_lambda=2.0` |

Resultados em teste:

| Modelo | Baseline test RMSE | Test RMSE final | Ganho vs. baseline | Test MAE | Test R² |
|---|---:|---:|---:|---:|---:|
| Random Forest Regressor | 0,046108 | 0,045343 | 0,000764 | 0,034145 | 0,801977 |
| XGBoost Regressor | 0,051662 | 0,046962 | 0,004700 | 0,035402 | 0,787586 |

Validação cruzada temporal:

| Modelo | CV RMSE médio | CV RMSE desvio | Coeficiente de variação | Estabilidade |
|---|---:|---:|---:|---|
| Random Forest Regressor | 0,053637 | 0,002765 | 0,051545 | moderada |
| XGBoost Regressor | 0,054655 | 0,002616 | 0,047870 | alta |

Diagnóstico de ajuste:

| Modelo | Train RMSE | CV validation RMSE | Gap treino-validação | Gap ratio | Diagnóstico |
|---|---:|---:|---:|---:|---|
| Random Forest Regressor | 0,039623 | 0,053637 | 0,014014 | 0,353693 | adequate |
| XGBoost Regressor | 0,047679 | 0,054655 | 0,006977 | 0,146332 | adequate |

### Escolha do champion

O Random Forest obteve o menor erro bruto em teste, mas o XGBoost foi escolhido como modelo recomendado para produção por decisão multicritério:

- desempenho competitivo;
- maior ganho em relação ao próprio baseline;
- estabilidade alta nos folds temporais;
- menor gap relativo entre treino e validação;
- menor proxy de complexidade (`260 x 4 = 1040`) do que o Random Forest (`120 x 14 = 1680`);
- robustez ligeiramente superior pela razão `RMSE/MAE`;
- integração operacional já configurada no job de criticidade.

Métricas finais consolidadas do XGBoost:

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

Os detalhes completos estão em `ml/notebooks/MODEL_TUNING_DECISIONS.md`.

### MLflow

O projeto usa MLflow para rastrear experimentos, registrar métricas, guardar artefatos e carregar o modelo final.

```bash
docker compose up -d --build db mlflow
```

- UI: `http://localhost:5000`
- Backend store: PostgreSQL do `docker-compose.yml`.
- Artefatos: volume Docker `mlflow_artifacts`.
- Variável padrão: `MLFLOW_TRACKING_URI=http://localhost:5000`.

### Job operacional de criticidade

O job `ml/jobs/generate_criticality_report.py` carrega o modelo do MLflow, monta o estoque operacional do dia, executa inferência e persiste o relatório no schema `ml`.

Modelo padrão:

- `DEFAULT_MODEL_NAME = "XGBoost Regressor"`
- `DEFAULT_MODEL_URI = "runs:/58db15b4b9364e6cb1bf7d9ebe65f922/model"`

Tabelas persistidas:

- `ml.job_status`
- `ml.criticidade_report_runs`
- `ml.criticidade_report_items`

Exemplo:

```bash
python ml/jobs/generate_criticality_report.py --reference-date today
```

Pré-condições:

- Postgres rodando e populado.
- MLflow rodando.
- Dependências de `ml/requirements.txt` instaladas.
- `CRITICIDADE_MODEL_URI` apontando para um modelo disponível no MLflow.

### Testar o modelo no frontend

1. Suba o ambiente com `./scripts/start-all.sh`.
2. Acesse `http://localhost:5173/ml/criticidade`.
3. Clique em `Rodar modelo`.
4. Confira status, KPIs, distribuição, itens zerados e ranking de criticidade.

<a id="agente-text-to-sql"></a>
## Agente Text-to-SQL

O agente fica em `backend/agent/` e expõe funções Python como `perguntar(question, session_id="default")`, além do endpoint `POST /api/agent/chat`.

Características:

- Usa Gemini via `google-genai`, quando `GOOGLE_API_KEY` está configurada.
- Restringe o escopo aos dados do Saltim: estoque, vendas, fornecedores, pedidos, compras e schema `ml`.
- Valida SQL com `sqlglot`.
- Bloqueia escrita, múltiplas queries e tabelas fora da allow-list.
- Adiciona ou limita `LIMIT` automaticamente.
- Mantém memória simples por sessão para perguntas de acompanhamento.
- Inclui fallback semântico para enriquecer contexto mesmo quando o modelo não está disponível.

Se `GOOGLE_API_KEY` não estiver configurada, o backend continua funcionando e o agente retorna uma mensagem amigável de configuração indisponível.

<a id="estrutura-do-repositorio"></a>
## Estrutura do Repositório

```text
.
|-- backend/
|   |-- agent/          # Agente Text-to-SQL
|   |-- app/            # API FastAPI, modelos, schemas e testes
|   `-- db/             # Scripts SQL de carga
|-- COMPRAS/            # Nota técnica sobre regra de sugestão de compras
|-- data/               # CSVs, scripts geradores e dataset de ML
|-- entregaveis/        # PDFs e materiais complementares
|-- frontend/           # Aplicação React/Vite
|-- ml/                 # Notebooks, requirements e jobs de ML
|-- mlflow/             # Dockerfile do MLflow
|-- scripts/            # Scripts de execução local
|-- docker-compose.yml
`-- README.md
```

<a id="entregaveis"></a>
## Entregáveis

- [backend/](backend) - API FastAPI, modelos, schemas, agente e testes.
- [frontend/](frontend) - aplicação web de estoque, compras, vendas, dashboard e ML.
- [data/](data) - bases CSV, scripts geradores e ABT de reposição.
- [ml/](ml) - notebooks, decisões de modelo e job operacional.
- [mlflow/](mlflow) - imagem do tracking server MLflow.
- [COMPRAS/](COMPRAS) - documentação da regra atual de sugestão de compras.
- [entregaveis/](entregaveis) - materiais formais do projeto.

<a id="equipe"></a>
## Equipe

<div align="center">

| [<img src="https://github.com/Thomazrlima.png" width="100" style="border-radius:50%"><br>Thomaz](https://github.com/Thomazrlima) | [<img src="https://github.com/paulorosadodev.png" width="100" style="border-radius:50%"><br>Paulo](https://github.com/paulorosadodev) | [<img src="https://github.com/gustavoyoq.png" width="100" style="border-radius:50%"><br>Gustavo](https://github.com/gustavoyoq) | [<img src="https://github.com/viniciusdandrade.png" width="100" style="border-radius:50%"><br>Vinícius](https://github.com/viniciusdandrade) | [<img src="https://github.com/Sophia-15.png" width="100" style="border-radius:50%"><br>Sophia](https://github.com/Sophia-15) | [<img src="https://github.com/Pandor4b.png" width="100" style="border-radius:50%"><br>Ana](https://github.com/Pandor4b) | [<img src="https://github.com/deadcube04.png" width="100" style="border-radius:50%"><br>Gabriel](https://github.com/deadcube04) | [<img src="https://github.com/aguiarth.png" width="100" style="border-radius:50%"><br>Thaís](https://github.com/aguiarth) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| trl | phrf | gmam | vaj | sagp | acgs | gmca | thcba |

</div>

## Observações

- O banco local usa as credenciais de desenvolvimento declaradas em `docker-compose.yml`.
- O backend aceita requisições do frontend em `localhost:5173` e `localhost:4173`.
- A aplicação é demonstrativa, mas os fluxos principais são persistidos no banco local.
- O modelo de criticidade depende de um artefato disponível no MLflow; sem ele, a aplicação continua operando, mas a execução do job de ML pode falhar.
- O agente usa apenas consultas de leitura e não executa alterações no banco.

<div align="center">

## Saltim Cafe

Gestão de estoque, vendas, compras e criticidade para uma operação de cafeteria mais previsível.

</div>
