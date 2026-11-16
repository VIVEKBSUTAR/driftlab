"""Authenticated, single-workspace HTTP transport over the public Python service."""

from contextlib import asynccontextmanager
from dataclasses import asdict
import hmac
import json
import logging
from pathlib import Path
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
import requests
from sqlalchemy import text
from driftlab.store import get_db, Run
from filelock import Timeout

from driftlab import __version__
from driftlab.api.responses import RunSummary, RunDetailResponse, ComparisonResponse
from driftlab.api.security import COOKIE, SecurityMiddleware, authenticated, issue_session
from driftlab.client import DriftLab
from driftlab.config.schemas import GenerationConfig
from driftlab.config.settings import Settings
from driftlab.datasets.loader import TaskSpec, builtin_tasks, load_dataset, validate_tasks
from driftlab.drift.decision import DriftVerdict
from driftlab.jobs import JobQueue, QueueFull
from driftlab.metrics.functions import METRIC_REGISTRY
from driftlab.reporting import format_drift_markdown_report

logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(
        default="mock", min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9_./:@-]+$"
    )
    run_type: Literal["baseline", "candidate"] = "baseline"
    repeats: int = Field(default=5, ge=1, le=100)
    metrics: list[str] = Field(
        default_factory=lambda: ["exact_match", "sequence_similarity"], min_length=1, max_length=10
    )
    tasks: list[TaskSpec] | None = None
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    seed: int = Field(default=42, ge=0, le=2**63 - 1)
    mock_profile: Literal["stable", "regression"] = "stable"
    background: Literal[True] = True

    @field_validator("tasks", mode="before")
    @classmethod
    def task_defaults(cls, value):
        return None if value is None else validate_tasks(value)


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_run_id: str = Field(min_length=1, max_length=100)
    candidate_run_id: str = Field(min_length=1, max_length=100)
    noise_floor: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    seed: int = Field(default=42, ge=0, le=2**63 - 1)
    n_resamples: int = Field(default=2000, ge=100, le=10000)
    n_permutations: int = Field(default=2000, ge=100, le=10000)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=256)


