# ============================================================
#  Engenharia de Software para Data Science & APIs
#  - text-book/ : textbook interativo (HTML)
# ============================================================

PORT ?= 8000

.PHONY: help textbook

help:
	@echo "Alvos disponíveis:"
	@echo "  make textbook  Sobe o textbook em http://localhost:$(PORT) (abre o navegador)"
	@echo ""
	@echo "Variáveis:"
	@echo "  PORT=$(PORT)"

## Sobe o textbook interativo localmente e abre no navegador
textbook:
	@echo "📚 Servindo o textbook em http://localhost:$(PORT)  (Ctrl+C para parar)"
	@( sleep 1; (command -v open >/dev/null 2>&1 && open "http://localhost:$(PORT)/") || \
	   (command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$(PORT)/") || true ) &
	@cd text-book && python3 -m http.server $(PORT)
