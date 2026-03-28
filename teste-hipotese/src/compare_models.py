"""Comparação estatística entre modelos usando testes de hipótese."""

import argparse
import logging

import mlflow
import numpy as np
import scikit_posthocs as sp
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from scipy import stats

from src.config import EXPERIMENT_NAME, METRICS, MLFLOW_TRACKING_URI, N_FOLDS, PRIMARY_METRIC

logger = logging.getLogger(__name__)
console = Console()

ALPHA = 0.05


def get_parent_runs(client):
    """Busca parent runs do experimento."""
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        console.print("[red]Experimento não encontrado no MLflow[/red]")
        return []

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=f"params.n_folds = '{N_FOLDS}'",
    )
    return [r for r in runs if r.data.params.get("model_type")]


def load_scores(run, metric, client):
    """Carrega fold scores de um run via metric history."""
    history = client.get_metric_history(run.info.run_id, metric)
    values = sorted(history, key=lambda m: m.step)
    return np.array([m.value for m in values if m.step < N_FOLDS])


def compare_two(name_a, scores_a, name_b, scores_b, metric):
    """Compara dois modelos. Retorna dict com resultados."""
    diff = scores_a - scores_b

    _, p_sw = stats.shapiro(diff)
    is_normal = p_sw >= ALPHA

    if is_normal:
        stat, p_val = stats.ttest_rel(scores_a, scores_b)
        test_name = "Paired t-test"
    else:
        stat, p_val = stats.wilcoxon(scores_a, scores_b)
        test_name = "Wilcoxon"

    std_diff = np.std(diff, ddof=1)
    d = np.mean(diff) / std_diff if std_diff > 0 else 0.0

    se = stats.sem(diff)
    ci = stats.t.interval(0.95, df=len(diff) - 1, loc=np.mean(diff), scale=se)

    return {
        "name_a": name_a, "name_b": name_b, "metric": metric,
        "mean_a": float(np.mean(scores_a)), "mean_b": float(np.mean(scores_b)),
        "mean_diff": float(np.mean(diff)), "test": test_name,
        "statistic": float(stat), "p_value": float(p_val),
        "cohens_d": float(d), "ci": (float(ci[0]), float(ci[1])),
        "significant": p_val < ALPHA, "shapiro_p": float(p_sw),
    }


def print_pairwise_result(result):
    """Imprime resultado de comparação pairwise com Rich."""
    sig_style = "bold green" if result["significant"] else "dim"
    sig_mark = "✓ Sig." if result["significant"] else "✗ N.S."

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Comparação", f"{result['name_a']} vs {result['name_b']}")
    table.add_row("Médias", f"{result['mean_a']:.4f} vs {result['mean_b']:.4f} (Δ={result['mean_diff']:+.4f})")
    table.add_row("Normalidade", f"Shapiro p={result['shapiro_p']:.4f}")
    table.add_row("Teste", f"{result['test']}: stat={result['statistic']:.4f}, p={result['p_value']:.4f}")
    table.add_row("Cohen's d", f"{result['cohens_d']:.4f}")
    table.add_row("IC 95%", f"[{result['ci'][0]:.4f}, {result['ci'][1]:.4f}]")
    table.add_row("Resultado", f"[{sig_style}]{sig_mark}[/{sig_style}]")

    console.print(Panel(table, title=f"[bold]{result['name_a']} vs {result['name_b']}[/bold]"))


def run_friedman_with_posthoc(all_scores, model_names, metric):
    """Friedman test + Nemenyi post-hoc."""
    arrays = [all_scores[name] for name in model_names]
    stat_f, p_f = stats.friedmanchisquare(*arrays)

    console.print(f"\n[bold]Friedman Test ({metric})[/bold]")
    console.print(f"  chi² = {stat_f:.4f}, p = {p_f:.6f}")

    if p_f < ALPHA:
        console.print(f"  [green]✓ Significativo — pelo menos um par difere[/green]\n")

        data_matrix = np.column_stack(arrays)
        nemenyi = sp.posthoc_nemenyi_friedman(data_matrix)
        nemenyi.index = model_names
        nemenyi.columns = model_names

        console.print("[bold]Post-hoc Nemenyi (p-valores):[/bold]")
        table = Table()
        table.add_column("", style="bold")
        for name in model_names:
            short = name.replace("_config_", " c")
            table.add_column(short, justify="right")

        for i, row_name in enumerate(model_names):
            row = [row_name.replace("_config_", " c")]
            for j in range(len(model_names)):
                p = nemenyi.iloc[i, j]
                if i == j:
                    row.append("[dim]—[/dim]")
                elif p < ALPHA:
                    row.append(f"[green]{p:.4f}[/green]")
                else:
                    row.append(f"{p:.4f}")
            table.add_row(*row)

        console.print(table)
    else:
        console.print(f"  [dim]✗ Não significativo — sem diferença global[/dim]")

    return {"statistic": stat_f, "p_value": p_f, "significant": p_f < ALPHA}


