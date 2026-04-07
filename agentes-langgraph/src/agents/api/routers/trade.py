"""Router do Pokémon Trade Center.

Endpoints para o treinador (chat) e admin para o Professor Oak.

Este router demonstra como expor um agente HITL via REST:
    - /invoke      → unifica primeira mensagem e resume de interrupt
    - /stream      → streaming SSE para UX em tempo real
    - /admin/...   → endpoints separados para o Professor Oak (workflow async)
"""

from fastapi import APIRouter, HTTPException
from fastapi.sse import EventSourceResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from agents.api.schemas import AgentRequest, AgentResponse, extract_text
from agents.api.streaming import stream_agent_events
from agents.trade import db
from agents.trade.agent import graph

router = APIRouter()


class AdminReviewRequest(BaseModel):
    """Request do Professor Oak para aprovar/rejeitar uma troca."""

    decision: str = Field(description="approve ou reject")


# --------------------------------------------------------------------------
# Endpoints do treinador
# --------------------------------------------------------------------------
@router.post("/invoke", response_model=AgentResponse)
async def invoke(request: AgentRequest) -> AgentResponse:
    """Endpoint unificado do treinador.

    - Sem interrupt pendente: processa normalmente
    - Com interrupt pendente (rare trade): resume com a mensagem do treinador
    """
    # Se o cliente não passou thread_id, geramos um novo (= nova conversa)
    thread_id = request.thread_id or db.generate_thread_id()
    config = {"configurable": {"thread_id": thread_id}}

    # --- Detecta se a conversa está em meio a um interrupt() ---
    # snapshot.next != [] significa que o grafo está pausado e esperando resume
    snapshot = graph.get_state(config)

    if snapshot and snapshot.next:
        # Conversa pausada → tratamos a mensagem como resposta ao interrupt.
        # Command(resume=...) faz o grafo continuar de onde parou.
        result = await graph.ainvoke(
            Command(resume=request.message),
            config=config,
        )
    else:
        # Conversa nova ou continuação normal → envia mensagem padrão.
        # O checkpointer vai mesclar com o histórico existente automaticamente.
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": request.message}],
                "pending_trade_id": "",
            },
            config=config,
        )

    # --- Após executar, checa se PAROU em um novo interrupt ---
    # Importante porque a próxima requisição precisa saber que está esperando
    # uma resposta do treinador (tipicamente confirmação de troca rara).
    snapshot = graph.get_state(config)
    if snapshot and snapshot.next and snapshot.tasks:
        for task in snapshot.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                # Retorna o conteúdo do interrupt como `response` e marca status
                # waiting_trainer — o frontend usa isso para mostrar UI de confirmação
                return AgentResponse(
                    thread_id=thread_id,
                    status="waiting_trainer",
                    response=str(task.interrupts[0].value),
                )

    # Resposta normal
    messages = result.get("messages", [])
    response_text = extract_text(messages[-1]) if messages else "Troca processada."
    return AgentResponse(
        thread_id=thread_id,
        status="completed",
        response=response_text,
    )


@router.post("/stream", response_class=EventSourceResponse)
async def stream(request: AgentRequest):
    """Streaming SSE para o treinador."""
    thread_id = request.thread_id or db.generate_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {
        "messages": [{"role": "user", "content": request.message}],
        "pending_trade_id": "",
    }
    async for event in stream_agent_events(graph, input_data, config, thread_id):
        yield event


# --------------------------------------------------------------------------
# Endpoints do Professor Oak (admin)
# --------------------------------------------------------------------------
@router.get("/admin/pending")
async def list_pending() -> dict:
    """Lista trocas lendárias pendentes de aprovação."""
    trades = db.list_pending_trades()
    return {"pending_trades": trades, "total": len(trades)}


@router.post("/admin/{thread_id}/review")
async def review_trade(thread_id: str, request: AdminReviewRequest) -> dict:
    """Professor Oak aprova ou rejeita uma troca lendária.

    Apenas muda o status no SQLite. O treinador verifica
    o resultado via check_professor_approval tool.

    Padrão arquitetural importante: este endpoint NÃO interage com o grafo
    LangGraph diretamente. Ele só atualiza o estado externo (JSON). A próxima
    vez que o treinador perguntar sobre a troca, o LLM chamará a tool
    check_professor_approval, que lê esse status. Esse desacoplamento permite
    aprovação totalmente assíncrona — o admin não precisa "estar conectado"
    à mesma sessão do treinador.
    """
    trade = db.get_pending_trade(thread_id)
    if trade is None:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma troca pendente para thread '{thread_id}'.",
        )

    status = "approved" if request.decision == "approve" else "rejected"
    db.update_trade_status(thread_id, status)

    return {
        "thread_id": thread_id,
        "decision": request.decision,
        "message": (
            f"Troca {'aprovada' if request.decision == 'approve' else 'rejeitada'} "
            "pelo Professor Oak."
        ),
    }
