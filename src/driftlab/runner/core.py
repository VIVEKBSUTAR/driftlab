"""
Runner orchestrator for DriftLab.

Executes prompt tasks against model adapters with k repeats per prompt, writes
observations immediately to append-only JSONL files, computes evaluation metrics,
and optionally synchronizes results into SQLite.
"""

from dataclasses import dataclass, field
from pathlib import Path
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import numpy as np
from sqlalchemy.orm import Session

from driftlab.adapters.base import ModelAdapter, GenerationConfig
from driftlab.metrics.functions import compute_metric, METRIC_REGISTRY
from driftlab.store.jsonl import (
    append_observation_record,
    ingest_jsonl_to_database,
    read_observation_records,
)
from driftlab.store.artifacts import recover_tail
from driftlab.store.models import MetricResult, PromptAggregate, Run, Observation


@dataclass
class TaskItem:
    """Represents a discrete prompt task to be executed."""

    id: str
    task_key: str
    category: str
    risk_level: str
    prompt: str
    system_prompt: Optional[str] = None
    expected_output: Optional[str] = None
    output_spec: Optional[Dict[str, Any]] = None


@dataclass
class RunnerResult:
    """Container for the results of a benchmark run execution."""

    run_id: str
    jsonl_path: str
    total_prompts: int
    total_repeats: int
    observations_count: int
    # task_id -> metric_name -> list of float scores for each repeat
    metric_values: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    # task_id -> metric_name -> {"mean": float, "std": float}
    aggregates: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)


