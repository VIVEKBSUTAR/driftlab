"""Public application service: one implementation for Python, CLI, and REST."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
import numpy as np

from driftlab.adapters import MockAdapter, OllamaAdapter
from driftlab.config.schemas import GenerationConfig
from driftlab.datasets.loader import builtin_tasks, validate_tasks
from driftlab.drift.decision import compare_runs_for_drift, evaluate_drift, DriftVerdict
from driftlab.fingerprint import hash_model
from driftlab.metrics.functions import METRIC_REGISTRY
from driftlab.risk.policy import get_risk_policy
from driftlab.runner import BenchmarkRunner, TaskItem
from driftlab.stats.core import holm_correction
from driftlab.store import get_engine, create_tables, get_session_factory, get_db
from driftlab.store.models import Run, Task, ModelSnapshot, DatasetVersion, Observation, Comparison, StatisticalTest, DriftResult
from driftlab.store.jsonl import read_observation_records, ingest_jsonl_to_database


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class DriftLab:
    """Local evaluation workspace. Raw artifacts and SQLite live under ``workspace``.

    >>> lab = DriftLab("./experiment")
    >>> baseline = lab.run(model="mock", repeats=5)
    """
    def __init__(self, workspace: str | Path = ".", db_url: str | None = None):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.engine = get_engine(db_url or f"sqlite:///{self.workspace / 'driftlab.db'}")
        create_tables(self.engine)
        self.sessions = get_session_factory(self.engine)

    def close(self):
        self.engine.dispose()

    def prepare_run(self, model="mock", run_type="baseline", repeats=5, metrics=None,
                    tasks=None, generation=None, seed=42, mock_profile="stable", output=None, adapter=None):
        if run_type not in ("baseline", "candidate") or not isinstance(repeats, int) or not 1 <= repeats <= 100:
            raise ValueError("Run type must be baseline/candidate and repeats must be 1–100.")
        metrics = metrics if metrics is not None else ["exact_match", "sequence_similarity"]
        if not metrics or set(metrics) - set(METRIC_REGISTRY) or len(metrics) != len(set(metrics)):
            raise ValueError("Choose unique registered metrics.")
        if mock_profile not in ("stable", "regression"):
            raise ValueError("Unknown synthetic profile.")
        specs = builtin_tasks() if tasks is None else validate_tasks([t.model_dump() if hasattr(t, "model_dump") else t for t in tasks])
        if any(m != "json_validity" for m in metrics) and any(t.expected_output is None for t in specs):
            raise ValueError("Selected reference-based metrics require expected_output for every prompt.")
        generation = GenerationConfig.model_validate(generation or {})
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
                rng = np.random.default_rng(seed)
                probability = .95 if mock_profile == "stable" else .45
                adapter = MockAdapter(response_sampler=lambda prompt: refs[prompt] if rng.random() < probability else "synthetic incorrect output")
            else:
                adapter = OllamaAdapter(model)
        synthetic = isinstance(adapter, MockAdapter)
        desc = adapter.describe()
        if builtin_mock:
            desc = {**desc, "identifier": f"mock-{mock_profile}", "profile": mock_profile}
        run_id = "run_" + uuid.uuid4().hex[:12]
        jsonl_path = str(Path(output).resolve() if output else self.workspace / "data" / "runs" / f"{run_id}.jsonl")
        if Path(jsonl_path).exists():
            raise ValueError("Output file already exists; choose a new path to preserve evidence.")
        manifest = {"schema_version": 1, "run_id": run_id, "model": desc, "dataset_digest": dataset_hash,
                    "tasks": [asdict(t) for t in task_items], "metrics": metrics, "repeats": repeats,
                    "seed": seed, "generation": generation.model_dump(), "synthetic": synthetic,
                    "run_type": run_type, "environment": {"driftlab":"0.1.0", "numpy":np.__version__}}
        path = Path(jsonl_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with get_db(self.sessions) as session:
            snapshot = session.query(ModelSnapshot).filter_by(digest=hash_model(desc)).first()
            if snapshot is None:
                snapshot = ModelSnapshot(model_family=desc.get("family", "custom"), identifier=desc["identifier"], digest=hash_model(desc), quantization=desc.get("quantization"), backend_version=desc.get("backend_version"))
                session.add(snapshot)
                session.flush()
            dataset = session.query(DatasetVersion).filter_by(digest=dataset_hash).first()
            if dataset is None:
                dataset = DatasetVersion(name="evaluation", version=dataset_hash[:12], digest=dataset_hash)
                session.add(dataset)
                session.flush()
            for t in task_items:
                if session.get(Task, t.id) is None:
                    values = asdict(t)
                    values.pop("system_prompt")
                    session.add(Task(**values, dataset_version_id=dataset.id))
            session.add(Run(id=run_id, model_snapshot_id=snapshot.id, dataset_version_id=dataset.id,
                            run_type=run_type, status="pending", jsonl_path=jsonl_path))
        return run_id, adapter, manifest

    def execute_run(self, prepared):
        run_id, adapter, manifest = prepared
        with get_db(self.sessions) as session:
            session.get(Run, run_id).status = "running"
        try:
            with get_db(self.sessions) as session:
                record = session.get(Run, run_id)
                result = BenchmarkRunner(adapter, repeats=manifest["repeats"], metric_names=manifest["metrics"],
                    generation_config=GenerationConfig(**manifest["generation"]), seed_base=manifest["seed"]).run(
                    [TaskItem(**t) for t in manifest["tasks"]], run_id, record.jsonl_path, session)
            return result
        except Exception as exc:
            with get_db(self.sessions) as session:
                record = session.get(Run, run_id)
                record.status = "failed"
                record.completed_at = datetime.now(timezone.utc)
                ingest_jsonl_to_database(record.jsonl_path, session, run_id)
                Path(record.jsonl_path).with_suffix(".error.txt").write_text(str(exc), encoding="utf-8")
            raise

    def run(self, **kwargs):
        """Execute and persist a benchmark, returning a RunnerResult."""
        return self.execute_run(self.prepare_run(**kwargs))

    def list_runs(self):
        with get_db(self.sessions) as session:
            return [self._run_record(r) for r in session.query(Run).order_by(Run.created_at.desc()).all()]

    def _run_record(self, r):
        path = Path(r.jsonl_path) if r.jsonl_path else None
        manifest_path = path.with_suffix(".manifest.json") if path else None
        manifest = json.loads(manifest_path.read_text()) if manifest_path and manifest_path.exists() else {}
        progress = sum(1 for line in path.open(encoding="utf-8") if line.endswith("\n")) if path and path.exists() else len(r.observations)
        error_path = path.with_suffix(".error.txt") if path else None
        return dict(id=r.id, run_type=r.run_type, status=r.status, model_identifier=r.model_snapshot.identifier,
            jsonl_path=r.jsonl_path, created_at=r.created_at.isoformat(), completed_at=r.completed_at.isoformat() if r.completed_at else None,
            observations_count=progress, expected_observations=len(manifest.get("tasks", []))*manifest.get("repeats", 0),
            dataset_digest=r.dataset_version.digest if r.dataset_version else None, synthetic=manifest.get("synthetic", False),
            model_digest=r.model_snapshot.digest, model_provenance=manifest.get("model", {}),
            generation=manifest.get("generation", {}), seed=manifest.get("seed"), metrics=manifest.get("metrics", []),
            error=error_path.read_text() if error_path and error_path.exists() else None)

    def get_run(self, run_id):
        with get_db(self.sessions) as session:
            r = session.get(Run, run_id)
            if r is None:
                raise LookupError("Run not found")
            return {**self._run_record(r), "model": {"identifier": r.model_snapshot.identifier,
                "family": r.model_snapshot.model_family, "digest": r.model_snapshot.digest},
                "aggregates": [dict(task_id=a.task_id, metric_name=a.metric_name, mean_value=a.mean_value,
                    std_value=a.std_value, repeats_count=a.repeats_count) for a in r.aggregates],
                "observations": [dict(task_id=o.task_id, task_key=o.task.task_key, prompt=o.task.prompt,
                    reference=o.task.expected_output, category=o.task.category, risk_level=o.task.risk_level,
                    repeat_index=o.repeat_index, raw_output=o.raw_output, latency_ms=o.latency_ms, error=o.error,
                    scores={m.metric_name:m.value for m in o.metric_results}) for o in sorted(r.observations, key=lambda o:(o.task.task_key,o.repeat_index))]}

    def compare(self, baseline_run_id, candidate_run_id, seed=42, noise_floor=None, n_resamples=2000, n_permutations=2000):
        """Compare matched datasets; Holm-adjust all category/metric/risk hypotheses."""
        if baseline_run_id == candidate_run_id:
            raise ValueError("Choose two different runs.")
        if noise_floor is not None and (not np.isfinite(noise_floor) or noise_floor < 0):
            raise ValueError("Noise floor must be finite and nonnegative.")
        if not 100 <= n_resamples <= 50000 or not 100 <= n_permutations <= 50000:
            raise ValueError("Resampling counts must be between 100 and 50000.")
        rng = np.random.default_rng(seed)
        with get_db(self.sessions) as session:
            baseline, candidate = session.get(Run, baseline_run_id), session.get(Run, candidate_run_id)
            if baseline is None or candidate is None:
                raise LookupError("One or both runs were not found.")
            if baseline.status != "completed" or candidate.status != "completed":
                raise ValueError("Both runs must have completed successfully.")
            if baseline.run_type != "baseline" or candidate.run_type != "candidate":
                raise ValueError("Select a baseline run and a candidate run in that order.")
            def collect(r):
                scores = {}
                for o in r.observations:
                    if o.error:
                        raise ValueError("Runs with generation errors cannot be compared.")
                    for m in o.metric_results:
                        scores.setdefault((o.task.category, m.metric_name, o.task.risk_level), {}).setdefault(o.task_id, []).append(m.value)
                return scores
            b, c = collect(baseline), collect(candidate)
            if not b or set(b) != set(c) or any(set(b[k]) != set(c[k]) for k in b):
                raise ValueError("Runs must contain the same prompt content, risk tiers, and metrics. Re-run both with the same dataset.")
            raw = []
            for key in sorted(b):
                category, metric, risk = key
                bp = {p:np.array(v) for p,v in b[key].items()}
                cp = {p:np.array(v) for p,v in c[key].items()}
                # Baseline repeat-resampling estimates stochastic noise conditional on these prompts.
                floor = noise_floor
                if floor is None:
                    samples = np.zeros(n_resamples)
                    for values in bp.values():
                        a = rng.choice(values, size=(n_resamples,len(values))).mean(axis=1)
                        d = rng.choice(values, size=(n_resamples,len(values))).mean(axis=1)
                        samples += (a-d)/len(bp)
                    floor = float(np.quantile(np.abs(samples), .95))
                verdict = compare_runs_for_drift(bp, cp, category, metric, get_risk_policy(risk), rng,
                    noise_floor_val=floor, n_resamples=n_resamples, n_permutations=n_permutations)
                raw.append(verdict)
            adjusted = holm_correction(np.array([v.p_value for v in raw]))
            verdicts = []
            for v, p in zip(raw, adjusted):
                policy = get_risk_policy(v.risk_level)
                final = evaluate_drift(v.estimate, v.ci_low, v.ci_high, float(p), v.noise_floor, policy,
                    v.details.get("n_prompts", 0), v.details.get("n_repeats", 0), v.category, v.metric_id)
                final.p_value, final.details = v.p_value, {**v.details, "correction": "Holm", "noise_source": "manual" if noise_floor is not None else "baseline repeat bootstrap"}
                verdicts.append(asdict(final))
                stat = StatisticalTest(baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id, category=v.category,
                    metric_id=v.metric_id, method="prompt BCa + within-prompt permutation + Holm", estimate=v.estimate,
                    ci_low=v.ci_low, ci_high=v.ci_high, p_value=v.p_value, p_adjusted=float(p), noise_floor=v.noise_floor)
                session.add(stat)
                session.flush()
                session.add(DriftResult(category=v.category, metric_id=v.metric_id, risk_level=v.risk_level, status=final.status, statistical_test_id=stat.id))
            statuses = {v["status"] for v in verdicts}
            recommendation = "block" if "high_risk_regression" in statuses else "review" if statuses - {"no_meaningful_drift", "statistically_detected_low_impact"} else "within_policy"
            result = dict(id="cmp_"+uuid.uuid4().hex[:12], baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id,
                created_at=datetime.now(timezone.utc).isoformat(), verdicts=verdicts, recommendation=recommendation,
                config={"seed":seed,"n_resamples":n_resamples,"n_permutations":n_permutations,"correction":"Holm","noise_floor":noise_floor},
                baseline=self._run_record(baseline), candidate=self._run_record(candidate))
            session.add(Comparison(id=result["id"], baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id, result=result))
            return result

    def list_comparisons(self):
        with get_db(self.sessions) as session:
            return [c.result for c in session.query(Comparison).order_by(Comparison.created_at.desc()).all()]

    def get_comparison(self, comparison_id):
        with get_db(self.sessions) as session:
            record = session.get(Comparison, comparison_id)
            if record is None:
                raise LookupError("Comparison not found")
            return record.result
