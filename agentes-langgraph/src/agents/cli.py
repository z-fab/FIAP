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
    },
    "2": {
        "name": "Agente de Pesquisa",
        "description": "Busca acadêmica e web com resumo",
        "loader": "agents.research.agent",
    },
    "3": {
        "name": "Pokémon Trade Center",
        "description": "Trocas de Pokémon com aprovação humana",
        "loader": "agents.trade.agent",
    },
}


def _select_agent() -> tuple[str, object, bool]:
    """Mostra menu e retorna (nome, graph, usa_checkpointer)."""
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

    # Apenas o agente Trade (3) usa checkpointer/HITL.
    # Os outros são stateless: cada turno é independente.
    uses_checkpointer = choice == "3"
    console.print(
        f"\n[bold green]{agent_info['name']}[/bold green] conectado. "
        "Digite 'sair' para encerrar.\n"
    )
    return agent_info["name"], graph, uses_checkpointer


async def _stream_response(graph, input_data: dict, config: dict) -> None:
    """Processa stream de eventos do agente e exibe no terminal.

    Usa astream_events v2, que emite eventos granulares durante a execução
    do grafo: início/fim de tools, tokens do LLM, início/fim de nós, etc.
    Aqui filtramos apenas os eventos relevantes para a UX da CLI.
    """
    token_buffer = ""

    # astream_events itera sobre eventos do grafo em tempo real (streaming)
    async for event in graph.astream_events(input_data, config=config, version="v2"):
        event_type = event["event"]

        # --- Tool foi chamada: mostra a chamada (estilo "trace") ---
        if event_type == "on_tool_start":
            tool_name = event.get("name", "?")
            tool_input = event.get("data", {}).get("input", {})
            if isinstance(tool_input, dict):
                args = ", ".join(f'{v}' for v in tool_input.values())
            else:
                args = str(tool_input)
            console.print(f"  [dim yellow]>> {tool_name}({args})[/dim yellow]")

        # --- Tool retornou: mostra o resultado truncado ---
        elif event_type == "on_tool_end":
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

    if token_buffer:
        console.print()


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
            console.print(Panel(
                interrupt_value,
                border_style="yellow",
                title="Confirmação necessária",
            ))
            approved = Confirm.ask("[bold yellow]Aprovar troca?[/bold yellow]")
            response = (
                "sim, eu confirmo a troca"
                if approved
                else "não, cancele a troca"
            )

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
    console.print(Panel(
        "[bold]Comandos disponíveis:[/bold]\n"
        "  [cyan]/agent[/cyan]  — trocar de agente\n"
        "  [cyan]/help[/cyan]   — mostrar esta ajuda\n"
        "  [cyan]/exit[/cyan]   — sair do chat",
        border_style="dim",
        title="Ajuda",
    ))


async def _chat_loop(agent_name: str, graph, uses_checkpointer: bool) -> str:
    """Loop principal do chat.

    Returns:
        "switch" se o usuário quer trocar de agente, "exit" para sair.
    """
    from agents.trade.db import generate_thread_id

    # thread_id identifica esta CONVERSA no checkpointer.
    # Sem ele, o grafo não consegue carregar/salvar estado entre turnos.
    thread_id = generate_thread_id() if uses_checkpointer else ""
    config = {"configurable": {"thread_id": thread_id}} if uses_checkpointer else {}

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

        input_data = {"messages": [{"role": "user", "content": user_input}]}
        if uses_checkpointer:
            input_data["pending_trade_id"] = ""

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
            agent_name, graph, uses_checkpointer = _select_agent()
            result = asyncio.run(_chat_loop(agent_name, graph, uses_checkpointer))
            if result == "exit":
                break
    except KeyboardInterrupt:
        pass

    console.print("\n[dim]Até logo, treinador![/dim]\n")
