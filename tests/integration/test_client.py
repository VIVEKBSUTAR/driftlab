"""Exercise saved evidence through the shared application service."""
import pytest
from driftlab import DriftLab


def test_persisted_runs_and_comparison(tmp_path):
    lab = DriftLab(tmp_path)
    try:
        baseline = lab.run(model="mock", repeats=5)
        candidate = lab.run(model="mock", run_type="candidate", repeats=5, mock_profile="regression")
        detail = lab.get_run(baseline.run_id)
        assert detail["status"] == "completed"
        assert detail["synthetic"] is True
        assert len(detail["observations"]) == 160
        assert len(detail["aggregates"]) == 64
        assert all(o["scores"] for o in detail["observations"])
        result = lab.compare(baseline.run_id, candidate.run_id, n_resamples=100, n_permutations=100)
        assert len(result["verdicts"]) == 4
        assert result["config"]["correction"] == "Holm"
        assert all(v["details"]["noise_source"] == "baseline repeat bootstrap" for v in result["verdicts"])
        assert lab.get_comparison(result["id"]) == result
        assert lab.list_comparisons()[0] == result
        with pytest.raises(ValueError, match="different runs"):
            lab.compare(baseline.run_id, baseline.run_id)
    finally:
        lab.close()


def test_failed_generation_remains_real_failure(tmp_path):
    class BrokenAdapter:
        def describe(self):
            return {"family": "test", "identifier": "broken", "digest": "test"}

        def generate(self, **kwargs):
            raise RuntimeError("inference failed")

    lab = DriftLab(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="inference failed"):
            lab.run(model="broken", adapter=BrokenAdapter())
        record = lab.list_runs()[0]
        assert record["status"] == "failed"
        assert record["observations_count"] == 1
        assert "inference failed" in record["error"]
        with pytest.raises(LookupError):
            lab.get_comparison("missing")
    finally:
        lab.close()
