"""Treinamento de MLP (PyTorch) com Grid Search, K-Fold CV e logging no MLflow."""

import logging

import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from torch.utils.data import DataLoader, TensorDataset

from src.config import (
    EXPERIMENT_NAME,
    METRICS,
    MLFLOW_TRACKING_URI,
    MLP_GRID,
    N_FOLDS,
    PRIMARY_METRIC,
    RANDOM_SEED,
)
from src.data import get_cv_splits, load_and_preprocess
from src.utils import compute_metrics

logger = logging.getLogger(__name__)
console = Console()


class MLP(nn.Module):
    """Multi-Layer Perceptron para classificacao binaria."""

    def __init__(self, input_dim: int, hidden_layers: list[int], dropout: float = 0.3):
        super().__init__()
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_layers:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


def set_seed(seed: int):
    """Fixa seed para reproducibilidade."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_one_fold(
    model: MLP,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    params: dict,
) -> tuple[MLP, list[float]]:
    """Treina MLP em um fold com early stopping."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Datasets
    train_ds = TensorDataset(
        torch.FloatTensor(X_train).to(device),
        torch.FloatTensor(y_train).to(device),
    )
    train_loader = DataLoader(train_ds, batch_size=params["batch_size"], shuffle=True)

    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.FloatTensor(y_val).to(device)

    # Peso para classe desbalanceada
    n_neg = (y_train == 0).sum()
    n_pos = max((y_train == 1).sum(), 1)
    pos_weight = torch.tensor([n_neg / n_pos]).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=params["learning_rate"])

    best_val_loss = float("inf")
    patience_counter = 0
    train_losses = []
    best_state = None

    for epoch in range(params["max_epochs"]):
        # Treino
        model.train()
        epoch_loss = 0.0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            logits = model(X_batch).squeeze()
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        train_losses.append(epoch_loss / len(train_loader))

        # Validacao
        model.eval()
        with torch.no_grad():
            val_logits = model(X_val_t).squeeze()
            val_loss = criterion(val_logits, y_val_t).item()

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= params["patience"]:
                logger.debug("Early stopping na epoca %d", epoch + 1)
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, train_losses


def predict_proba(model: MLP, X: np.ndarray) -> np.ndarray:
    """Gera probabilidades de predicao."""
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        logits = model(torch.FloatTensor(X).to(device)).squeeze()
        probs = torch.sigmoid(logits).cpu().numpy()
    return probs


def train_config_cv(params, run_name, X, y, splits):
    """Trains one MLP config with K-Fold CV, logs to MLflow."""
    fold_scores = {metric: [] for metric in METRICS}

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params({f"mlp_{k}": v for k, v in params.items()})
        mlflow.log_param("model_type", run_name)
        mlflow.log_param("n_folds", N_FOLDS)
        mlflow.log_param("random_seed", RANDOM_SEED)

        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            set_seed(RANDOM_SEED + fold_idx)
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = MLP(X_train.shape[1], params["hidden_layers"], params["dropout"])
            model, train_losses = train_one_fold(model, X_train, y_train, X_test, y_test, params)

            y_prob = predict_proba(model, X_test)
            y_pred = (y_prob >= 0.5).astype(int)
            metrics = compute_metrics(y_test, y_pred, y_prob)

            # Log fold metrics with step parameter
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value, step=fold_idx)

            with mlflow.start_run(run_name=f"{run_name}_fold_{fold_idx}", nested=True):
                mlflow.log_param("fold", fold_idx)
                mlflow.log_metrics(metrics)
                mlflow.log_metric("n_epochs", len(train_losses))

            for metric in METRICS:
                fold_scores[metric].append(metrics[metric])

        for metric in METRICS:
            values = fold_scores[metric]
            mlflow.log_metric(f"mean_{metric}", float(np.mean(values)))
            mlflow.log_metric(f"std_{metric}", float(np.std(values)))

        # Log model artifact (last fold's model)
        mlflow.pytorch.log_model(model, name="model")

    return {
        "run_name": run_name,
        "run_id": run.info.run_id,
        "mean": {m: float(np.mean(fold_scores[m])) for m in METRICS},
        "std": {m: float(np.std(fold_scores[m])) for m in METRICS},
    }


def print_results_table(results):
    table = Table(title="\n[bold]MLP — Grid Search Results[/bold]")
    table.add_column("Config", style="cyan")
    table.add_column(f"Mean {PRIMARY_METRIC}", justify="right")
    table.add_column(f"Std {PRIMARY_METRIC}", justify="right")
    table.add_column("Mean F1", justify="right")

    best_idx = max(range(len(results)), key=lambda i: results[i]["mean"][PRIMARY_METRIC])

    for i, r in enumerate(results):
        style = "bold green" if i == best_idx else ""
        marker = " *" if i == best_idx else ""
        table.add_row(
            r["run_name"] + marker,
            f"{r['mean'][PRIMARY_METRIC]:.4f}",
            f"{r['std'][PRIMARY_METRIC]:.4f}",
            f"{r['mean']['f1']:.4f}",
            style=style,
        )

    console.print(table)
    best = results[best_idx]
    console.print(
        f"\n[bold green]Melhor:[/bold green] {best['run_name']} "
        f"({PRIMARY_METRIC}={best['mean'][PRIMARY_METRIC]:.4f})"
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    console.print("\n[bold]Carregando dataset...[/bold]")
    X, y, _ = load_and_preprocess()
    splits = get_cv_splits(X, y)
    console.print(f"[dim]Dataset: {X.shape[0]} amostras, {X.shape[1]} features, {N_FOLDS}-fold CV[/dim]\n")

    console.rule("[bold cyan]MLP (PyTorch)[/bold cyan]")

    results = []
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(), console=console,
    ) as progress:
        task = progress.add_task("[cyan]MLP Grid Search", total=len(MLP_GRID))
        for i, params in enumerate(MLP_GRID):
            run_name = f"mlp_config_{i}"
            result = train_config_cv(params, run_name, X, y, splits)
            results.append(result)
            progress.update(task, advance=1)

    print_results_table(results)
    console.print("\n[bold green]Treino MLP concluído![/bold green]")
    console.print(f"[dim]Resultados logados no MLflow: {MLFLOW_TRACKING_URI}[/dim]\n")


if __name__ == "__main__":
    main()
