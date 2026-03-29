# Estágio 03 — Async (RabbitMQ + Celery + PostgreSQL)

## O que este estágio demonstra

Este estágio introduz o padrão **fire-and-forget com fila de mensagens** como solução
ao problema de workers bloqueados durante inferência LLM, exposto no estágio 02.

O cliente agora tem quatro opções:

- **POST /invoke** — comportamento idêntico ao estágio 01 (mantido para comparação).
- **POST /stream** — streaming SSE do estágio 02 (mantido para comparação).
- **POST /invoke/async** — enfileira a tarefa e retorna imediatamente um `task_id`.
- **GET /tasks/{task_id}** — consulta o status e o resultado da tarefa.

### O que o Estágio 03 resolve em relação ao Estágio 02

| Problema (Estágio 02) | Solução (Estágio 03) |
|---|---|
| **Worker HTTP bloqueado por até 60s** | API retorna em <50ms; processamento ocorre em worker Celery separado |
| **Escala limitada pelo número de workers HTTP** | Workers Celery escalam independentemente da API |
| **Timeout de gateway** — ALB (60s) e nginx (120s) podem encerrar requisições longas | Tarefa enfileirada não depende de conexão HTTP ativa |
| **Sem persistência de tarefas** | Resultado salvo no PostgreSQL; cliente pode consultar depois |
| **Sem retry automático** | Celery pode reprocessar tarefas falhas (configurável) |

### O que o Estágio 03 ainda não resolve

| Limitação | Descrição |
|---|---|
| **Sem autenticação** | Qualquer cliente pode consultar qualquer task_id |
| **Sem notificação push** | Cliente precisa fazer polling manualmente |
| **Sem observabilidade** | Não há métricas, tracing ou alertas (tema do estágio 04) |

---

## Arquitetura

```
Cliente HTTP
     |
     |  POST /invoke/async
     v
+---------------------------+
|  FastAPI (API)            |  <-- retorna task_id em <50ms
|  main.py                  |
+---------------------------+
     |                 ^
     | enfileira       | GET /tasks/{task_id}
     v                 |
+---------------------------+
|  RabbitMQ                 |  <-- absorve picos de tráfego
|  (broker de mensagens)    |
+---------------------------+
     |
     | consome
     v
+---------------------------+
|  Celery Worker            |  <-- executa inferência LLM
|  tasks.py                 |
|  run_agent()              |
+---------------------------+
     |
     | persiste resultado
     v
+---------------------------+
|  PostgreSQL               |  <-- armazena status e resultado
|  task_records             |
+---------------------------+
     |
     v
LangGraph ReAct Agent
(agent.py)
    |           |
    v           v
search_     calculate
database    (ast)
    |
    v
SQLite (memória)
```

---

## Serviços Docker

| Serviço    | Imagem                          | Porta   | Descrição |
|------------|---------------------------------|---------|-----------|
| `api`      | build local                     | `8000`  | FastAPI — recebe requisições e enfileira tarefas |
| `worker`   | build local                     | —       | Celery worker — processa tarefas da fila |
| `rabbitmq` | `rabbitmq:4-management-alpine`  | `15672` | Broker de mensagens + painel de administração |
| `postgres` | `postgres:17-alpine`            | `5432`  | Banco de dados para persistência das tarefas |

---

## Como rodar

### 1. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite .env e insira sua GEMINI_API_KEY
```

### 2. Suba todos os serviços com Docker Compose

```bash
docker compose up --build
```

Aguarde todos os serviços ficarem saudáveis. O painel do RabbitMQ estará disponível
em `http://localhost:15672` (usuário: `guest`, senha: `guest`).

### 3. Enfileire uma tarefa assíncrona

```bash
curl -s -X POST http://localhost:8000/invoke/async \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' \
  | python3 -m json.tool
```

Resposta imediata (HTTP 202):

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "poll_url": "/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Consulte o status da tarefa

```bash
curl -s http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000 \
  | python3 -m json.tool
```

Enquanto o worker processa (status `processing`):

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "input_message": "Qual produto teve maior receita em 2025?",
  "output": null,
  "tools_used": null
}
```

Após a conclusão (status `completed`):

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "input_message": "Qual produto teve maior receita em 2025?",
  "output": "O produto com maior receita em 2025 foi o AI Assistant...",
  "tools_used": ["search_database"],
  "token_count": 1842,
  "step_count": 4,
  "duration_ms": 12350,
  "error": null,
  "created_at": "2025-03-28T14:00:00",
  "completed_at": "2025-03-28T14:00:15"
}
```

### 5. Compare com os endpoints do estágio 02 (mantidos)

```bash
# Síncrono — worker bloqueado até concluir
curl -s -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' \
  | python3 -m json.tool

# Streaming SSE — worker bloqueado, mas cliente recebe feedback incremental
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}'
```

---

## Endpoints

| Método | Caminho              | Status HTTP | Tipo de resposta   | Descrição |
|--------|----------------------|-------------|--------------------|-----------|
| `POST` | `/invoke`            | `200`       | `application/json` | Resposta completa ao final (estágio 01) |
| `POST` | `/stream`            | `200`       | `text/event-stream`| Eventos SSE incrementais (estágio 02) |
| `POST` | `/invoke/async`      | `202`       | `application/json` | Enfileira tarefa e retorna task_id |
| `GET`  | `/tasks/{task_id}`   | `200`/`404` | `application/json` | Consulta status e resultado da tarefa |
| `GET`  | `/docs`              | `200`       | HTML               | Documentação interativa Swagger UI |
| `GET`  | `/redoc`             | `200`       | HTML               | Documentação alternativa ReDoc |

---

## Ciclo de vida da tarefa

```
POST /invoke/async
       |
       v
   [pending]   <- registro criado no PostgreSQL; mensagem na fila RabbitMQ
       |
       | worker consome da fila
       v
  [processing] <- worker atualizou status; está executando o agente
       |
  +----|----+
  |         |
  v         v
[completed] [failed]  <- resultado ou erro persistido no PostgreSQL
```

---

## Por que worker_prefetch_multiplier=1?

Com o prefetch padrão do Celery (4), um worker pode reservar múltiplas tarefas antes
de começar a processá-las. Para tarefas de inferência LLM — longas e que consomem muita
memória — isso significa que o worker trava tarefas que poderiam ser processadas por outro
worker disponível.

Definir `worker_prefetch_multiplier=1` garante que cada worker reserve apenas **uma tarefa
por vez**, deixando as demais disponíveis na fila para outros workers consumirem.

---

## O que muda no próximo estágio

No **Estágio 04 — Produção**, o foco muda para operações: observabilidade (métricas,
logs estruturados, tracing), configuração de produção (gunicorn + uvicorn workers),
health checks e preparação para deploy em Kubernetes ou ECS.
