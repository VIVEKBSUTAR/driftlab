"""
Unit tests for driftlab.runner.core.
"""

from pathlib import Path
import pytest
from driftlab.adapters import MockAdapter
from driftlab.runner import BenchmarkRunner, TaskItem
from driftlab.store import (
    get_engine,
    create_tables,
    get_session_factory,
    get_db,
    Run,
    Task,
    ModelSnapshot,
    Observation,
    MetricResult,
    PromptAggregate,
    read_observation_records,
)


@pytest.fixture
def test_db():
    engine = get_engine("sqlite:///:memory:")
    create_tables(engine)
    return get_session_factory(engine)


def test_benchmark_runner_jsonl_and_metrics(tmp_path: Path):
    """Verifies that the runner executes tasks with repeats, saves to JSONL, and computes metrics."""
    jsonl_path = tmp_path / "run_observations.jsonl"
    adapter = MockAdapter(outputs=["Paris", "London", "Tokyo"])

    tasks = [
        TaskItem(
            id="task_1",
            task_key="cap_france",
            category="geography",
            risk_level="low",
            prompt="Capital of France?",
            expected_output="Paris",
        ),
        TaskItem(
            id="task_2",
            task_key="cap_uk",
            category="geography",
            risk_level="low",
            prompt="Capital of UK?",
            expected_output="London",
        ),
    ]

    runner = BenchmarkRunner(
        adapter=adapter,
        repeats=3,
        metric_names=["exact_match", "sequence_similarity"],
    )

    result = runner.run(
        tasks=tasks,
        run_id="run-test-01",
        jsonl_path=jsonl_path,
    )

    assert result.run_id == "run-test-01"
    assert result.total_prompts == 2
    assert result.total_repeats == 3
    assert result.observations_count == 6

    # Verify JSONL lines on disk
    records = read_observation_records(jsonl_path)
    assert len(records) == 6
    assert records[0]["run_id"] == "run-test-01"
    assert records[0]["task_id"] == "task_1"
    assert records[0]["repeat_index"] == 0

    # Verify aggregates
    assert "task_1" in result.aggregates
    assert "exact_match" in result.aggregates["task_1"]
    assert "mean" in result.aggregates["task_1"]["exact_match"]


def test_benchmark_runner_with_database_sync(tmp_path: Path, test_db):
    """Verifies that runner can synchronize observations, metrics, and aggregates to SQLite."""
    jsonl_path = tmp_path / "run_db_sync.jsonl"
    adapter = MockAdapter(outputs=["42"])

    tasks = [
        TaskItem(
            id="task_math",
            task_key="meaning_life",
            category="reasoning",
            risk_level="medium",
            prompt="What is the answer?",
            expected_output="42",
        )
    ]

    # Pre-create model, task, and run records in DB
    with get_db(test_db) as session:
        model = ModelSnapshot(model_family="mock", identifier="mock-model", digest="sha256:0")
        session.add(model)
        session.flush()

        task_record = Task(
            id="task_math",
            task_key="meaning_life",
            category="reasoning",
            risk_level="medium",
            prompt="What is the answer?",
            expected_output="42",
        )
        session.add(task_record)

        run_record = Run(
            id="run_sync_01",
            model_snapshot_id=model.id,
            run_type="candidate",
            status="pending",
        )
        session.add(run_record)
        session.flush()

    runner = BenchmarkRunner(
        adapter=adapter,
        repeats=2,
        metric_names=["exact_match"],
    )

    with get_db(test_db) as session:
        runner.run(
            tasks=tasks,
            run_id="run_sync_01",
            jsonl_path=jsonl_path,
            db_session=session,
        )

    # Verify database state after sync
    with get_db(test_db) as session:
        run = session.query(Run).filter_by(id="run_sync_01").one()
        assert run.status == "completed"
        assert len(run.observations) == 2
        assert run.observations[0].raw_output == "42"

        metric_records = session.query(MetricResult).all()
        assert len(metric_records) == 2
        assert metric_records[0].value == 1.0

        aggregates = session.query(PromptAggregate).filter_by(run_id="run_sync_01").all()
        assert len(aggregates) == 1
        assert aggregates[0].mean_value == 1.0
        assert aggregates[0].repeats_count == 2
