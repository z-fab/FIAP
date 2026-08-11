"""Aplicação FastAPI principal — monta todos os routers de agentes.

Para rodar em desenvolvimento:
    make dev

Ou diretamente:
    uv run uvicorn agents.api.main:app --reload
"""

import logging

from fastapi import FastAPI

from agents.api.routers import financial, roteiro, trade

# Configurar logging para ver execução dos nós e tools no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Agentes FIAP — LangGraph",
    description=(
        "API do projeto prático de Agentes de IA com LangGraph.\n\n"
        "Três agentes demonstrando padrões diferentes:\n"
        "- **Financeiro**: create_agent (abordagem simplificada)\n"
        "- **Estúdio de Roteiro**: workflow multi-nó + loop de crítica\n"
        "- **Pokémon Trade Center**: Human-in-the-Loop (interrupt)"
    ),
    version="0.1.0",
)

# Montar routers — cada agente tem seu próprio prefixo e tag
app.include_router(financial.router, prefix="/financial", tags=["Agente Financeiro"])
app.include_router(roteiro.router, prefix="/roteiro", tags=["Estúdio de Roteiro"])
app.include_router(trade.router, prefix="/trade", tags=["Pokémon Trade Center"])


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raiz — verifica se a API está rodando."""
    return {
        "status": "online",
        "project": "Agentes FIAP — LangGraph",
        "agents": [
            {
                "name": "Financeiro",
                "prefix": "/financial",
                "pattern": "create_agent",
            },
            {
                "name": "Estúdio de Roteiro",
                "prefix": "/roteiro",
                "pattern": "workflow + critique loop",
            },
            {
                "name": "Pokémon Trade",
                "prefix": "/trade",
                "pattern": "ReAct + HITL",
            },
        ],
    }
