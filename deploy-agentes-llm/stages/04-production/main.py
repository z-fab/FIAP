"""
Estagio 04 — Producao (Controles de Producao)

Evolucao do estagio 03: mantem todos os endpoints e adiciona controles
que tornam o servico pronto para producao:

1. **Concorrencia** (concurrency.py) — semaforo limita agentes simultaneos
2. **Timeouts** (timeouts.py) — limites de tempo por camada
3. **Health checks** (health.py) — verificacao de dependencias
4. **Logging estruturado** (logging_config.py) — structlog JSON/console
5. **Erros tipados** (errors.py) — hierarquia de excecoes com HTTP semantico

Cada controle e um modulo separado com uma responsabilidade. O main.py
apenas orquestra: conecta os modulos aos endpoints e ao ciclo de vida.

Principio de logging neste modulo
-----------------------------------
- Endpoints logam SUCESSO com metricas de negocio (tokens, steps, duracao).
- Endpoints NAO logam erros — apenas re-levantam excecoes de dominio.
- O exception handler em errors.py e o UNICO ponto de logging de erros.
- O middleware loga TODA requisicao (sucesso ou erro) com metricas HTTP.

Isso evita duplicacao de logs e garante que cada camada tem
responsabilidade unica.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog

import agent as agent_module
from concurrency import agent_semaphore
from database import SessionLocal, init_db
from db_models import TaskRecord
from errors import AgentExecutionError, AgentServiceError, register_error_handlers
from fastapi import FastAPI, HTTPException, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from health import run_health_check
from logging_config import generate_request_id, get_logger, setup_logging
from models import (
    AsyncInvokeResponse,
    InvokeRequest,
    InvokeResponse,
    TaskStatusResponse,
)
from rich.console import Console
from tasks import run_agent  # noqa: F401 — importado para registro da task
from timeouts import AGENT_TIMEOUT, with_timeout

_console = Console(force_terminal=True)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicacao.

    Na inicializacao:
    - Configura logging estruturado (structlog).
    - Inicializa o schema PostgreSQL.
    - Exibe informacoes do servico.
    """
    setup_logging()
    init_db()

    _console.rule("[bold blue]Agent Service — Stage 04 (Production)[/]")
    _console.print("[bold]Controles:[/] Semaforo | Timeouts | Health | Logging | Erros tipados")
    _console.print(
        "[bold]Endpoints:[/] POST /invoke  |  POST /stream  |  "
        "POST /invoke/async  |  GET /tasks/{task_id}  |  GET /health"
    )
    _console.print(f"[bold]Timeouts:[/] Agente={AGENT_TIMEOUT}s")

    _console.print()
    _console.print("[dim]Aguardando requisicoes em http://0.0.0.0:8000 ...[/]")
    _console.rule()

    yield

    _console.rule("[bold red]Encerrando servico[/]")


# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Service — Stage 04 (Production)",
    description=(
        "Estagio 04: todos os endpoints dos estagios anteriores + controles de producao "
        "(concorrencia, timeouts, health checks, logging estruturado, erros tipados)."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

# Registra handlers de erro tipados (errors.py)
# A partir deste ponto, qualquer AgentServiceError levantada em qualquer
# endpoint e automaticamente convertida em JSON com o status HTTP correto.
register_error_handlers(app)


# ---------------------------------------------------------------------------
# Middleware — logging de requisicoes
# ---------------------------------------------------------------------------


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware que:
    1. Gera um request_id unico para rastreamento.
    2. Vincula o request_id ao contexto do structlog (aparece em todos os logs).
    3. Mede a duracao da requisicao.
    4. Loga request_completed com metodo, path, status e duracao.
    5. Adiciona header X-Request-ID na resposta.

    Este e o unico ponto que loga metricas HTTP. Endpoints nao logam
    status codes — o middleware ve o status final da resposta
    (inclusive quando o exception handler converte um erro em 504/429/etc).
    """
    request_id = generate_request_id()

    # Vincula request_id ao contexto structlog (contextvars)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.monotonic()

    response = await call_next(request)

    duration_ms = int((time.monotonic() - start_time) * 1000)

    logger = get_logger("middleware")
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )

    response.headers["X-Request-ID"] = request_id

    return response


# ---------------------------------------------------------------------------
# Endpoints — com controles de producao
# ---------------------------------------------------------------------------


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(request: InvokeRequest) -> InvokeResponse:
    """
    Invoca o agente e retorna a resposta completa.

    Controles aplicados neste estagio:
    - Semaforo: limita execucoes simultaneas (429 se lotado)
    - Timeout: cancela se o agente demorar mais que AGENT_TIMEOUT (504)
    - Logging: registra metricas de execucao via structlog (apenas sucesso)

    Fluxo de erro:
    1. AgentServiceError (timeout, concorrencia) → re-levanta sem logar
       (o exception handler em errors.py loga e converte para JSON)
    2. Exception generica → converte para AgentExecutionError (500)
    """
    logger = get_logger("invoke")

    await agent_semaphore.acquire()
    try:
        result = await with_timeout(
            agent_module.run(request.message),
            timeout_seconds=AGENT_TIMEOUT,
            context="execucao do agente (invoke)",
        )
    except AgentServiceError:
        # Erros de dominio (timeout, concorrencia): re-levanta sem logar.
        # O exception handler em errors.py e responsavel por logar e
        # converter em resposta JSON com o status HTTP correto.
        raise
    except Exception as exc:
        # Erros inesperados (bug, rede, etc.): converte para
        # AgentExecutionError (500) com mensagem descritiva.
        # Nao expoe stack traces ao cliente — apenas a mensagem.
        raise AgentExecutionError(
            detail=f"Erro na execucao do agente: {exc}"
        ) from exc
    finally:
        # Libera o semaforo SEMPRE, mesmo em caso de erro.
        # Sem finally, um timeout deixaria o semaforo "preso",
        # reduzindo a capacidade do servico permanentemente.
        agent_semaphore.release()

    # Logging de sucesso: apenas metricas de negocio.
    # Erros nao chegam aqui — foram tratados acima.
    logger.info(
        "invoke_completed",
        tokens=result.token_count,
        steps=result.step_count,
        tools=result.tools_used,
        duration_ms=result.duration_ms,
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
    Invoca o agente em modo streaming com eventos SSE.

    Controles aplicados:
    - Semaforo: acquire/release envolvendo o gerador SSE
    - Timeout: AGENT_TIMEOUT via asyncio.timeout (Python 3.11+)

    Diferenca do /invoke: o streaming usa asyncio.timeout como
    context manager em vez de asyncio.wait_for, porque o gerador
    SSE e um async for — nao uma unica coroutine.

    Em caso de timeout, o gerador e cancelado e o cliente recebe
    um evento SSE de erro antes da conexao fechar.
    """
    logger = get_logger("stream")

    await agent_semaphore.acquire()
    try:
        async with asyncio.timeout(AGENT_TIMEOUT):
            async for agent_event in agent_module.run_stream(request.message):
                yield ServerSentEvent(
                    event=agent_event.type,
                    data=agent_event.data,
                )

        logger.info("stream_completed")

    except asyncio.TimeoutError:
        # Timeout durante streaming: envia um evento SSE de erro para
        # que o cliente saiba o que aconteceu (em vez de a conexao
        # simplesmente fechar sem explicacao).
        logger.warning(
            "stream_timeout",
            timeout_seconds=AGENT_TIMEOUT,
        )
        yield ServerSentEvent(
            event="error",
            data={"error": "AgentTimeoutError", "detail": f"Timeout de {AGENT_TIMEOUT}s excedido"},
        )

    except Exception as exc:
        logger.error("stream_failed", error=str(exc), error_type=type(exc).__name__)
        yield ServerSentEvent(
            event="error",
            data={"error": "AgentExecutionError", "detail": str(exc)},
        )

    finally:
        agent_semaphore.release()


# ---------------------------------------------------------------------------
# Endpoints asincronos — com logging estruturado
# ---------------------------------------------------------------------------


@app.post("/invoke/async", response_model=AsyncInvokeResponse, status_code=202)
async def invoke_async(request: InvokeRequest) -> AsyncInvokeResponse:
    """
    Enfileira a execucao do agente e retorna imediatamente um task_id.

    Mesmo comportamento do estagio 03, com logging estruturado.
    """
    logger = get_logger("invoke_async")

    task_id = str(uuid.uuid4())

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

    run_agent.delay(task_id, request.message)

    logger.info(
        "task_enqueued",
        task_id=task_id,
        message_preview=request.message[:60],
    )

    return AsyncInvokeResponse(
        task_id=task_id,
        status="pending",
        poll_url=f"/tasks/{task_id}",
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str) -> TaskStatusResponse:
    """
    Consulta o status e o resultado de uma tarefa assincrona.

    Mesmo comportamento do estagio 03, com logging estruturado.
    """
    logger = get_logger("get_task")

    db = SessionLocal()
    try:
        task_record = db.get(TaskRecord, task_id)
        if task_record is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tarefa '{task_id}' nao encontrada.",
            )

        tools_used: list[str] | None = None
        if task_record.tools_used is not None:
            try:
                tools_used = json.loads(task_record.tools_used)
            except (json.JSONDecodeError, TypeError):
                tools_used = []

        logger.info(
            "task_queried",
            task_id=task_id,
            status=task_record.status,
        )

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


# ---------------------------------------------------------------------------
# Health check — com metricas do semaforo
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """
    Verifica a saude do servico e suas dependencias.

    Retorna:
    - Status das dependencias (PostgreSQL, RabbitMQ, Gemini API)
    - Metricas do semaforo de concorrencia (ativos, fila, processados)
    """
    health_result = await run_health_check()

    # Adiciona metricas do semaforo
    semaphore_stats = agent_semaphore.stats
    health_result["concurrency"] = {
        "active": semaphore_stats.active,
        "waiting": semaphore_stats.waiting,
        "max_concurrent": semaphore_stats.max_concurrent,
        "total_processed": semaphore_stats.total_processed,
        "total_rejected": semaphore_stats.total_rejected,
    }

    return health_result
