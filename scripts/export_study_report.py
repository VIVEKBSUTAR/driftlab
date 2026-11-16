"""Export a reviewable Markdown summary of an actual completed local study."""

import argparse
import json
from pathlib import Path
from driftlab import DriftLab

parser = argparse.ArgumentParser()
parser.add_argument("study_file", type=Path)
parser.add_argument("--workspace", default=".")
parser.add_argument("--output", type=Path, default=Path("dist/study-report.md"))
args = parser.parse_args()
study = json.loads(args.study_file.read_text())
lab = DriftLab(args.workspace)
lines = [
    "# DriftLab real-model validation",
    "",
    "This is a small exploratory study, not a full benchmark leaderboard or a safety certification.",
    "",
    "## Recorded environment",
    "",
    "```json",
    json.dumps(study["context"], indent=2),
    "```",
    "",
    "## Results",
    "",
    "Each condition evaluates 30 distinct prompts with five repeats unless the configuration above specifies otherwise. Scores are extracted-answer agreement. Confidence intervals are at the medium-risk policy's 95% level. Holm correction applies within each comparison; exploratory comparisons across the whole study are not jointly corrected.",
    "",
    "| Dataset | Condition | Baseline score | Candidate score | Effect | Confidence interval | Adjusted p | Verdict |",
    "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
]
try:
    for item in study["results"]:
        comparison = item["comparison"]

        def score(run_id):
            aggregates = lab.get_run(run_id)["aggregates"]
            return sum(a["mean_value"] for a in aggregates) / len(aggregates)

        for v in comparison["verdicts"]:
            lines.append(
                f"| {Path(item['dataset']).stem} | {item['kind']} | {score(comparison['baseline_run_id']):.3f} | {score(comparison['candidate_run_id']):.3f} | {v['estimate']:+.3f} | [{v['ci_low']:+.3f}, {v['ci_high']:+.3f}] | {v['p_adjusted']:.4g} | {v['status']} |"
            )
    lines += ["", "## Evidence identifiers", ""]
    for item in study["results"]:
        c = item["comparison"]
        lines.append(
            f"- {Path(item['dataset']).stem} / {item['kind']}: comparison `{c['id']}`, baseline `{c['baseline_run_id']}`, candidate `{c['candidate_run_id']}`."
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "Two small model families and 30-prompt samples exercise the model-agnostic pipeline but do not establish broad generalizability. Medium risk and its 0.05 margin are illustrative choices. Cross-family differences do not isolate a version-update effect. The 128-token cap can truncate mathematical explanations; answer extraction does not evaluate explanation correctness. Same-model controls use independent seeds but only a small number of conditions, which is insufficient to estimate a reliable empirical false positive rate. Inconclusive findings remain inconclusive.",
        "",
        "Keep the full JSON study file, raw run outputs, scored sidecars, manifests, prepared dataset/source files, and SQLite database together for reproducibility. Dataset attribution and preparation are documented in docs/MODELS_AND_DATA.md.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output.resolve())
finally:
    lab.close()
