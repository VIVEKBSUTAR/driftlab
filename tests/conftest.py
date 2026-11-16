"""Isolated workspaces and explicit ASGI lifecycle for HTTP tests."""

import pytest
from fastapi.testclient import TestClient
from driftlab.api.main import create_app
from driftlab.config.settings import Settings


@pytest.fixture
def api(tmp_path):
    app = create_app(
        Settings(workspace=tmp_path, worker_enabled=False, allowed_hosts=["testserver"])
    )
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        yield client, app
