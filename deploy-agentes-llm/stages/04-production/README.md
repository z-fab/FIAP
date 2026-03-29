# Estagio 04 — Producao (Controles de Producao)

## O que este estagio demonstra

Este estagio e a culminacao do curso. Partimos do agente funcional dos estagios
anteriores e adicionamos os **controles que separam um prototipo de um servico
pronto para producao**.

Cada controle e um modulo separado com uma unica responsabilidade, bem comentado
para explicar **por que** cada controle existe — nao apenas como implementa-lo.

### Tabela de controles

| Arquivo | O que faz | Por que existe |
|---|---|---|
| `concurrency.py` | Semaforo com fila limitada | Evita OOM e rate limit do provider quando muitas requisicoes chegam ao mesmo tempo |
| `timeouts.py` | Limites de tempo por camada | Impede que requisicoes travadas consumam recursos indefinidamente |
| `health.py` | Verificacao de dependencias | Orquestradores (Docker, K8s) precisam saber se o container esta apto a receber trafego |
| `logging_config.py` | Logging estruturado (structlog) | Logs JSON para ferramentas de observabilidade; console colorido para desenvolvimento |
| `errors.py` | Hierarquia de excecoes tipadas | Codigos HTTP semanticos (429, 504, 502, 500) para cada tipo de falha |

### O que o Estagio 04 resolve em relacao ao Estagio 03

| Problema (Estagio 03) | Solucao (Estagio 04) |
|---|---|
| **Sem limite de concorrencia** — 100 requests = 100 agentes simultaneos | Semaforo limita a N agentes; excedente aguarda na fila ou recebe 429 |
| **Sem timeout** — agente pode travar indefinidamente | Timeout por camada (request, agente, ferramenta) cancela execucoes lentas |
| **Sem health check** — orquestrador nao sabe se o servico esta saudavel | Endpoint /health verifica PostgreSQL, RabbitMQ e Gemini API |
| **Logs de texto livre** — dificil de parsear em ferramentas | structlog emite JSON em producao, console colorido em desenvolvimento |
| **Erros genericos** — tudo vira 500 Internal Server Error | Excecoes tipadas mapeiam para 429, 504, 502, 500 com mensagens claras |
| **Sem observabilidade de requests** — impossivel rastrear problemas | Middleware adiciona request_id a todos os logs e respostas (X-Request-ID) |

---

## Arquitetura

```
Cliente HTTP
     |
     |  POST /invoke (ou /stream, /invoke/async)
     v
+--------------------------------------------------+
|  Middleware (logging_middleware)                   |
|  - Gera request_id                               |
|  - Mede duracao                                  |
|  - Loga request_completed                        |
|  - Header X-Request-ID                           |
+--------------------------------------------------+
     |
     v
+--------------------------------------------------+
|  Endpoint (/invoke, /stream)                      |
|                                                   |
|  +--------------------------------------------+  |
|  |  Semaforo (concurrency.py)                  |  |
|  |  - MAX_CONCURRENT=3 agentes simultaneos     |  |
|  |  - MAX_QUEUE_SIZE=10 na fila de espera      |  |
|  |  - 429 se fila cheia                        |  |
|  +--------------------------------------------+  |
|       |                                           |
|       v                                           |
|  +--------------------------------------------+  |
|  |  Timeout (timeouts.py)                      |  |
|  |  - AGENT_TIMEOUT=90s para execucao completa |  |
|  |  - 504 se exceder                           |  |
|  +--------------------------------------------+  |
|       |                                           |
|       v                                           |
|  +--------------------------------------------+  |
|  |  Agente LLM (agent.py)                     |  |
|  |  - ReAct loop com ferramentas               |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
     |
     v
+--------------------------------------------------+
|  Error Handler (errors.py)                        |
|  - AgentTimeoutError    -> 504                    |
|  - ConcurrencyLimitError -> 429                   |
|  - ToolExecutionError    -> 502                   |
|  - AgentExecutionError   -> 500                   |
+--------------------------------------------------+
```

Para o fluxo assincrono (`/invoke/async`), a fila RabbitMQ e os workers
Celery continuam funcionando como no estagio 03.

---

## Servicos Docker

| Servico    | Imagem                          | Porta   | Descricao |
|------------|---------------------------------|---------|-----------|
| `api`      | build local                     | `8000`  | FastAPI com todos os controles de producao |
| `worker`   | build local                     | —       | Celery worker |
| `rabbitmq` | `rabbitmq:4-management-alpine`  | `15672` | Broker de mensagens + painel de administracao |
| `postgres` | `postgres:17-alpine`            | `5432`  | Banco de dados para persistencia das tarefas |

