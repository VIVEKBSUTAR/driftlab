"""
Command-line interface for DriftLab using Typer.
Thin wrappers over core runner, stats, and reporting modules.
"""

from pathlib import Path
from typing import List, Optional
import json
import uuid
import numpy as np
import typer

from driftlab.adapters import MockAdapter, OllamaAdapter
from driftlab.drift import compare_runs_for_drift
from driftlab.fingerprint import hash_dataset, hash_model
from driftlab.reporting import (
    format_drift_table,
    format_drift_markdown_report,
    format_drift_json,
)
from driftlab.risk import get_risk_policy
from driftlab.runner import BenchmarkRunner, TaskItem
from driftlab.store import (
    get_engine,
    create_tables,
    get_session_factory,
    get_db,
    Run,
    ModelSnapshot,
    Task,
    Observation,
    MetricResult,
    PromptAggregate,
)

app = typer.Typer(help="DriftLab: Statistical behavioral drift detection for local LLMs.")


@app.command()
def version():
    """Prints the current DriftLab version."""
    typer.echo("DriftLab v0.1.0")


@app.command()
def run(
    model: str = typer.Option("mock", "--model", "-m", help="Model identifier (e.g. 'llama3:8b' or 'mock')"),
    run_type: str = typer.Option("baseline", "--type", "-t", help="Run type: 'baseline' or 'candidate'"),
    repeats: int = typer.Option(3, "--repeats", "-k", help="Number of repetitions per prompt"),
    dataset_path: Optional[str] = typer.Option(None, "--dataset", "-d", help="Path to JSON/JSONL dataset file"),
    output_jsonl: Optional[str] = typer.Option(None, "--output", "-o", help="Path to write append-only JSONL output"),
    db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url", help="Database connection URL"),
    metrics: str = typer.Option("exact_match", "--metrics", help="Comma-separated metric names"),
):
    """Executes a benchmark run against a model adapter and records observations."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    jsonl_file = output_jsonl or f"data/runs/{run_id}.jsonl"

    typer.echo(f"Starting {run_type} run: {run_id} using model '{model}' with {repeats} repeats")

    # 1. Instantiate adapter
    if model.lower() == "mock":
        adapter = MockAdapter()
    else:
        adapter = OllamaAdapter(model_name=model)

    desc = adapter.describe()
    model_digest = hash_model(desc)

    # 2. Load or generate default tasks
    tasks: List[TaskItem] = []
    if dataset_path and Path(dataset_path).exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                tasks.append(
                    TaskItem(
                        id=data.get("id", f"t_{line_no}"),
                        task_key=data.get("task_key", f"key_{line_no}"),
                        category=data.get("category", "general"),
                        risk_level=data.get("risk_level", "medium"),
                        prompt=data.get("prompt", ""),
                        expected_output=data.get("expected_output"),
                        output_spec=data.get("output_spec"),
                    )
                )
    else:
        # Default sanity tasks
        tasks = [
            TaskItem(
                id="task_demo_1",
                task_key="math_basic",
                category="reasoning",
                risk_level="medium",
                prompt="What is 15 + 27?",
                expected_output="42",
            ),
            TaskItem(
                id="task_demo_2",
                task_key="geo_france",
                category="knowledge",
                risk_level="low",
                prompt="What is the capital of France?",
                expected_output="Paris",
            ),
        ]

    # 3. Setup DB & Register Run
    engine = get_engine(db_url)
    create_tables(engine)
    session_factory = get_session_factory(engine)

    with get_db(session_factory) as session:
        # Register or fetch ModelSnapshot
        snapshot = session.query(ModelSnapshot).filter_by(digest=model_digest).first()
        if not snapshot:
            snapshot = ModelSnapshot(
                model_family=desc.get("family", "unknown"),
                identifier=desc.get("identifier", model),
                digest=model_digest,
                quantization=desc.get("quantization"),
                backend_version=desc.get("backend_version"),
            )
            session.add(snapshot)
            session.flush()

        # Register tasks if not present
        for t in tasks:
            if not session.query(Task).filter_by(id=t.id).first():
                session.add(
                    Task(
                        id=t.id,
                        task_key=t.task_key,
                        category=t.category,
                        risk_level=t.risk_level,
                        prompt=t.prompt,
                        expected_output=t.expected_output,
                        output_spec=t.output_spec,
                    )
                )
        session.flush()

        # Create Run record
        run_record = Run(
            id=run_id,
            model_snapshot_id=snapshot.id,
            run_type=run_type,
            status="running",
            jsonl_path=jsonl_file,
        )
        session.add(run_record)
        session.flush()

        # 4. Execute runner
        runner = BenchmarkRunner(
            adapter=adapter,
            repeats=repeats,
            metric_names=metric_list,
        )
        result = runner.run(
            tasks=tasks,
            run_id=run_id,
            jsonl_path=jsonl_file,
            db_session=session,
        )

    typer.echo(f"Run completed successfully.")
    typer.echo(f"- Run ID: {result.run_id}")
    typer.echo(f"- Prompts: {result.total_prompts}, Repeats: {result.total_repeats}")
    typer.echo(f"- Observations Logged: {result.observations_count} -> {result.jsonl_path}")


@app.command()
def compare(
    baseline_run_id: str = typer.Argument(..., help="Run ID of the baseline model run"),
    candidate_run_id: str = typer.Argument(..., help="Run ID of the candidate model run"),
    db_url: str = typer.Option("sqlite:///driftlab.db", "--db-url", help="Database connection URL"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: 'table', 'markdown', 'json'"),
    seed: int = typer.Option(42, "--seed", help="Random seed for statistical bootstrap & permutation"),
):
    """Compares a candidate run against a baseline run using the statistical drift decision engine."""
    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    rng = np.random.default_rng(seed)

    with get_db(session_factory) as session:
        base_run = session.query(Run).filter_by(id=baseline_run_id).first()
        cand_run = session.query(Run).filter_by(id=candidate_run_id).first()

        if not base_run or not cand_run:
            typer.echo(f"Error: Run not found (baseline: {bool(base_run)}, candidate: {bool(cand_run)})", err=True)
            raise typer.Exit(code=1)

        # Collect observations grouped by task and metric
        def get_run_scores(run_id: str) -> dict:
            # task_id -> list of float scores across repeats
            results: dict = {}
            for obs in session.query(Observation).filter_by(run_id=run_id).all():
                for m in obs.metric_results:
                    key = (obs.task.category, m.metric_name, obs.task.risk_level)
                    if key not in results:
                        results[key] = {}
                    if obs.task_id not in results[key]:
                        results[key][obs.task_id] = []
                    results[key][obs.task_id].append(m.value)
            return results

        base_scores = get_run_scores(baseline_run_id)
        cand_scores = get_run_scores(candidate_run_id)

        all_keys = set(base_scores.keys()).union(cand_scores.keys())
        verdicts = []

        for (category, metric_name, risk_level) in all_keys:
            b_map = {p: np.array(v) for p, v in base_scores.get((category, metric_name, risk_level), {}).items()}
            c_map = {p: np.array(v) for p, v in cand_scores.get((category, metric_name, risk_level), {}).items()}
            policy = get_risk_policy(risk_level)

            verdict = compare_runs_for_drift(
                baseline_scores=b_map,
                candidate_scores=c_map,
                category=category,
                metric_id=metric_name,
                risk_policy=policy,
                rng=rng,
                noise_floor_val=0.01,
            )
            verdicts.append(verdict)

    if output_format == "json":
        typer.echo(format_drift_json(verdicts))
    elif output_format == "markdown":
        typer.echo(format_drift_markdown_report(verdicts))
    else:
        typer.echo(format_drift_table(verdicts))


if __name__ == "__main__":
    app()
