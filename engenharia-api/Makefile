# ============================================================
#  Engenharia de Software para Data Science & APIs
#  - text-book/ : textbook interativo (HTML)
#  - codigos/   : implementação prática (California Housing)
# ============================================================

PORT ?= 8000

.PHONY: help textbook codigos-install codigos-train codigos-test codigos-run

help:
	@echo "Alvos disponíveis:"
	@echo "  make textbook         Sobe o textbook em http://localhost:$(PORT) (abre o navegador)"
	@echo "  make codigos-install  Instala as dependências da pasta codigos/ (uv sync)"
	@echo "  make codigos-train    Treina o modelo (codigos/)"
	@echo "  make codigos-test     Roda os testes (codigos/)"
	@echo "  make codigos-run      Sobe a API FastAPI (codigos/)"

## Sobe o textbook interativo localmente e abre no navegador
textbook:
	@echo "📚 Servindo o textbook em http://localhost:$(PORT)  (Ctrl+C para parar)"
	@( sleep 1; (command -v open >/dev/null 2>&1 && open "http://localhost:$(PORT)/") || \
	   (command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$(PORT)/") || true ) &
	@cd text-book && python3 -m http.server $(PORT)

## Atalhos para a pasta de código prático
codigos-install:
	@cd codigos && uv sync

codigos-train:
	@cd codigos && uv run task train

codigos-test:
	@cd codigos && uv run task test

codigos-run:
	@cd codigos && uv run task run
