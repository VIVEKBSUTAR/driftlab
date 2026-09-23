"""
Unit tests for driftlab.store (SQLAlchemy models and append-only JSONL persistence).
"""

import os
import json
import pytest
from pathlib import Path
from driftlab.store import (
    Base,
    Experiment,
    ModelSnapshot,
    DatasetVersion,
    Task,
    Run,
    Observation,
    MetricResult,
    PromptAggregate,
    StatisticalTest,
    RiskPolicy,
    DriftResult,
    get_engine,
    create_tables,
    get_session_factory,
    get_db,
    append_observation_record,
    read_observation_records,
    ingest_jsonl_to_database,
)


@pytest.fixture
def in_memory_db():
    engine = get_engine("sqlite:///:memory:")
    create_tables(engine)
    session_factory = get_session_factory(engine)
    return session_factory


def test_schema_creation_and_relations(in_memory_db):
    """Verifies that all 11 models can be created and queried with foreign key relationships."""
    with get_db(in_memory_db) as session:
        # 1. Experiment
        exp = Experiment(name="exp-001", description="Baseline test experiment")
        session.add(exp)

        # 2. ModelSnapshot
        model = ModelSnapshot(
            model_family="llama",
            identifier="llama3:8b",
            digest="sha256:abc12345",
            quantization="q4_0",
            backend_version="ollama/0.1.30",
        )
        session.add(model)

        # 3. DatasetVersion
        dataset = DatasetVersion(
            name="safety_bench",
            version="1.0.0",
            digest="sha256:dataset123",
        )
        session.add(dataset)
        session.flush()

        # 4. Task (Appendix minimal fields: task_key, category, risk_level, prompt, expected_output, output_spec)
        task = Task(
            task_key="prompt_001",
            category="reasoning",
            risk_level="high",
            prompt="What is 2 + 2?",
            expected_output="4",
            output_spec={"type": "integer"},
            dataset_version_id=dataset.id,
        )
        session.add(task)

        # 5. Run
        run = Run(
            experiment_id=exp.id,
            model_snapshot_id=model.id,
            dataset_version_id=dataset.id,
            run_type="baseline",
            status="completed",
            jsonl_path="data/runs/run1.jsonl",
        )
        session.add(run)
        session.flush()

        # 6. Observation (Appendix minimal fields: run_id, task_id, repeat_index, seed, raw_output, latency_ms, error)
        obs = Observation(
            run_id=run.id,
            task_id=task.id,
            repeat_index=0,
            seed=42,
            raw_output="The answer is 4.",
            latency_ms=124.5,
            error=None,
        )
        session.add(obs)
        session.flush()

        # 7. MetricResult
        metric = MetricResult(
            observation_id=obs.id,
            metric_name="exact_match",
            value=1.0,
        )
        session.add(metric)

        # 8. PromptAggregate
        agg = PromptAggregate(
            run_id=run.id,
            task_id=task.id,
            metric_name="exact_match",
            mean_value=1.0,
            std_value=0.0,
            repeats_count=1,
        )
        session.add(agg)

        # 9. StatisticalTest (Appendix: category, metric_id, method, estimate, ci_low, ci_high, p_value, p_adjusted, noise_floor)
        stat_test = StatisticalTest(
            baseline_run_id=run.id,
            candidate_run_id=run.id,
            category="reasoning",
            metric_id="exact_match",
            method="bootstrap_ci",
            estimate=0.02,
            ci_low=-0.01,
            ci_high=0.05,
            p_value=0.18,
            p_adjusted=0.25,
            noise_floor=0.015,
        )
        session.add(stat_test)
        session.flush()

        # 10. RiskPolicy
        policy = RiskPolicy(
            name="standard_high_risk",
            risk_level="high",
            margin=0.05,
            alpha=0.01,
            min_prompts=20,
            min_repeats=5,
        )
        session.add(policy)

        # 11. DriftResult (Appendix: category, metric_id, risk_level, status, statistical_test_id)
        drift = DriftResult(
            category="reasoning",
            metric_id="exact_match",
            risk_level="high",
            status="no_meaningful_drift",
            statistical_test_id=stat_test.id,
        )
        session.add(drift)
        session.flush()

        run_id = run.id
        drift_id = drift.id

    # Query back to verify persistence
    with get_db(in_memory_db) as session:
        stored_run = session.query(Run).filter_by(id=run_id).one()
        assert stored_run.run_type == "baseline"
        assert len(stored_run.observations) == 1
        assert stored_run.observations[0].raw_output == "The answer is 4."
        assert len(stored_run.observations[0].metric_results) == 1
        assert stored_run.observations[0].metric_results[0].metric_name == "exact_match"

        stored_drift = session.query(DriftResult).filter_by(id=drift_id).one()
        assert stored_drift.status == "no_meaningful_drift"
        assert stored_drift.statistical_test.estimate == 0.02
        assert stored_drift.statistical_test.noise_floor == 0.015


def test_jsonl_append_and_read(tmp_path: Path):
    """Tests writing records to an append-only JSONL file and reading them back."""
    jsonl_file = tmp_path / "test_run.jsonl"

    rec1 = {
        "run_id": "run-101",
        "task_id": "task-01",
        "repeat_index": 0,
        "seed": 1234,
        "raw_output": "output line 1",
        "latency_ms": 45.2,
        "error": None,
    }
    rec2 = {
        "run_id": "run-101",
        "task_id": "task-01",
        "repeat_index": 1,
        "seed": 1235,
        "raw_output": "output line 2",
        "latency_ms": 48.1,
        "error": None,
    }

    append_observation_record(jsonl_file, rec1)
    append_observation_record(jsonl_file, rec2)

    records = read_observation_records(jsonl_file)
    assert len(records) == 2
    assert records[0]["raw_output"] == "output line 1"
    assert records[1]["raw_output"] == "output line 2"


def test_jsonl_ingest_to_db(tmp_path: Path, in_memory_db):
    """Verifies that raw JSONL observations are reliably ingested into SQLite."""
    jsonl_file = tmp_path / "run_source_of_truth.jsonl"

    with get_db(in_memory_db) as session:
        # Pre-create prerequisites
        model = ModelSnapshot(model_family="test", identifier="test-m", digest="sha256:1")
        session.add(model)
        session.flush()

        task = Task(task_key="t1", category="c1", risk_level="low", prompt="test prompt")
        session.add(task)

        run = Run(id="run-test", model_snapshot_id=model.id, run_type="baseline")
        session.add(run)
        session.flush()

        task_id = task.id

    rec1 = {
        "run_id": "run-test",
        "task_id": task_id,
        "repeat_index": 0,
        "seed": 100,
        "raw_output": "First answer",
        "latency_ms": 20.0,
        "error": None,
    }
    rec2 = {
        "run_id": "run-test",
        "task_id": task_id,
        "repeat_index": 1,
        "seed": 101,
        "raw_output": "Second answer",
        "latency_ms": 22.5,
        "error": None,
    }

    append_observation_record(jsonl_file, rec1)
    append_observation_record(jsonl_file, rec2)

    with get_db(in_memory_db) as session:
        count = ingest_jsonl_to_database(jsonl_file, session)
        assert count == 2

    # Verify duplicate ingestion avoids redundant rows
    with get_db(in_memory_db) as session:
        count_repeat = ingest_jsonl_to_database(jsonl_file, session)
        assert count_repeat == 0

        obs_list = session.query(Observation).filter_by(run_id="run-test").all()
        assert len(obs_list) == 2
        assert obs_list[0].raw_output == "First answer"
        assert obs_list[1].raw_output == "Second answer"
