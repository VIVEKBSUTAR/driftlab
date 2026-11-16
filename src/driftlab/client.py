"""Public application service: one implementation for Python, CLI, and REST."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from functools import lru_cache
from filelock import FileLock, Timeout
from sqlalchemy import func
from sqlalchemy.orm import selectinload, object_session
from driftlab import __version__
from driftlab.store.schema import upgrade_schema
from driftlab.store.artifacts import atomic_json, write_error
from driftlab.runner.control import RunCancelled, WorkerStopping
from driftlab.adapters.synthetic import SyntheticAdapter
import numpy as np

from driftlab.adapters import MockAdapter, OllamaAdapter
from driftlab.config.schemas import GenerationConfig
from driftlab.datasets.loader import builtin_tasks, validate_tasks
from driftlab.drift.decision import compare_runs_for_drift, evaluate_drift
from driftlab.fingerprint import hash_model
from driftlab.metrics.functions import METRIC_REGISTRY
from driftlab.risk.policy import load_policies
from driftlab.runner import BenchmarkRunner, TaskItem
from driftlab.stats.core import holm_correction
from driftlab.store import get_engine, get_session_factory, get_db
from driftlab.store.models import (
    Run,
    Task,
    ModelSnapshot,
    DatasetVersion,
    Observation,
    Comparison,
    StatisticalTest,
    DriftResult,
    MetricResult,
    RunJob,
)
from driftlab.store.jsonl import ingest_jsonl_to_database


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class DriftLab:
    """Local evaluation workspace. Raw artifacts and SQLite live under ``workspace``.

    >>> lab = DriftLab("./experiment")
    >>> baseline = lab.run(model="mock", repeats=5)
    """

    def __init__(
        self,
        workspace: str | Path = ".",
        db_url: str | None = None,
        *,
        ollama_url="http://127.0.0.1:11434",
        policy_file=None,
    ):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.workspace / "data").mkdir(exist_ok=True, mode=0o700)
        (self.workspace / "data" / "runs").mkdir(exist_ok=True, mode=0o700)
        self.engine = get_engine(db_url or f"sqlite:///{self.workspace / 'driftlab.db'}")
        try:
            upgrade_schema(self.engine, self.workspace)
            self.policies = load_policies(policy_file)
        except BaseException:
            self.engine.dispose()
            raise
        self.ollama_url = ollama_url
        self.sessions = get_session_factory(self.engine)

    def artifact_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.workspace / path

    def close(self):
        self.engine.dispose()

    def prepare_run(
        self,
        model="mock",
        run_type="baseline",
        repeats=5,
        metrics=None,
        tasks=None,
        generation=None,
        seed=42,
        mock_profile="stable",
        output=None,
        adapter=None,
        enqueue=False,
    ):
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 or seed > 2**63 - 1:
            raise ValueError("Seed must be a nonnegative integer below 2**63")
        if (
            run_type not in ("baseline", "candidate")
            or not isinstance(repeats, int)
            or not 1 <= repeats <= 100
        ):
            raise ValueError("Run type must be baseline/candidate and repeats must be 1–100.")
        metrics = metrics if metrics is not None else ["exact_match", "sequence_similarity"]
        if not metrics or set(metrics) - set(METRIC_REGISTRY) or len(metrics) != len(set(metrics)):
            raise ValueError("Choose unique registered metrics.")
        if mock_profile not in ("stable", "regression"):
            raise ValueError("Unknown synthetic profile.")
        specs = (
            builtin_tasks()
            if tasks is None
            else validate_tasks([t.model_dump() if hasattr(t, "model_dump") else t for t in tasks])
        )
        if any(m != "json_validity" for m in metrics) and any(
            t.expected_output is None for t in specs
        ):
            raise ValueError(
                "Selected reference-based metrics require expected_output for every prompt."
            )
        generation = GenerationConfig.model_validate(generation or {})
        if generation.seed is not None:
            raise ValueError(
                "Set the run seed directly; per-generation seeds are derived and recorded automatically"
            )
        records = [t.model_dump() for t in specs]
        dataset_hash = digest(sorted(records, key=lambda t: t["task_key"]))
        task_items = []
        for record in records:
            record["id"] = "task_" + digest(record)
            task_items.append(TaskItem(**record))
        builtin_mock = adapter is None and model == "mock"
        if adapter is None:
            if model == "mock":
                refs = {t.prompt: t.expected_output or "{}" for t in task_items}
                adapter = SyntheticAdapter(refs, mock_profile)
            else:
                adapter = OllamaAdapter(model, base_url=self.ollama_url)
        synthetic = isinstance(adapter, MockAdapter)
        desc = adapter.describe()
        if not isinstance(desc, dict) or not all(
            isinstance(desc.get(k), str) and desc[k].strip() for k in ("identifier", "digest")
        ):
            raise ValueError("Adapters must provide a nonempty model identifier and digest")
        if builtin_mock:
            desc = {**desc, "identifier": f"mock-{mock_profile}", "profile": mock_profile}
        run_id = "run_" + uuid.uuid4().hex[:12]
        jsonl_path = str(
            Path(output).resolve()
            if output
            else self.workspace / "data" / "runs" / f"{run_id}.jsonl"
        )
        if Path(jsonl_path).exists():
            raise ValueError("Output file already exists; choose a new path to preserve evidence.")
        manifest = {
            "schema_version": 2,
            "run_id": run_id,
            "model": desc,
            "dataset_digest": dataset_hash,
            "tasks": [asdict(t) for t in task_items],
            "metrics": metrics,
            "repeats": repeats,
            "seed_scheme": "numpy-seed-sequence-v2",
            "seed": seed,
            "generation": generation.model_dump(),
            "synthetic": synthetic,
            "run_type": run_type,
            "environment": {"driftlab": __version__, "numpy": np.__version__},
        }
        path = Path(jsonl_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path.with_suffix(".manifest.json"), manifest)
        with get_db(self.sessions) as session:
            snapshot = session.query(ModelSnapshot).filter_by(digest=hash_model(desc)).first()
            if snapshot is None:
                snapshot = ModelSnapshot(
                    model_family=desc.get("family", "custom"),
                    identifier=desc["identifier"],
                    digest=hash_model(desc),
                    quantization=desc.get("quantization"),
                    backend_version=desc.get("backend_version"),
                )
                session.add(snapshot)
                session.flush()
            dataset = session.query(DatasetVersion).filter_by(digest=dataset_hash).first()
            if dataset is None:
                dataset = DatasetVersion(
                    name="evaluation", version=dataset_hash[:12], digest=dataset_hash
                )
                session.add(dataset)
                session.flush()
            for t in task_items:
                if session.get(Task, t.id) is None:
                    values = asdict(t)
                    values.pop("system_prompt")
                    session.add(Task(**values, dataset_version_id=dataset.id))
            session.add(
                Run(
                    id=run_id,
                    model_snapshot_id=snapshot.id,
                    dataset_version_id=dataset.id,
                    run_type=run_type,
                    status="pending",
                    jsonl_path=str(path.relative_to(self.workspace))
                    if path.is_relative_to(self.workspace)
                    else jsonl_path,
                )
            )
            if enqueue:
                session.flush()
                session.add(
                    RunJob(
                        run_id=run_id,
                        payload={
                            "manifest": manifest,
                            "model": model,
                            "mock_profile": mock_profile,
                        },
                        status="queued",
                    )
                )
        return run_id, adapter, manifest

    def execute_run(self, prepared, *, resume=False, check_control=None):
        run_id, adapter, manifest = prepared
        # A workspace has one writer performing inference/artifact synchronization at a time.
        with FileLock(str(self.workspace / ".execution.lock"), timeout=0):
            with get_db(self.sessions) as session:
                record = session.get(Run, run_id)
                if record is None or record.status == "completed":
                    raise ValueError("Run does not exist or has already completed")
                record.status = "running"
                jsonl_path = str(self.artifact_path(record.jsonl_path))
            try:
                runner = BenchmarkRunner(
                    adapter,
                    repeats=manifest["repeats"],
                    metric_names=manifest["metrics"],
                    generation_config=GenerationConfig(**manifest["generation"]),
                    seed_base=manifest["seed"],
                )
                result = runner.run(
                    [TaskItem(**t) for t in manifest["tasks"]],
                    run_id,
                    jsonl_path,
                    resume=resume,
                    check_control=check_control,
                )
                if check_control:
                    check_control()
                if hash_model(adapter.describe()) != hash_model(manifest["model"]):
                    raise ValueError(
                        "Model identity changed during evaluation; outputs were retained for inspection"
                    )
                # Inference never holds a database transaction open.
                with get_db(self.sessions) as session:
                    runner._sync_to_database(
                        session, run_id, jsonl_path, result.metric_values, result.aggregates
                    )
                return result
            except WorkerStopping:
                with get_db(self.sessions) as session:
                    session.get(Run, run_id).status = "pending"
                raise
            except Exception as exc:
                with get_db(self.sessions) as session:
                    record = session.get(Run, run_id)
                    record.status = "cancelled" if isinstance(exc, RunCancelled) else "failed"
                    record.completed_at = datetime.now(timezone.utc)
                    ingest_jsonl_to_database(jsonl_path, session, run_id)
                    write_error(Path(jsonl_path).with_suffix(".error.txt"), str(exc))
                raise

    def run(self, **kwargs):
        """Execute and persist a benchmark, returning a RunnerResult."""
        prepared = self.prepare_run(**kwargs)
        try:
            return self.execute_run(prepared)
        except Timeout:
            with get_db(self.sessions) as session:
                record = session.get(Run, prepared[0])
                record.status = "failed"
                record.completed_at = datetime.now(timezone.utc)
                write_error(
                    self.artifact_path(record.jsonl_path).with_suffix(".error.txt"),
                    "Workspace busy before execution",
                )
            raise

    def list_runs(self, limit=100, offset=0):
        with get_db(self.sessions) as session:
            return [
                self._run_record(r)
                for r in session.query(Run)
                .options(selectinload(Run.model_snapshot), selectinload(Run.dataset_version))
                .order_by(Run.created_at.desc(), Run.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            ]

    @staticmethod
    @lru_cache(maxsize=512)
    def _manifest_summary(path, modified):
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        return {
            key: manifest.get(key)
            for key in ("generation", "seed", "metrics", "model", "synthetic", "repeats")
        } | {"task_count": len(manifest.get("tasks", []))}

    def _run_record(self, r):
        path = self.artifact_path(r.jsonl_path) if r.jsonl_path else None
        manifest_path = path.with_suffix(".manifest.json") if path else None
        manifest = (
            self._manifest_summary(str(manifest_path), manifest_path.stat().st_mtime_ns)
            if manifest_path and manifest_path.exists()
            else {}
        )
        if r.status in ("pending", "running") and path and path.exists():
            with path.open("rb") as stream:
                progress = sum(1 for line in stream if line.endswith(b"\n"))
        else:
            progress = (
                object_session(r).query(func.count(Observation.id)).filter_by(run_id=r.id).scalar()
            )
        error_path = path.with_suffix(".error.txt") if path else None
        return dict(
            id=r.id,
            run_type=r.run_type,
            status=r.status,
            model_identifier=r.model_snapshot.identifier,
            jsonl_path=r.jsonl_path,
            created_at=r.created_at.isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            observations_count=progress,
            expected_observations=manifest.get("task_count", 0) * (manifest.get("repeats") or 0),
            dataset_digest=r.dataset_version.digest if r.dataset_version else None,
            synthetic=manifest.get("synthetic", r.model_snapshot.model_family == "mock"),
            model_digest=r.model_snapshot.digest,
            model_provenance=manifest.get("model", {}),
            generation=manifest.get("generation", {}),
            seed=manifest.get("seed"),
            metrics=manifest.get("metrics", []),
            error=error_path.read_text() if error_path and error_path.exists() else None,
        )

    def get_run(self, run_id, observation_limit=None, observation_offset=0):
        with get_db(self.sessions) as session:
            r = session.get(Run, run_id)
            if r is None:
                raise LookupError("Run not found")
            observations = (
                session.query(Observation)
                .options(selectinload(Observation.task), selectinload(Observation.metric_results))
                .filter_by(run_id=run_id)
                .order_by(Observation.task_id, Observation.repeat_index)
                .offset(observation_offset)
            )
            if observation_limit is not None:
                observations = observations.limit(observation_limit)
            return {
                **self._run_record(r),
                "observations_total": session.query(func.count(Observation.id))
                .filter_by(run_id=run_id)
                .scalar(),
                "model": {
                    "identifier": r.model_snapshot.identifier,
                    "family": r.model_snapshot.model_family,
                    "digest": r.model_snapshot.digest,
                },
                "aggregates": [
                    dict(
                        task_id=a.task_id,
                        metric_name=a.metric_name,
                        mean_value=a.mean_value,
                        std_value=a.std_value,
                        repeats_count=a.repeats_count,
                    )
                    for a in r.aggregates
                ],
                "observations": [
                    dict(
                        task_id=o.task_id,
                        task_key=o.task.task_key,
                        prompt=o.task.prompt,
                        reference=o.task.expected_output,
                        category=o.task.category,
                        risk_level=o.task.risk_level,
                        repeat_index=o.repeat_index,
                        raw_output=o.raw_output,
                        latency_ms=o.latency_ms,
                        finish_reason=o.finish_reason,
                        prompt_tokens=o.prompt_tokens,
                        completion_tokens=o.completion_tokens,
                        error=o.error,
                        scores={m.metric_name: m.value for m in o.metric_results},
                    )
                    for o in observations.all()
                ],
            }

    def compare(
        self,
        baseline_run_id,
        candidate_run_id,
        seed=42,
        noise_floor=None,
        n_resamples=2000,
        n_permutations=2000,
    ):
        """Compare matched datasets; Holm-adjust all category/metric/risk hypotheses."""
        if baseline_run_id == candidate_run_id:
            raise ValueError("Choose two different runs.")
        if noise_floor is not None and (not np.isfinite(noise_floor) or noise_floor < 0):
            raise ValueError("Noise floor must be finite and nonnegative.")
        if not 100 <= n_resamples <= 50000 or not 100 <= n_permutations <= 50000:
            raise ValueError("Resampling counts must be between 100 and 50000.")
        rng = np.random.default_rng(seed)
        with get_db(self.sessions) as session:
            baseline, candidate = (
                session.get(Run, baseline_run_id),
                session.get(Run, candidate_run_id),
            )
            if baseline is None or candidate is None:
                raise LookupError("One or both runs were not found.")
            if baseline.status != "completed" or candidate.status != "completed":
                raise ValueError("Both runs must have completed successfully.")
            if baseline.run_type != "baseline" or candidate.run_type != "candidate":
                raise ValueError("Select a baseline run and a candidate run in that order.")

            def collect(r):
                scores = {}
                if (
                    session.query(Observation.id)
                    .filter(Observation.run_id == r.id, Observation.error.is_not(None))
                    .first()
                ):
                    raise ValueError("Runs with generation errors cannot be compared")
                rows = (
                    session.query(
                        Task.category,
                        MetricResult.metric_name,
                        Task.risk_level,
                        Observation.task_id,
                        MetricResult.value,
                    )
                    .join(Observation, Observation.task_id == Task.id)
                    .join(MetricResult, MetricResult.observation_id == Observation.id)
                    .filter(Observation.run_id == r.id)
                    .order_by(
                        Task.category,
                        MetricResult.metric_name,
                        Task.risk_level,
                        Observation.task_id,
                        Observation.repeat_index,
                    )
                )
                for category, metric, risk, task_id, value in rows:
                    scores.setdefault((category, metric, risk), {}).setdefault(task_id, []).append(
                        value
                    )
                manifest_path = self.artifact_path(r.jsonl_path).with_suffix(".manifest.json")
                if not manifest_path.exists():
                    raise ValueError(
                        "A run manifest is missing; restore its evidence before comparing"
                    )
                design = self._manifest_summary(
                    str(manifest_path), manifest_path.stat().st_mtime_ns
                )
                counts = [len(values) for group in scores.values() for values in group.values()]
                expected = design["task_count"] * design["repeats"] * len(design["metrics"])
                if sum(counts) != expected or any(count != design["repeats"] for count in counts):
                    raise ValueError("Stored scores do not match the completed run design")
                return scores

            b, c = collect(baseline), collect(candidate)
            if not b or set(b) != set(c) or any(set(b[k]) != set(c[k]) for k in b):
                raise ValueError(
                    "Runs must contain the same prompt content, risk tiers, and metrics. Re-run both with the same dataset."
                )
            raw = []
            for key in sorted(b):
                category, metric, risk = key
                bp = {p: np.array(v) for p, v in b[key].items()}
                cp = {p: np.array(v) for p, v in c[key].items()}
                # Baseline repeat-resampling estimates stochastic noise conditional on these prompts.
                floor = noise_floor
                if floor is None:
                    samples = np.zeros(n_resamples)
                    for values in bp.values():
                        a = rng.choice(values, size=(n_resamples, len(values))).mean(axis=1)
                        d = rng.choice(values, size=(n_resamples, len(values))).mean(axis=1)
                        samples += (a - d) / len(bp)
                    floor = float(np.quantile(np.abs(samples), 0.95))
                verdict = compare_runs_for_drift(
                    bp,
                    cp,
                    category,
                    metric,
                    self.policies[risk],
                    rng,
                    noise_floor_val=floor,
                    n_resamples=n_resamples,
                    n_permutations=n_permutations,
                )
                raw.append(verdict)
            adjusted = holm_correction(np.array([v.p_value for v in raw]))
            verdicts = []
            for v, p in zip(raw, adjusted):
                policy = self.policies[v.risk_level]
                final = evaluate_drift(
                    v.estimate,
                    v.ci_low,
                    v.ci_high,
                    float(p),
                    v.noise_floor,
                    policy,
                    v.details.get("n_prompts", 0),
                    v.details.get("n_repeats", 0),
                    v.category,
                    v.metric_id,
                )
                final.p_value, final.details = (
                    v.p_value,
                    {
                        **v.details,
                        "correction": "Holm",
                        "noise_source": "manual"
                        if noise_floor is not None
                        else "baseline repeat bootstrap",
                    },
                )
                verdicts.append(asdict(final))
                stat = StatisticalTest(
                    baseline_run_id=baseline_run_id,
                    candidate_run_id=candidate_run_id,
                    category=v.category,
                    metric_id=v.metric_id,
                    method="prompt BCa + within-prompt permutation + Holm",
                    estimate=v.estimate,
                    ci_low=v.ci_low,
                    ci_high=v.ci_high,
                    p_value=v.p_value,
                    p_adjusted=float(p),
                    noise_floor=v.noise_floor,
                )
                session.add(stat)
                session.flush()
                session.add(
                    DriftResult(
                        category=v.category,
                        metric_id=v.metric_id,
                        risk_level=v.risk_level,
                        status=final.status,
                        statistical_test_id=stat.id,
                    )
                )
            statuses = {v["status"] for v in verdicts}
            recommendation = (
                "block"
                if "high_risk_regression" in statuses
                else "review"
                if statuses - {"no_meaningful_drift", "statistically_detected_low_impact"}
                else "within_policy"
            )
            result = dict(
                id="cmp_" + uuid.uuid4().hex[:12],
                baseline_run_id=baseline_run_id,
                candidate_run_id=candidate_run_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                verdicts=verdicts,
                recommendation=recommendation,
                config={
                    "seed": seed,
                    "n_resamples": n_resamples,
                    "n_permutations": n_permutations,
                    "correction": "Holm",
                    "noise_floor": noise_floor,
                    "policies": {k: asdict(v) for k, v in self.policies.items()},
                    "driftlab": __version__,
                },
                baseline=self._run_record(baseline),
                candidate=self._run_record(candidate),
            )
            session.add(
                Comparison(
                    id=result["id"],
                    baseline_run_id=baseline_run_id,
                    candidate_run_id=candidate_run_id,
                    result=result,
                )
            )
            return result

    def list_comparisons(self, limit=100, offset=0):
        with get_db(self.sessions) as session:
            return [
                c.result
                for c in session.query(Comparison)
                .order_by(Comparison.created_at.desc(), Comparison.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            ]

    def get_comparison(self, comparison_id):
        with get_db(self.sessions) as session:
            record = session.get(Comparison, comparison_id)
            if record is None:
                raise LookupError("Comparison not found")
            return record.result

    def summary(self):
        with get_db(self.sessions) as session:
            statuses = dict(
                session.query(Run.status, func.count(Run.id)).group_by(Run.status).all()
            )
            completed_observations = session.query(func.count(Observation.id)).scalar()
            active = session.query(Run).filter(Run.status.in_(["pending", "running"])).all()
            partial = sum(self._run_record(r)["observations_count"] for r in active)
            return {
                "runs": sum(statuses.values()),
                "statuses": statuses,
                "models": session.query(func.count(ModelSnapshot.id)).scalar(),
                "observations": completed_observations + partial,
                "comparisons": session.query(func.count(Comparison.id)).scalar(),
                "alerts": session.query(func.count(DriftResult.id))
                .filter(DriftResult.status == "high_risk_regression")
                .scalar(),
            }
