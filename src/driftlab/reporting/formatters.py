"""
Reporting formatters for DriftLab evaluation and drift analysis.
Generates Markdown, JSON, and terminal-friendly tables.
"""

import json
from typing import Any, Dict, List, Optional
from driftlab.drift.decision import DriftVerdict


STATUS_BADGES = {
    "high_risk_regression": "🚨 HIGH RISK REGRESSION",
    "meaningful_drift": "⚠️ MEANINGFUL DRIFT",
    "statistically_detected_low_impact": "ℹ️ DETECTED (LOW IMPACT)",
    "no_meaningful_drift": "✅ NO MEANINGFUL DRIFT",
    "insufficient_evidence": "⚖️ INSUFFICIENT EVIDENCE",
    "insufficient_data": "⏳ INSUFFICIENT DATA",
}


def format_drift_table(verdicts: List[DriftVerdict]) -> str:
    """Formats a list of drift verdicts into a markdown table."""
    lines = [
        "| Category | Metric | Risk Tier | Estimate | 95% CI | Noise Floor | Margin | p-adj | Status |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for v in verdicts:
        badge = STATUS_BADGES.get(v.status, v.status.upper())
        ci_str = f"[{v.ci_low:+.3f}, {v.ci_high:+.3f}]"
        lines.append(
            f"| {v.category} | {v.metric_id} | {v.risk_level} | {v.estimate:+.4f} | {ci_str} | {v.noise_floor:.4f} | ±{v.margin:.4f} | {v.p_adjusted:.4f} | {badge} |"
        )
    return "\n".join(lines)


def format_drift_markdown_report(
    verdicts: List[DriftVerdict],
    baseline_info: Optional[Dict[str, Any]] = None,
    candidate_info: Optional[Dict[str, Any]] = None,
    experiment_name: str = "DriftLab Analysis",
) -> str:
    """Generates a complete executive and technical report in GitHub Flavored Markdown."""
    lines = [
        f"# DriftLab Report: {experiment_name}",
        "",
        "## Summary of Findings",
        "",
    ]

    # Counts
    counts: Dict[str, int] = {}
    for v in verdicts:
        counts[v.status] = counts.get(v.status, 0) + 1

    for status, count in counts.items():
        badge = STATUS_BADGES.get(status, status)
        lines.append(f"- **{badge}**: {count}")
    lines.append("")

    if baseline_info or candidate_info:
        lines.append("## Evaluation Context")
        if baseline_info:
            lines.append(f"- **Baseline**: `{baseline_info.get('identifier', 'N/A')}` (digest: `{baseline_info.get('digest', 'N/A')}`)")
        if candidate_info:
            lines.append(f"- **Candidate**: `{candidate_info.get('identifier', 'N/A')}` (digest: `{candidate_info.get('digest', 'N/A')}`)")
        lines.append("")

    lines.append("## Statistical Tests & Equivalence Checks")
    lines.append("")
    lines.append(format_drift_table(verdicts))
    lines.append("")

    lines.append("## Detailed Explanations")
    lines.append("")
    for v in verdicts:
        badge = STATUS_BADGES.get(v.status, v.status)
        lines.append(f"### `{v.category}` - `{v.metric_id}`: {badge}")
        lines.append(f"- **Decision**: {v.explanation}")
        lines.append(f"- **Point Estimate**: {v.estimate:+.4f}")
        lines.append(f"- **Confidence Interval**: [{v.ci_low:+.4f}, {v.ci_high:+.4f}]")
        lines.append(f"- **Adjusted p-value**: {v.p_adjusted:.4g} (alpha={v.details.get('alpha', 'default')})")
        lines.append(f"- **Equivalence Margin**: ±{v.margin:.4f}")
        lines.append(f"- **Noise Floor**: {v.noise_floor:.4f}")
        lines.append("")

    return "\n".join(lines)


def format_drift_json(verdicts: List[DriftVerdict]) -> str:
    """Serializes verdicts into an indented JSON string."""
    data = []
    for v in verdicts:
        data.append({
            "category": v.category,
            "metric_id": v.metric_id,
            "risk_level": v.risk_level,
            "status": v.status,
            "estimate": v.estimate,
            "ci_low": v.ci_low,
            "ci_high": v.ci_high,
            "p_value": v.p_value,
            "p_adjusted": v.p_adjusted,
            "noise_floor": v.noise_floor,
            "margin": v.margin,
            "explanation": v.explanation,
        })
    return json.dumps(data, indent=2)
