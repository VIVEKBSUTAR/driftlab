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
def run(model: str = typer.Option("mock", "--model", "-m"),
        run_type: str = typer.Option("baseline", "--type", "-t"),
        repeats: int = typer.Option(5, "--repeats", "-k", min=1, max=100),
        dataset_path: str | None = typer.Option(None, "--dataset", "-d"),
        output_jsonl: str | None = typer.Option(None, "--output", "-o"),
        db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url"),
        metrics: str = typer.Option("exact_match,sequence_similarity", "--metrics"),
        seed: int = typer.Option(42, min=0),
        temperature: float = typer.Option(0.7, min=0, max=2),
        mock_profile: str = typer.Option("stable", "--mock-profile")):
    """Record a benchmark using a JSON/JSONL dataset or the bundled functional suite."""
    lab = DriftLab(db_url=db_url)
    try:
        result = lab.run(model=model, run_type=run_type, repeats=repeats,
            tasks=load_dataset(dataset_path) if dataset_path else None, metrics=[m.strip() for m in metrics.split(",") if m.strip()],
            seed=seed, generation={"temperature":temperature}, mock_profile=mock_profile, output=output_jsonl)
        typer.echo(f"Run completed successfully.\n- Run ID: {result.run_id}\n- Prompts: {result.total_prompts}, Repeats: {result.total_repeats}\n- Observations Logged: {result.observations_count} -> {result.jsonl_path}")
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    finally:
        lab.close()


@app.command()
def compare(baseline_run_id: str, candidate_run_id: str,
        db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url"),
        output_format: str = typer.Option("table", "--format", "-f"),
        seed: int = typer.Option(42, min=0),
        output: Path | None = typer.Option(None, "--output", "-o")):
    """Persist a comparison and export a table, Markdown report, or full JSON evidence."""
    lab = DriftLab(db_url=db_url)
    try:
        if output_format not in ("table", "markdown", "json"):
            raise ValueError("Format must be table, markdown, or json.")
        result = lab.compare(baseline_run_id, candidate_run_id, seed=seed)
        verdicts = [DriftVerdict(**v) for v in result["verdicts"]]
        text = json.dumps(result, indent=2, allow_nan=False) if output_format == "json" else format_drift_markdown_report(verdicts) if output_format == "markdown" else format_drift_table(verdicts)
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
    typer.echo(f"DriftLab dashboard: http://{host}:{port}/app/")
    uvicorn.run("driftlab.api.main:app", host=host, port=port)


if __name__ == "__main__":
    app()
