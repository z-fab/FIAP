"""
Controle de concorrência com semáforo — Stage 04 (Production).

Por que limitar concorrência de agentes LLM?
----------------------------------------------
Cada execução de agente consome:
- Memória do processo Python (~50-200 MB por execução com LangGraph)
- Uma conexão ativa com a API do modelo (Gemini) — sujeita a rate limit
- CPU para parsing de ferramentas e serialização

Sem limite, um pico de requisições pode:
1. Esgotar a memória do container (OOM kill)
2. Estourar o rate limit da API do modelo (429 do Google)
3. Degradar latência de TODAS as requisições (contenção de recursos)

O semáforo garante que no máximo N agentes executem simultaneamente.
Requisições excedentes aguardam numa fila; se a fila também encher,
o servidor retorna 429 imediatamente — sinalizando ao cliente para
fazer backoff, em vez de aceitar trabalho que não consegue processar.

Analogia: é como o limite de mesas em um restaurante. Quando lota,
clientes esperam na fila. Quando a fila transborda, o segurança
pede para voltarem mais tarde.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from rich.console import Console

from errors import ConcurrencyLimitError

# ---------------------------------------------------------------------------
# Console Rich para logs de rejeição
# ---------------------------------------------------------------------------

_console = Console()

# ---------------------------------------------------------------------------
# Configuração via variáveis de ambiente
# ---------------------------------------------------------------------------

MAX_CONCURRENT: int = int(os.getenv("MAX_CONCURRENT_AGENTS", "3"))
"""Número máximo de agentes executando simultaneamente."""

MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "10"))
"""Número máximo de requisições aguardando na fila do semáforo."""


# ---------------------------------------------------------------------------
# Estatísticas de concorrência
# ---------------------------------------------------------------------------


@dataclass
class ConcurrencyStats:
    """Snapshot das métricas do semáforo em um instante."""

    active: int
    """Número de agentes executando agora."""

    waiting: int
    """Número de requisições aguardando na fila."""

    max_concurrent: int
    """Limite máximo configurado de execuções simultâneas."""

    total_processed: int
    """Total acumulado de requisições processadas desde o boot."""

    total_rejected: int
    """Total acumulado de requisições rejeitadas (429) desde o boot."""


# ---------------------------------------------------------------------------
# Semáforo de agentes
# ---------------------------------------------------------------------------


class AgentSemaphore:
    """
    Semáforo assíncrono com fila limitada para controle de concorrência.

    Uso típico:
        await agent_semaphore.acquire()
        try:
            resultado = await agent.run(...)
        finally:
            agent_semaphore.release()
    """

    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT,
        max_queue: int = MAX_QUEUE_SIZE,
    ):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._max_queue = max_queue

        # Contadores atômicos (seguros em asyncio single-thread)
        self._active: int = 0
        self._waiting: int = 0
        self._total_processed: int = 0
        self._total_rejected: int = 0

    async def acquire(self) -> None:
        """
        Adquire uma vaga no semáforo ou aguarda na fila.

        Se a fila de espera já atingiu MAX_QUEUE_SIZE, rejeita
        imediatamente com ConcurrencyLimitError (429).
        """
        if self._waiting >= self._max_queue:
            self._total_rejected += 1
            _console.print(
                f"[bold red]Requisição rejeitada (429)[/] | "
                f"fila={self._waiting}/{self._max_queue} | "
                f"ativos={self._active}/{self._max_concurrent}"
            )
            raise ConcurrencyLimitError(
                f"Limite de concorrência atingido. "
                f"Ativos: {self._active}/{self._max_concurrent}, "
                f"Fila: {self._waiting}/{self._max_queue}. "
                f"Tente novamente em instantes."
            )

        self._waiting += 1
        try:
            await self._semaphore.acquire()
        finally:
            self._waiting -= 1

        self._active += 1

    def release(self) -> None:
        """Libera a vaga no semáforo e incrementa o contador de processados."""
        self._active -= 1
        self._total_processed += 1
        self._semaphore.release()

    @property
    def stats(self) -> ConcurrencyStats:
        """Retorna um snapshot das métricas atuais do semáforo."""
        return ConcurrencyStats(
            active=self._active,
            waiting=self._waiting,
            max_concurrent=self._max_concurrent,
            total_processed=self._total_processed,
            total_rejected=self._total_rejected,
        )


# ---------------------------------------------------------------------------
# Instância global (singleton)
# ---------------------------------------------------------------------------

agent_semaphore = AgentSemaphore()
"""
Instância global do semáforo de agentes.

Compartilhada entre todos os endpoints da API. Cada worker uvicorn
mantém sua própria instância (não é compartilhada entre processos).
"""
