"""Run preselected model/dataset comparisons; never substitute synthetic evidence.

python examples/local_model_study.py --models MODEL_A MODEL_B --datasets data/a.jsonl data/b.jsonl
First install and run Ollama, then pull the exact model identifiers you intend to study.
"""
import argparse
import json
from pathlib import Path
from driftlab import DriftLab
from driftlab.datasets.loader import load_dataset

parser = argparse.ArgumentParser()
parser.add_argument("--models", nargs="+", required=True)
parser.add_argument("--datasets", nargs="+", required=True)
parser.add_argument("--workspace", default="study-workspace")
parser.add_argument("--repeats", default=5, type=int)
args = parser.parse_args()
lab = DriftLab(args.workspace)
results = []
try:
    for dataset in args.datasets:
        tasks = load_dataset(dataset)
        baseline = lab.run(model=args.models[0], tasks=tasks, repeats=args.repeats, seed=42)
        # Independent same-model control; new seed, same configuration and task set.
        control = lab.run(model=args.models[0], run_type="candidate", tasks=tasks, repeats=args.repeats, seed=1042)
        results.append({"dataset":dataset,"kind":"same_model_control","comparison":lab.compare(baseline.run_id,control.run_id)})
        for model in args.models[1:]:
            candidate = lab.run(model=model, run_type="candidate", tasks=tasks, repeats=args.repeats, seed=2042)
            results.append({"dataset":dataset,"kind":"cross_model","comparison":lab.compare(baseline.run_id,candidate.run_id)})
    Path(args.workspace, "study-results.json").write_text(json.dumps(results, indent=2, allow_nan=False))
finally:
    lab.close()
