"""
Estágio 01 — Endpoint Síncrono (request-response simples)

Este é o padrão mais simples de servir um agente LLM: o cliente faz uma
requisição HTTP POST, a conexão fica aberta enquanto o agente processa
(podendo levar dezenas de segundos), e a resposta completa é retornada
de uma vez ao final.

Problemas expostos por este padrão:
- A conexão TCP fica aberta durante todo o processamento do agente.
- Sem feedback incremental — o cliente não sabe se algo está acontecendo.
- Gateways e load balancers com timeouts curtos podem encerrar a conexão.
- Difícil escalar horizontalmente: workers bloqueados durante toda a inferência.
- Experiência ruim para o usuário final em perguntas complexas (>30s).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import agent as agent_module
from fastapi import FastAPI
from models import InvokeRequest, InvokeResponse
from rich.console import Console

_console = Console(force_terminal=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.

    Na inicialização, exibe informações do serviço no terminal usando Rich.
    O agente e o banco de dados são inicializados de forma lazy na primeira
    requisição (ver agent.py).
    """
    _console.rule("[bold blue]Agent Service — Stage 01 (Sync)[/]")
    _console.print("[bold]Padrão:[/] Request-Response síncrono")
    _console.print("[bold]Endpoint:[/] POST /invoke")
    _console.print(
        "[bold]Problema principal:[/] conexão bloqueante durante toda a inferência"
    )
    _console.print()
    _console.print("[dim]Aguardando requisições em http://0.0.0.0:8000 ...[/]")
    _console.rule()

    yield

    _console.rule("[bold red]Encerrando serviço[/]")


app = FastAPI(
    title="Agent Service — Stage 01 (Sync)",
    description=(
        "Implementação de referência do padrão síncrono mais simples: "
        "o cliente aguarda bloqueado até o agente concluir o processamento. "
        "Use este estágio para entender os problemas de timeout e ausência "
        "de feedback antes de avançar para padrões mais robustos."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest) -> InvokeResponse:
    """
    Invoca o agente e retorna a resposta completa em uma única chamada.

    A conexão HTTP permanece aberta enquanto o agente executa o loop ReAct
    — podendo envolver múltiplas chamadas ao LLM e às ferramentas. O cliente
    não recebe nenhum sinal de progresso até que o processamento termine.
    """
    result = await agent_module.run(request.message)

    _console.print(
        f"[green]Concluído[/] | "
        f"tokens={result.token_count} | "
        f"passos={result.step_count} | "
        f"ferramentas={result.tools_used} | "
        f"duração={result.duration_ms}ms"
    )

    return InvokeResponse(
        output=result.output,
        tools_used=result.tools_used,
        token_count=result.token_count,
        step_count=result.step_count,
        duration_ms=result.duration_ms,
    )
