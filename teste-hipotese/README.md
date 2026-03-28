# Teste de Hipótese Aplicado à Avaliação de Modelos de ML

Material de aula para o curso de **Machine Learning Engineering** (PosTech FIAP) sobre como usar testes de hipótese para comparar modelos de ML com rigor estatístico.

## Conteúdo

### Apostila Interativa (`docs/textbook/`)

Apostila em HTML/CSS/JS com 6 capítulos navegáveis, contendo:

- Teoria completa sobre teste de hipótese aplicado a ML
- Simuladores interativos (p-valor, erro tipo I/II, poder)
- Calculadoras de testes estatísticos (t-test, Wilcoxon, Friedman, Cohen's d)

### Código Prático (`src/` e `notebooks/`)

Pipeline completo de treinamento com grid search e comparação estatística:

- **Dataset**: UCI Default of Credit Card Clients (30k amostras, classificação binária)
- **Modelos**: Random Forest, Logistic Regression, MLP (PyTorch) — múltiplas configs cada
- **Tracking**: MLflow para registro de experimentos (grid search completo)
- **Comparação**: Testes de hipótese recuperando dados do MLflow

## Quick Start

### 1. Setup

```bash
make setup
source .venv/bin/activate
```

### 2. MLflow

```bash
make infra-up
# MLflow UI: http://localhost:5001
```

### 3. Dataset

```bash
make data
```

### 4. Treinamento (Grid Search)

```bash
make train-all      # Grid search sklearn + MLP
# ou individualmente:
make train-sklearn   # RF + LogReg grid search
make train-mlp       # MLP grid search
```

### 5. Comparação Estatística

```bash
make compare           # Comparação estatística entre modelos
make compare-register  # Compara + registra vencedor no MLflow Registry
```

> Os scores são recuperados diretamente do MLflow (sem CSVs intermediários).
> Use `--register` para registrar o modelo vencedor no Model Registry.

### 6. Apostila Interativa

```bash
make textbook
# Abra http://localhost:8000
```

## Estrutura do Repositório

```
├── docs/
│   └── textbook/                    # Apostila interativa (HTML)
│       ├── pages/01-intro.html      # Cap 1: Por que Teste de Hipótese?
│       ├── ...
│       └── pages/06-pitfalls.html
├── src/
│   ├── config.py                    # Configurações + grids de hiperparâmetros
│   ├── data.py                      # Download, preprocessamento, loading
│   ├── train_sklearn.py             # Grid search RF + LogReg
│   ├── train_mlp.py                 # Grid search MLP PyTorch
│   ├── compare_models.py            # Comparação estatística (CLI)
│   └── utils.py                     # Funções utilitárias
├── notebooks/
│   ├── 01_eda.ipynb                 # EDA rápido
│   └── 02_hypothesis_tests.ipynb    # Testes de hipótese (core)
├── docker-compose.yml               # MLflow server
├── Makefile                         # Comandos úteis
└── pyproject.toml                   # Dependências
```
