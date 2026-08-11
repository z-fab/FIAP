"""CLI de chat interativo com os agentes.

Uso:
    make chat
    uv run python -m agents

Esta CLI demonstra como CONSUMIR um grafo LangGraph:
    - Streaming de eventos em tempo real (astream_events v2)
    - Tratamento de interrupt() para HITL no terminal
    - Uso de checkpointer + thread_id para manter estado entre turnos
"""

import asyncio

# Command(resume=...) é a primitiva usada para RETOMAR um grafo pausado
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

# --- Registro de agentes disponíveis ---
# Cada agente é importado lazy (apenas quando o usuário escolher), assim
# não pagamos o custo de inicializar todos os modelos no startup da CLI.
AGENTS = {
    "1": {
        "name": "Agente Financeiro",
        "description": "Cotações de moedas e ações em tempo real",
        "loader": "agents.financial.agent",
        "kind": "financial",
    },
    "2": {
        "name": "Estúdio de Roteiro",
        "description": "Pipeline criativo: brief → pesquisa → roteiro → crítica",
        "loader": "agents.roteiro.agent",
        "kind": "roteiro",
    },
    "3": {
        "name": "Pokémon Trade Center",
        "description": "Trocas de Pokémon com aprovação humana",
        "loader": "agents.trade.agent",
        "kind": "trade",
    },
}

# Estado inicial do Estúdio de Roteiro (campos reais do pipeline)
_ROTEIRO_ESTADO_INICIAL = {
    "brief": "",
    "research_notes": "",
    "draft": "",
    "critique": "",
    "revision_count": 0,
    "approved": False,
}


def _select_agent() -> tuple[str, object, str]:
    """Mostra menu e retorna (nome, graph, kind)."""
    console.print()
    console.print(Panel("[bold]Agentes disponíveis[/bold]", border_style="cyan"))
    for key, info in AGENTS.items():
        console.print(f"  [cyan]{key}[/cyan]. [bold]{info['name']}[/bold] — {info['description']}")
    console.print()

    choice = Prompt.ask("Escolha um agente", choices=list(AGENTS.keys()), default="3")
    agent_info = AGENTS[choice]

    # Import dinâmico do módulo do agente — só carregamos o que vai ser usado
    module = __import__(agent_info["loader"], fromlist=["graph"])
    graph = module.graph

    console.print(
        f"\n[bold green]{agent_info['name']}[/bold green] conectado. Digite 'sair' para encerrar.\n"
    )
    return agent_info["name"], graph, agent_info["kind"]


def _message_text(msg) -> str:
    """Extrai texto de uma mensagem LangChain / dict (Gemini pode devolver lista)."""
    if msg is None:
        return ""
    content = msg.content if hasattr(msg, "content") else msg
    if isinstance(content, dict) and "content" in content:
        content = content["content"]
    if isinstance(content, list):
        return "".join(
            b["text"] if isinstance(b, dict) and "text" in b else str(b) for b in content
        )
    return str(content) if content is not None else ""


def _texto_finalizar(output) -> str:
    """Pega o AIMessage empacotado pelo nó `finalizar` (sem streaming de LLM)."""
    if not isinstance(output, dict):
        return ""
    messages = output.get("messages") or []
    if not messages:
        return ""
    return _message_text(messages[-1]).strip()


