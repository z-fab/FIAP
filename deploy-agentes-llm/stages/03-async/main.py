"""
Estágio 03 — Assíncrono (RabbitMQ + Celery + PostgreSQL)

Evolução do estágio 02: mantém /invoke e /stream e adiciona o padrão
fire-and-forget via /invoke/async + polling via /tasks/{task_id}.

Por que o padrão assíncrono com fila resolve problemas do estágio 02?
----------------------------------------------------------------------
No estágio 02, mesmo com SSE, o worker HTTP permanecia ocupado durante
toda a inferência (~10-60s). Isso limita a escala horizontal: 10 workers
= 10 requisições simultâneas em processamento.

Com fila (RabbitMQ + Celery):
- A API recebe a requisição, cria o registro no banco e retorna em <50ms.
- O worker HTTP fica livre imediatamente.
- O processamento ocorre em workers Celery independentes, que podem
  escalar separadamente da API.
- O cliente faz polling em GET /tasks/{task_id} até receber o resultado.

Casos de uso que este padrão habilita:
- Jobs mais longos que o timeout do gateway (ALB: 60s, nginx: 120s padrão)
- Processamento em lote: enfileira N tarefas e consome gradualmente
- Fire-and-forget: cliente não precisa manter conexão aberta
- Absorção de picos: a fila acumula tarefas; workers processam no ritmo deles
- Retry automático: Celery pode reprocessar tarefas que falharam
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import agent as agent_module
from database import SessionLocal, init_db
from db_models import TaskRecord
from fastapi import FastAPI, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from models import (
    AsyncInvokeResponse,
    InvokeRequest,
    InvokeResponse,
    TaskStatusResponse,
)
from rich.console import Console
from tasks import run_agent  # noqa: F401 — importado para registro da task

_console = Console(force_terminal=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.

    Na inicialização:
    - Exibe informações do serviço no terminal.
    - Inicializa o schema PostgreSQL (cria tabelas se não existirem).
    """
    _console.rule("[bold blue]Agent Service — Stage 03 (Async)[/]")
    _console.print("[bold]Padrão:[/] Fire-and-forget com RabbitMQ + Celery + PostgreSQL")
    _console.print(
        "[bold]Endpoints:[/] POST /invoke  |  POST /stream  |  "
        "POST /invoke/async  |  GET /tasks/{task_id}"
    )
    _console.print(
        "[bold]Solução:[/] Fila absorve picos; workers processam de forma desacoplada"
    )
    _console.print()

    _console.print("[bold cyan]Inicializando banco de dados PostgreSQL...[/]")
    init_db()
    _console.print("[bold green]Banco de dados pronto.[/]")

    _console.print()
    _console.print("[dim]Aguardando requisições em http://0.0.0.0:8000 ...[/]")
    _console.rule()

    yield

    _console.rule("[bold red]Encerrando serviço[/]")


app = FastAPI(
    title="Agent Service — Stage 03 (Async)",
    description=(
        "Evolução do estágio 02: adiciona o padrão fire-and-forget com RabbitMQ e Celery. "
        "O endpoint POST /invoke/async enfileira a tarefa e retorna imediatamente um task_id. "
        "O cliente consulta o resultado via GET /tasks/{task_id}. "
        "Os endpoints /invoke e /stream do estágio 02 são mantidos para comparação."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints herdados do estágio 02
# ---------------------------------------------------------------------------


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest) -> InvokeResponse:
    """
    Invoca o agente e retorna a resposta completa em uma única chamada.

    Mantido do estágio 02 para permitir comparação direta com /invoke/async.
    O worker HTTP permanece ocupado durante toda a execução do agente.
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

    Mantido do estágio 02. Cada passo da execução é enviado como evento SSE
    separado — eliminando a "tela em branco", mas ainda bloqueando o worker.

    O FastAPI serializa cada ServerSentEvent no formato SSE automaticamente
    quando o endpoint usa yield + response_class=EventSourceResponse.

    Tipos de evento emitidos:
        step_start   — início de um passo do loop ReAct
        tool_call    — chamada de ferramenta pelo modelo
        tool_result  — resultado devolvido pela ferramenta
        token        — fragmento de texto gerado pelo modelo
        done         — execução concluída; data contém o resultado completo
    """
    async for agent_event in agent_module.run_stream(request.message):
        yield ServerSentEvent(
            event=agent_event.type,
            data=agent_event.data,
        )

    _console.print("[green]Concluído (stream)[/]")


# ---------------------------------------------------------------------------
# Novos endpoints do estágio 03 — padrão assíncrono
# ---------------------------------------------------------------------------


@app.post("/invoke/async", response_model=AsyncInvokeResponse, status_code=202)
async def invoke_async(request: InvokeRequest) -> AsyncInvokeResponse:
    """
    Enfileira a execução do agente e retorna imediatamente um task_id.

    Fluxo:
    1. Gera um UUID para a tarefa.
    2. Persiste um registro com status='pending' no PostgreSQL.
    3. Enfileira a task run_agent no RabbitMQ via Celery.
    4. Retorna task_id + poll_url — sem aguardar o agente.

    O cliente deve fazer polling em GET /tasks/{task_id} para obter o resultado.
    HTTP 202 Accepted indica que a requisição foi aceita para processamento.
    """
    task_id = str(uuid.uuid4())

    # Persiste o registro no banco antes de enfileirar (garante que o worker
    # encontre o registro ao iniciar o processamento)
    db = SessionLocal()
    try:
        task_record = TaskRecord(
            id=task_id,
            status="pending",
            input_message=request.message,
        )
        db.add(task_record)
        db.commit()
    finally:
        db.close()

    # Enfileira a tarefa no RabbitMQ
    run_agent.delay(task_id, request.message)

    _console.print(
        f"[bold blue]Tarefa enfileirada[/] {task_id} | "
        f"mensagem: {request.message[:60]!r}{'...' if len(request.message) > 60 else ''}"
    )

    return AsyncInvokeResponse(
        task_id=task_id,
        status="pending",
        poll_url=f"/tasks/{task_id}",
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str) -> TaskStatusResponse:
    """
    Consulta o status e o resultado de uma tarefa assíncrona.

    Retorna o estado atual da tarefa no PostgreSQL:
    - pending    — aguardando na fila
    - processing — worker está executando
    - completed  — resultado disponível nos campos de resposta
    - failed     — erro disponível no campo 'error'

    HTTP 404 caso o task_id não exista.
    """
    db = SessionLocal()
    try:
        task_record = db.get(TaskRecord, task_id)
        if task_record is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tarefa '{task_id}' não encontrada.",
            )

        # Desserializa tools_used de JSON string para lista
        tools_used: list[str] | None = None
        if task_record.tools_used is not None:
            try:
                tools_used = json.loads(task_record.tools_used)
            except (json.JSONDecodeError, TypeError):
                tools_used = []

        return TaskStatusResponse(
            task_id=task_record.id,
            status=task_record.status,
            input_message=task_record.input_message,
            output=task_record.output,
            tools_used=tools_used,
            token_count=task_record.token_count,
            step_count=task_record.step_count,
            duration_ms=task_record.duration_ms,
            error=task_record.error,
            created_at=task_record.created_at,
            completed_at=task_record.completed_at,
        )
    finally:
        db.close()
