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
* CSVs em `data/`
* Carga relacional dos CSVs no schema `public` via backend
* Datasets de ML no schema `ml`
* Notebooks em `data/notebooks/` e `ml/`
* Scripts de geração em `data/scripts/`

<a id="como-executar"></a>
## 🚀 **Como Executar**

### **Pré-requisitos**

* Bun para o frontend
* Python 3.11+ para o backend
* Docker e Docker Compose para o banco

### **1. Executar em modo desenvolvimento**

```bash
./scripts/run-dev.sh
```

O script sobe o Postgres, instala dependências quando necessário, inicia o backend em `http://localhost:8000` e o frontend em `http://localhost:5173`.

Ao iniciar, o backend executa os SQLs de `backend/db/` e carrega os CSVs de `data/` no schema `public` e os datasets de `data/ml_dataset/outputs/` no schema `ml`. Para iniciar sem recarregar os CSVs:

```bash
LOAD_CSV_DATA_ON_STARTUP=0 ./scripts/run-dev.sh
```

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
* Health check: `http://localhost:8000/health`

<a id="api"></a>
## 🧪 **API**

### **Estoque**

* `GET /api/estoque` - lista os ingredientes
* `GET /api/estoque/paginado` - lista paginada
* `PATCH /api/estoque` - atualiza o estoque em lote
* `PATCH /api/ingredientes/{ingrediente_id}` - edita um ingrediente

### **Histórico**

* `GET /api/log` - retorna o histórico geral de contagens
* `GET /api/log/{ingrediente_id}` - retorna o histórico de um ingrediente

### **Saúde**

* `GET /health` - verifica se a API está ativa

<a id="entregaveis"></a>
## 📁 **Entregáveis**

<details>
<summary>Clique para abrir os artefatos do projeto</summary>

* [backend/](backend) - API FastAPI, modelos, schemas e integração com o banco.
* [frontend/](frontend) - interface de controle de estoque com dashboard, estoque, contagem e edição.
* [data/](data) - bases CSV, notebooks e scripts de apoio.
* [ml/](ml) - pipeline de análise e baseline preditivo.
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
