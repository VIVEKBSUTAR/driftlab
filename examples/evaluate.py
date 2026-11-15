"""A self-contained, persisted experiment using the installed public package."""
import json
from driftlab import DriftLab

lab = DriftLab("./example-workspace")
try:
    baseline = lab.run(model="mock", run_type="baseline", repeats=5, seed=42)
    candidate = lab.run(model="mock", run_type="candidate", repeats=5,
                        seed=91, mock_profile="regression")
    result = lab.compare(baseline.run_id, candidate.run_id)
    print(json.dumps(result, indent=2, allow_nan=False))
finally:
    lab.close()
