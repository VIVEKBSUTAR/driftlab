"""REST transport for the public DriftLab service; serves the built dashboard."""
from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
import requests
from driftlab import __version__
from driftlab.client import DriftLab
from driftlab.config.schemas import GenerationConfig
from driftlab.datasets.loader import TaskSpec, builtin_tasks
from driftlab.metrics.functions import METRIC_REGISTRY
from driftlab.risk.policy import DEFAULT_POLICIES
from driftlab.reporting import format_drift_markdown_report
from driftlab.drift.decision import DriftVerdict

WORKSPACE = Path(os.getenv("DRIFTLAB_WORKSPACE", ".")).resolve()
DEFAULT_DB_URL = os.getenv("DRIFTLAB_DB_URL", f"sqlite:///{WORKSPACE / 'driftlab.db'}")


@lru_cache(maxsize=8)
def service(db_url=DEFAULT_DB_URL):
    return DriftLab(WORKSPACE, db_url)


@asynccontextmanager
async def lifespan(app):
    lab = service()
    # A local worker cannot survive a process restart. Never leave stale jobs running.
    from driftlab.store import get_db, Run
    with get_db(lab.sessions) as session:
        for run in session.query(Run).filter(Run.status.in_(["running", "pending"])):
            run.status = "failed"
            Path(run.jsonl_path).with_suffix(".error.txt").write_text("Server stopped before this run completed. Start a new run.")
    yield


app = FastAPI(title="DriftLab API", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(default="mock", min_length=1)
    run_type: Literal["baseline", "candidate"] = "baseline"
    repeats: int = Field(default=5, ge=1, le=100)
    metrics: list[str] = Field(default_factory=lambda:["exact_match", "sequence_similarity"], min_length=1)
    tasks: list[TaskSpec] | None = None
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    seed: int = Field(default=42, ge=0)
    mock_profile: Literal["stable", "regression"] = "stable"
    background: bool = False
    db_url: str = DEFAULT_DB_URL


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_run_id: str
    candidate_run_id: str
    noise_floor: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    seed: int = Field(default=42, ge=0)
    n_resamples: int = Field(default=2000, ge=100, le=50000)
    n_permutations: int = Field(default=2000, ge=100, le=50000)
    db_url: str = DEFAULT_DB_URL


def translate_error(exc):
    if isinstance(exc, LookupError):
        return HTTPException(404, str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(422, str(exc))
    if isinstance(exc, (requests.RequestException, RuntimeError, ImportError, OSError)):
        return HTTPException(503, f"Evaluation unavailable: {exc}")
    return HTTPException(500, "Evaluation failed; inspect the saved run error.")


@app.get("/")
def read_root():
    return {"status":"healthy", "service":"driftlab", "version":__version__}


@app.get("/catalog")
def catalog():
    return {"tasks":[t.model_dump() for t in builtin_tasks()], "policies":[asdict(p) for p in DEFAULT_POLICIES.values()],
        "metrics":list(METRIC_REGISTRY), "dataset_name":"DriftLab functional suite", "dataset_description":"32 original smoke-test prompts. Synthetic runs validate the pipeline; they are not model-quality research evidence."}


@app.get("/models")
def models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        response.raise_for_status()
        return {"available":True, "models":response.json().get("models",[])}
    except requests.RequestException:
        return {"available":False, "models":[], "message":"Ollama is unavailable. Start Ollama to use local models."}


@app.get("/runs")
def list_runs(db_url: str = DEFAULT_DB_URL):
    return service(db_url).list_runs()


@app.get("/runs/{run_id}")
def get_run(run_id: str, db_url: str = DEFAULT_DB_URL):
    try:
        return service(db_url).get_run(run_id)
    except Exception as exc:
        raise translate_error(exc) from exc


def execute_background(lab, prepared):
    try:
        lab.execute_run(prepared)
    except Exception:
        # The service persists failure details. The polling client reads them from /runs/{id}.
        import logging
        logging.getLogger(__name__).exception("Benchmark %s failed", prepared[0])


@app.post("/runs")
def trigger_run(payload: RunRequest, background_tasks: BackgroundTasks):
    try:
        lab = service(payload.db_url)
        options = payload.model_dump(exclude={"db_url", "background"})
        prepared = lab.prepare_run(**options)
        if payload.background:
            background_tasks.add_task(execute_background, lab, prepared)
            return {"status":"pending", "run_id":prepared[0]}
        result = lab.execute_run(prepared)
        return {"status":"success", "run_id":result.run_id, "jsonl_path":result.jsonl_path,
            "observations_count":result.observations_count,"total_prompts":result.total_prompts,"total_repeats":result.total_repeats}
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post("/compare")
def compare_runs(payload: CompareRequest):
    try:
        return service(payload.db_url).compare(**payload.model_dump(exclude={"db_url"}))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.get("/comparisons")
def list_comparisons(db_url: str = DEFAULT_DB_URL):
    return service(db_url).list_comparisons()


@app.get("/comparisons/{comparison_id}")
def get_comparison(comparison_id: str, db_url: str = DEFAULT_DB_URL):
    try:
        return service(db_url).get_comparison(comparison_id)
    except Exception as exc:
        raise translate_error(exc) from exc


@app.get("/comparisons/{comparison_id}/report", response_class=PlainTextResponse)
def report(comparison_id: str, db_url: str = DEFAULT_DB_URL):
    result = get_comparison(comparison_id, db_url)
    text = format_drift_markdown_report([DriftVerdict(**v) for v in result["verdicts"]],
        baseline_info={"identifier":result["baseline"]["model_identifier"],"digest":result["baseline"].get("dataset_digest")},
        candidate_info={"identifier":result["candidate"]["model_identifier"],"digest":result["candidate"].get("dataset_digest")})
    text += f"\n## Reproducibility\n\nComparison: `{result['id']}`\n\nConfiguration: `{result['config']}`\n\nSynthetic: {result['baseline']['synthetic'] or result['candidate']['synthetic']}\n"
    return PlainTextResponse(text, headers={"Content-Disposition":f'attachment; filename="{comparison_id}.md"'})


# The same API is reachable under /api in the installed, single-origin application.
api_routes = list(app.router.routes)
for route in api_routes:
    if getattr(route, "path", "") not in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
        app.add_api_route("/api"+route.path, route.endpoint, methods=list(route.methods), include_in_schema=False)

frontend = Path(os.getenv("DRIFTLAB_FRONTEND", str(Path(__file__).parents[3] / "frontend" / "dist")))
if not frontend.exists():
    frontend = Path(__file__).parent / "static"
if frontend.exists():
    app.mount("/app", StaticFiles(directory=frontend, html=True), name="dashboard")