---

## Como rodar

### 1. Configure as variaveis de ambiente

```bash
cp .env.example .env
# Edite .env e insira sua GEMINI_API_KEY
```

### 2. Suba todos os servicos

```bash
docker compose up --build
```


---

## Guia de Testes

### Teste 1 — Invocacao sincrona

```bash
curl -s -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' \
  | python3 -m json.tool
```

Verifique o header `X-Request-ID` na resposta:

```bash
curl -v -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' 2>&1 \
  | grep -i x-request-id
```

### Teste 2 — Streaming SSE

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare AI Assistant vs Cloud Platform em 2025"}'
```

### Teste 3 — Fluxo assincrono completo

```bash
# Enfileira a tarefa
TASK_ID=$(curl -s -X POST http://localhost:8000/invoke/async \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual regiao mais cresceu em 2025?"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

echo "Task ID: $TASK_ID"

# Aguarda 10 segundos e consulta o resultado
sleep 10
curl -s http://localhost:8000/tasks/$TASK_ID | python3 -m json.tool
```

### Teste 4 — Semaforo de concorrencia (teste de carga)

Envia 15 requisicoes simultaneas. Com MAX_CONCURRENT=3 e MAX_QUEUE_SIZE=10,
espera-se que algumas recebam HTTP 429:

```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" \
    -X POST http://localhost:8000/invoke \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Request numero $i: qual produto vendeu mais em Q4 2025?\"}" &
done
wait
```

### Teste 5 — Health check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Resposta esperada:

```json
{
  "status": "healthy",
  "components": {
    "postgres": {"status": "ok"},
    "rabbitmq": {"status": "ok"},
    "gemini": {"status": "ok"}
  },
  "concurrency": {
    "active": 0,
    "waiting": 0,
    "max_concurrent": 3,
    "total_processed": 5,
    "total_rejected": 2
  }
}
```


---

## Endpoints

| Metodo | Caminho              | Status HTTP       | Tipo de resposta    | Descricao |
|--------|----------------------|-------------------|---------------------|-----------|
| `POST` | `/invoke`            | `200` / `429` / `504` | `application/json`  | Resposta completa com semaforo + timeout |
| `POST` | `/stream`            | `200` / `429`     | `text/event-stream` | Streaming SSE com semaforo |
| `POST` | `/invoke/async`      | `202`             | `application/json`  | Enfileira tarefa e retorna task_id |
| `GET`  | `/tasks/{task_id}`   | `200` / `404`     | `application/json`  | Consulta status da tarefa assincrona |
| `GET`  | `/health`            | `200`             | `application/json`  | Saude do servico + metricas do semaforo |
| `GET`  | `/docs`              | `200`             | HTML                | Documentacao interativa Swagger UI |
| `GET`  | `/redoc`             | `200`             | HTML                | Documentacao alternativa ReDoc |

---

## Variaveis de ambiente

| Variavel | Padrao | Descricao |
|---|---|---|
| `GEMINI_API_KEY` | — | Chave da API Google Gemini (obrigatoria) |
| `DATABASE_URL` | `postgresql://agent:agent@postgres:5432/agent_tasks` | URL de conexao do PostgreSQL |
| `CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:5672//` | URL do broker RabbitMQ |
| `RABBITMQ_HOST` | `rabbitmq` | Hostname do RabbitMQ (para health check) |
| `MAX_CONCURRENT_AGENTS` | `3` | Maximo de agentes executando simultaneamente |
| `MAX_QUEUE_SIZE` | `10` | Maximo de requisicoes na fila de espera do semaforo |
| `REQUEST_TIMEOUT` | `120` | Timeout total da requisicao HTTP (segundos) |
| `AGENT_TIMEOUT` | `90` | Timeout para execucao completa do agente (segundos) |
| `TOOL_TIMEOUT` | `30` | Timeout por chamada de ferramenta (segundos) |
| `ENVIRONMENT` | `development` | `development` (console colorido) ou `production` (JSON logs) |

---

## O que muda neste estagio vs. os anteriores

Este e o estagio final do curso. Os estagios anteriores construiram
incrementalmente a infraestrutura de serving:

- **Estagio 01** — endpoint sincrono basico
- **Estagio 02** — streaming SSE para feedback incremental
- **Estagio 03** — fila assincrona para desacoplar API de processamento
- **Estagio 04** — controles de producao para tornar o servico robusto

O estagio 04 nao muda a logica do agente. Ele adiciona a camada de
**operacoes** que todo servico precisa antes de ir para producao.
