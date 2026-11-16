"""Cross-layer invariants needed for review: evidence, failure handling, and identity."""

import json
import numpy as np
import pytest
from driftlab import DriftLab
from driftlab.datasets.loader import load_dataset
from driftlab.drift.decision import compare_runs_for_drift
from driftlab.fingerprint import hash_model
from driftlab.risk import get_risk_policy
from driftlab.stats.core import bootstrap_ci
from driftlab.store import get_db
from driftlab.store.models import StatisticalTest


def tasks(reference="4", prompt="Return 2+2"):
    return [
        dict(
            id=f"t{i}",
            task_key=f"k{i}",
            prompt=f"{prompt} (case {i})",
            expected_output=reference,
            category="reasoning",
            risk_level="medium",
        )
        for i in range(10)
    ]


def test_degenerate_confidence_intervals_are_json_safe():
    estimate, low, high = bootstrap_ci(np.zeros(20), 100, np.random.default_rng(42))
    assert (estimate, low, high) == (0, 0, 0)
    json.dumps([estimate, low, high], allow_nan=False)


def test_candidate_repeat_minimum_is_enforced():
    b = {str(i): np.ones(5) for i in range(10)}
    c = {str(i): np.ones(1) for i in range(10)}
    v = compare_runs_for_drift(
        b, c, "test", "exact_match", get_risk_policy("medium"), np.random.default_rng(1)
    )
    assert v.status == "insufficient_data"
    assert v.details["n_repeats"] == 1


def test_dataset_json_jsonl_and_invalid_inputs(tmp_path):
    data = tasks()
    for ext, content in [
        ("json", json.dumps(data)),
        ("jsonl", "\n".join(json.dumps(t) for t in data)),
    ]:
        p = tmp_path / f"tasks.{ext}"
        p.write_text(content)
        assert len(load_dataset(p)) == 10
    with pytest.raises(ValueError, match="does not exist"):
        load_dataset(tmp_path / "missing.json")
    p = tmp_path / "duplicate-tasks.json"
    p.write_text(json.dumps([data[0], data[0]]))
    with pytest.raises(ValueError, match="unique"):
        load_dataset(p)


def test_content_identity_blocks_changed_prompt(tmp_path):
    lab = DriftLab(tmp_path)
    try:
        b = lab.run(tasks=tasks(), repeats=3)
        c = lab.run(tasks=tasks(prompt="Return 3+3"), run_type="candidate", repeats=3)
        with pytest.raises(ValueError, match="same prompt content"):
            lab.compare(b.run_id, c.run_id, n_resamples=100, n_permutations=100)
        original = lab.get_run(b.run_id)
        assert original["observations"][0]["prompt"].startswith("Return 2+2")
    finally:
        lab.close()


def test_run_validation_prevents_silent_metric_failures(tmp_path):
    lab = DriftLab(tmp_path)
    try:
        for options in [
            dict(metrics=["missing"]),
            dict(tasks=[]),
            dict(repeats=0),
            dict(metrics=[]),
            dict(run_type="invalid"),
        ]:
            with pytest.raises(ValueError):
                lab.run(**options)
        no_reference = tasks()
        no_reference[0].pop("expected_output")
        with pytest.raises(ValueError, match="reference-based"):
            lab.run(tasks=no_reference)
        assert lab.list_runs() == []
    finally:
        lab.close()


def test_corrected_evidence_is_persisted(tmp_path):
    lab = DriftLab(tmp_path)
    try:
        b = lab.run(repeats=5, seed=42)
        c = lab.run(run_type="candidate", repeats=5, seed=91, mock_profile="regression")
        result = lab.compare(b.run_id, c.run_id)
        assert result["recommendation"] == "block"
        assert all(v["p_adjusted"] >= v["p_value"] for v in result["verdicts"])
        json.dumps(result, allow_nan=False)
        with get_db(lab.sessions) as session:
            assert session.query(StatisticalTest).count() == 4
        reopened = DriftLab(tmp_path)
        try:
            assert reopened.get_comparison(result["id"]) == result
        finally:
            reopened.close()
    finally:
        lab.close()


def test_api_background_and_export_share_stored_evidence(api):
    client, app = api
    assert client.get("/api/catalog").status_code == 200
    options = dict(tasks=tasks(), repeats=3)
    b = client.post("/api/runs", json=options)
    assert b.status_code == 202
    b_id = b.json()["run_id"]
    app.state.queue.run_once()
    c_id = client.post(
        "/api/runs",
        json={**options, "run_type": "candidate", "mock_profile": "regression", "seed": 91},
    ).json()["run_id"]
    app.state.queue.run_once()
    detail = client.get(f"/api/runs/{b_id}").json()
    assert detail["status"] == "completed" and len(detail["observations"]) == 30
    result = client.post(
        "/api/compare",
        json={
            "baseline_run_id": b_id,
            "candidate_run_id": c_id,
            "n_resamples": 100,
            "n_permutations": 100,
        },
    )
    assert result.status_code == 200
    saved = result.json()
    report = client.get(f"/api/comparisons/{saved['id']}/report")
    assert (
        report.status_code == 200
        and saved["id"] in report.text
        and "Synthetic: True" in report.text
    )
    assert client.post("/api/runs", json={"repeats": -1}).status_code == 422


def test_model_digest_participates_in_identity():
    assert hash_model({"identifier": "same-tag", "digest": "a"}) != hash_model(
        {"identifier": "same-tag", "digest": "b"}
    )


def test_official_dataset_conversion_preserves_answers():
    from scripts.prepare_benchmarks import convert

    math = convert("gsm8k", {"question": "What is 2+2?", "answer": "Working. #### 4"}, 7)
    boolean = convert(
        "boolq", {"question": "Is it true?", "passage": "It is false.", "answer": False}, 9
    )
    assert math["expected_output"] == "4"
    assert math["output_spec"]["answer_type"] == "numeric"
    assert boolean["expected_output"] == "no"
    assert boolean["output_spec"]["answer_type"] == "boolean"


def test_api_and_library_share_task_defaults(api):
    client, app = api
    response = client.post(
        "/api/runs", json={"tasks": [{"prompt": "2+2?", "expected_output": "4"}]}
    )
    assert response.status_code == 202
    app.state.queue.run_once()
    assert client.get(f"/api/runs/{response.json()['run_id']}").json()["observations_count"] == 5
    assert client.post("/api/runs", json={"tasks": ["not a task"]}).status_code == 422


def test_custom_adapter_keeps_its_own_identity(tmp_path):
    class CustomAdapter:
        def describe(self):
            return {"family": "custom", "identifier": "custom-state", "digest": "custom-digest"}

        def generate(self, **kwargs):
            return {"text": "4", "latency_ms": 0}

    lab = DriftLab(tmp_path)
    try:
        result = lab.run(adapter=CustomAdapter(), tasks=tasks(), repeats=3)
        record = lab.get_run(result.run_id)
        assert record["model_identifier"] == "custom-state"
        assert record["synthetic"] is False
        assert all(o["scores"]["exact_match"] == 1 for o in record["observations"])
    finally:
        lab.close()
