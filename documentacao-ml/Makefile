# Textbook — Documentação em ML
# Servidor local para preview do textbook estático.

PORT    ?= 8765
HOST    ?= localhost
DIR     := textbook
URL     := http://$(HOST):$(PORT)/index.html
PIDFILE := .textbook-server.pid

.PHONY: help serve stop open restart status clean

help: ## Mostra esta ajuda
	@echo "Textbook — Documentação em ML"
	@echo ""
	@echo "Alvos disponíveis:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Variáveis:"
	@echo "  PORT=$(PORT)  HOST=$(HOST)  DIR=$(DIR)"

serve: ## Sobe servidor HTTP em primeiro plano (Ctrl+C para parar)
	@echo "→ Servindo $(DIR)/ em $(URL)"
	@echo "  Ctrl+C para parar."
	@cd $(DIR) && python3 -m http.server $(PORT) --bind $(HOST)

start: ## Sobe servidor em background e salva PID
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "→ Já rodando (PID $$(cat $(PIDFILE))) em $(URL)"; \
	else \
		cd $(DIR) && python3 -m http.server $(PORT) --bind $(HOST) > /tmp/textbook-server.log 2>&1 & \
		echo $$! > $(PIDFILE); \
		sleep 0.4; \
		echo "→ Servidor iniciado (PID $$(cat $(PIDFILE))) em $(URL)"; \
	fi

stop: ## Para o servidor em background
	@if [ -f $(PIDFILE) ]; then \
		PID=$$(cat $(PIDFILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID && echo "→ Servidor parado (PID $$PID)"; \
		else \
			echo "→ Processo $$PID não está rodando"; \
		fi; \
		rm -f $(PIDFILE); \
	else \
		echo "→ Nenhum servidor gerenciado ativo"; \
	fi
	@-lsof -ti:$(PORT) | xargs -r kill 2>/dev/null || true

restart: stop start ## Reinicia o servidor em background

status: ## Mostra o status do servidor
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "→ Rodando (PID $$(cat $(PIDFILE))) em $(URL)"; \
	else \
		echo "→ Parado"; \
	fi

open: ## Abre o textbook no navegador padrão (usar com 'make start' antes)
	@command -v open > /dev/null && open "$(URL)" || \
	 command -v xdg-open > /dev/null && xdg-open "$(URL)" || \
	 echo "→ Abra manualmente: $(URL)"

clean: ## Remove artefatos de preview (screenshots, logs)
	@rm -f $(PIDFILE) /tmp/textbook-server.log
	@rm -rf .playwright-mcp
	@find . -maxdepth 2 -name 'tb-*.png' -delete 2>/dev/null || true
	@find . -maxdepth 2 -name 'cap*-snap.yml' -delete 2>/dev/null || true
	@echo "→ Artefatos removidos"
