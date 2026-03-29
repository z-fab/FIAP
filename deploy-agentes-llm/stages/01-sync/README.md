# Estágio 01 — Endpoint Síncrono

## O que este estágio demonstra

Este é o ponto de partida do curso: o padrão **request-response síncrono**, o mais simples possível para servir um agente LLM via HTTP.

O cliente envia uma mensagem no corpo do POST e **aguarda bloqueado** até que o agente conclua o processamento — o que pode levar de 10 a 60 segundos, dependendo da complexidade da pergunta e do número de chamadas de ferramentas necessárias.

### Problemas expostos por este padrão

| Problema | Descrição |
|---|---|
| **Conexão bloqueante** | A conexão TCP fica aberta durante toda a inferência. Gateways com timeout curto (ex.: AWS ALB padrão = 60s) podem encerrá-la prematuramente. |
| **Sem feedback** | O cliente não sabe se o servidor está trabalhando ou travado. Nenhuma barra de progresso é possível. |
| **Má utilização de workers** | Cada worker fica ocupado por toda a duração da inferência, limitando a concorrência real. |
| **Experiência ruim** | Para o usuário final, aguardar 30+ segundos sem resposta visual é inaceitável em produção. |

Esses problemas são resolvidos progressivamente nos estágios seguintes.

---

## Arquitetura

```
Cliente HTTP
     |
     |  POST /invoke  (conexão aberta por toda a duração)
     v
+--------------------+
|   FastAPI (sync)   |
|   main.py          |
+--------------------+
         |
         |  await agent.run(message)
         v
+--------------------+
|  LangGraph ReAct   |
|  agent.py          |
+--------------------+
    |          |
    v          v
search_    calculate
database   (ast)
    |
    v
SQLite
(memória)
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

### 3. Envie uma requisição de teste

```bash
curl -s -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual produto teve maior receita em 2025?"}' \
  | python3 -m json.tool
```

Exemplo de resposta:

```json
{
  "output": "O produto com maior receita em 2025 foi o AI Assistant...",
  "tools_used": ["search_database", "calculate"],
  "token_count": 1842,
  "step_count": 4,
  "duration_ms": 12350
}
```

---

## Endpoints

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `POST` | `/invoke` | Envia uma mensagem ao agente e aguarda a resposta completa |
| `GET`  | `/docs`   | Documentação interativa Swagger UI (gerada pelo FastAPI) |
| `GET`  | `/redoc`  | Documentação alternativa ReDoc |

---

## O que muda no próximo estágio

No **Estágio 02 — Stream**, o endpoint passa a usar `StreamingResponse` com
Server-Sent Events (SSE). O cliente recebe fragmentos de texto à medida que
o agente os gera, eliminando a espera silenciosa e permitindo experiências
de UX progressivas — sem abrir mão da simplicidade de uma única conexão HTTP.
