# Do Script ao Serviço — Como Servir Agentes LLM

Repositório da aula hands-on sobre **deploy e serving de agentes LLM**.
Material da pós-graduação em Machine Learning Engineering — FIAP.

## O que você vai aprender

Como transformar um agente funcional em um serviço confiável, resiliente e
deployável, passando por três padrões de comunicação e controles de produção:

- **Request-Response Síncrono** — o padrão mais simples e seus limites
- **Streaming SSE** — feedback em tempo real sem polling
- **Fila Assíncrona** — desacoplamento com RabbitMQ e Celery
- **Controles de Produção** — concorrência, timeouts, health check e logging estruturado

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [Python 3.11+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (gerenciador de pacotes Python)
- [API Key do Gemini](https://aistudio.google.com/apikey) (gratuita)

## Quickstart

```bash
# 1. Clone o repositório
git clone <repo-url>
cd deploy-agentes-llm

# 2. Configure a API key
cp stages/01-sync/.env.example stages/01-sync/.env
# Edite stages/01-sync/.env e insira sua GEMINI_API_KEY

# 3. Rode o primeiro estágio
make stage-1
```

Acesse [http://localhost:8000/docs](http://localhost:8000/docs) para ver a API interativa.

## Estrutura do Repositório

```
deploy-agentes-llm/
├── stages/                 # Código progressivo da aula
│   ├── 01-sync/            # Endpoint síncrono (request-response)
│   ├── 02-stream/          # + Streaming SSE (eventos em tempo real)
│   ├── 03-async/           # + Padrão assíncrono (RabbitMQ + Celery)
│   └── 04-production/      # + Controles de produção
├── textbook/               # Material teórico interativo (HTML)
├── notebooks/              # Notebooks complementares (deep dives)
├── Makefile                # Atalhos para tudo
└── README.md               # Este arquivo
```

## Estágios

Cada estágio é **autossuficiente** — entre na pasta e rode `docker compose up --build`.
O Makefile oferece atalhos para todos eles.

| Estágio | Tema | Serviços | Endpoints |
|---------|------|----------|-----------|
| **01-sync** | Request-Response Síncrono | FastAPI | `POST /invoke` |
| **02-stream** | + Streaming SSE | FastAPI | + `POST /stream` |
| **03-async** | + Fila Assíncrona | FastAPI, Celery, RabbitMQ, PostgreSQL | + `POST /invoke/async`, `GET /tasks/{id}` |
| **04-production** | + Controles de Produção | FastAPI, Celery, RabbitMQ, PostgreSQL | + `GET /health` |

### Controles de Produção (Estágio 04)

| Controle | Arquivo | Descrição |
|----------|---------|-----------|
| Semáforo de concorrência | `concurrency.py` | Limita chamadas simultâneas ao LLM; excedente aguarda na fila ou recebe 429 |
| Timeout em camadas | `timeouts.py` | Request → Agente → Tool; retorna 504 se exceder |
| Erros tipados | `errors.py` | Cada falha mapeia para um status HTTP semântico (429, 502, 504, 500) |
| Health check | `health.py` | Monitora PostgreSQL, RabbitMQ e API do Gemini |
| Logging estruturado | `logging_config.py` | JSON em produção, console colorido em desenvolvimento |

## Textbook

Material teórico interativo com componentes visuais que acompanham a aula:

```bash
make textbook
# Acesse http://localhost:8080
```

## Notebooks

Deep dives complementares para explorar os conceitos com mais profundidade:

| Notebook | Tema |
|----------|------|
| `01-gemini-api-basics` | SDK do Gemini, chamadas e tool calling |
| `02-sse-under-the-hood` | Como SSE funciona por baixo do protocolo HTTP |
| `03-asyncio-semaphore` | Concorrência com asyncio na prática |
| `04-broker-worker-queues` | RabbitMQ, Celery e padrões de fila |
| `05-react-from-scratch` | Loop ReAct manual sem framework |

```bash
make notebooks
```

## Comandos Disponíveis

```bash
make help               # Lista todos os comandos disponíveis
```

### Estágios

```bash
make stage-1            # Sobe Estágio 01 (Sync)
make stage-2            # Sobe Estágio 02 (Stream)
make stage-3            # Sobe Estágio 03 (Async)
make stage-4            # Sobe Estágio 04 (Production)
make stage-down         # Para todos os estágios em execução
```

### Material

```bash
make textbook           # Abre o textbook interativo (http://localhost:8080)
make notebooks          # Abre os notebooks Jupyter
```

### Demos por estágio

Comandos para testar cada endpoint. Suba o estágio desejado antes de usar.

```bash
# Estágio 01
make invoke-1           # Testa POST /invoke

# Estágio 02
make invoke-2           # Testa POST /invoke
make stream-2           # Testa POST /stream (SSE em tempo real)

# Estágio 03
make invoke-3           # Testa POST /invoke
make stream-3           # Testa POST /stream (SSE)
```

### Fluxo assíncrono (Estágio 03/04)

```bash
make async-submit       # Enfileira uma task (retorna task_id)
make async-submit-batch # Enfileira 5 tasks de uma vez
make async-poll ID=xxx  # Consulta status de uma task específica
make async-poll-loop ID=xxx  # Polling contínuo até completar (a cada 2s)
```

Exemplo de fluxo completo:

```bash
# 1. Suba o estágio 03
make stage-3

# 2. Em outro terminal, enfileira uma task
make async-submit
# Copie o task_id da resposta

# 3. Faça polling para acompanhar
make async-poll-loop ID=<task-id-copiado>
# Verá: pending → processing → completed
```

### Testes do Estágio 04 (Production)

Requer `make stage-4` rodando.

```bash
make test-sync          # Testa POST /invoke (com semáforo + timeout)
make test-stream        # Testa POST /stream (SSE com semáforo)
make test-async         # Testa fluxo assíncrono completo
make test-timeout       # Envia query complexa para testar timeout
make test-concurrency   # 15 requests simultâneas (espera alguns 429s)
make test-health        # Testa GET /health
```

### Utilidades

```bash
make expose             # Expõe a API via ngrok (requer ngrok instalado)
make clean              # Para containers e remove volumes
make logs               # docker compose logs -f do estágio 04
```

## Stack Tecnológica

| Componente | Tecnologia |
|------------|------------|
| API | FastAPI |
| Agente | LangGraph + Gemini 2.5 Flash |
| Message Broker | RabbitMQ |
| Task Worker | Celery |
| Banco de Dados | PostgreSQL |
| Banco do Agente | SQLite |
| Containerização | Docker Compose |
| Pacotes | uv |
| Logging | structlog + Rich |
