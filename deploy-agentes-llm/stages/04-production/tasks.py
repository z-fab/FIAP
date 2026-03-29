"""
Worker Celery — Stage 03.

Define o app Celery e a task run_agent, que:
1. Atualiza o status da tarefa para 'processing' no PostgreSQL.
2. Aguarda 2 segundos para simular latência de fila (visível na demo).
3. Executa o agente LLM via asyncio.run().
4. Persiste o resultado (ou o erro) no PostgreSQL.

Por que worker_prefetch_multiplier=1?
--------------------------------------
Tarefas de inferência LLM são longas e consomem muita memória. Com o
prefetch padrão (4), um worker pode reservar várias tarefas antes de
processá-las, deixando as outras esperando na memória do worker em vez
de ficarem na fila para outros workers consumirem. Definir como 1 garante
que cada worker pegue apenas uma tarefa por vez — comportamento ideal para
cargas pesadas e heterogêneas.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime

from celery import Celery
from rich.console import Console

import agent as agent_module
from timeouts import AGENT_TIMEOUT, with_timeout
from database import SessionLocal, init_db
from db_models import TaskRecord

# ---------------------------------------------------------------------------
# Console Rich para output do worker
# ---------------------------------------------------------------------------

_console = Console(force_terminal=True)

# ---------------------------------------------------------------------------
# Configuração do app Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL: str = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//",
)

celery_app = Celery(
    "agent_tasks",
    broker=CELERY_BROKER_URL,
)

celery_app.conf.update(
    # Cada worker reserva apenas 1 tarefa por vez — crítico para tarefas longas
    worker_prefetch_multiplier=1,
    # Confirma a mensagem somente após a tarefa ser concluída (acks_late evita
    # perda de tarefas se o worker morrer durante o processamento)
    task_acks_late=True,
    # Serialização JSON para interoperabilidade
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Fuso horário
    timezone="America/Sao_Paulo",
    enable_utc=True,
)

# ---------------------------------------------------------------------------
# Task principal
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.run_agent", bind=True, max_retries=0)
def run_agent(self, task_id: str, message: str) -> dict:
    """
    Executa o agente LLM de forma assíncrona em background.

    Parâmetros:
        task_id: UUID da tarefa criada pela API (já existe no banco).
        message: Pergunta ou instrução enviada ao agente.

    Retorna:
        Dicionário com status, output e métricas (para fins de log).
    """
    # Garante que o schema está criado antes do primeiro acesso
    init_db()

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # 1. Marca a tarefa como em processamento
        # ------------------------------------------------------------------
        task_record = db.get(TaskRecord, task_id)
        if task_record is None:
            _console.print(
                f"[bold red]Tarefa não encontrada:[/] {task_id}"
            )
            return {"status": "not_found", "task_id": task_id}

        task_record.status = "processing"
        db.commit()

        _console.print(
            f"[bold cyan]Processando tarefa[/] {task_id} | "
            f"mensagem: {message[:60]!r}{'...' if len(message) > 60 else ''}"
        )

        # ------------------------------------------------------------------
        # 2. Simula latência de fila (demonstração em aula)
        # ------------------------------------------------------------------
        _console.print("[dim]Simulando latência de fila (3s)...[/]")
        time.sleep(3)

        # ------------------------------------------------------------------
        # 3. Executa o agente com timeout
        # ------------------------------------------------------------------
        # Reseta o singleton do agente para forcar a criacao de um novo
        # httpx.AsyncClient no event loop desta task. Sem isso, o client
        # herdado do processo pai (fork do Celery) tenta operar em um
        # event loop que nao existe neste processo.
        #
        # O timeout aqui usa o mesmo AGENT_TIMEOUT dos endpoints HTTP.
        # Sem timeout, uma task travada bloqueia o worker Celery
        # indefinidamente — e como workers tem concurrency limitada
        # (--concurrency=2), bastam 2 tasks travadas para parar toda
        # a fila de processamento.
        agent_module.reset_agent()

        async def _run_with_timeout():
            return await with_timeout(
                agent_module.run(message),
                timeout_seconds=AGENT_TIMEOUT,
                context="execucao do agente (celery task)",
            )

        result = asyncio.run(_run_with_timeout())

        # ------------------------------------------------------------------
        # 4. Simula processamento do resultado (demonstração em aula)
        # ------------------------------------------------------------------
        _console.print("[dim]Persistindo resultado (2s)...[/]")
        time.sleep(2)

        # ------------------------------------------------------------------
        # 5. Persiste o resultado no PostgreSQL
        # ------------------------------------------------------------------
        task_record.status = "completed"
        task_record.output = result.output
        task_record.tools_used = json.dumps(result.tools_used)
        task_record.token_count = result.token_count
        task_record.step_count = result.step_count
        task_record.duration_ms = result.duration_ms
        task_record.completed_at = datetime.utcnow()
        db.commit()

        _console.print(
            f"[bold green]Concluído[/] {task_id} | "
            f"tokens={result.token_count} | "
            f"passos={result.step_count} | "
            f"ferramentas={result.tools_used} | "
            f"duração={result.duration_ms}ms"
        )

        return {
            "status": "completed",
            "task_id": task_id,
            "token_count": result.token_count,
            "step_count": result.step_count,
            "duration_ms": result.duration_ms,
        }

    except Exception as exc:
        # ------------------------------------------------------------------
        # 5. Persiste o erro no PostgreSQL
        # ------------------------------------------------------------------
        _console.print(
            f"[bold red]Erro na tarefa[/] {task_id}: {exc}"
        )
        try:
            db.rollback()  # Limpa transação inválida antes de tentar persistir o erro
            task_record = db.get(TaskRecord, task_id)
            if task_record is not None:
                task_record.status = "failed"
                task_record.error = str(exc)
                task_record.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_exc:
            _console.print(
                f"[bold red]Erro ao persistir falha:[/] {db_exc}"
            )

        raise  # propaga para o Celery registrar como falha

    finally:
        db.close()
