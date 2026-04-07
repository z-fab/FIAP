"""Router do agente de pesquisa acadêmica.

Endpoints para interação síncrona (invoke) e streaming (SSE).
"""

import uuid

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse

from agents.api.schemas import AgentRequest, AgentResponse, extract_text
from agents.api.streaming import stream_agent_events
from agents.research.agent import graph

router = APIRouter()


@router.post("/invoke", response_model=AgentResponse)
async def invoke(request: AgentRequest) -> AgentResponse:
    """Envia uma mensagem ao agente de pesquisa e retorna a resposta completa."""
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": request.message}],
            "query": request.message,
            "sources_found": 0,
        },
        config=config,
    )

    last_message = result["messages"][-1]
    response_text = extract_text(last_message)

    return AgentResponse(
        thread_id=thread_id,
        status="completed",
        response=response_text,
    )


@router.post("/stream", response_class=EventSourceResponse)
async def stream(request: AgentRequest):
    """Streaming SSE do agente de pesquisa."""
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {
        "messages": [{"role": "user", "content": request.message}],
        "query": request.message,
        "sources_found": 0,
    }

    async for event in stream_agent_events(graph, input_data, config, thread_id):
        yield event
