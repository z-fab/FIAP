"""
Configuração do banco de dados PostgreSQL — Stage 03.

Usa SQLAlchemy com DeclarativeBase para ORM e expõe:
- engine / SessionLocal para uso interno
- get_db() como dependência FastAPI (via Depends)
- init_db() chamado no lifespan para criar as tabelas
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# URL de conexão
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://agent:agent@postgres:5432/agent_tasks",
)

# ---------------------------------------------------------------------------
# Engine e fábrica de sessões
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    # Pool conservador: adequado para workers Celery com concorrência baixa
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # verifica conexão antes de usar do pool
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Base declarativa compartilhada pelos modelos ORM
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Base para todos os modelos SQLAlchemy deste estágio."""


# ---------------------------------------------------------------------------
# Dependência FastAPI
# ---------------------------------------------------------------------------


def get_db():
    """
    Dependência FastAPI que fornece uma sessão de banco de dados por requisição.

    Uso:
        @app.get("/exemplo")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Inicialização do schema
# ---------------------------------------------------------------------------


def init_db() -> None:
    """
    Cria todas as tabelas definidas nos modelos ORM, se ainda não existirem.

    Deve ser chamado no lifespan da aplicação FastAPI e no início de cada
    worker Celery para garantir que o schema esteja pronto antes do uso.
    """
    # Importa os modelos para garantir que estejam registrados na Base antes
    # de chamar create_all
    import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