def public_record(record):
    return {k: v for k, v in record.items() if k != "jsonl_path"}


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    comparison_lock = threading.Semaphore(1)

    @asynccontextmanager
    async def lifespan(app):
        lab = DriftLab(
            settings.workspace, ollama_url=settings.ollama_url, policy_file=settings.policy_file
        )
        queue = JobQueue(lab, settings.max_pending_jobs)
        app.state.lab, app.state.queue = lab, queue
        try:
            if settings.worker_enabled:
                queue.start()
            yield
        finally:
            queue.stop()
            if not queue.healthy:
                lab.close()

    app = FastAPI(
        title="DriftLab API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        description="Single-workspace behavioral drift evaluation. Server deployments require Bearer authentication or a workspace session.",
    )
    app.state.settings = settings
    app.add_middleware(SecurityMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request, exc):
        logger.exception("Unhandled API error", extra={"request_id": request.state.request_id})
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal error; refer to the request ID in server logs",
                "request_id": request.state.request_id,
            },
            headers={
                "X-Request-ID": request.state.request_id,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def lab():
        if not hasattr(app.state, "lab"):
            raise HTTPException(503, "Application startup is incomplete")
        return app.state.lab

    def translate(exc):
        if isinstance(exc, LookupError):
            return HTTPException(404, str(exc))
        if isinstance(exc, QueueFull):
            return HTTPException(429, str(exc), headers={"Retry-After": "30"})
        if isinstance(exc, ValueError):
            return HTTPException(422, str(exc))
        if isinstance(exc, Timeout):
            return HTTPException(409, "The workspace is busy; try again")
        logger.exception("Evaluation operation failed")
        return HTTPException(
            503, "Evaluation unavailable; check the inference service and server logs"
        )

    @app.get("/")
    @app.get("/livez")
    def health():
        return {"status": "healthy", "service": "driftlab", "version": __version__}

    @app.get("/readyz")
    def ready():
        with lab().engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        if settings.worker_enabled and not app.state.queue.healthy:
            raise HTTPException(503, "Evaluation worker is not running")
        return {"status": "ready", "worker": "running" if settings.worker_enabled else "disabled"}

    @app.get("/auth/session")
    def session(request: Request):
        return {
            "authenticated": authenticated(request, settings),
            "required": bool(settings.api_key),
            "mode": settings.mode,
        }

    @app.post("/auth/login")
    def login(payload: LoginRequest, response: Response):
        if not settings.api_key or not hmac.compare_digest(
            payload.token.encode(), settings.api_key.get_secret_value().encode()
        ):
            raise HTTPException(401, "Invalid workspace access key")
        response.set_cookie(
            COOKIE,
            issue_session(settings),
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.session_seconds,
            path="/",
        )
        return {"authenticated": True}

    @app.post("/auth/logout")
    def logout(response: Response):
        response.delete_cookie(
            COOKIE, path="/", secure=settings.cookie_secure, httponly=True, samesite="strict"
        )
        return {"authenticated": False}

    @app.get("/catalog")
    def catalog():
        tasks = [t.model_dump() for t in builtin_tasks()]
        description = "Original functional prompts for software validation; synthetic runs are not model-quality evidence."
        datasets = [
            {
                "id": "functional",
                "name": "DriftLab functional suite",
                "tasks": tasks,
                "description": description,
            }
        ]
        warnings = []
        for path in sorted((settings.workspace / "data" / "benchmarks").glob("*.jsonl")):
            try:
                if path.stat().st_size > settings.max_body_bytes:
                    raise ValueError("Dataset exceeds the configured size limit")
                source_path = path.with_suffix(".source.json")
                source = json.loads(source_path.read_text()) if source_path.exists() else {}
                records = [t.model_dump() for t in load_dataset(path)]
                datasets.append(
                    {
                        "id": path.stem,
                        "name": source.get("name", path.stem.upper()),
                        "tasks": records,
                        "source": source,
                        "description": f"{len(records)} prompts. Source license: {source.get('license', 'see dataset source')}.",
                    }
                )
            except (ValueError, OSError):
                logger.warning("Dataset not loaded: %s", path.name)
                warnings.append(
                    {
                        "dataset": path.stem,
                        "message": "Dataset could not be loaded; validate its format and configured size limit",
                    }
                )
        return {
            "tasks": tasks,
            "datasets": datasets,
            "warnings": warnings,
            "policies": [asdict(p) for p in lab().policies.values()],
            "version": __version__,
            "metrics": list(METRIC_REGISTRY),
            "dataset_name": "DriftLab functional suite",
            "dataset_description": description,
            "limits": {
                "max_tasks": settings.max_tasks,
                "max_observations": settings.max_observations,
                "max_body_bytes": settings.max_body_bytes,
            },
        }

    @app.get("/models")
    def models():
        try:
            response = requests.get(settings.ollama_url + "/api/tags", timeout=3)
            response.raise_for_status()
            allowed = (
                "family",
                "families",
                "parameter_size",
                "quantization_level",
                "context_length",
            )
            return {
                "available": True,
                "models": [
                    {k: m.get(k) for k in ("name", "size", "digest")}
                    | {"details": {k: m.get("details", {}).get(k) for k in allowed}}
                    for m in response.json().get("models", [])
                ],
            }
        except (requests.RequestException, ValueError):
            return {
                "available": False,
                "models": [],
                "message": "The configured Ollama service is unavailable",
            }

    @app.get("/workspace")
    def workspace():
        return {
            **lab().summary(),
            "worker_running": app.state.queue.healthy,
            "version": __version__,
        }

    @app.get("/runs", response_model=list[RunSummary])
    def runs(limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
        return [public_record(r) for r in lab().list_runs(limit, offset)]

    @app.get("/runs/{run_id}", response_model=RunDetailResponse)
    def run_detail(
        run_id: str,
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            return public_record(
                lab().get_run(run_id, observation_limit=limit, observation_offset=offset)
            )
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/runs", status_code=202)
    def trigger(payload: RunRequest):
        options = payload.model_dump(exclude={"background"})
        tasks = payload.tasks or builtin_tasks()
        if (
            len(tasks) > settings.max_tasks
            or len(tasks) * payload.repeats > settings.max_observations
        ):
            raise HTTPException(422, "Evaluation exceeds the configured task or observation budget")
        if (
            payload.generation.timeout_seconds > 120
            or payload.generation.max_tokens > 4096
            or len(tasks) * payload.repeats * payload.generation.max_tokens > 2_000_000
        ):
            raise HTTPException(422, "Evaluation exceeds the token or inference-time budget")
        try:
            run_id = app.state.queue.enqueue(**options)
            return {"status": "pending", "run_id": run_id}
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/runs/{run_id}/artifacts/{kind}")
    def artifact(run_id: str, kind: Literal["raw", "scores", "manifest"]):
        with get_db(lab().sessions) as session:
            record = session.get(Run, run_id)
            if record is None:
                raise HTTPException(404, "Run not found")
            path = lab().artifact_path(record.jsonl_path)
        path = (
            path
            if kind == "raw"
            else Path(str(path) + ".scores.jsonl")
            if kind == "scores"
            else path.with_suffix(".manifest.json")
        )
        if not path.resolve().is_relative_to(settings.workspace) or not path.is_file():
            raise HTTPException(404, "Artifact is not available in this workspace")
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/json" if kind == "manifest" else "application/x-ndjson",
        )

    @app.post("/runs/{run_id}/cancel", status_code=202)
    def cancel(run_id: str):
        try:
            app.state.queue.cancel(run_id)
            return {"run_id": run_id, "status": "cancellation_requested"}
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/compare", response_model=ComparisonResponse)
    def compare(payload: CompareRequest):
        if not comparison_lock.acquire(blocking=False):
            raise HTTPException(429, "Another comparison is running", headers={"Retry-After": "10"})
        try:
            result = lab().compare(**payload.model_dump())
            return {
                **result,
                "baseline": public_record(result["baseline"]),
                "candidate": public_record(result["candidate"]),
            }
        except Exception as exc:
            raise translate(exc) from exc
        finally:
            comparison_lock.release()

    @app.get("/comparisons", response_model=list[ComparisonResponse])
    def comparisons(
        limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0)
    ):
        return [
            {
                **c,
                "baseline": public_record(c["baseline"]),
                "candidate": public_record(c["candidate"]),
            }
            for c in lab().list_comparisons(limit, offset)
        ]

    @app.get("/comparisons/{comparison_id}", response_model=ComparisonResponse)
    def comparison(comparison_id: str):
        try:
            result = lab().get_comparison(comparison_id)
            return {
                **result,
                "baseline": public_record(result["baseline"]),
                "candidate": public_record(result["candidate"]),
            }
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/comparisons/{comparison_id}/report", response_class=PlainTextResponse)
    def report(comparison_id: str):
        result = comparison(comparison_id)
        report_text = format_drift_markdown_report(
            [DriftVerdict(**v) for v in result["verdicts"]],
            baseline_info={
                "identifier": result["baseline"]["model_identifier"],
                "digest": result["baseline"].get("model_digest"),
            },
            candidate_info={
                "identifier": result["candidate"]["model_identifier"],
                "digest": result["candidate"].get("model_digest"),
            },
        )
        report_text += f"\n## Reproducibility\n\nComparison: `{result['id']}`\n\nConfiguration: `{result['config']}`\n\nSynthetic: {result['baseline']['synthetic'] or result['candidate']['synthetic']}\n"
        return PlainTextResponse(
            report_text,
            headers={"Content-Disposition": f'attachment; filename="{result["id"]}.md"'},
        )

    original_openapi = app.openapi

    def openapi():
        schema = original_openapi()
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
            {
                "BearerAuth": {"type": "http", "scheme": "bearer"},
                "WorkspaceSession": {"type": "apiKey", "in": "cookie", "name": COOKIE},
            }
        )
        schema["security"] = [{"BearerAuth": []}, {"WorkspaceSession": []}]
        for path, methods in schema["paths"].items():
            if path in ("/", "/livez", "/auth/session", "/auth/login"):
                for operation in methods.values():
                    if isinstance(operation, dict):
                        operation["security"] = []
        return schema

    app.openapi = openapi

    for route in list(app.router.routes):
        if getattr(route, "path", "") not in (
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ):
            app.add_api_route(
                "/api" + route.path,
                route.endpoint,
                methods=list(route.methods),
                status_code=route.status_code,
                response_model=route.response_model,
                include_in_schema=False,
            )
    frontend = settings.frontend_dir or Path(__file__).parents[3] / "frontend" / "dist"
    if not frontend.exists():
        frontend = Path(__file__).parent / "static"
    if frontend.exists():
        app.mount("/app", StaticFiles(directory=frontend, html=True), name="dashboard")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard():
        return RedirectResponse("/app/")

    return app


app = create_app()
