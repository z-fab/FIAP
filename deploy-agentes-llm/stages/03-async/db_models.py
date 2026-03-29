"""
Modelos ORM SQLAlchemy — Stage 03.

Define a tabela task_records que persiste o estado e o resultado de cada
tarefa assíncrona processada pelos workers Celery.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

# ---------------------------------------------------------------------------
# Modelo de tarefa
# ---------------------------------------------------------------------------


class TaskRecord(Base):
    """
    Registro de uma tarefa assíncrona de execução do agente.

    Ciclo de vida do campo status:
        pending     → criado pela API antes de enfileirar
        processing  → worker assumiu a tarefa
        completed   → agente finalizou com sucesso
        failed      → erro durante a execução
    """

    __tablename__ = "task_records"

    # Chave primária: UUID gerado pela API antes de enfileirar
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Estado atual da tarefa
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    # Mensagem de entrada enviada ao agente
    input_message: Mapped[str] = mapped_column(Text, nullable=False)

    # Resposta final gerada pelo agente (nulo enquanto não concluído)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ferramentas utilizadas, armazenadas como JSON string (ex.: '["search_database"]')
    tools_used: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Métricas de execução
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Mensagem de erro (preenchida apenas quando status='failed')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<TaskRecord id={self.id!r} status={self.status!r}>"
