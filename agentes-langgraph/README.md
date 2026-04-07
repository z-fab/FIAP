# Agentes de IA com LangGraph

Projeto prático da pós-graduação em **ML Engineering** da **FIAP**. Implementa três padrões distintos de agentes com [LangGraph](https://langchain-ai.github.io/langgraph/), cada um demonstrando uma abordagem arquitetural diferente: prebuilt simplificado, ReAct manual e Human-in-the-Loop.

## Agentes

| Agente | Padrão | Descrição |
|---|---|---|
| **Financeiro** | `create_agent` (prebuilt) | Cotações de moedas, preços de ações, cálculo de retornos e comparações |
| **Pesquisa** | `StateGraph` manual (ReAct explícito) | Busca acadêmica, pesquisa web e resumo de textos |
| **Pokémon Trade Center** | ReAct + `interrupt()` (HITL) | Trocas de Pokémon com aprovação humana e fluxo administrativo |

## Arquitetura dos Grafos

### Financeiro — Prebuilt Simplificado

Usa `create_agent` do LangGraph, que abstrai o loop ReAct internamente. Ideal para agentes simples com ferramentas independentes.

**Ferramentas:** cotação de moeda (AwesomeAPI), preço de ação (yfinance), cálculo de retorno, comparação de ativos.

### Pesquisa — StateGraph Manual

Constrói o ciclo ReAct explicitamente com `StateGraph`, definindo nós e arestas condicionais. Estado customizado com `ResearchState` (query, sources_found).

**Ferramentas:** busca de artigos (Semantic Scholar), pesquisa web (Tavily), resumo de texto.

### Pokémon Trade Center — ReAct + Human-in-the-Loop

Agente conversacional que usa `interrupt()` para pausar o grafo e aguardar aprovação humana. Três fluxos de troca:

| Tipo | Critério | Fluxo de aprovação |
|---|---|---|
| **Comum** | BST < 500 | Aprovação automática |
| **Rara** | BST >= 500 | `interrupt()` — treinador confirma via CLI/API |
| **Lendária** | Pokémon lendário | Registrada como pendente — Professor Oak aprova via endpoints admin |

**Ferramentas:** consultar/comparar Pokémon (PokéAPI), propor troca, verificar status com Professor Oak.

## Setup

**Requisitos:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```bash
# Instalar dependências
make install

# Configurar variáveis de ambiente
cp .env.example .env
# Preencha GOOGLE_API_KEY e TAVILY_API_KEY
```

| Variável | Serviço |
|---|---|
| `GOOGLE_API_KEY` | Google Gemini (LLM) |
| `TAVILY_API_KEY` | Tavily (pesquisa web) |

## Uso

### CLI de Chat (interface principal)

```bash
make chat
```

Interface interativa com [Rich](https://rich.readthedocs.io/): menu de seleção de agente, streaming de tokens, eventos de tools em tempo real e prompt HITL para aprovação de trocas.

### API REST

```bash
make dev
```

FastAPI em `http://localhost:8000` com documentação Swagger em `/docs`.

Cada agente expõe dois endpoints:

- `POST /{agent}/invoke` — resposta completa
- `POST /{agent}/stream` — streaming via SSE (eventos: `node_start`, `tool_call`, `tool_result`, `token`, `node_end`, `done`)

#### Endpoints do Professor Oak (admin)

```bash
# Listar trocas pendentes
GET /trade/admin/pending

# Aprovar ou rejeitar uma troca lendária
POST /trade/admin/{thread_id}/review
# Body: {"decision": "approve"} ou {"decision": "reject"}
```

## Estrutura do Projeto

```
src/agents/
├── __init__.py
├── __main__.py            # Entry point: python -m agents
├── config.py              # Pydantic settings (GOOGLE_API_KEY, TAVILY_API_KEY)
├── cli.py                 # CLI de chat interativo com Rich
├── financial/
│   ├── agent.py           # create_agent — prebuilt simplificado
│   └── tools.py           # Cotação moeda, ação, retorno, comparação
├── research/
│   ├── state.py           # ResearchState (MessagesState + query, sources_found)
│   ├── agent.py           # StateGraph manual — ReAct explícito
│   └── tools.py           # buscar_artigos, buscar_web, resumir_texto
├── trade/
│   ├── state.py           # TradeState (MessagesState + pending_trade_id)
│   ├── agent.py           # ReAct conversacional + interrupt() HITL
│   ├── tools.py           # consultar/comparar pokemon, propor_troca, check_professor
│   └── db.py              # Persistência JSON para trocas pendentes
└── api/
    ├── main.py            # FastAPI app
    ├── schemas.py         # AgentRequest, AgentResponse, extract_text
    ├── streaming.py       # SSE streaming via astream_events
    └── routers/
        ├── financial.py   # /financial/invoke, /financial/stream
        ├── research.py    # /research/invoke, /research/stream
        └── trade.py       # /trade/invoke, /trade/stream, /trade/admin/*
```

## Comandos Make

| Comando | Descrição |
|---|---|
| `make install` | Instala dependências com `uv sync` |
| `make chat` | Inicia CLI de chat interativo |
| `make dev` | Inicia servidor FastAPI com hot-reload |
| `make lint` | Verifica código com ruff |
| `make format` | Formata código com ruff |
| `make typecheck` | Verifica tipos com ty |
| `make check` | Executa lint + typecheck |
| `make graph-all` | Exporta todos os grafos como Mermaid |
| `make help` | Lista todos os comandos disponíveis |

## Tecnologias

| Tecnologia | Papel |
|---|---|
| [LangGraph](https://langchain-ai.github.io/langgraph/) | Orquestração dos agentes |
| [Google Gemini](https://ai.google.dev/) | LLM via langchain-google-genai |
| [FastAPI](https://fastapi.tiangolo.com/) | API REST + SSE streaming |
| [Rich](https://rich.readthedocs.io/) | Interface CLI |
| [PokéAPI](https://pokeapi.co/) | Dados de Pokémon |
| [AwesomeAPI](https://docs.awesomeapi.com.br/) | Cotações de câmbio |
| [yfinance](https://github.com/ranaroussi/yfinance) | Dados de ações |
| [Tavily](https://tavily.com/) | Pesquisa na web |
| [Semantic Scholar](https://www.semanticscholar.org/) | Busca de artigos acadêmicos |
