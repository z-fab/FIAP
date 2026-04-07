.PHONY: install dev chat textbook lint format typecheck check

install: ## Instala dependências
	uv sync

dev: ## Roda o servidor de desenvolvimento (API)
	uv run uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8000

chat: ## Chat interativo com os agentes
	uv run python -m agents

textbook: ## Serve o textbook em http://localhost:8080
	@uv run python -c "from rich import print; print('[bold cyan]Textbook em http://localhost:8080[/bold cyan]')"
	@cd textbook && uv run python -m http.server 8080

lint: ## Verifica código com ruff
	uv run ruff check src/

format: ## Formata código com ruff
	uv run ruff format src/

typecheck: ## Verifica tipos com ty
	uv run ty check src/

check: lint typecheck ## Roda lint + typecheck

# ======================================================================
# Exportação de grafos (Mermaid)
# ======================================================================
FMT_GRAPH := uv run python scripts/export_graph.py

graph-financial: ## Exporta grafo do agente financeiro (Mermaid)
	@$(FMT_GRAPH) financial

graph-research: ## Exporta grafo do agente de pesquisa (Mermaid)
	@$(FMT_GRAPH) research

graph-trade: ## Exporta grafo do Pokémon Trade Center (Mermaid)
	@$(FMT_GRAPH) trade

graph-all: ## Exporta todos os grafos (Mermaid)
	@$(FMT_GRAPH) all

graph-save: ## Exporta e salva todos os grafos em docs/graphs/
	@$(FMT_GRAPH) all --save

help: ## Mostra esta ajuda
	@uv run python -c "\
	from rich.console import Console; \
	from rich.table import Table; \
	c = Console(); \
	t = Table(title='Comandos disponíveis', show_header=True, header_style='bold cyan'); \
	t.add_column('Comando', style='green', no_wrap=True); \
	t.add_column('Descrição'); \
	import re; \
	[t.add_row(m.group(1), m.group(2)) for line in open('Makefile') if (m := re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line))] or None; \
	c.print(t)"
