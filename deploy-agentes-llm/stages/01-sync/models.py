"""
Schemas Pydantic para o endpoint síncrono — Stage 01.

Define os contratos de entrada e saída da API REST.
"""

from __future__ import annotations

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
