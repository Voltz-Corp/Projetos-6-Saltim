<p align="center">
  <img src="assets/saltim-logo.svg" alt="Saltim logo" width="220" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Em%20desenvolvimento-green?style=for-the-badge&logo=github" alt="Status" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi" alt="Backend" />
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react" alt="Frontend" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-316192?style=for-the-badge&logo=postgresql" alt="Database" />
</p>

<p align="center">
  <a href="#sobre-o-projeto">Sobre</a> •
  <a href="#leitura-do-projeto">Leitura do projeto</a> •
  <a href="#funcionalidades-principais">Funcionalidades</a> •
  <a href="#tecnologias">Tecnologias</a> •
  <a href="#como-executar">Como executar</a> •
  <a href="#entregaveis">Entregáveis</a> •
  <a href="#equipe">Equipe</a>
</p>

<a id="sobre-o-projeto"></a>
## 🤔 **Sobre o Projeto**

O **Saltim Café** é a solução de controle de estoque da cafeteria Saltim. O sistema foi pensado para apoiar a operação diária de insumos, contagem, ajuste de quantidades e rastreabilidade das movimentações.

O repositório mistura duas camadas complementares: a aplicação web de estoque, feita em **React + Vite + FastAPI**, e os materiais analíticos que dão base ao domínio, incluindo notebooks, scripts de geração e o pipeline exploratório em ML.

<a id="leitura-do-projeto"></a>
## 📚 **Leitura do Projeto**

<details>
<summary>Clique para abrir a leitura técnica do domínio</summary>

Os PDFs de definição e plano técnico mostram que o problema do Saltim vai além de uma tela de estoque. A proposta do projeto é estruturar a operação com dados próprios e dados externos, cobrindo:

* previsão de necessidade de compra;
* recomendação de fornecedor;
* uso de dados de vendas, estoque e fornecedores;
* métricas de avaliação para classificação e regressão.

No notebook de exploração, essa ideia aparece na forma de um pipeline com carga de dados, EDA, limpeza, tratamento de outliers e baseline preditivo semanal. Já os scripts em `data/scripts/` mostram a preparação de bases sintéticas de vendas e estoques para sustentar esse cenário.

</details>

<a id="funcionalidades-principais"></a>
## ⭐ **Funcionalidades Principais**

### **📋 Estoque e consulta**

* Visualização do estoque com busca, filtros e paginação.
* Classificação automática por status: OK, Atenção, Crítico e Esgotado.
* Ordenação por categoria, nome, preço e quantidade.

### **🧮 Contagem operacional**

* Fluxo guiado de contagem por categoria de insumos.
* Progresso global e progresso por categoria.
* Salvamento em lote ao final da conferência.

### **✏️ Edição de ingredientes**

* Alteração individual de nome, unidade, preço, categoria e quantidade mínima.
* Atualização direta na API com retorno imediato ao estoque.

### **🧾 Histórico**

* Registro das alterações de contagem com quantidade anterior, nova quantidade e delta.
* Consulta do histórico geral e por ingrediente.

<a id="tecnologias"></a>
## 🧰 **Tecnologias**

<details>
<summary>Clique para ver as tecnologias usadas</summary>

### **Frontend**

* React 19
* TypeScript
* Vite
* TanStack Router
* TanStack Query
* TanStack Table
* Tailwind CSS 4

### **Backend**

* FastAPI
* SQLAlchemy
* Pydantic
* Uvicorn
* psycopg2-binary

### **Dados e análise**

* PostgreSQL 16
* Mailpit para captura local de emails de pedidos
* CSVs em `data/`
* Carga relacional dos CSVs no schema `public` via backend
* Datasets/saídas de ML no schema `ml` e em `data/ml_dataset/outputs/`
* Notebooks e utilitários de ML em `ml/notebooks/`
* Jobs operacionais de ML em `ml/jobs/`
* MLflow 3.12 (tracking server + Model Registry + artefatos)
* Modelos/stack: scikit-learn e XGBoost
* Scripts de geração em `data/scripts/`

</details>

<a id="como-executar"></a>
## 🚀 **Como Executar**

### **Pré-requisitos**

* Bun para o frontend
* Python 3.11+ para o backend
* Docker e Docker Compose para Postgres, MLflow e Mailpit
* Bash para executar o script unico:
  * Linux/WSL: terminal normal
  * Windows: Git Bash ou WSL2

### **1. Executar em modo desenvolvimento**

```bash
./scripts/start-all.sh
```

O script sobe Postgres, MLflow e Mailpit, instala dependencias quando necessario, inicia o backend em `http://localhost:8000` e o frontend em `http://localhost:5173`.

Tambem funciona chamar diretamente:

```bash
./scripts/run-dev.sh
```