def register_winner(client, run, model_name, registry_name, alias, tags):
    """Registra modelo no MLflow Model Registry com alias e tags."""
    model_uri = f"runs:/{run.info.run_id}/model"
    mv = mlflow.register_model(model_uri, registry_name)

    client.set_registered_model_alias(registry_name, alias, mv.version)
    for key, value in tags.items():
        client.set_model_version_tag(registry_name, mv.version, key, str(value))

    console.print(f"  [green]✓[/green] {model_name} → {registry_name} v{mv.version} (alias: {alias})")
    return mv


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

    parser = argparse.ArgumentParser(description="Comparação estatística de modelos")
    parser.add_argument("--register", action="store_true", help="Registrar modelos no MLflow Registry")
    parser.add_argument("--metric", default=PRIMARY_METRIC, help="Métrica para comparação")
    args = parser.parse_args()

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()

    # 1. Carregar todos os scores
    parent_runs = get_parent_runs(client)
    if len(parent_runs) < 2:
        console.print("[red]Menos de 2 runs encontradas. Execute make train-all primeiro.[/red]")
        return

    metric = args.metric
    all_scores = {}
    run_map = {}
    for run in parent_runs:
        name = run.data.tags.get("mlflow.runName", run.info.run_id)
        scores = load_scores(run, metric, client)
        if len(scores) == N_FOLDS:
            all_scores[name] = scores
            run_map[name] = run

    model_names = sorted(all_scores.keys())
    console.rule(f"[bold]Comparação Estatística — {metric}[/bold]")
    console.print(f"Modelos: {len(model_names)} | Folds: {N_FOLDS} | α = {ALPHA}\n")

    # Resumo
    table = Table(title="Resumo")
    table.add_column("Modelo", style="cyan")
    table.add_column(f"Mean {metric}", justify="right")
    table.add_column(f"Std {metric}", justify="right")
    for name in model_names:
        s = all_scores[name]
        table.add_row(name, f"{np.mean(s):.4f}", f"{np.std(s):.4f}")
    console.print(table)

    # 2. Friedman + Nemenyi (visão global)
    if len(model_names) >= 3:
        run_friedman_with_posthoc(all_scores, model_names, metric)

    # 3. Selecionar representantes por parcimônia (config_0 = mais simples)
    # Nemenyi mostra que configs dentro de cada família são equivalentes
    rf_names = sorted([n for n in model_names if n.startswith("random_forest")])
    mlp_names = sorted([n for n in model_names if n.startswith("mlp")])

    rf_representative = rf_names[0] if rf_names else None  # config_0
    mlp_representative = mlp_names[0] if mlp_names else None  # config_0

    if rf_representative and mlp_representative:
        console.rule("[bold]Comparação Focada (parcimônia → config_0)[/bold]")
        console.print(
            f"  RF:  {rf_representative} ({metric}={np.mean(all_scores[rf_representative]):.4f})\n"
            f"  MLP: {mlp_representative} ({metric}={np.mean(all_scores[mlp_representative]):.4f})\n"
        )

        # 4. Teste pareado único (comparação pré-planejada)
        result = compare_two(
            rf_representative, all_scores[rf_representative],
            mlp_representative, all_scores[mlp_representative], metric,
        )
        print_pairwise_result(result)

        # 5. Decisão
        console.rule("[bold]Decisão[/bold]")
        if result["significant"]:
            champion = rf_representative if result["mean_diff"] > 0 else mlp_representative
            reason = "estatisticamente superior"
        else:
            champion = rf_representative
            reason = "parcimônia — sem diferença significativa, preferir modelo mais simples"

        console.print(f"  Champion: [bold green]{champion}[/bold green]")
        console.print(f"  Razão: {reason}\n")

        # 6. Registro no MLflow
        if args.register:
            console.rule("[bold]Registrando Modelos[/bold]")

            # RF candidate
            rf_tags = {
                f"mean_{metric}": f"{np.mean(all_scores[rf_representative]):.4f}",
                "test_used": result["test"],
                "p_value": f"{result['p_value']:.4f}",
                "cohens_d": f"{result['cohens_d']:.4f}",
            }
            rf_mv = register_winner(
                client, run_map[rf_representative], rf_representative,
                "credit-default-rf", "candidate", rf_tags,
            )

            # MLP candidate
            mlp_tags = {
                f"mean_{metric}": f"{np.mean(all_scores[mlp_representative]):.4f}",
                "test_used": result["test"],
                "p_value": f"{result['p_value']:.4f}",
                "cohens_d": f"{result['cohens_d']:.4f}",
            }
            mlp_mv = register_winner(
                client, run_map[mlp_representative], mlp_representative,
                "credit-default-mlp", "candidate", mlp_tags,
            )

            # Champion alias
            if champion == rf_representative:
                champ_registry, champ_version = "credit-default-rf", rf_mv.version
            else:
                champ_registry, champ_version = "credit-default-mlp", mlp_mv.version

            client.set_registered_model_alias(champ_registry, "champion", champ_version)
            client.set_model_version_tag(champ_registry, champ_version, "decision", reason)
            console.print(f"\n  🏆 Champion: {champion} → {champ_registry} v{champ_version}")


if __name__ == "__main__":
    main()
