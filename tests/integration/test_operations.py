"""Security, restart recovery, cancellation, migrations, and portable evidence."""

from dataclasses import asdict
import json
import sqlite3
import zipfile

from fastapi.testclient import TestClient
from filelock import Timeout
import pytest
from driftlab import DriftLab
from driftlab.api.main import create_app
from driftlab.config.settings import Settings
from driftlab.jobs import JobQueue
from driftlab.maintenance import backup_workspace, restore_workspace
from driftlab.store import get_db
from driftlab.store.models import Run, RunJob
from driftlab.adapters.synthetic import SyntheticAdapter
from driftlab.datasets.loader import validate_tasks
from driftlab.risk.policy import DEFAULT_POLICIES


def task_records(n=3):
    return [
        {
            "id": str(i),
            "task_key": str(i),
            "prompt": f"Return the number {i}",
            "expected_output": str(i),
        }
        for i in range(n)
    ]


def server(tmp_path, **overrides):
    settings = Settings(
        workspace=tmp_path,
        mode="server",
        api_key="a-long-workspace-test-key-12345678",
        cookie_secure=True,
        worker_enabled=False,
        allowed_hosts=["testserver"],
        **overrides,
    )
    return create_app(settings)


def test_server_requires_secret_and_secure_cookies(tmp_path):
    with pytest.raises(ValueError, match="API_KEY"):
        Settings(mode="server", cookie_secure=True)
    with pytest.raises(ValueError, match="secure"):
        Settings(mode="server", api_key="x" * 40)
    with pytest.raises(ValueError):
        Settings(ollama_url="http://user:password@example.com")
    with pytest.raises(ValueError):
        Settings(allowed_hosts=["*"])


