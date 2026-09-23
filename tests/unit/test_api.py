"""
Unit tests for the DriftLab FastAPI endpoints.
"""

from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from driftlab.api.main import app

client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "driftlab"


def test_trigger_and_query_run(tmp_path: Path):
    db_file = tmp_path / "api_test.db"
    db_url = f"sqlite:///{db_file}"

    # 1. Trigger baseline run
    payload_base = {
        "model": "mock",
        "run_type": "baseline",
        "repeats": 2,
        "metrics": ["exact_match"],
        "tasks": [
            {
                "id": "t1",
                "task_key": "t1",
                "category": "logic",
                "risk_level": "medium",
                "prompt": "What is 2+2?",
                "expected_output": "4",
            }
        ],
        "db_url": db_url,
    }
    res_base = client.post("/runs", json=payload_base)
    assert res_base.status_code == 200
    base_data = res_base.json()
    assert base_data["status"] == "success"
    base_run_id = base_data["run_id"]

    # 2. Trigger candidate run
    payload_cand = {
        "model": "mock",
        "run_type": "candidate",
        "repeats": 2,
        "metrics": ["exact_match"],
        "tasks": [
            {
                "id": "t1",
                "task_key": "t1",
                "category": "logic",
                "risk_level": "medium",
                "prompt": "What is 2+2?",
                "expected_output": "4",
            }
        ],
        "db_url": db_url,
    }
    res_cand = client.post("/runs", json=payload_cand)
    assert res_cand.status_code == 200
    cand_data = res_cand.json()
    cand_run_id = cand_data["run_id"]

    # 3. List runs
    res_list = client.get(f"/runs?db_url={db_url}")
    assert res_list.status_code == 200
    runs = res_list.json()
    assert len(runs) == 2

    # 4. Get run details
    res_get = client.get(f"/runs/{base_run_id}?db_url={db_url}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["id"] == base_run_id
    assert detail["observations_count"] == 2

    # 5. Compare runs
    compare_payload = {
        "baseline_run_id": base_run_id,
        "candidate_run_id": cand_run_id,
        "db_url": db_url,
        "noise_floor": 0.01,
        "seed": 42,
    }
    res_compare = client.post("/compare", json=compare_payload)
    assert res_compare.status_code == 200
    comp_data = res_compare.json()
    assert comp_data["baseline_run_id"] == base_run_id
    assert len(comp_data["verdicts"]) > 0
    assert "status" in comp_data["verdicts"][0]
