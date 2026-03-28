import logging

import numpy as np
import polars as pl
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from src.config import DATA_DIR, DATASET_FILENAME, N_FOLDS, RANDOM_SEED

logger = logging.getLogger(__name__)


def download_dataset() -> pl.DataFrame:
    """Baixa o dataset UCI Default of Credit Card Clients via Kaggle."""
    filepath = DATA_DIR / DATASET_FILENAME

    if filepath.exists():
        logger.info("Dataset já existe em %s", filepath)
        return pl.read_csv(filepath)

    import kagglehub

    logger.info("Baixando dataset do Kaggle...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dataset_path = kagglehub.dataset_download("uciml/default-of-credit-card-clients-dataset")
    df = pl.read_csv(f"{dataset_path}/UCI_Credit_Card.csv")

    # Renomear colunas
    rename_map = {}
    if "default.payment.next.month" in df.columns:
        rename_map["default.payment.next.month"] = "default"
    if "default payment next month" in df.columns:
        rename_map["default payment next month"] = "default"
    if "PAY_0" in df.columns:
        rename_map["PAY_0"] = "PAY_1"
    if rename_map:
        df = df.rename(rename_map)

    # Remover coluna ID
    if "ID" in df.columns:
        df = df.drop("ID")

    df.write_csv(filepath)
    logger.info("Dataset salvo em %s (%d linhas, %d colunas)", filepath, df.height, df.width)

    return df


def load_and_preprocess() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Carrega e preprocessa o dataset. Retorna X (scaled), y, feature_names."""
    df = download_dataset()

    y = df["default"].to_numpy()
    X_df = df.drop("default")
    feature_names = X_df.columns

    scaler = StandardScaler()
    X = scaler.fit_transform(X_df.to_numpy().astype(np.float32))

    logger.info(
        "Dataset preprocessado: X=%s, y=%s, positivos=%.1f%%",
        X.shape,
        y.shape,
        y.mean() * 100,
    )

    return X, y, feature_names


def get_cv_splits(
    X: np.ndarray, y: np.ndarray, n_folds: int = N_FOLDS, seed: int = RANDOM_SEED
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Retorna splits de Stratified K-Fold CV."""
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    return list(skf.split(X, y))


def load_fold_metrics_from_mlflow(run_id: str, metrics: list[str], client) -> dict[str, np.ndarray]:
    """Carrega métricas por fold de um run via MLflow metric history."""
    result = {}
    for metric_name in metrics:
        history = client.get_metric_history(run_id, metric_name)
        values = sorted(history, key=lambda m: m.step)
        result[metric_name] = np.array([m.value for m in values])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
    X, y, features = load_and_preprocess()
    print(f"Dataset pronto: {X.shape[0]} amostras, {X.shape[1]} features")
    print(f"Distribuição target: {np.bincount(y)} (negativos, positivos)")
    print(f"Taxa de default: {y.mean():.1%}")
