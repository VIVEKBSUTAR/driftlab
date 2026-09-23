"""
Unit tests for the DriftLab Typer CLI.
"""

from pathlib import Path
from typer.testing import CliRunner
from driftlab.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "DriftLab v0.1.0" in result.stdout


def test_cli_run_and_compare(tmp_path: Path):
    db_file = tmp_path / "cli_test.db"
    db_url = f"sqlite:///{db_file}"

    # 1. Run baseline
    res_base = runner.invoke(app, [
        "run",
        "--model", "mock",
        "--type", "baseline",
        "--repeats", "2",
        "--db-url", db_url,
    ])
    assert res_base.exit_code == 0
    assert "Run completed successfully" in res_base.stdout

    # Extract baseline run ID
    base_line = [l for l in res_base.stdout.split("\n") if "Run ID:" in l][0]
    base_run_id = base_line.split("Run ID:")[1].strip()

    # 2. Run candidate
    res_cand = runner.invoke(app, [
        "run",
        "--model", "mock",
        "--type", "candidate",
        "--repeats", "2",
        "--db-url", db_url,
    ])
    assert res_cand.exit_code == 0
    cand_line = [l for l in res_cand.stdout.split("\n") if "Run ID:" in l][0]
    cand_run_id = cand_line.split("Run ID:")[1].strip()

    # 3. Compare runs
    res_comp = runner.invoke(app, [
        "compare",
        base_run_id,
        cand_run_id,
        "--db-url", db_url,
        "--format", "table",
    ])
    assert res_comp.exit_code == 0
    assert "| Category | Metric | Risk Tier |" in res_comp.stdout
