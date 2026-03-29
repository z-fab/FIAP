"""
Configuração de logging estruturado — Stage 04 (Production).

Por que structlog em vez de logging padrão?
---------------------------------------------
O módulo logging do Python emite mensagens de texto livre. Em produção,
ferramentas como ELK, Datadog e CloudWatch Logs precisam parsear essas
mensagens com regex frágeis para extrair campos.

structlog emite eventos estruturados (chave=valor) que, em modo
produção, são serializados como JSON — prontos para ingestão direta
por qualquer sistema de observabilidade:

    {"event": "request_completed", "method": "POST", "path": "/invoke",
     "status": 200, "duration_ms": 1234, "request_id": "a1b2c3d4"}

Em desenvolvimento, o mesmo log aparece colorido e legível no terminal:

    [info] request_completed  method=POST  path=/invoke  status=200

Dois modos, mesmo código — alternado pela variável ENVIRONMENT.
"""

from __future__ import annotations

import os
import uuid

import structlog


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
"""Ambiente atual: 'development' (console colorido) ou 'production' (JSON)."""


def setup_logging() -> None:
    """
    Configura structlog para o ambiente atual.

    - development: ConsoleRenderer com cores para leitura humana.
    - production: JSONRenderer para ingestão por ferramentas de log.

    Deve ser chamada uma vez no lifespan da aplicação, antes de qualquer
    log ser emitido.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if ENVIRONMENT == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Retorna um logger structlog vinculado ao nome do módulo.

    Argumentos:
        name: nome do módulo (tipicamente __name__).

    Retorna:
        Logger com o campo 'logger' pré-preenchido.
    """
    return structlog.get_logger(name)


def generate_request_id() -> str:
    """
    Gera um ID curto e único para rastreamento de requisição.

    Formato: primeiros 8 caracteres de um UUID4 (ex: "a1b2c3d4").
    Suficiente para identificar requisições em logs durante a vida
    útil típica de uma sessão de debug.
    """
    return str(uuid.uuid4())[:8]
