"""
Health checks — Stage 04 (Production).

Por que health checks são essenciais?
---------------------------------------
Orquestradores (Docker, Kubernetes, ECS) usam health checks para
decidir se um container está apto a receber tráfego. Sem eles:
- Um container com banco inacessível continua recebendo requests → 500s
- Um container sem conectividade com o broker não processa tarefas async
- Deploys blue/green não sabem quando a nova versão está pronta

Verificamos três dependências críticas:
1. **PostgreSQL** — sem banco, as tasks async não persistem
2. **RabbitMQ** — sem broker, /invoke/async não funciona
3. **Gemini API** — sem modelo, nenhuma inferência é possível

Se todas estão OK → "healthy" (200)
Se alguma falhou → "degraded" (200, mas com componentes detalhados)

O status "degraded" permite que o load balancer mantenha o container
ativo (serve /invoke e /stream que não dependem de fila), enquanto
alertas notificam a equipe sobre a dependência degradada.
"""

from __future__ import annotations

import os
import socket
from typing import Any

import httpx
from sqlalchemy import text

from database import SessionLocal

# ---------------------------------------------------------------------------
# Variáveis de ambiente para conectividade
# ---------------------------------------------------------------------------

RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# Checagens individuais
# ---------------------------------------------------------------------------


def check_postgres() -> dict[str, Any]:
    """
    Verifica conectividade com o PostgreSQL executando SELECT 1.

    Retorna:
        {"status": "ok"} ou {"status": "error", "detail": "..."}
    """
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok"}
        finally:
            db.close()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_rabbitmq() -> dict[str, Any]:
    """
    Verifica conectividade com o RabbitMQ via socket TCP.

    Não usa AMQP completo para manter a checagem leve e rápida
    (< 100ms em condições normais).

    Retorna:
        {"status": "ok"} ou {"status": "error", "detail": "..."}
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((RABBITMQ_HOST, RABBITMQ_PORT))
        sock.close()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


async def check_gemini() -> dict[str, Any]:
    """
    Verifica conectividade com a API Gemini listando modelos disponíveis.

    Usa um endpoint leve (list models) para confirmar que a API key é
    válida e que o serviço está acessível.

    Retorna:
        {"status": "ok"} ou {"status": "error", "detail": "..."}
    """
    if not GEMINI_API_KEY:
        return {"status": "error", "detail": "GEMINI_API_KEY não configurada"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": GEMINI_API_KEY},
            )
            if response.status_code == 200:
                return {"status": "ok"}
            return {
                "status": "error",
                "detail": f"HTTP {response.status_code}",
            }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ---------------------------------------------------------------------------
# Checagem agregada
# ---------------------------------------------------------------------------


async def run_health_check() -> dict[str, Any]:
    """
    Executa todas as checagens e retorna um relatório consolidado.

    Retorna:
        {
            "status": "healthy" | "degraded",
            "components": {
                "postgres": {"status": "ok"},
                "rabbitmq": {"status": "ok"},
                "gemini": {"status": "ok"}
            }
        }
    """
    postgres = check_postgres()
    rabbitmq = check_rabbitmq()
    gemini = await check_gemini()

    components = {
        "postgres": postgres,
        "rabbitmq": rabbitmq,
        "gemini": gemini,
    }

    all_ok = all(c["status"] == "ok" for c in components.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "components": components,
    }
