"""The public API queues work and never accepts infrastructure from callers."""


def test_health_and_readiness(api):
    client, app = api
    assert client.get("/").json()["service"] == "driftlab"
    assert client.get("/api/readyz").json()["worker"] == "disabled"
    assert client.get("/api/workspace").json()["runs"] == 0


def test_run_and_compare(api):
    client, app = api
    options = {
        "model": "mock",
        "repeats": 3,
        "tasks": [
            {
                "id": f"t{i}",
                "task_key": f"t{i}",
                "prompt": f"What is {i}+1?",
                "expected_output": str(i + 1),
            }
            for i in range(10)
        ],
    }
    b = client.post("/api/runs", json=options)
    assert b.status_code == 202
    b_id = b.json()["run_id"]
    assert client.get(f"/api/runs/{b_id}").json()["status"] == "pending"
    assert app.state.queue.run_once()
    c = client.post("/api/runs", json={**options, "run_type": "candidate"})
    c_id = c.json()["run_id"]
    assert app.state.queue.run_once()
    assert len(client.get("/api/runs").json()) == 2
    detail = client.get(f"/api/runs/{b_id}").json()
    assert detail["observations_count"] == 30
    assert "jsonl_path" not in detail
    response = client.post(
        "/api/compare",
        json={
            "baseline_run_id": b_id,
            "candidate_run_id": c_id,
            "n_resamples": 100,
            "n_permutations": 100,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert client.get(f"/api/comparisons/{result['id']}/report").status_code == 200
    raw = client.get(f"/api/runs/{b_id}/artifacts/raw")
    assert raw.status_code == 200 and len(raw.text.splitlines()) == 30


def test_infrastructure_is_not_an_api_parameter(api):
    client, _ = api
    assert client.post("/api/runs", json={"db_url": "sqlite:////tmp/other.db"}).status_code == 422
    assert client.get("/api/runs?db_url=sqlite://").status_code == 422
    assert client.post("/api/runs", json={"background": False}).status_code == 422
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/runs?limit=1001").status_code == 422
