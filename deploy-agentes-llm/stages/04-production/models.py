"""
Schemas Pydantic para os endpoints síncrono, streaming e assíncrono — Stage 03.

Define os contratos de entrada e saída da API REST, incluindo os modelos
para os novos endpoints de enfileiramento assíncrono e polling de status.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InvokeRequest(BaseModel):
    """Corpo da requisição para invocar o agente."""

    message: str = Field(
        ...,
        description="Pergunta ou instrução em linguagem natural enviada ao agente.",
        examples=[
            "Qual produto teve maior receita no Q4 de 2025?",
            "Compare o crescimento do AI Assistant em 2024 vs 2025.",
            "Qual a margem de lucro média por região no último trimestre?",
        ],
    )


class InvokeResponse(BaseModel):
    """Corpo da resposta após a execução completa do agente."""

    output: str = Field(
        description="Resposta final gerada pelo agente em linguagem natural."
    )
    tools_used: list[str] = Field(
        description="Lista com os nomes das ferramentas invocadas durante a execução."
    )
    token_count: int = Field(
        description="Total de tokens consumidos na execução (entrada + saída)."
    )
    step_count: int = Field(
        description="Número de passos (iterações) executados no loop ReAct."
    )
    duration_ms: int = Field(
        description="Tempo total de execução em milissegundos, medido no servidor."
    )


class StreamEvent(BaseModel):
    """Evento individual do streaming SSE."""

    type: str = Field(..., description="Tipo do evento.")
    data: dict = Field(default_factory=dict, description="Payload do evento.")


# ---------------------------------------------------------------------------
# Novos schemas do estágio 03 — padrão assíncrono
# ---------------------------------------------------------------------------


class AsyncInvokeResponse(BaseModel):
    """
    Resposta imediata do endpoint POST /invoke/async.

    Retornada assim que a tarefa é criada no banco e enfileirada no
    RabbitMQ — sem aguardar a execução do agente.
    """

    task_id: str = Field(
        description="UUID único da tarefa. Use para consultar o status via GET /tasks/{task_id}."
    )
    status: str = Field(
        description="Status inicial da tarefa. Sempre 'pending' neste momento.",
        examples=["pending"],
    )
    poll_url: str = Field(
        description="URL completa para consultar o status/resultado da tarefa."
    )


class TaskStatusResponse(BaseModel):
    """
    Resposta do endpoint GET /tasks/{task_id}.

    Reflete o estado atual da tarefa no banco PostgreSQL. Os campos de
    resultado (output, tools_used, etc.) ficam nulos enquanto a tarefa
    não estiver concluída.
    """

    task_id: str = Field(description="UUID único da tarefa.")
    status: str = Field(
        description="Estado atual: pending | processing | completed | failed."
    )
    input_message: str = Field(description="Mensagem original enviada ao agente.")
    output: str | None = Field(
        default=None,
        description="Resposta final do agente (disponível quando status='completed').",
    )
    tools_used: list[str] | None = Field(
        default=None,
        description="Ferramentas usadas pelo agente (disponível quando status='completed').",
    )
    token_count: int | None = Field(
        default=None,
        description="Total de tokens consumidos (disponível quando status='completed').",
    )
    step_count: int | None = Field(
        default=None,
        description="Número de passos do loop ReAct (disponível quando status='completed').",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Duração em milissegundos (disponível quando status='completed').",
    )
    error: str | None = Field(
        default=None,
        description="Mensagem de erro (disponível quando status='failed').",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Data e hora de criação da tarefa (UTC).",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Data e hora de conclusão da tarefa (UTC).",
    )
