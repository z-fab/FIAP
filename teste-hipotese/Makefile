.PHONY: help setup infra-up infra-down data train-sklearn train-mlp train-all compare compare-register textbook clean

help: ## Mostra comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Cria venv e instala dependências
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	@echo "\n✅ Setup completo. Ative o venv com: source .venv/bin/activate"

infra-up: ## Sobe MLflow (docker compose)
	docker compose up -d
	@echo "\n✅ MLflow disponível em http://localhost:5001"

infra-down: ## Para MLflow
	docker compose down

data: ## Baixa e preprocessa dataset
	python -m src.data
	@echo "\n✅ Dataset pronto em data/"

train-sklearn: ## Treina RF + LogReg (grid search)
	python -m src.train_sklearn

train-mlp: ## Treina MLP PyTorch (grid search)
	python -m src.train_mlp

train-all: train-sklearn train-mlp ## Treina todos os modelos

compare: ## Comparação estatística entre modelos
	python -m src.compare_models

compare-register: ## Compara + registra vencedor no MLflow Registry
	python -m src.compare_models --register

textbook: ## Serve apostila interativa no browser
	@echo "📖 Apostila disponível em http://localhost:8000"
	cd docs/textbook && python -m http.server 8000

clean: ## Remove dados e artefatos
	rm -rf data/*.csv data/*.xlsx data/scores/ mlflow-data/ mlruns/
	@echo "🧹 Limpeza concluída"
