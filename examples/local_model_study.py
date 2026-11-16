"""Run real-model controls and comparisons, persisting evidence incrementally.

python examples/local_model_study.py --models qwen2.5:0.5b smollm2:360m \
    --datasets data/benchmarks/gsm8k.jsonl data/benchmarks/boolq.jsonl --workspace .
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import requests
from driftlab import DriftLab
from driftlab.datasets.loader import load_dataset

parser = argparse.ArgumentParser()
parser.add_argument("--models", nargs="+", required=True)
parser.add_argument("--datasets", nargs="+", required=True)
parser.add_argument("--workspace", default="study-workspace")
parser.add_argument("--repeats", default=5, type=int)
parser.add_argument("--seed", default=42, type=int)
parser.add_argument("--temperature", default=0.7, type=float)
parser.add_argument("--max-tokens", default=128, type=int)
args = parser.parse_args()
lab = DriftLab(args.workspace)
results = []
output = Path(args.workspace) / "data" / "study"
output.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
result_file = output / f"study-{stamp}.json"
context = {
    "created_at": stamp,
    "platform": platform.platform(),
    "processor": platform.processor(),
    "python": platform.python_version(),
    "ollama": requests.get("http://localhost:11434/api/version", timeout=10).json(),
    "configuration": vars(args),
}


def record(dataset, kind, baseline, candidate):
    comparison = lab.compare(baseline.run_id, candidate.run_id)
    item = {"dataset": dataset, "kind": kind, "comparison": comparison}
    results.append(item)
    result_file.write_text(
        json.dumps({"context": context, "results": results}, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Saved {kind}: {comparison['id']} ({comparison['recommendation']})", flush=True)
    for verdict in comparison["verdicts"]:
        print(
            f"  {verdict['category']}: delta={verdict['estimate']:+.4f}, p_adj={verdict['p_adjusted']:.4g}, {verdict['status']}",
            flush=True,
        )


try:
    for dataset in args.datasets:
        tasks = load_dataset(dataset)
        options = dict(
            tasks=tasks,
            repeats=args.repeats,
            metrics=["answer_match"],
            generation={
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                "timeout_seconds": 120,
            },
        )
        print(f"Dataset {dataset}: {len(tasks)} prompts x {args.repeats} repeats", flush=True)
        print(f"Baseline: {args.models[0]}", flush=True)
        baseline = lab.run(model=args.models[0], seed=args.seed, **options)
        print(f"Baseline saved: {baseline.run_id}", flush=True)
        print("Independent same-model control", flush=True)
        control = lab.run(
            model=args.models[0], run_type="candidate", seed=args.seed + 1000, **options
        )
        record(dataset, "same_model_control", baseline, control)
        for model in args.models[1:]:
            print(f"Cross-family comparison: {model}", flush=True)
            candidate = lab.run(model=model, run_type="candidate", seed=args.seed + 2000, **options)
            record(dataset, "cross_model", baseline, candidate)
    print(f"Study evidence: {result_file}", flush=True)
finally:
    lab.close()
