"""
FastAPI application for DriftLab.
Defines endpoints as thin wrappers over the runner, store, drift decision, and risk modules.
"""

from typing import Any, Dict, List, Optional
import uuid
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from driftlab.adapters import MockAdapter, OllamaAdapter
from driftlab.drift import compare_runs_for_drift
from driftlab.fingerprint import hash_model
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

app = FastAPI(
    title="DriftLab API",
    description="Statistical framework for behavioral drift detection in local LLMs.",
    version="0.1.0",
)

DEFAULT_DB_URL = "sqlite:///driftlab.db"


class RunRequest(BaseModel):
    model: str = "mock"
    run_type: str = "baseline"
    repeats: int = 3
    metrics: List[str] = ["exact_match"]
    tasks: Optional[List[Dict[str, Any]]] = None
    db_url: str = DEFAULT_DB_URL


class CompareRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    noise_floor: float = 0.01
    seed: int = 42
    db_url: str = DEFAULT_DB_URL


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "driftlab",
        "version": "0.1.0",
    }


@app.get("/runs")
def list_runs(db_url: str = DEFAULT_DB_URL):
    """Lists all stored experiment runs."""
    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    with get_db(session_factory) as session:
        runs = session.query(Run).all()
        return [
            {
                "id": r.id,
                "run_type": r.run_type,
                "status": r.status,
                "model_identifier": r.model_snapshot.identifier if r.model_snapshot else None,
                "jsonl_path": r.jsonl_path,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "observations_count": len(r.observations),
            }
            for r in runs
        ]


@app.get("/runs/{run_id}")
def get_run(run_id: str, db_url: str = DEFAULT_DB_URL):
    """Retrieves full details and observations of a specific run."""
    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    with get_db(session_factory) as session:
        r = session.query(Run).filter_by(id=run_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        return {
            "id": r.id,
            "run_type": r.run_type,
            "status": r.status,
            "jsonl_path": r.jsonl_path,
            "model": {
                "identifier": r.model_snapshot.identifier if r.model_snapshot else None,
                "family": r.model_snapshot.model_family if r.model_snapshot else None,
                "digest": r.model_snapshot.digest if r.model_snapshot else None,
            },
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "observations_count": len(r.observations),
            "aggregates": [
                {
                    "task_id": agg.task_id,
                    "metric_name": agg.metric_name,
                    "mean_value": agg.mean_value,
                    "std_value": agg.std_value,
                    "repeats_count": agg.repeats_count,
                }
                for agg in r.aggregates
            ],
        }


@app.post("/runs")
def trigger_run(payload: RunRequest):
    """Executes a benchmark run against a model adapter and synchronizes to SQLite."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    jsonl_file = f"data/runs/{run_id}.jsonl"

    if payload.model.lower() == "mock":
        adapter = MockAdapter()
    else:
        adapter = OllamaAdapter(model_name=payload.model)

    desc = adapter.describe()
    model_digest = hash_model(desc)

    task_items: List[TaskItem] = []
    if payload.tasks:
        for idx, t in enumerate(payload.tasks, 1):
            task_items.append(
                TaskItem(
                    id=t.get("id", f"t_{idx}"),
                    task_key=t.get("task_key", f"k_{idx}"),
                    category=t.get("category", "general"),
                    risk_level=t.get("risk_level", "medium"),
                    prompt=t.get("prompt", ""),
                    expected_output=t.get("expected_output"),
                    output_spec=t.get("output_spec"),
                )
            )
    else:
        task_items = [
            TaskItem(
                id="task_1",
                task_key="k_1",
                category="general",
                risk_level="medium",
                prompt="What is the speed of light?",
                expected_output="approx 300,000 km/s",
            )
        ]

    engine = get_engine(payload.db_url)
    create_tables(engine)
    session_factory = get_session_factory(engine)

    with get_db(session_factory) as session:
        snapshot = session.query(ModelSnapshot).filter_by(digest=model_digest).first()
        if not snapshot:
            snapshot = ModelSnapshot(
                model_family=desc.get("family", "unknown"),
                identifier=desc.get("identifier", payload.model),
                digest=model_digest,
                quantization=desc.get("quantization"),
                backend_version=desc.get("backend_version"),
            )
            session.add(snapshot)
            session.flush()

        for t in task_items:
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

        run_rec = Run(
            id=run_id,
            model_snapshot_id=snapshot.id,
            run_type=payload.run_type,
            status="running",
            jsonl_path=jsonl_file,
        )
        session.add(run_rec)
        session.flush()

        runner = BenchmarkRunner(
            adapter=adapter,
            repeats=payload.repeats,
            metric_names=payload.metrics,
        )
        res = runner.run(
            tasks=task_items,
            run_id=run_id,
            jsonl_path=jsonl_file,
            db_session=session,
        )

    return {
        "status": "success",
        "run_id": res.run_id,
        "jsonl_path": res.jsonl_path,
        "observations_count": res.observations_count,
        "total_prompts": res.total_prompts,
        "total_repeats": res.total_repeats,
    }


@app.post("/compare")
def compare_runs(payload: CompareRequest):
    """Compares baseline and candidate runs using statistical drift analysis."""
    engine = get_engine(payload.db_url)
    session_factory = get_session_factory(engine)
    rng = np.random.default_rng(payload.seed)

    with get_db(session_factory) as session:
        base_run = session.query(Run).filter_by(id=payload.baseline_run_id).first()
        cand_run = session.query(Run).filter_by(id=payload.candidate_run_id).first()

        if not base_run or not cand_run:
            raise HTTPException(status_code=404, detail="One or both runs were not found.")

        def get_run_scores(run_id: str) -> dict:
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

        base_scores = get_run_scores(payload.baseline_run_id)
        cand_scores = get_run_scores(payload.candidate_run_id)

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
                noise_floor_val=payload.noise_floor,
            )
            verdicts.append({
                "category": verdict.category,
                "metric_id": verdict.metric_id,
                "risk_level": verdict.risk_level,
                "status": verdict.status,
                "estimate": verdict.estimate,
                "ci_low": verdict.ci_low,
                "ci_high": verdict.ci_high,
                "p_value": verdict.p_value,
                "p_adjusted": verdict.p_adjusted,
                "noise_floor": verdict.noise_floor,
                "margin": verdict.margin,
                "explanation": verdict.explanation,
            })

    return {
        "baseline_run_id": payload.baseline_run_id,
        "candidate_run_id": payload.candidate_run_id,
        "verdicts": verdicts,
    }