async def _stream_response(graph, input_data: dict | Command, config: dict) -> None:
    """Processa stream de eventos do agente e exibe no terminal.

    Usa astream_events v2, que emite eventos granulares durante a execução
    do grafo: início/fim de tools, tokens do LLM, início/fim de nós, etc.
    Aqui filtramos apenas os eventos relevantes para a UX da CLI.

    Nota: o nó `finalizar` do Estúdio de Roteiro monta a entrega sem chamar
    o LLM — não há on_chat_model_stream. Por isso lemos on_chain_end.
    """
    token_buffer = ""

    def _flush_token_line() -> None:
        """Garante quebra de linha após stream de tokens (evita 'texto ● nó')."""
        nonlocal token_buffer
        if token_buffer:
            if not token_buffer.endswith("\n"):
                console.file.write("\n")
                console.file.flush()
            token_buffer = ""

    # astream_events itera sobre eventos do grafo em tempo real (streaming)
    async for event in graph.astream_events(input_data, config=config, version="v2"):
        event_type = event["event"]

        # --- Nó do grafo iniciado (útil no pipeline do Estúdio de Roteiro) ---
        if event_type == "on_chain_start" and event.get("name"):
            node_name = event["name"]
            if node_name in {
                "brief",
                "pesquisar",
                "roteirizar",
                "validar",
                "finalizar",
                "model",  # create_agent (Agente Financeiro)
                "assistant",  # ReAct manual (Trade)
                "tools",
            }:
                _flush_token_line()
                console.print(f"  [dim cyan]● {node_name}[/dim cyan]")

        # --- Entrega do Estúdio: mensagem montada no nó (sem tokens de LLM) ---
        elif event_type == "on_chain_end" and event.get("name") == "finalizar":
            entrega = _texto_finalizar(event.get("data", {}).get("output"))
            if entrega:
                _flush_token_line()
                console.print()
                console.print(Panel(entrega, border_style="green", title="Entrega final"))

        # --- Tool foi chamada: mostra a chamada (estilo "trace") ---
        elif event_type == "on_tool_start":
            _flush_token_line()
            tool_name = event.get("name", "?")
            tool_input = event.get("data", {}).get("input", {})
            if isinstance(tool_input, dict):
                # Só args do LLM (config injetado pelo runtime não entra no schema)
                public = {k: v for k, v in tool_input.items() if k != "config"}
                args = ", ".join(f"{k}={v!r}" for k, v in public.items())
            else:
                args = str(tool_input)
            # Tools de trade: thread_id vem do config da sessão, não do LLM
            if tool_name in {"propor_troca", "check_professor_approval"}:
                tid = config.get("configurable", {}).get("thread_id")
                if tid:
                    suffix = f", thread_id={tid!r} [injetado]"
                    args = f"{args}{suffix}" if args else f"thread_id={tid!r} [injetado]"
            console.print(f"  [dim yellow]>> {tool_name}({args})[/dim yellow]")

        # --- Tool retornou: mostra o resultado truncado ---
        elif event_type == "on_tool_end":
            _flush_token_line()
            tool_name = event.get("name", "?")
            tool_output = event.get("data", {}).get("output", "")
            if hasattr(tool_output, "content"):
                output_str = str(tool_output.content)
            else:
                output_str = str(tool_output)
            if len(output_str) > 150:
                output_str = output_str[:150] + "..."
            console.print(f"  [dim green]<< {tool_name}: {output_str}[/dim green]")

        # --- Token do LLM (streaming token-a-token) ---
        # Esse é o evento que dá a sensação de "digitação ao vivo"
        elif event_type == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(
                        b["text"] for b in content if isinstance(b, dict) and "text" in b
                    )
                if content:
                    if not token_buffer:
                        console.print()
                    token_buffer += content
                    console.file.write(content)
                    console.file.flush()

    _flush_token_line()


async def _handle_interrupt(graph, config: dict) -> bool:
    """Verifica se há interrupt pendente e trata HITL.

    Após cada execução do grafo, inspecionamos o snapshot do estado.
    Se o grafo está pausado em um interrupt(), snapshot.next não é vazio
    e a task associada terá `interrupts` preenchido. Mostramos a mensagem
    do interrupt ao usuário e enviamos a resposta via Command(resume=...).
    """
    # get_state retorna o snapshot atual do checkpointer (estado + posição)
    snapshot = graph.get_state(config)
    if not (snapshot and snapshot.next and snapshot.tasks):
        return False

    for task in snapshot.tasks:
        if hasattr(task, "interrupts") and task.interrupts:
            # O valor passado para interrupt() vem aqui como .value
            interrupt_value = str(task.interrupts[0].value)
            console.print()
            console.print(
                Panel(
                    interrupt_value,
                    border_style="yellow",
                    title="Confirmação necessária",
                )
            )
            approved = Confirm.ask("[bold yellow]Aprovar troca?[/bold yellow]")
            response = "sim, eu confirmo a troca" if approved else "não, cancele a troca"

            # Command(resume=...) retoma o grafo do ponto exato do interrupt.
            # O valor passado vira o retorno da função interrupt() no nó.
            await _stream_response(
                graph,
                Command(resume=response),
                config,
            )
            return True
    return False


