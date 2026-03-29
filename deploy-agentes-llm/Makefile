.PHONY: stage-1 stage-2 stage-3 stage-4 stage-down textbook notebooks expose \
        invoke-1 invoke-2 stream-2 invoke-3 stream-3 \
        async-submit async-submit-batch async-poll async-poll-loop \
        test-sync test-stream test-async test-timeout test-concurrency test-health \
        clean logs help

# === Variáveis ===
DOCKER_COMPOSE = docker compose
API_URL = http://localhost:8000

# === Help (target padrão) ===
help: ## Mostra esta ajuda
	@echo ""
	@echo "  Comandos disponíveis:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# === Estágios ===
stage-1: ## Sobe o Estágio 01 (Sync)
	cd stages/01-sync && $(DOCKER_COMPOSE) up --build

stage-2: ## Sobe o Estágio 02 (Stream)
	cd stages/02-stream && $(DOCKER_COMPOSE) up --build

stage-3: ## Sobe o Estágio 03 (Async)
	cd stages/03-async && $(DOCKER_COMPOSE) up --build

stage-4: ## Sobe o Estágio 04 (Production)
	cd stages/04-production && $(DOCKER_COMPOSE) up --build

stage-down: ## Para o estágio que estiver rodando
	@for dir in stages/01-sync stages/02-stream stages/03-async stages/04-production; do \
		(cd $$dir && $(DOCKER_COMPOSE) down 2>/dev/null) || true; \
	done
	@echo "Todos os estágios parados."

# === Textbook ===
textbook: ## Abre o textbook interativo no browser
	@echo "Textbook disponível em: http://localhost:8080"
	@echo "Pressione Ctrl+C para parar."
	python -m http.server 8080 -d textbook/

# === Notebooks ===
notebooks: ## Abre os notebooks Jupyter
	cd notebooks && uv run jupyter notebook

# === Exposição (ngrok) ===
expose: ## Expõe a API via ngrok para acesso externo (requer ngrok instalado)
	@command -v ngrok >/dev/null 2>&1 || { \
		echo "ngrok não encontrado. Instale em: https://ngrok.com/download"; \
		exit 1; \
	}
	@echo "Expondo porta 8000 via ngrok..."
	@echo "Compartilhe a URL gerada com os alunos."
	ngrok http 8000

# === Demos por estágio ===
invoke-1: ## Testa POST /invoke no Estágio 01
	@curl -s -X POST $(API_URL)/invoke \
		-H "Content-Type: application/json" \
		-d '{"message": "Qual o produto com maior receita no Q3 de 2024?"}' | python3 -m json.tool

invoke-2: ## Testa POST /invoke no Estágio 02
	@curl -s -X POST $(API_URL)/invoke \
		-H "Content-Type: application/json" \
		-d '{"message": "Qual o produto com maior receita no Q3 de 2024?"}' | python3 -m json.tool

stream-2: ## Testa POST /stream no Estágio 02 (SSE em tempo real)
	@echo "Streaming SSE (Ctrl+C para parar)..."
	@curl -N -X POST $(API_URL)/stream \
		-H "Content-Type: application/json" \
		-d '{"message": "Compare as vendas do Q2 e Q3 de 2024 por região."}'

invoke-3: ## Testa POST /invoke no Estágio 03
	@curl -s -X POST $(API_URL)/invoke \
		-H "Content-Type: application/json" \
		-d '{"message": "Qual o produto com maior receita no Q3 de 2024?"}' | python3 -m json.tool

stream-3: ## Testa POST /stream no Estágio 03
	@echo "Streaming SSE (Ctrl+C para parar)..."
	@curl -N -X POST $(API_URL)/stream \
		-H "Content-Type: application/json" \
		-d '{"message": "Compare vendas do Q2 e Q3 de 2024."}'

async-submit: ## Enfileira uma task assíncrona (Estágio 03/04)
	@curl -s -X POST $(API_URL)/invoke/async \
		-H "Content-Type: application/json" \
		-d '{"message": "Faça uma análise completa das vendas do AI Assistant em 2025, incluindo crescimento trimestral e comparação entre regiões."}' | python3 -m json.tool

async-submit-batch: ## Enfileira 5 tasks de uma vez (Estágio 03/04)
	@echo "Enfileirando 5 tasks..."
	@for i in 1 2 3 4 5; do \
		echo "--- Task $$i ---"; \
		curl -s -X POST $(API_URL)/invoke/async \
			-H "Content-Type: application/json" \
			-d "{\"message\": \"Análise $$i: Qual a receita total do produto número $$i?\"}" | python3 -m json.tool; \
		echo ""; \
	done

