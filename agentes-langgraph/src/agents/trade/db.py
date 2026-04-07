"""Persistência JSON para o Pokémon Trade Center.

Gerencia trocas pendentes de aprovação do Professor Oak
usando um arquivo JSON simples compartilhado entre CLI e API.

POR QUE JSON em vez de SQLite/Postgres?
    - Simplicidade didática: alunos podem ABRIR o arquivo e ver o estado
      em tempo real, o que ajuda a entender o fluxo HITL assíncrono.
    - Zero dependências externas — funciona out-of-the-box.
    - Compartilhado entre processos: a CLI e a API leem/escrevem o MESMO
      arquivo, então você pode iniciar uma troca lendária pela CLI e
      aprová-la via endpoint admin da API (ou vice-versa).
    - Em produção: trocar por um BD real (Postgres + SQLAlchemy, etc.).
"""

import json
import uuid
from pathlib import Path

# Caminho do arquivo — na raiz do projeto
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
TRADES_FILE = DATA_DIR / "trades.json"


def _read() -> dict:
    """Lê o arquivo JSON. Retorna dict vazio se não existe."""
    if not TRADES_FILE.exists():
        return {"pending": {}, "completed": {}}
    return json.loads(TRADES_FILE.read_text())


def _write(data: dict) -> None:
    """Escreve no arquivo JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRADES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def generate_thread_id() -> str:
    """Gera um thread ID amigável no formato 'trade-XXXXXX'."""
    return "trade-" + uuid.uuid4().hex[:6]


# --------------------------------------------------------------------------
# Trocas pendentes (Professor Oak)
# --------------------------------------------------------------------------
def save_pending_trade(
    thread_id: str,
    pokemon_offered: str,
    pokemon_requested: str,
    analysis: str,
) -> None:
    """Salva uma troca lendária pendente de aprovação."""
    data = _read()
    data["pending"][thread_id] = {
        "pokemon_offered": pokemon_offered,
        "pokemon_requested": pokemon_requested,
        "analysis": analysis,
        "status": "pending",
    }
    _write(data)


def get_pending_trade(thread_id: str) -> dict | None:
    """Retorna uma troca pendente pelo thread_id, ou None."""
    data = _read()
    return data["pending"].get(thread_id)


def list_pending_trades() -> list[dict]:
    """Lista todas as trocas com status 'pending'."""
    data = _read()
    return [
        {"thread_id": tid, **trade}
        for tid, trade in data["pending"].items()
        if trade["status"] == "pending"
    ]


def update_trade_status(thread_id: str, status: str) -> bool:
    """Atualiza o status de uma troca pendente. Retorna True se encontrou."""
    data = _read()
    if thread_id not in data["pending"]:
        return False
    data["pending"][thread_id]["status"] = status
    _write(data)
    return True


def remove_pending_trade(thread_id: str) -> None:
    """Remove uma troca pendente (após conclusão/rejeição)."""
    data = _read()
    data["pending"].pop(thread_id, None)
    _write(data)


# --------------------------------------------------------------------------
# Trocas concluídas
# --------------------------------------------------------------------------
def save_completed_trade(trade_id: str, offered: str, requested: str) -> None:
    """Registra uma troca concluída."""
    data = _read()
    data["completed"][trade_id] = {
        "offered": offered.lower().strip(),
        "requested": requested.lower().strip(),
    }
    _write(data)
