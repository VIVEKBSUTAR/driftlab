"""
Unit tests for driftlab.reporting formatters.
"""

from driftlab.drift.decision import DriftVerdict
from driftlab.reporting import (
    format_drift_table,
    format_drift_markdown_report,
    format_drift_json,
)


def sample_verdicts():
    return [
        DriftVerdict(
            status="high_risk_regression",
            category="safety",
            metric_id="toxicity",
            risk_level="high",
            estimate=-0.08,
            ci_low=-0.12,
            ci_high=-0.04,
            p_value=0.001,
            p_adjusted=0.001,
            noise_floor=0.01,
            margin=0.03,
            explanation="CRITICAL: Statistically significant regression on high-risk task.",
        ),
        DriftVerdict(
            status="no_meaningful_drift",
            category="reasoning",
            metric_id="exact_match",
            risk_level="medium",
            estimate=0.01,
            ci_low=-0.02,
            ci_high=0.03,
            p_value=0.45,
            p_adjusted=0.45,
            noise_floor=0.015,
            margin=0.05,
            explanation="Equivalence confirmed: CI lies within practical margin.",
        ),
    ]


def test_format_drift_table():
    verdicts = sample_verdicts()
    table = format_drift_table(verdicts)
    assert "| Category | Metric | Risk Tier |" in table
    assert "safety" in table
    assert "reasoning" in table
    assert "HIGH RISK REGRESSION" in table
    assert "NO MEANINGFUL DRIFT" in table


def test_format_drift_markdown_report():
    verdicts = sample_verdicts()
    report = format_drift_markdown_report(
        verdicts=verdicts,
        baseline_info={"identifier": "llama3:8b", "digest": "sha256:111"},
        candidate_info={"identifier": "llama3:8b-q4", "digest": "sha256:222"},
        experiment_name="Quantization Drift Audit",
    )
    assert "# DriftLab Report: Quantization Drift Audit" in report
    assert "llama3:8b" in report
    assert "llama3:8b-q4" in report
    assert "Detailed Explanations" in report


def test_format_drift_json():
    verdicts = sample_verdicts()
    json_str = format_drift_json(verdicts)
    assert '"status": "high_risk_regression"' in json_str
    assert '"category": "safety"' in json_str
