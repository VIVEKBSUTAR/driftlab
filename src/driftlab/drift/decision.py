"""
Drift decision engine for DriftLab.

Implements the formal decision hierarchy for determining behavioral drift:
1. insufficient data if prompt count or repeat count is below policy minimum
2. high risk regression if high risk tier, harmful direction, significant, and beyond margin
3. meaningful drift if significant and beyond margin
4. statistically detected but low practical impact if significant and below margin
5. no meaningful drift if confidence interval lies entirely inside margin
6. insufficient evidence otherwise (absence of significance is never proof of no drift)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
import numpy as np

from driftlab.risk.policy import RiskPolicyConfig, get_risk_policy
from driftlab.stats.core import bootstrap_ci, permutation_test, equivalence_check

DriftStatus = Literal[
    "insufficient_data",
    "high_risk_regression",
    "meaningful_drift",
    "statistically_detected_low_impact",
    "no_meaningful_drift",
    "insufficient_evidence",
]


@dataclass
class DriftVerdict:
    """Encapsulates the statistical evidence, risk thresholds, and final drift decision."""
    status: DriftStatus
    category: str
    metric_id: str
    risk_level: str
    estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    p_adjusted: float
    noise_floor: float
    margin: float
    explanation: str
    details: Dict[str, Any] = field(default_factory=dict)


def evaluate_drift(
    estimate: float,
    ci_low: float,
    ci_high: float,
    p_adjusted: float,
    noise_floor: float,
    risk_policy: RiskPolicyConfig,
    n_prompts: int,
    n_repeats: int,
    category: str = "general",
    metric_id: str = "score",
) -> DriftVerdict:
    """
    Applies the ordered DriftLab decision rules to produce a definitive drift verdict.
    """
    margin = risk_policy.margin
    alpha = risk_policy.alpha
    risk_level = risk_policy.risk_level.lower()

    # Rule 1: Insufficient data
    if n_prompts < risk_policy.min_prompts or n_repeats < risk_policy.min_repeats:
        return DriftVerdict(
            status="insufficient_data",
            category=category,
            metric_id=metric_id,
            risk_level=risk_level,
            estimate=estimate,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_adjusted,
            p_adjusted=p_adjusted,
            noise_floor=noise_floor,
            margin=margin,
            explanation=f"Insufficient sample size: {n_prompts} prompts (min {risk_policy.min_prompts}) or {n_repeats} repeats (min {risk_policy.min_repeats}).",
        )

    # Statistical significance requires p_adjusted < alpha and effect beyond natural noise floor
    is_significant = (p_adjusted < alpha) and (abs(estimate) > noise_floor)

    # Rule 2: High risk regression
    is_harmful = (
        (estimate < -margin) if risk_policy.harmful_direction == "negative"
        else (estimate > margin)
    )
    if risk_level in ("high", "critical") and is_significant and is_harmful:
        return DriftVerdict(
            status="high_risk_regression",
            category=category,
            metric_id=metric_id,
            risk_level=risk_level,
            estimate=estimate,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_adjusted,
            p_adjusted=p_adjusted,
            noise_floor=noise_floor,
            margin=margin,
            explanation=f"CRITICAL: Statistically significant regression of {estimate:.4f} beyond {margin:.4f} margin on {risk_level}-risk task.",
        )

    # Rule 3: Meaningful drift (significant and beyond practical margin)
    if is_significant and abs(estimate) > margin:
        return DriftVerdict(
            status="meaningful_drift",
            category=category,
            metric_id=metric_id,
            risk_level=risk_level,
            estimate=estimate,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_adjusted,
            p_adjusted=p_adjusted,
            noise_floor=noise_floor,
            margin=margin,
            explanation=f"Meaningful drift detected: effect size {estimate:.4f} exceeds practical margin {margin:.4f} (p_adj={p_adjusted:.4g}).",
        )

    # Rule 4: Statistically detected but low practical impact
    if is_significant and abs(estimate) <= margin:
        return DriftVerdict(
            status="statistically_detected_low_impact",
            category=category,
            metric_id=metric_id,
            risk_level=risk_level,
            estimate=estimate,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_adjusted,
            p_adjusted=p_adjusted,
            noise_floor=noise_floor,
            margin=margin,
            explanation=f"Statistical difference detected (p_adj={p_adjusted:.4g}) but effect size {estimate:.4f} is within acceptable practical margin {margin:.4f}.",
        )

    # Rule 5: No meaningful drift (entire confidence interval inside margin)
    if equivalence_check(ci_low, ci_high, margin):
        return DriftVerdict(
            status="no_meaningful_drift",
            category=category,
            metric_id=metric_id,
            risk_level=risk_level,
            estimate=estimate,
            ci_low=ci_low,
            ci_high=ci_high,
            p_value=p_adjusted,
            p_adjusted=p_adjusted,
            noise_floor=noise_floor,
            margin=margin,
            explanation=f"Equivalence confirmed: complete confidence interval [{ci_low:.4f}, {ci_high:.4f}] lies within practical margin ±{margin:.4f}.",
        )

    # Rule 6: Insufficient evidence
    return DriftVerdict(
        status="insufficient_evidence",
        category=category,
        metric_id=metric_id,
        risk_level=risk_level,
        estimate=estimate,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_adjusted,
        p_adjusted=p_adjusted,
        noise_floor=noise_floor,
        margin=margin,
        explanation="No sufficient evidence of meaningful drift under this design.",
    )


def compare_runs_for_drift(
    baseline_scores: Dict[str, np.ndarray],
    candidate_scores: Dict[str, np.ndarray],
    category: str,
    metric_id: str,
    risk_policy: RiskPolicyConfig,
    rng: np.random.Generator,
    noise_floor_val: float = 0.0,
    n_resamples: int = 1000,
    n_permutations: int = 1000,
) -> DriftVerdict:
    """
    Computes statistical tests and evaluates drift decision between baseline and candidate scores.
    Scores dict maps prompt_id -> 1D numpy array of repeat values.
    """
    common_prompts = sorted(set(baseline_scores.keys()).intersection(candidate_scores.keys()))
    n_prompts = len(common_prompts)
    
    # Calculate repeats count
    n_repeats = min(len(baseline_scores[p]) for p in common_prompts) if common_prompts else 0

    if n_prompts == 0:
        return evaluate_drift(
            estimate=0.0,
            ci_low=0.0,
            ci_high=0.0,
            p_adjusted=1.0,
            noise_floor=noise_floor_val,
            risk_policy=risk_policy,
            n_prompts=0,
            n_repeats=0,
            category=category,
            metric_id=metric_id,
        )

    # Compute per-prompt mean differences (candidate - baseline)
    prompt_diffs = np.array([
        np.mean(candidate_scores[p]) - np.mean(baseline_scores[p])
        for p in common_prompts
    ], dtype=float)

    # Bootstrap confidence interval on clustered differences
    est, ci_low, ci_high = bootstrap_ci(
        differences=prompt_diffs,
        n_resamples=n_resamples,
        rng=rng,
        alpha=risk_policy.alpha,
    )

    # Permutation test
    filtered_base = {p: baseline_scores[p] for p in common_prompts}
    filtered_cand = {p: candidate_scores[p] for p in common_prompts}
    p_val = permutation_test(
        baseline=filtered_base,
        candidate=filtered_cand,
        n_permutations=n_permutations,
        rng=rng,
    )

    return evaluate_drift(
        estimate=est,
        ci_low=ci_low,
        ci_high=ci_high,
        p_adjusted=p_val,
        noise_floor=noise_floor_val,
        risk_policy=risk_policy,
        n_prompts=n_prompts,
        n_repeats=n_repeats,
        category=category,
        metric_id=metric_id,
    )
