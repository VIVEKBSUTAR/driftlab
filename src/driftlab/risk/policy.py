"""
Risk tier definitions, practical margins, and policy specifications for DriftLab.
"""

from dataclasses import dataclass
from typing import Dict, Literal

RiskTier = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class RiskPolicyConfig:
    """Configurable risk thresholds and margins for statistical drift evaluation."""
    name: str
    risk_level: RiskTier
    margin: float
    alpha: float = 0.05
    min_prompts: int = 10
    min_repeats: int = 3
    # Direction in which a change represents a quality degradation ('negative' for score/accuracy, 'positive' for error)
    harmful_direction: Literal["negative", "positive"] = "negative"


DEFAULT_POLICIES: Dict[str, RiskPolicyConfig] = {
    "low": RiskPolicyConfig(
        name="low_risk_default",
        risk_level="low",
        margin=0.08,
        alpha=0.05,
        min_prompts=5,
        min_repeats=3,
        harmful_direction="negative",
    ),
    "medium": RiskPolicyConfig(
        name="medium_risk_default",
        risk_level="medium",
        margin=0.05,
        alpha=0.05,
        min_prompts=10,
        min_repeats=3,
        harmful_direction="negative",
    ),
    "high": RiskPolicyConfig(
        name="high_risk_default",
        risk_level="high",
        margin=0.03,
        alpha=0.01,
        min_prompts=20,
        min_repeats=5,
        harmful_direction="negative",
    ),
    "critical": RiskPolicyConfig(
        name="critical_risk_default",
        risk_level="critical",
        margin=0.015,
        alpha=0.005,
        min_prompts=30,
        min_repeats=5,
        harmful_direction="negative",
    ),
}


def get_risk_policy(risk_level: str) -> RiskPolicyConfig:
    """Retrieves standard risk policy for a given risk level, falling back to medium."""
    level = risk_level.lower()
    return DEFAULT_POLICIES.get(level, DEFAULT_POLICIES["medium"])