class BenchmarkRunner:
    """
    Orchestrates execution of tasks across repeats against a specified ModelAdapter.
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        repeats: int = 3,
        generation_config: Optional[GenerationConfig] = None,
        metric_names: Optional[List[str]] = None,
        seed_base: int = 42,
    ) -> None:
        if repeats < 1:
            raise ValueError("repeats must be positive")
        unknown = set(metric_names or ["exact_match"]) - set(METRIC_REGISTRY)
        if unknown:
            raise ValueError(f"Unknown metrics: {sorted(unknown)}")
        self.adapter = adapter
        self.repeats = repeats
        self.generation_config = generation_config or GenerationConfig()
        self.metric_names = metric_names or ["exact_match"]
        self.seed_base = seed_base

    def run(
        self,
        tasks: List[TaskItem],
        run_id: str,
        jsonl_path: Union[str, Path],
        db_session: Optional[Session] = None,
        check_control=None,
        resume: bool = False,
    ) -> RunnerResult:
        """
        Runs all tasks across k repeats. Outputs are streamed immediately to JSONL.
        """
        jsonl_path_str = str(jsonl_path)
        metric_values: Dict[str, Dict[str, List[float]]] = {
            t.id: {m: [] for m in self.metric_names} for t in tasks
        }
        observations_count = 0
        cached = {}
        scored_keys = set()
        if resume:
            recover_tail(Path(jsonl_path_str))
            recover_tail(Path(jsonl_path_str + ".scores.jsonl"))
            for record in read_observation_records(jsonl_path_str):
                key = (record["task_id"], record["repeat_index"])
                if key in cached or record["run_id"] != run_id:
                    raise ValueError("Duplicate or mismatched raw evidence; refusing to resume")
                cached[key] = record
            scored_keys = {
                (r["task_id"], r["repeat_index"])
                for r in read_observation_records(jsonl_path_str + ".scores.jsonl")
            }

        for task_idx, task in enumerate(tasks):
            for repeat_idx in range(self.repeats):
                # Derive deterministic seed per repeat
                if check_control:
                    check_control()
                repeat_seed = int(
                    np.random.SeedSequence([self.seed_base, task_idx, repeat_idx]).generate_state(
                        1, dtype=np.uint64
                    )[0]
                ) & ((1 << 63) - 1)
                config_with_seed = GenerationConfig(
                    temperature=self.generation_config.temperature,
                    top_p=self.generation_config.top_p,
                    max_tokens=self.generation_config.max_tokens,
                    seed=repeat_seed,
                    stop_sequences=self.generation_config.stop_sequences,
                    timeout_seconds=self.generation_config.timeout_seconds,
                )

                key = (task.id, repeat_idx)
                if key in cached:
                    record = cached[key]
                    if record["seed"] != repeat_seed:
                        raise ValueError("Generation seed does not match stored evidence")
                    text, latency_ms, error = (
                        record["raw_output"],
                        record["latency_ms"],
                        record.get("error"),
                    )
                else:
                    started = time.perf_counter()
                    try:
                        result = self.adapter.generate(
                            prompt=task.prompt,
                            system_prompt=task.system_prompt,
                            config=config_with_seed,
                        )
                        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
                            raise ValueError("Adapter must return a text string")
                        text = result["text"]
                        latency_ms = float(
                            result.get("latency_ms", (time.perf_counter() - started) * 1000)
                        )
                        if not np.isfinite(latency_ms) or latency_ms < 0:
                            raise ValueError("Adapter latency must be finite and nonnegative")
                        error = result.get("error")
                    except Exception as exc:
                        result = {}
                        text, error = "", str(exc)
                        latency_ms = (time.perf_counter() - started) * 1000
                    record = {
                        "run_id": run_id,
                        "task_id": task.id,
                        "repeat_index": repeat_idx,
                        "seed": repeat_seed,
                        "raw_output": text,
                        "latency_ms": latency_ms,
                        "error": error,
                        "finish_reason": result.get("finish_reason"),
                        "prompt_tokens": result.get("prompt_tokens"),
                        "completion_tokens": result.get("completion_tokens"),
                    }
                    append_observation_record(jsonl_path_str, record)
                observations_count += 1

                if error:
                    raise RuntimeError(f"Generation failed for {task.task_key}: {error}")
                scores = {}
                for metric_name in self.metric_names:
                    val = compute_metric(
                        metric_name=metric_name,
                        prediction=text,
                        reference=task.expected_output,
                        answer_type=task.output_spec.get("answer_type")
                        if task.output_spec
                        else None,
                        required_keys=task.output_spec.get("required_keys")
                        if task.output_spec
                        else None,
                    )
                    if not np.isfinite(val):
                        raise ValueError(f"Non-finite score from {metric_name}")
                    metric_values[task.id][metric_name].append(val)
                    scores[metric_name] = val
                # Raw output was already flushed; scoring errors cannot erase it.
                if key not in scored_keys:
                    append_observation_record(
                        str(jsonl_path_str) + ".scores.jsonl", {**record, "scores": scores}
                    )

        # Compute prompt-level aggregates (mean and std across repeats)
        aggregates: Dict[str, Dict[str, Dict[str, float]]] = {}
        for task_id, m_dict in metric_values.items():
            aggregates[task_id] = {}
            for metric_name, values in m_dict.items():
                arr = np.array(values, dtype=float)
                mean_val = float(np.mean(arr)) if len(arr) > 0 else 0.0
                std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
                aggregates[task_id][metric_name] = {
                    "mean": mean_val,
                    "std": std_val,
                }

        # Optional database synchronization
        if db_session is not None:
            self._sync_to_database(
                db_session=db_session,
                run_id=run_id,
                jsonl_path=jsonl_path_str,
                metric_values=metric_values,
                aggregates=aggregates,
            )

        return RunnerResult(
            run_id=run_id,
            jsonl_path=jsonl_path_str,
            total_prompts=len(tasks),
            total_repeats=self.repeats,
            observations_count=observations_count,
            metric_values=metric_values,
            aggregates=aggregates,
        )

    def _sync_to_database(
        self,
        db_session: Session,
        run_id: str,
        jsonl_path: str,
        metric_values: Dict[str, Dict[str, List[float]]],
        aggregates: Dict[str, Dict[str, Dict[str, float]]],
    ) -> None:
        """Synchronizes JSONL records, metric results, and aggregates into SQLite."""
        # 1. Ingest raw observations from JSONL
        ingest_jsonl_to_database(jsonl_path, db_session, run_id=run_id)

        # Query back saved observations for this run to attach MetricResult entities
        obs_map: Dict[tuple, str] = {}
        for obs in db_session.query(Observation).filter_by(run_id=run_id).all():
            obs_map[(obs.task_id, obs.repeat_index)] = obs.id

        # 2. Persist MetricResult rows
        for task_id, m_dict in metric_values.items():
            for metric_name, values in m_dict.items():
                for repeat_idx, val in enumerate(values):
                    obs_id = obs_map.get((task_id, repeat_idx))
                    if obs_id:
                        db_session.add(
                            MetricResult(
                                observation_id=obs_id,
                                metric_name=metric_name,
                                value=val,
                            )
                        )

        # 3. Persist PromptAggregate rows
        for task_id, agg_dict in aggregates.items():
            for metric_name, stats in agg_dict.items():
                db_session.add(
                    PromptAggregate(
                        run_id=run_id,
                        task_id=task_id,
                        metric_name=metric_name,
                        mean_value=stats["mean"],
                        std_value=stats["std"],
                        repeats_count=self.repeats,
                    )
                )

        # 4. Update Run metadata if present
        run_record = db_session.query(Run).filter_by(id=run_id).first()
        if run_record:
            run_record.status = "completed"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.jsonl_path = jsonl_path

        db_session.flush()