No Windows, execute pelo **Git Bash** ou pelo **WSL2**. O script detecta automaticamente o Python do virtualenv em `.venv/bin/python` ou `.venv/Scripts/python.exe`.

Ao iniciar, o backend executa os SQLs de `backend/db/` e carrega os CSVs de `data/` no schema `public` e os datasets de `data/ml_dataset/outputs/` no schema `ml`. Para iniciar sem recarregar os CSVs:

```bash
LOAD_CSV_DATA_ON_STARTUP=0 ./scripts/run-dev.sh
```

Servicos opcionais:

```bash
START_MLFLOW=0 ./scripts/run-dev.sh   # sobe sem MLflow
START_MAILPIT=0 ./scripts/run-dev.sh  # sobe sem inbox de emails
START_DB=0 ./scripts/run-dev.sh       # usa um Postgres ja existente
```

SMTP local de desenvolvimento:

* Inbox de emails: `http://localhost:8025`
* SMTP local: `localhost:1025`
* O backend ja inicia com `SMTP_HOST=localhost`, `SMTP_PORT=1025`, `SMTP_FROM_EMAIL=pedidos@saltim.local` e `SMTP_USE_TLS=0`.

### **2. Executar manualmente o backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### **3. Executar manualmente o frontend**

```bash
cd frontend
bun install
bun run dev
```

### **4. Acessar o sistema**

* Frontend: `http://localhost:5173`
* Backend: `http://localhost:8000`
* API docs: `http://localhost:8000/docs`
* Health check: `http://localhost:8000/health`
* Inbox de emails de pedidos: `http://localhost:8025`
* MLflow UI: `http://localhost:5000`
* Configuracoes de aparencia: `http://localhost:5173/configuracoes/aparencia`

### **Rotas novas de pedidos e emails**

* `POST /api/pedidos`: cria pedidos e tenta enviar um email por fornecedor com os itens e quantidades confirmados.
* A resposta inclui `email_results`, com um registro por fornecedor:
  * `sent`: email enviado.
  * `disabled`: SMTP nao configurado.
  * `missing_email`: fornecedor sem email cadastrado.
  * `failed`: falha no envio; o pedido continua salvo.
* Os emails de desenvolvimento aparecem no Mailpit em `http://localhost:8025`.

### **Rotas de exportacao**

Formatos aceitos em todas as rotas: `pdf`, `excel`, `csv`, `json`, `xml`, `yaml`.
O formato `excel` gera arquivo `.xlsx` com filtros automaticos, colunas ajustadas e cabecalho laranja.

* `GET /api/export/estoque?format=csv&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`: exporta o historico de movimentacoes do estoque no periodo.
* `GET /api/export/pedidos?format=csv&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`: exporta o historico de pedidos realizados no periodo.
* `GET /api/export/fornecedores?format=csv`: exporta a lista completa de fornecedores cadastrados, sem filtro de data.

### **5. ML (modelo de criticidade) e MLflow**

Este repositório inclui um pipeline de **ML para criticidade de estoque**. A ideia é estimar um **limiar dinâmico de “alerta de compra”** por ingrediente e, a partir dele, derivar a criticidade operacional.

**O que o modelo prevê (target):**

* `y_alert_threshold_pct`: percentual (0–1) que representa o limiar de cobertura de estoque a partir do qual o item deve ser classificado como **Alerta de compra**.
* `y_critical_threshold_pct`: limiar crítico derivado do limiar de alerta (gap fixo no utilitário `two_stage_common.py`).

A classificação final usada nos relatórios/jobs é derivada de `cobertura_estoque_pct` vs. esses limiares (labels: `OK` e `Alerta de compra`).

#### MLflow (tracking server)

Os notebooks registram **métricas, predições, gráficos e o artefato do modelo** no MLflow (não geramos `.pkl` versionados no repositório).

Para subir o MLflow com backend store em PostgreSQL (definido no `docker-compose.yml`):

```bash
docker compose up -d --build db mlflow
```

* O **backend store** (experimentos/runs/Model Registry) fica no Postgres.
* Os **artefatos** (modelos, gráficos, CSVs logados) ficam no volume Docker `mlflow_artifacts`.

Acesse:

* MLflow UI: `http://localhost:5000`

Variáveis relevantes:

* `MLFLOW_TRACKING_URI` (default: `http://localhost:5000`)

> Dica: para rodar o sistema web sem MLflow, use `START_MLFLOW=0 ./scripts/run-dev.sh`.

#### Rodar notebooks de ML

Pré-requisitos: Python 3.11+ e Jupyter.

```bash
cd ml
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Os notebooks ficam em `ml/notebooks/` e usam, por padrão, `MLFLOW_TRACKING_URI=http://localhost:5000`.

* `01_modelos_teste/`: experimentos e comparações rápidas.
* `02_modelos_finais/`: tuning e champions (ex.: RandomForest e XGBoost) com dataset completo.