def _print_help() -> None:
    """Mostra os comandos disponíveis no chat."""
    console.print()
    console.print(
        Panel(
            "[bold]Comandos disponíveis:[/bold]\n"
            "  [cyan]/agent[/cyan]  — trocar de agente\n"
            "  [cyan]/help[/cyan]   — mostrar esta ajuda\n"
            "  [cyan]/exit[/cyan]   — sair do chat",
            border_style="dim",
            title="Ajuda",
        )
    )


def _build_input(kind: str, user_input: str) -> dict:
    """Monta o dict de entrada adequado ao agente escolhido."""
    input_data: dict = {"messages": [{"role": "user", "content": user_input}]}
    if kind == "roteiro":
        input_data.update(_ROTEIRO_ESTADO_INICIAL)
    return input_data


async def _chat_loop(agent_name: str, graph, kind: str) -> str:
    """Loop principal do chat.

    Returns:
        "switch" se o usuário quer trocar de agente, "exit" para sair.
    """
    from agents.trade.db import generate_thread_id

    uses_checkpointer = kind == "trade"

    # thread_id identifica esta CONVERSA no checkpointer.
    # Sem ele, o grafo não consegue carregar/salvar estado entre turnos.
    # Para trocas lendárias, o MESMO id é a chave no JSON (data/trades.json).
    thread_id = generate_thread_id() if uses_checkpointer else ""
    config = {"configurable": {"thread_id": thread_id}} if uses_checkpointer else {}

    if uses_checkpointer:
        console.print(
            f"[dim]Sessão trade — thread_id: [cyan]{thread_id}[/cyan] "
            "(use este id em GET /trade/admin/pending e "
            "POST /trade/admin/{{thread_id}}/review)[/dim]"
        )

    console.print("[dim]Comandos: /agent (trocar) · /help · /exit[/dim]")

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]Você[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            return "exit"

        stripped = user_input.strip()
        if not stripped:
            continue

        # --- Comandos slash ---
        cmd = stripped.lower()
        if cmd in ("/exit", "/quit", "/sair", "sair", "exit", "quit"):
            return "exit"
        if cmd in ("/agent", "/agentes"):
            return "switch"
        if cmd in ("/help", "/ajuda", "/?"):
            _print_help()
            continue

        # --- Detecta se o grafo está pausado de um turno anterior ---
        # Se snapshot.next existe, o grafo parou em um interrupt e está
        # esperando um resume. Tratamos a entrada do usuário como a
        # resposta ao interrupt em vez de uma nova mensagem.
        if uses_checkpointer:
            snapshot = graph.get_state(config)
            if snapshot and snapshot.next:
                await _stream_response(
                    graph,
                    Command(resume=user_input),
                    config,
                )
                await _handle_interrupt(graph, config)
                continue

        input_data = _build_input(kind, user_input)
        await _stream_response(graph, input_data, config)

        if uses_checkpointer:
            await _handle_interrupt(graph, config)


def main():
    """Entry point do CLI."""
    console.print(
        Panel(
            "[bold]Agentes FIAP — LangGraph[/bold]\nChat interativo com agentes de IA",
            border_style="blue",
        )
    )

    try:
        # Loop de seleção: cada vez que o usuário digita /agent, voltamos pro menu
        while True:
            agent_name, graph, kind = _select_agent()
            result = asyncio.run(_chat_loop(agent_name, graph, kind))
            if result == "exit":
                break
    except KeyboardInterrupt:
        pass

    console.print("\n[dim]Até logo, treinador![/dim]\n")
