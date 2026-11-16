"""Exercise an authenticated deployed API without external inference or test dependencies."""

import json
import os
import time
import urllib.request

base = os.environ.get("DRIFTLAB_TEST_URL", "http://127.0.0.1:8000")
key = os.environ["DRIFTLAB_API_KEY"]


def call(path, body=None):
    request = urllib.request.Request(
        base + "/api" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait(run_id):
    for _ in range(120):
        run = call("/runs/" + run_id)
        if run["status"] == "completed":
            return
        if run["status"] in ("failed", "cancelled"):
            raise RuntimeError(run.get("error") or run["status"])
        time.sleep(0.5)
    raise RuntimeError("Container job did not complete")


for _ in range(60):
    try:
        call("/readyz")
        break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError("Container did not become ready")
b = call("/runs", {"repeats": 5, "seed": 42})["run_id"]
c = call(
    "/runs", {"run_type": "candidate", "repeats": 5, "seed": 91, "mock_profile": "regression"}
)["run_id"]
wait(b)
wait(c)
comparison = call("/compare", {"baseline_run_id": b, "candidate_run_id": c})
assert comparison["recommendation"] == "block", comparison
assert call("/workspace")["runs"] == 2
assert len(call("/runs/" + b)["observations"]) == 160
with urllib.request.urlopen(base + "/app/", timeout=5) as response:
    assert response.status == 200
print(
    "PASS: authenticated container, persistent queue, 320 generations, comparison, and packaged dashboard"
)
