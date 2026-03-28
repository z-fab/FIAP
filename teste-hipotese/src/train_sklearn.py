"""Grid search de modelos sklearn (RF + LogReg) com K-Fold CV e MLflow."""

import logging

import mlflow
import mlflow.sklearn
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.config import (
    EXPERIMENT_NAME, LR_GRID, METRICS, MLFLOW_TRACKING_URI,
    N_FOLDS, PRIMARY_METRIC, RANDOM_SEED, RF_GRID,
)
from src.data import get_cv_splits, load_and_preprocess
from src.utils import compute_metrics

logger = logging.getLogger(__name__)
console = Console()


def train_config_cv(model_class, params, run_name, X, y, splits):
    """Trains one sklearn config with K-Fold CV, logs to MLflow."""
    fold_scores = {metric: [] for metric in METRICS}
    last_model = None

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        mlflow.log_param("model_type", run_name)
        mlflow.log_param("n_folds", N_FOLDS)
        mlflow.log_param("random_seed", RANDOM_SEED)

        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = model_class(**params)
            model.fit(X_train, y_train)
            last_model = model

            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            metrics = compute_metrics(y_test, y_pred, y_prob)

            # Log fold metrics with step parameter
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value, step=fold_idx)

            with mlflow.start_run(run_name=f"{run_name}_fold_{fold_idx}", nested=True):
                mlflow.log_param("fold", fold_idx)
                mlflow.log_metrics(metrics)

            for metric in METRICS:
                fold_scores[metric].append(metrics[metric])

        # Log aggregated metrics
        for metric in METRICS:
            values = fold_scores[metric]
            mlflow.log_metric(f"mean_{metric}", float(np.mean(values)))
            mlflow.log_metric(f"std_{metric}", float(np.std(values)))

        # Log model artifact
        mlflow.sklearn.log_model(last_model, name="model")

    return {
        "run_name": run_name,
        "run_id": run.info.run_id,
        "mean": {m: float(np.mean(fold_scores[m])) for m in METRICS},
        "std": {m: float(np.std(fold_scores[m])) for m in METRICS},
    }


def run_grid_search(model_class, grid, model_type, X, y, splits):
    """Runs grid search with Rich progress bar."""
    results = []
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(), console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]{model_type}", total=len(grid))
        for i, params in enumerate(grid):
            run_name = f"{model_type}_config_{i}"
            result = train_config_cv(model_class, params, run_name, X, y, splits)
            results.append(result)
            progress.update(task, advance=1)
    return results


def print_results_table(model_type, results):
    """Rich table with best config highlighted in green."""
    table = Table(title=f"\n[bold]{model_type} — Grid Search Results[/bold]")
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

    # Random Forest grid search
    console.rule("[bold cyan]Random Forest[/bold cyan]")
    rf_results = run_grid_search(RandomForestClassifier, RF_GRID, "random_forest", X, y, splits)
    print_results_table("Random Forest", rf_results)

    # Logistic Regression grid search
    console.rule("[bold cyan]Logistic Regression[/bold cyan]")
    lr_results = run_grid_search(LogisticRegression, LR_GRID, "logistic_regression", X, y, splits)
    print_results_table("Logistic Regression", lr_results)

    console.print("\n[bold green]Treino sklearn concluído![/bold green]")
    console.print(f"[dim]Resultados logados no MLflow: {MLFLOW_TRACKING_URI}[/dim]\n")


if __name__ == "__main__":
    main()
