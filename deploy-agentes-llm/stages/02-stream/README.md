# Estágio 02 — Streaming SSE (Server-Sent Events)

## O que este estágio demonstra

Este estágio introduz o padrão de **streaming via Server-Sent Events (SSE)** como solução
ao problema de "tela em branco" exposto no estágio 01.

O cliente agora tem duas opções:

- **POST /invoke** — comportamento idêntico ao estágio 01 (mantido para comparação).
- **POST /stream** — retorna eventos incrementais enquanto o agente processa, usando SSE
  nativo do FastAPI (sem bibliotecas externas, disponível desde a versão 0.135+).

### O que o Estágio 02 resolve em relação ao Estágio 01

| Problema (Estágio 01) | Solução (Estágio 02) |
|---|---|
| **Tela em branco** — cliente sem feedback por 10–60s | SSE envia eventos a cada passo do agente |
| **Cancelamentos prematuros** — usuário encerra a requisição por achar que travou | O cliente vê progresso contínuo e aguarda naturalmente |
| **Impossível mostrar barra de progresso** | Eventos `step_start`, `tool_call`, `token` permitem UX progressiva |
| **Gateway timeout** — ALB/nginx pode encerrar conexão longa sem dados | SSE mantém a conexão "viva" com eventos regulares |

### O que o Estágio 02 ainda não resolve

| Limitação | Descrição |
|---|---|
| **Conexão ainda bloqueante por worker** | O worker permanece ocupado durante toda a inferência — só melhora com filas (Estágio 03) |
| **Sem persistência de tarefas** | Se o servidor reiniciar durante o processamento, a tarefa é perdida |
| **Sem retry automático** | Se a conexão cair, o cliente precisa reiniciar a requisição do zero |

---

## Arquitetura

```
Cliente HTTP
     |
     |  POST /stream
     |  Accept: text/event-stream
     v
+-------------------------+
|  FastAPI (SSE)          |
|  main.py                |
|  EventSourceResponse    |
+-------------------------+
         |
         |  agent_module.run_stream(message)
         |  (async generator)
         v
+-------------------------+
|  LangGraph ReAct        |
|  agent.py               |
|  agent.astream(...)     |
+-------------------------+
    |           |
    v           v
search_     calculate
database    (ast)
    |
    v
SQLite
(memória)
         |
         | AgentEvent (step_start)
         |<--------------------------
         | AgentEvent (tool_call)
         |<--------------------------
         | AgentEvent (tool_result)
         |<--------------------------
         | AgentEvent (token)
         |<--------------------------
         | AgentEvent (done)
         |<--------------------------
     Cliente
```

---

## Como rodar

### 1. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite .env e insira sua GEMINI_API_KEY
```

### 2. Suba o serviço com Docker Compose

```bash
docker compose up --build
```

O serviço estará disponível em `http://localhost:8000`.

### 3. Teste o endpoint síncrono (igual ao estágio 01)

```bash
curl -s -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' \
  | python3 -m json.tool
```

### 4. Teste o endpoint de streaming (novidade do estágio 02)

O flag `-N` no curl desativa o buffer — necessário para ver os eventos em tempo real:

```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}'
```

Exemplo de saída incremental:

```
event: step_start
data: {"node": "agent", "step": 1}

event: tool_call
data: {"tool": "search_database", "args": {"query": "SELECT ..."}}

event: tool_result
data: {"tool": "search_database", "content": "+--------+..."}

event: token
data: {"content": "O produto com maior receita em 2025 foi o AI Assistant..."}

event: done
data: {"result": {"output": "...", "tools_used": [...], "token_count": 1842, "step_count": 4, "duration_ms": 12350}}
```

---

## Endpoints

| Método | Caminho   | Tipo de resposta         | Descrição |
|--------|-----------|--------------------------|-----------|
| `POST` | `/invoke` | `application/json`       | Resposta completa ao final (idêntico ao estágio 01) |
| `POST` | `/stream` | `text/event-stream` (SSE)| Eventos incrementais durante a execução |
| `GET`  | `/docs`   | HTML                     | Documentação interativa Swagger UI |
| `GET`  | `/redoc`  | HTML                     | Documentação alternativa ReDoc |

---

## Eventos SSE

| Evento        | Quando é emitido                        | Payload (campo `data`)                                     |
|---------------|-----------------------------------------|------------------------------------------------------------|
| `step_start`  | Início de cada passo do loop ReAct      | `{"node": "<nome>", "step": <número>}`                     |
| `tool_call`   | Quando o modelo decide usar uma ferramenta | `{"tool": "<nome>", "args": {...}}`                     |
| `tool_result` | Após a ferramenta retornar resultado    | `{"tool": "<nome>", "content": "<resultado>"}`             |
| `token`       | Quando o modelo gera conteúdo de texto  | `{"content": "<fragmento>"}`                               |
| `done`        | Ao final da execução (último evento)    | `{"result": {"output": "...", "tools_used": [...], "token_count": N, "step_count": N, "duration_ms": N}}` |

---

## O que muda no próximo estágio

No **Estágio 03 — Async (Filas)**, o padrão evolui para um modelo de tarefa assíncrona
desacoplada: o cliente envia a mensagem e recebe imediatamente um `task_id`. O processamento
ocorre em background e o resultado fica disponível para polling ou notificação. Isso libera
os workers durante a inferência, permitindo escala horizontal real sem conexões bloqueantes.
