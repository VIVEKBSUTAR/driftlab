"""Command-line transport for the public DriftLab package."""

from pathlib import Path
import json
import typer
from driftlab import __version__
from driftlab.client import DriftLab
from driftlab.datasets.loader import load_dataset
from driftlab.drift.decision import DriftVerdict
from driftlab.reporting import format_drift_table, format_drift_markdown_report

app = typer.Typer(help="DriftLab: risk-aware statistical behavioral drift evaluation.")


@app.command()
def version():
    typer.echo(f"DriftLab v{__version__}")


@app.command()
def run(
    model: str = typer.Option("mock", "--model", "-m"),
    run_type: str = typer.Option("baseline", "--type", "-t"),
    repeats: int = typer.Option(5, "--repeats", "-k", min=1, max=100),
    dataset_path: str | None = typer.Option(None, "--dataset", "-d"),
    output_jsonl: str | None = typer.Option(None, "--output", "-o"),
    db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url"),
    metrics: str = typer.Option("exact_match,sequence_similarity", "--metrics"),
    seed: int = typer.Option(42, min=0),
    temperature: float = typer.Option(0.7, min=0, max=2),
    mock_profile: str = typer.Option("stable", "--mock-profile"),
):
    """Record a benchmark using a JSON/JSONL dataset or the bundled functional suite."""
    lab = DriftLab(db_url=db_url)
    try:
        result = lab.run(
            model=model,
            run_type=run_type,
            repeats=repeats,
            tasks=load_dataset(dataset_path) if dataset_path else None,
            metrics=[m.strip() for m in metrics.split(",") if m.strip()],
            seed=seed,
            generation={"temperature": temperature},
            mock_profile=mock_profile,
            output=output_jsonl,
        )
        typer.echo(
            f"Run completed successfully.\n- Run ID: {result.run_id}\n- Prompts: {result.total_prompts}, Repeats: {result.total_repeats}\n- Observations Logged: {result.observations_count} -> {result.jsonl_path}"
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    finally:
        lab.close()


@app.command()
def compare(
    baseline_run_id: str,
    candidate_run_id: str,
    db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url"),
    output_format: str = typer.Option("table", "--format", "-f"),
    seed: int = typer.Option(42, min=0),
    output: Path | None = typer.Option(None, "--output", "-o"),
):
    """Persist a comparison and export a table, Markdown report, or full JSON evidence."""
    lab = DriftLab(db_url=db_url)
    try:
        if output_format not in ("table", "markdown", "json"):
            raise ValueError("Format must be table, markdown, or json.")
        result = lab.compare(baseline_run_id, candidate_run_id, seed=seed)
        verdicts = [DriftVerdict(**v) for v in result["verdicts"]]
        text = (
            json.dumps(result, indent=2, allow_nan=False)
            if output_format == "json"
            else format_drift_markdown_report(verdicts)
            if output_format == "markdown"
            else format_drift_table(verdicts)
        )
        if output:
            output.write_text(text, encoding="utf-8")
        typer.echo(text)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    finally:
        lab.close()


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Start the API and bundled dashboard at /app/."""
    import uvicorn
    from driftlab.logging_config import configure_logging

    configure_logging()
    from driftlab.config.settings import Settings

    settings = Settings.from_env()
    if host not in ("127.0.0.1", "localhost", "::1") and settings.mode != "server":
        raise typer.BadParameter(
            "Non-loopback binding requires DRIFTLAB_MODE=server and an API key"
        )
    typer.echo(f"DriftLab dashboard: http://{host}:{port}/app/")
    uvicorn.run("driftlab.api.main:app", host=host, port=port, access_log=False)


@app.command()
def backup(destination: Path, workspace: Path = Path(".")):
    """Create a consistent database/artifact backup while inference is idle."""
    from driftlab.maintenance import backup_workspace

    from driftlab.config.settings import Settings

    lab = DriftLab(workspace, policy_file=Settings.from_env().policy_file)
    try:
        typer.echo(str(backup_workspace(lab, destination)))
    except Exception as exc:
        typer.echo(f"Backup failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    finally:
        lab.close()


@app.command()
def restore(archive: Path, destination: Path):
    """Verify a backup and restore it to a NEW directory; never overwrite data."""
    from driftlab.maintenance import restore_workspace

    try:
        typer.echo(str(restore_workspace(archive, destination)))
    except Exception as exc:
        typer.echo(f"Restore failed: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command()
def migrate(workspace: Path = Path(".")):
    """Apply additive schema upgrades, preserving existing evidence."""
    from driftlab.store.schema import SCHEMA_VERSION

    lab = DriftLab(workspace)
    lab.close()
    typer.echo(f"Workspace schema is at version {SCHEMA_VERSION}")


if __name__ == "__main__":
    app()
