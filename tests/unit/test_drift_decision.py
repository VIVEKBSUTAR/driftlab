"""
Unit tests for the DriftLab statistical decision hierarchy.
"""

import numpy as np
from driftlab.drift.decision import evaluate_drift, compare_runs_for_drift
from driftlab.risk.policy import RiskPolicyConfig, get_risk_policy


def test_rule1_insufficient_data():
    policy = RiskPolicyConfig(
        name="test_policy",
        risk_level="high",
        margin=0.05,
        alpha=0.01,
        min_prompts=15,
        min_repeats=5,
    )
    # n_prompts below minimum
    verdict = evaluate_drift(
        estimate=-0.1,
        ci_low=-0.15,
        ci_high=-0.05,
        p_adjusted=0.001,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=10,
        n_repeats=5,
    )
    assert verdict.status == "insufficient_data"

    # n_repeats below minimum
    verdict_rep = evaluate_drift(
        estimate=-0.1,
        ci_low=-0.15,
        ci_high=-0.05,
        p_adjusted=0.001,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=20,
        n_repeats=3,
    )
    assert verdict_rep.status == "insufficient_data"


def test_rule2_high_risk_regression():
    policy = RiskPolicyConfig(
        name="test_high",
        risk_level="high",
        margin=0.03,
        alpha=0.01,
        min_prompts=10,
        min_repeats=3,
        harmful_direction="negative",
    )
    # Significant, negative degradation beyond margin on high risk tier
    verdict = evaluate_drift(
        estimate=-0.06,
        ci_low=-0.09,
        ci_high=-0.035,
        p_adjusted=0.002,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=20,
        n_repeats=5,
    )
    assert verdict.status == "high_risk_regression"


def test_rule3_meaningful_drift():
    policy = RiskPolicyConfig(
        name="test_med",
        risk_level="medium",
        margin=0.05,
        alpha=0.05,
        min_prompts=10,
        min_repeats=3,
        harmful_direction="negative",
    )
    # Significant change beyond margin
    verdict = evaluate_drift(
        estimate=0.08,
        ci_low=0.055,
        ci_high=0.105,
        p_adjusted=0.01,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=15,
        n_repeats=3,
    )
    assert verdict.status == "meaningful_drift"


def test_rule4_statistically_detected_low_impact():
    policy = RiskPolicyConfig(
        name="test_low",
        risk_level="low",
        margin=0.05,
        alpha=0.05,
        min_prompts=10,
        min_repeats=3,
    )
    # Statistically significant (p < alpha and > noise_floor), but effect size <= margin
    verdict = evaluate_drift(
        estimate=0.03,
        ci_low=0.015,
        ci_high=0.045,
        p_adjusted=0.01,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=20,
        n_repeats=5,
    )
    assert verdict.status == "statistically_detected_low_impact"


def test_rule5_no_meaningful_drift():
    policy = RiskPolicyConfig(
        name="test_equiv",
        risk_level="medium",
        margin=0.05,
        alpha=0.05,
        min_prompts=10,
        min_repeats=3,
    )
    # Entire confidence interval lies within [-0.05, 0.05]
    verdict = evaluate_drift(
        estimate=0.005,
        ci_low=-0.02,
        ci_high=0.03,
        p_adjusted=0.35,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=25,
        n_repeats=5,
    )
    assert verdict.status == "no_meaningful_drift"


def test_rule6_insufficient_evidence():
    policy = RiskPolicyConfig(
        name="test_null",
        risk_level="medium",
        margin=0.05,
        alpha=0.05,
        min_prompts=10,
        min_repeats=3,
    )
    # Not significant (p > 0.05), but CI spans outside margin [-0.07, 0.06]
    verdict = evaluate_drift(
        estimate=0.02,
        ci_low=-0.07,
        ci_high=0.06,
        p_adjusted=0.20,
        noise_floor=0.01,
        risk_policy=policy,
        n_prompts=10,
        n_repeats=3,
    )
    assert verdict.status == "insufficient_evidence"
    assert "No sufficient evidence of meaningful drift under this design" in verdict.explanation


def test_compare_runs_for_drift():
    rng = np.random.default_rng(42)
    policy = get_risk_policy("medium")

    # Identical distributions across 10 prompts
    baseline_scores = {f"p_{i}": np.array([0.9, 0.95, 0.92]) for i in range(10)}
    candidate_scores = {f"p_{i}": np.array([0.91, 0.94, 0.93]) for i in range(10)}

    verdict = compare_runs_for_drift(
        baseline_scores=baseline_scores,
        candidate_scores=candidate_scores,
        category="knowledge",
        metric_id="exact_match",
        risk_policy=policy,
        rng=rng,
        noise_floor_val=0.02,
    )
    assert verdict.status in ("no_meaningful_drift", "insufficient_evidence")
