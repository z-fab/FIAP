#!/usr/bin/env python3
"""Exporta o grafo de um agente como diagrama Mermaid.

Uso: uv run python scripts/export_graph.py <financial|research|trade> [--save]

Sem --save: imprime o Mermaid no terminal.
Com --save: salva em docs/graphs/<agente>.mmd

POR QUE exportar para Mermaid?
    Todo grafo LangGraph compilado expõe `.get_graph().draw_mermaid()`,
    que retorna uma representação textual do grafo no formato Mermaid.
    Isso é ÓTIMO para documentação porque:
    - Renderiza no GitHub/GitLab/Notion automaticamente
    - Pode ser visualizado em https://mermaid.live
    - Facilita explicar a arquitetura do agente em aulas/textbook
    - Atualiza automaticamente quando você muda o grafo no código
"""

import argparse
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

AGENTS = {
    "financial": "agents.financial.agent",
    "research": "agents.research.agent",
    "trade": "agents.trade.agent",
}


def _apply_dark_theme(mermaid: str) -> str:
    """Substitui as classes CSS padrão do LangGraph por cores para fundo escuro.

    O LangGraph emite Mermaid com cores claras (fundo branco). Aqui fazemos
    substituições por regex para adaptar ao tema One Dark do textbook.
    """
    mermaid = re.sub(
        r"classDef default fill:#f2f0ff,line-height:1\.2",
        "classDef default fill:#282c34,line-height:1.2,color:#abb2bf,stroke:#61afef",
        mermaid,
    )
    mermaid = re.sub(
        r"classDef first fill-opacity:0",
        "classDef first fill-opacity:0,color:#abb2bf,stroke:#61afef",
        mermaid,
    )
    mermaid = re.sub(
        r"classDef last fill:#bfb6fc",
        "classDef last fill:#c678dd,color:#282c34,stroke:#c678dd",
        mermaid,
    )
    return mermaid


def main():
    parser = argparse.ArgumentParser(description="Exporta grafo LangGraph como Mermaid")
    parser.add_argument(
        "agent",
        choices=list(AGENTS.keys()) + ["all"],
        help="Agente para exportar (ou 'all' para todos)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Salva em docs/graphs/<agente>.mmd",
    )
    args = parser.parse_args()

    agents_to_export = list(AGENTS.keys()) if args.agent == "all" else [args.agent]

    for agent_name in agents_to_export:
        module_path = AGENTS[agent_name]
        try:
            module = __import__(module_path, fromlist=["graph"])
            graph = module.graph
            mermaid = _apply_dark_theme(graph.get_graph().draw_mermaid())
        except Exception as e:
            console.print(f"[red]Erro ao exportar '{agent_name}': {e}[/red]")
            continue

        if args.save:
            out_dir = Path("docs/graphs")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{agent_name}.mmd"
            out_file.write_text(mermaid)
            console.print(f"[green]Salvo:[/green] {out_file}")
        else:
            syntax = Syntax(mermaid, "mermaid", theme="monokai", line_numbers=False)
            console.print(
                Panel(syntax, title=f"Grafo: {agent_name}", border_style="cyan", expand=False)
            )

    if not args.save:
        console.print(
            "\n[dim]Dica: use --save para salvar em docs/graphs/ "
            "ou cole em https://mermaid.live para visualizar[/dim]"
        )


if __name__ == "__main__":
    main()