async-poll: ## Consulta status de uma task (uso: make async-poll ID=<task-id>)
	@if [ -z "$(ID)" ]; then \
		echo "Uso: make async-poll ID=<task-id>"; \
		echo "Exemplo: make async-poll ID=abc-123-def"; \
		exit 1; \
	fi
	@curl -s $(API_URL)/tasks/$(ID) | python3 -m json.tool

async-poll-loop: ## Faz polling contínuo de uma task (uso: make async-poll-loop ID=<task-id>)
	@if [ -z "$(ID)" ]; then \
		echo "Uso: make async-poll-loop ID=<task-id>"; \
		exit 1; \
	fi
	@echo "Polling task $(ID) a cada 2s (Ctrl+C para parar)..."
	@while true; do \
		STATUS=$$(curl -s $(API_URL)/tasks/$(ID) | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))"); \
		echo "$$(date +%H:%M:%S) | Status: $$STATUS"; \
		if [ "$$STATUS" = "completed" ] || [ "$$STATUS" = "failed" ]; then \
			echo ""; \
			echo "Resultado final:"; \
			curl -s $(API_URL)/tasks/$(ID) | python3 -m json.tool; \
			break; \
		fi; \
		sleep 2; \
	done

# === Testes do Estágio 04 (requer Estágio 04 rodando) ===
test-sync: ## [Stage 04] Testa o endpoint síncrono (POST /invoke)
	@echo "Testando POST /invoke..."
	@curl -s -X POST $(API_URL)/invoke \
		-H "Content-Type: application/json" \
		-d '{"message": "Qual o produto com maior receita no Q3 de 2024?"}' | python -m json.tool

test-stream: ## [Stage 04] Testa o endpoint de streaming SSE (POST /stream)
	@echo "Testando POST /stream (Ctrl+C para parar)..."
	@curl -N -X POST $(API_URL)/stream \
		-H "Content-Type: application/json" \
		-d '{"message": "Compare as vendas por região no primeiro semestre de 2024."}'

test-async: ## [Stage 04] Testa o fluxo assíncrono (POST /invoke/async + polling)
	@echo "Enfileirando task..."
	@TASK_ID=$$(curl -s -X POST $(API_URL)/invoke/async \
		-H "Content-Type: application/json" \
		-d '{"message": "Qual a tendência de crescimento do AI Assistant?"}' | \
		python -c "import sys,json; print(json.load(sys.stdin)['task_id'])") && \
	echo "Task ID: $$TASK_ID" && \
	echo "Aguardando 8 segundos..." && \
	sleep 8 && \
	echo "Consultando resultado:" && \
	curl -s $(API_URL)/tasks/$$TASK_ID | python -m json.tool

test-timeout: ## [Stage 04] Testa timeout com query complexa (espera ~20s e retorna 504)
	@echo "Enviando request complexa (AGENT_TIMEOUT=20s)..."
	@echo "Aguarde ate 30 segundos para o timeout disparar."
	@HTTP_CODE=$$(curl -s --max-time 30 \
		-o /tmp/agent-timeout-response.json \
		-w "%{http_code}" \
		-X POST $(API_URL)/invoke \
		-H "Content-Type: application/json" \
		-d '{"message": "Faça uma análise completa de todos os produtos em todas as regiões, comparando receita, custo, margem e crescimento trimestre a trimestre, com projeções para Q4 2025."}') && \
	echo "" && \
	echo "HTTP Status: $$HTTP_CODE" && \
	echo "Resposta:" && \
	python -m json.tool /tmp/agent-timeout-response.json 2>/dev/null || cat /tmp/agent-timeout-response.json

test-concurrency: ## [Stage 04] Testa semáforo com 15 requests simultâneas (espera alguns 429s)
	@echo "Enviando 15 requests simultâneas..."
	@for i in $$(seq 1 15); do \
		curl -s -o /dev/null -w "Request $$i: HTTP %{http_code}\n" \
			-X POST $(API_URL)/invoke \
			-H "Content-Type: application/json" \
			-d "{\"message\": \"Request $$i: Qual a receita total?\"}" & \
	done; \
	wait
	@echo "Verifique: algumas devem retornar 429 (limite de concorrência)."

test-health: ## [Stage 04] Testa o health check (GET /health)
	@echo "Testando GET /health..."
	@curl -s $(API_URL)/health | python -m json.tool

# === Utilidades ===
clean: ## Para todos os containers e remove volumes
	@for dir in stages/01-sync stages/02-stream stages/03-async stages/04-production; do \
		(cd $$dir && $(DOCKER_COMPOSE) down -v 2>/dev/null) || true; \
	done
	@echo "Containers parados e volumes removidos."

logs: ## Mostra logs do estágio 04 (production) em tempo real
	cd stages/04-production && $(DOCKER_COMPOSE) logs -f
