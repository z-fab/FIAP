"""Configuracoes centrais do projeto."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Reproducibilidade
RANDOM_SEED = 42
N_FOLDS = 10

# MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
EXPERIMENT_NAME = "teste-hipotese-credit-default"

# Dataset
DATASET_KAGGLE = "uciml/default-of-credit-card-clients-dataset"
DATASET_FILENAME = "credit_default.csv"
TARGET_COL = "default"

# Metricas para avaliacao
METRICS = ["roc_auc", "f1", "recall", "precision", "average_precision"]
PRIMARY_METRIC = "roc_auc"

# Grid Search — Random Forest
RF_GRID = [
    {
        "n_estimators": 100,
        "max_depth": 5,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    },
    {
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    },
    {
        "n_estimators": 300,
        "max_depth": 15,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    },
]

# Grid Search — Logistic Regression
LR_GRID = [
    {
        "C": 0.1,
        "max_iter": 1000,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
    },
    {
        "C": 1.0,
        "max_iter": 1000,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
    },
    {
        "C": 10.0,
        "max_iter": 1000,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
    },
]

# Grid Search — MLP
MLP_GRID = [
    {
        "hidden_layers": [64, 32],
        "dropout": 0.3,
        "learning_rate": 1e-3,
        "batch_size": 256,
        "max_epochs": 100,
        "patience": 10,
    },
    {
        "hidden_layers": [128, 64],
        "dropout": 0.2,
        "learning_rate": 5e-4,
        "batch_size": 128,
        "max_epochs": 100,
        "patience": 10,
    },
    {
        "hidden_layers": [128, 64, 32],
        "dropout": 0.2,
        "learning_rate": 5e-4,
        "batch_size": 128,
        "max_epochs": 150,
        "patience": 15,
    },
]