#### Job: relatório diário de criticidade (inferência)

O job `ml/jobs/generate_criticality_report.py` executa uma inferência operacional (por dia), **carrega um modelo do MLflow** e grava o resultado no Postgres (schema `ml`), além de logar uma execução no MLflow.

Pré-condições:

* Postgres rodando e populado (ex.: via `./scripts/run-dev.sh`, que carrega CSVs no startup quando `LOAD_CSV_DATA_ON_STARTUP=1`).
* MLflow rodando (`docker compose up -d mlflow`).

Variáveis do job:

* `DATABASE_URL` (default: `postgresql://saltim:saltim123@localhost:5432/saltim_db`)
* `MLFLOW_TRACKING_URI` (default: `http://localhost:5000`)
* `CRITICIDADE_MODEL_URI` (default: um `runs:/.../model`)
* `CRITICIDADE_DAILY_MLFLOW_EXPERIMENT` (default: `jobs/criticidade/relatorio_diario`)

Exemplo:

```bash
python ml/jobs/generate_criticality_report.py --reference-date today
```

<a id="teste-modelo"></a>
## 🧪 **Testar o modelo no Frontend**

A forma mais simples de validar o modelo “no projeto” (sem rodar notebook) é pela tela de **Criticidade** no próprio frontend:

* Rota: `http://localhost:5173/ml/criticidade` (menu lateral → **Criticidade**)
* Ação: clique em **“Rodar modelo”** para disparar a geração do relatório do dia.
* Resultado: a página atualiza o status (`running/success/failed`), KPIs e as tabelas/gráficos com os itens em **OK** vs **Alerta de compra**.

Pré-condições para funcionar:

* Backend rodando e acessível pelo frontend (por padrão `http://localhost:8000`).
  * Se necessário, configure `VITE_API_URL` no frontend (ex.: `VITE_API_URL=http://localhost:8000`).
* Postgres rodando e populado (ex.: `./scripts/run-dev.sh` com `LOAD_CSV_DATA_ON_STARTUP=1`).
* MLflow rodando para carregar o modelo configurado em `CRITICIDADE_MODEL_URI`.

<a id="entregaveis"></a>
## 📁 **Entregáveis**

<details>
<summary>Clique para abrir os artefatos do projeto</summary>

* [backend/](backend) - API FastAPI, modelos, schemas e integração com o banco.
* [frontend/](frontend) - interface de controle de estoque com dashboard, estoque, contagem e edição.
* [data/](data) - bases CSV, notebooks e scripts de apoio.
* [ml/](ml) - notebooks/utilitários de ML e jobs de criticidade.
* [mlflow/](mlflow) - imagem (Dockerfile) do tracking server MLflow.
* [entregaveis/](entregaveis) - materiais complementares do projeto.

</details>

<a id="equipe"></a>
## 👥 **Equipe**

<div align="center">

| [<img src="https://github.com/Thomazrlima.png" width="100" style="border-radius:50%"><br>Thomaz](https://github.com/Thomazrlima) | [<img src="https://github.com/paulorosadodev.png" width="100" style="border-radius:50%"><br>Paulo](https://github.com/paulorosadodev) | [<img src="https://github.com/gustavoyoq.png" width="100" style="border-radius:50%"><br>Gustavo](https://github.com/gustavoyoq) | [<img src="https://github.com/viniciusdandrade.png" width="100" style="border-radius:50%"><br>Vinícius](https://github.com/viniciusdandrade) | [<img src="https://github.com/Sophia-15.png" width="100" style="border-radius:50%"><br>Sophia](https://github.com/Sophia-15) | [<img src="https://github.com/Pandor4b.png" width="100" style="border-radius:50%"><br>Ana](https://github.com/Pandor4b) | [<img src="https://github.com/deadcube04.png" width="100" style="border-radius:50%"><br>Gabriel](https://github.com/deadcube04) | [<img src="https://github.com/aguiarth.png" width="100" style="border-radius:50%"><br>Thaís](https://github.com/aguiarth) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 📧  trl  | 📧  phrf | 📧  gmam | 📧  vaj  | 📧  sagp | 📧 acgs | 📧  gmca | 📧 thcba |

</div>

<details>
<summary><strong>📝 Observações</strong></summary>

* O backend aceita requisições do frontend em `localhost:5173` e `localhost:4173`.
* O banco usa as credenciais padrão declaradas em `docker-compose.yml` para desenvolvimento local.
* O projeto foi organizado para apoiar o fluxo real de controle de estoque da Saltim e o material analítico que sustenta o domínio.

</details>

<div align="center">

## ☕ Saltim Café

Controle de estoque com foco em contagem, rastreabilidade e apoio à decisão.

</div>