def test_authentication_cookie_bearer_tamper_and_logout(tmp_path):
    app = server(tmp_path)
    with TestClient(app, base_url="https://testserver", client=("198.51.100.1", 1000)) as client:
        assert client.get("/api/livez").status_code == 200
        assert client.get("/api/runs").status_code == 401
        assert client.get("/api/auth/session").json()["authenticated"] is False
        assert client.post("/api/auth/login", json={"token": "wrong"}).status_code == 401
        response = client.post(
            "/api/auth/login", json={"token": app.state.settings.api_key.get_secret_value()}
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
        assert client.get("/api/workspace").status_code == 200
        assert (
            client.get("/api/runs", headers={"Cookie": "driftlab_session=tampered"}).status_code
            == 401
        )
        assert client.post("/api/auth/logout", json={}).status_code == 200
        assert client.get("/api/runs").status_code == 401
        assert (
            client.get(
                "/api/runs",
                headers={
                    "Authorization": "Bearer " + app.state.settings.api_key.get_secret_value()
                },
            ).status_code
            == 200
        )


def test_untrusted_origin_host_and_non_loopback_local_access(tmp_path):
    app = create_app(
        Settings(workspace=tmp_path, worker_enabled=False, allowed_hosts=["testserver"])
    )
    with TestClient(app, client=("127.0.0.1", 1000)) as client:
        assert client.get("/api/runs", headers={"Host": "attacker.example"}).status_code == 400
        assert (
            client.post(
                "/api/runs", json={}, headers={"Origin": "https://attacker.example"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/runs",
                content="model=mock",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ).status_code
            == 415
        )
        response = client.get("/api/runs")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert len(response.headers["x-request-id"]) == 32
    with TestClient(app, client=("198.51.100.1", 1000)) as client:
        assert client.get("/api/runs").status_code == 403


def test_body_limits_apply_without_content_length(tmp_path):
    app = create_app(
        Settings(
            workspace=tmp_path,
            worker_enabled=False,
            allowed_hosts=["testserver"],
            max_body_bytes=1024,
        )
    )
    with TestClient(app, client=("127.0.0.1", 1000)) as client:
        assert client.post("/api/runs", json={"tasks": ["x" * 2048]}).status_code == 413
        response = client.post(
            "/api/runs",
            content=iter([b'{"tasks":', b'"' + b"x" * 2048 + b'"}']),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413


def test_limits_and_queue_capacity_fail_before_execution(tmp_path):
    app = create_app(
        Settings(
            workspace=tmp_path,
            worker_enabled=False,
            allowed_hosts=["testserver"],
            max_tasks=2,
            max_observations=6,
            max_pending_jobs=1,
        )
    )
    with TestClient(app, client=("127.0.0.1", 1000)) as client:
        assert client.post("/api/runs", json={"tasks": task_records(3)}).status_code == 422
        assert (
            client.post("/api/runs", json={"tasks": task_records(2), "repeats": 4}).status_code
            == 422
        )
        assert client.post("/api/runs", json={"tasks": task_records(1)}).status_code == 202
        assert client.post("/api/runs", json={"tasks": task_records(1)}).status_code == 429
        assert len(app.state.lab.list_runs()) == 1


def test_login_rate_limit(tmp_path):
    app = server(tmp_path)
    with TestClient(app, base_url="https://testserver", client=("127.0.0.1", 1000)) as client:
        for _ in range(10):
            assert client.post("/api/auth/login", json={"token": "wrong"}).status_code == 401
        response = client.post("/api/auth/login", json={"token": "wrong"})
        assert response.status_code == 429 and response.headers["retry-after"] == "60"


def test_worker_restart_resumes_without_duplicate_generations(tmp_path, monkeypatch):
    lab = DriftLab(tmp_path)
    queue = JobQueue(lab)
    run_id = queue.enqueue(tasks=task_records(), repeats=3)
    original = SyntheticAdapter.generate
    calls = []

    def interrupted(self, **kwargs):
        calls.append(kwargs["config"].seed)
        result = original(self, **kwargs)
        if len(calls) == 2:
            queue.stop_event.set()
        return result

    monkeypatch.setattr(SyntheticAdapter, "generate", interrupted)
    assert queue.run_once()
    assert lab.get_run(run_id)["status"] == "pending"
    with get_db(lab.sessions) as session:
        session.get(RunJob, run_id).status = "running"
        session.get(Run, run_id).status = "running"
    raw_path = lab.artifact_path(lab.get_run(run_id)["jsonl_path"])
    with raw_path.open("ab") as stream:
        stream.write(b'{"interrupted":')

    def resumed(self, **kwargs):
        calls.append(kwargs["config"].seed)
        return original(self, **kwargs)

    monkeypatch.setattr(SyntheticAdapter, "generate", resumed)
    restarted = JobQueue(lab)
    assert restarted.run_once()
    detail = lab.get_run(run_id)
    assert detail["status"] == "completed" and detail["observations_count"] == 9
    assert len(calls) == 9 and len(set(calls)) == 9
    assert len(detail["observations"]) == 9 and all(o["scores"] for o in detail["observations"])
    assert list(raw_path.parent.glob(raw_path.name + ".interrupted-*"))
    lab.close()


def test_cancellation_retains_partial_evidence(tmp_path, monkeypatch):
    lab = DriftLab(tmp_path)
    queue = JobQueue(lab)
    run_id = queue.enqueue(tasks=task_records(), repeats=3)
    original = SyntheticAdapter.generate

    def cancel_after_one(self, **kwargs):
        queue.cancel(run_id)
        return original(self, **kwargs)

    monkeypatch.setattr(SyntheticAdapter, "generate", cancel_after_one)
    queue.run_once()
    detail = lab.get_run(run_id)
    assert detail["status"] == "cancelled" and detail["observations_count"] == 1
    assert len(detail["observations"]) == 1
    assert not queue.run_once()
    lab.close()


def test_only_one_worker_owns_a_workspace_and_stop_releases_lock(tmp_path):
    lab = DriftLab(tmp_path)
    first, second = JobQueue(lab), JobQueue(lab)
    first.start()
    try:
        with pytest.raises(Timeout):
            second.start()
    finally:
        first.stop()
    second.start()
    assert second.healthy
    second.stop()
    lab.close()


def test_backup_restore_preserves_comparisons_and_pending_jobs(tmp_path):
    source = DriftLab(tmp_path / "source")
    b = source.run(tasks=task_records(10), repeats=3)
    c = source.run(tasks=task_records(10), repeats=3, run_type="candidate", seed=101)
    evidence = source.compare(b.run_id, c.run_id, n_resamples=100, n_permutations=100)
    pending = JobQueue(source).enqueue(tasks=task_records(), repeats=3)
    archive = backup_workspace(source, tmp_path / "backup.zip")
    restored = restore_workspace(archive, tmp_path / "restored")
    target = DriftLab(restored)
    assert target.get_comparison(evidence["id"]) == evidence
    assert len(target.get_run(b.run_id)["observations"]) == 30
    assert JobQueue(target).run_once()
    assert target.get_run(pending)["status"] == "completed"
    assert source.get_run(pending)["status"] == "pending"
    with pytest.raises(ValueError, match="must not exist"):
        restore_workspace(archive, restored)
    target.close()
    source.close()


def test_restore_rejects_path_traversal(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../escape", "bad")
        archive.writestr("backup-manifest.json", "{}")
    with pytest.raises(ValueError, match="Unsafe"):
        restore_workspace(path, tmp_path / "target")
    assert not (tmp_path / "escape").exists() and not (tmp_path / "target").exists()


def test_restore_detects_modified_evidence(tmp_path):
    lab = DriftLab(tmp_path / "source")
    lab.run(tasks=task_records(), repeats=2)
    original = backup_workspace(lab, tmp_path / "original.zip")
    modified = tmp_path / "modified.zip"
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(modified, "w") as dst:
        for name in src.namelist():
            data = src.read(name)
            dst.writestr(name, data + b"changed" if name.endswith(".jsonl") else data)
    with pytest.raises(ValueError, match="checksum"):
        restore_workspace(modified, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    lab.close()


def test_schema_rejects_newer_version_and_preserves_old_data(tmp_path):
    lab = DriftLab(tmp_path)
    result = lab.run(tasks=task_records(), repeats=2)
    lab.close()
    with sqlite3.connect(tmp_path / "driftlab.db") as connection:
        connection.execute("UPDATE schema_version SET version=999")
    with pytest.raises(RuntimeError, match="newer"):
        DriftLab(tmp_path)
    with sqlite3.connect(tmp_path / "driftlab.db") as connection:
        assert (
            connection.execute("SELECT status FROM runs WHERE id=?", (result.run_id,)).fetchone()[0]
            == "completed"
        )


def test_policy_configuration_is_validated_and_saved_in_evidence(tmp_path):
    policies = [asdict(p) for p in DEFAULT_POLICIES.values()]
    policies[1]["margin"] = 0.2
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps(policies))
    lab = DriftLab(tmp_path, policy_file=policy_file)
    b = lab.run(tasks=task_records(10), repeats=3)
    c = lab.run(tasks=task_records(10), repeats=3, run_type="candidate")
    result = lab.compare(b.run_id, c.run_id, n_resamples=100, n_permutations=100)
    assert result["verdicts"][0]["margin"] == 0.2
    assert result["config"]["policies"]["medium"]["margin"] == 0.2
    lab.close()
    policy_file.write_text("[]")
    with pytest.raises(ValueError):
        DriftLab(tmp_path, policy_file=policy_file)


def test_duplicate_prompt_contexts_do_not_inflate_sample_size():
    records = task_records(2)
    records[1]["prompt"] = records[0]["prompt"]
    with pytest.raises(ValueError, match="Duplicate prompt"):
        validate_tasks(records)


def test_new_provenance_and_mid_run_identity_change_are_not_silent(tmp_path):
    class ChangingAdapter(SyntheticAdapter):
        changed = False

        def describe(self):
            description = super().describe()
            if self.changed:
                description["digest"] = "replacement-model-digest"
            return description

        def generate(self, *args, **kwargs):
            result = super().generate(*args, **kwargs)
            self.changed = True
            return {
                **result,
                "finish_reason": "length",
                "prompt_tokens": 12,
                "completion_tokens": 16,
            }

    lab = DriftLab(tmp_path)
    adapter = ChangingAdapter({"Return the number 0": "0"}, "stable")
    with pytest.raises(ValueError, match="identity changed"):
        lab.run(tasks=task_records(1), repeats=2, adapter=adapter)
    run = lab.get_run(lab.list_runs()[0]["id"])
    assert run["status"] == "failed"
    assert len(run["observations"]) == 2
    assert run["observations"][0]["finish_reason"] == "length"
    assert run["observations"][0]["prompt_tokens"] == 12
    assert run["observations"][0]["completion_tokens"] == 16
    lab.close()


def test_upgrade_legacy_observation_columns_preserves_evidence(tmp_path):
    lab = DriftLab(tmp_path)
    result = lab.run(tasks=task_records(2), repeats=2)
    lab.close()
    with sqlite3.connect(tmp_path / "driftlab.db") as connection:
        for name in ("finish_reason", "prompt_tokens", "completion_tokens"):
            connection.execute(f"ALTER TABLE observations DROP COLUMN {name}")
        connection.execute("UPDATE schema_version SET version=1")
    upgraded = DriftLab(tmp_path)
    detail = upgraded.get_run(result.run_id)
    assert detail["status"] == "completed" and detail["observations_total"] == 4
    assert all(o["finish_reason"] is None for o in detail["observations"])
    upgraded.close()


def test_settings_never_print_secret_values(tmp_path):
    secret = "unique-private-workspace-key-12345678"
    settings = Settings(api_key=secret)
    assert secret not in repr(settings)
    with pytest.raises(ValueError) as error:
        Settings(mode="server", api_key=secret, cookie_secure=False)
    assert secret not in str(error.value)
    with pytest.raises(ValueError, match="256"):
        Settings(api_key="x" * 257)
