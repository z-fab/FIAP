"""Utilitários de streaming SSE compartilhados entre os routers.

Processa eventos do LangGraph (astream_events v2) e emite eventos SSE
tipados: início/fim de nó, chamadas de ferramentas, tokens de texto.

POR QUE SSE (Server-Sent Events) e não WebSocket?
    - SSE é unidirecional (servidor → cliente), perfeito para streaming
      de respostas de LLM. Não precisamos de bidirecional aqui.
    - Funciona sobre HTTP normal (sem upgrade), passa por proxies/CDNs.
    - O navegador implementa reconexão automática.
    - Mais simples que WebSocket para esse caso de uso.

Mapeamento de eventos LangGraph → SSE:
    on_chain_start    → node_start
    on_chain_end      → node_end
    on_tool_start     → tool_call
    on_tool_end       → tool_result
    on_chat_model_stream → token (um por token gerado pelo LLM)
    (final do iter)   → done
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi.sse import ServerSentEvent

logger = logging.getLogger("agents.stream")


async def stream_agent_events(
    graph: Any,
    input_data: dict,
    config: dict,
    thread_id: str,
) -> AsyncIterator[ServerSentEvent]:
    """Gera eventos SSE a partir do stream de um grafo LangGraph.

    Eventos emitidos:
    - **node_start**: Início de execução de um nó (nome do nó)
    - **node_end**: Fim de execução de um nó
    - **tool_call**: Agente decidiu chamar uma ferramenta (nome + argumentos)
    - **tool_result**: Resultado da execução de uma ferramenta
    - **token**: Token de texto gerado pelo modelo (streaming)
    - **done**: Fim do stream

    Args:
        graph: Grafo LangGraph compilado.
        input_data: Dados de entrada para o grafo.
        config: Configuração com thread_id.
        thread_id: ID da sessão para incluir nos eventos.
    """
    async for event in graph.astream_events(input_data, config=config, version="v2"):
        event_type = event["event"]

        # --- Início de nó ---
        if event_type == "on_chain_start" and event.get("name"):
            node_name = event["name"]
            # Filtrar nós internos do LangGraph (começam com __)
            if not node_name.startswith("_"):
                logger.info("Nó iniciado: %s", node_name)
                yield ServerSentEvent(
                    data=dict({
                        "node": node_name,
                        "thread_id": thread_id,
                    }),
                    event="node_start",
                )

        # --- Fim de nó ---
        elif event_type == "on_chain_end" and event.get("name"):
            node_name = event["name"]
            if not node_name.startswith("_"):
                logger.info("Nó finalizado: %s", node_name)
                yield ServerSentEvent(
                    data=dict({
                        "node": node_name,
                        "thread_id": thread_id,
                    }),
                    event="node_end",
                )

        # --- Chamada de ferramenta (agente decidiu usar tool) ---
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "unknown")
            tool_input = event.get("data", {}).get("input", {})
            logger.info("Tool chamada: %s(%s)", tool_name, tool_input)
            yield ServerSentEvent(
                data=dict({
                    "tool": tool_name,
                    "input": tool_input,
                    "thread_id": thread_id,
                }),
                event="tool_call",
            )

        # --- Resultado de ferramenta ---
        elif event_type == "on_tool_end":
            tool_name = event.get("name", "unknown")
            tool_output = event.get("data", {}).get("output", "")
            # Extrair .content se for um objeto de mensagem do LangChain
            if hasattr(tool_output, "content"):
                output_str = str(tool_output.content)
            else:
                output_str = str(tool_output)
            if len(output_str) > 500:
                output_str = output_str[:500] + "..."
            logger.info("Tool resultado: %s → %s", tool_name, output_str[:100])
            yield ServerSentEvent(
                data=dict({
                    "tool": tool_name,
                    "output": output_str,
                    "thread_id": thread_id,
                }),
                event="tool_result",
            )

        # --- Token de texto (streaming do modelo) ---
        elif event_type == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                # Normalizar content (pode ser lista no Gemini)
                if isinstance(content, list):
                    content = "".join(
                        b["text"] for b in content if isinstance(b, dict) and "text" in b
                    )
                if content:
                    yield ServerSentEvent(
                        data=dict({"token": content, "thread_id": thread_id}),
                        event="token",
                    )

    # --- Fim do stream ---
    yield ServerSentEvent(
        data=dict({"thread_id": thread_id, "status": "completed"}),
        event="done",
    )
