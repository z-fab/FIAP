"""
Estágio 02 — Streaming SSE (Server-Sent Events)

Evolução do estágio 01: mantém o endpoint síncrono /invoke e adiciona
o endpoint /stream, que usa Server-Sent Events nativos do FastAPI para
enviar fragmentos da execução do agente ao cliente em tempo real.

Por que SSE resolve o "blank screen" do estágio 01?
----------------------------------------------------
No estágio 01, o cliente ficava sem qualquer feedback visual enquanto
aguardava a resposta. O usuário não tinha como saber se o servidor estava processando
ou se a conexão havia caído. Isso causava cancelamentos prematuros e
péssima experiência de uso.

Com SSE, a conexão HTTP permanece aberta e o servidor envia eventos
incrementais (passo do agente, chamada de ferramenta, fragmento de texto,
conclusão) à medida que a execução avança. O cliente pode exibir progresso
em tempo real sem qualquer mudança na infraestrutura de rede.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import agent as agent_module
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
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
    _console.rule("[bold blue]Agent Service — Stage 02 (Stream)[/]")
    _console.print("[bold]Padrão:[/] Request-Response síncrono + Streaming SSE")
    _console.print("[bold]Endpoints:[/] POST /invoke  |  POST /stream")
    _console.print("[bold]Solução:[/] SSE elimina a 'tela em branco' do estágio 01")
    _console.print()
    _console.print("[dim]Aguardando requisições em http://0.0.0.0:8000 ...[/]")
    _console.rule()

    yield

    _console.rule("[bold red]Encerrando serviço[/]")


app = FastAPI(
    title="Agent Service — Stage 02 (Stream)",
    description=(
        "Evolução do estágio 01: adiciona o endpoint /stream com Server-Sent Events "
        "nativos do FastAPI. O cliente recebe eventos incrementais durante a execução "
        "do agente — eliminando a espera silenciosa ('blank screen') do padrão síncrono puro. "
        "O endpoint /invoke é mantido para compatibilidade e comparação."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest) -> InvokeResponse:
    """
    Invoca o agente e retorna a resposta completa em uma única chamada.

    Idêntico ao endpoint do estágio 01: a conexão HTTP permanece aberta
    enquanto o agente executa o loop ReAct. O cliente não recebe nenhum
    sinal de progresso até que o processamento termine.

    Mantido neste estágio para permitir comparação direta com /stream
    e para demonstrar que ambos os padrões podem coexistir no mesmo serviço.
    """
    result = await agent_module.run(request.message)

    _console.print(
        f"[green]Concluído (invoke)[/] | "
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


@app.post("/stream", response_class=EventSourceResponse)
async def stream(request: InvokeRequest):
    """
    Invoca o agente em modo streaming e retorna eventos SSE incrementalmente.

    Cada passo da execução (início de etapa, chamada de ferramenta, resultado
    de ferramenta, fragmento de texto gerado, conclusão) é enviado ao cliente
    como um evento SSE separado, com o campo 'event' indicando o tipo e o
    campo 'data' contendo o payload JSON.

    O cliente deve usar EventSource (browser) ou curl -N para consumir o stream.
    A conexão é encerrada automaticamente após o evento do tipo 'done'.

    Formato de cada evento SSE:
        event: <tipo>
        data: <payload JSON>

    Tipos de evento emitidos:
        step_start   — início de um passo do loop ReAct
        tool_call    — chamada de ferramenta pelo modelo
        tool_result  — resultado devolvido pela ferramenta
        token        — fragmento de texto gerado pelo modelo
        done         — execução concluída; data contém o resultado completo

    Nota: O FastAPI serializa ServerSentEvent no routing layer quando
    o endpoint usa yield + response_class=EventSourceResponse.
    """
    async for agent_event in agent_module.run_stream(request.message):
        _console.print(f"[blue]Evento SSE enviado:[/] {agent_event.type}")
        yield ServerSentEvent(
            event=agent_event.type,
            data=agent_event.data,
        )

    _console.print("[green]Concluído (stream)[/]")
