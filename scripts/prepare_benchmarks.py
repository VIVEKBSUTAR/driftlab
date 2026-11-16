"""Download and reproducibly sample original GSM8K and BoolQ releases.

Only prepared prompts and source metadata are produced. No model results are invented.
Downloaded datasets stay outside Git and retain their upstream licenses.
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import requests
from driftlab.datasets.loader import validate_tasks

GSM8K_REVISION = "3101c7d5072418e28b9008a6636bde82a006892c"
SOURCES = {
    "gsm8k": {
        "url": f"https://raw.githubusercontent.com/openai/grade-school-math/{GSM8K_REVISION}/grade_school_math/data/test.jsonl",
        "source": "https://github.com/openai/grade-school-math",
        "license": "MIT",
        "split": "test",
        "revision": GSM8K_REVISION,
    },
    "boolq": {
        "url": "https://storage.googleapis.com/boolq/dev.jsonl",
        "source": "https://github.com/google-research-datasets/boolean-questions",
        "license": "CC BY-SA 3.0",
        "split": "dev",
        "revision": "SHA-256 recorded at download",
    },
}


def convert(name, row, index):
    if name == "gsm8k":
        return dict(
            id=f"gsm8k_test_{index}",
            task_key=f"gsm8k_test_{index}",
            category="math_reasoning",
            risk_level="medium",
            prompt="Solve the problem. End your response with #### followed by the final numeric answer.\n\n"
            + row["question"],
            expected_output=row["answer"].rsplit("####", 1)[-1].strip(),
            output_spec={"answer_type": "numeric"},
        )
    return dict(
        id=f"boolq_dev_{index}",
        task_key=f"boolq_dev_{index}",
        category="reading_comprehension",
        risk_level="medium",
        prompt=f"Based only on the passage, answer the question. Begin your response with Yes or No.\n\nPassage: {row['passage']}\n\nQuestion: {row['question']}",
        expected_output="yes" if row["answer"] else "no",
        output_spec={"answer_type": "boolean"},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/benchmarks")
    args = parser.parse_args()
    if args.count < 10:
        parser.error("Use at least 10 prompts for the medium-risk sample policy.")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name, source in SOURCES.items():
        response = requests.get(source["url"], timeout=60)
        if name == "boolq" and response.status_code == 403:
            # The original public bucket can be unavailable; use Google's maintained mirror.
            info = requests.get("https://huggingface.co/api/datasets/google/boolq", timeout=30)
            info.raise_for_status()
            revision = info.json()["sha"]
            rows = []
            for offset in range(0, 3270, 100):
                page = requests.get(
                    "https://datasets-server.huggingface.co/rows",
                    params={
                        "dataset": "google/boolq",
                        "config": "default",
                        "split": "validation",
                        "offset": offset,
                        "length": 100,
                    },
                    timeout=60,
                )
                page.raise_for_status()
                rows.extend(item["row"] for item in page.json()["rows"])
            raw = ("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n").encode()
            source = {
                **source,
                "mirror": "https://huggingface.co/datasets/google/boolq",
                "revision": revision,
                "original_download_status": 403,
            }
        else:
            response.raise_for_status()
            raw = response.content
            rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
        indices = sorted(random.Random(args.seed).sample(range(len(rows)), args.count))
        tasks = [
            t.model_dump() for t in validate_tasks([convert(name, rows[i], i) for i in indices])
        ]
        prepared = "\n".join(json.dumps(t, ensure_ascii=False) for t in tasks) + "\n"
        (output / f"{name}.jsonl").write_text(prepared, encoding="utf-8")
        metadata = {
            **source,
            "dataset": name,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "prepared_sha256": hashlib.sha256(prepared.encode()).hexdigest(),
            "source_rows": len(rows),
            "sample_rows": len(tasks),
            "sample_indices": indices,
            "sampling_seed": args.seed,
            "transform": "DriftLab prepare_benchmarks.py v1: explicit answer instructions; medium task risk for experimental evaluation, not domain safety classification",
        }
        (output / f"{name}.source.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        print(f"Prepared {name}: {len(tasks)} prompts from {len(rows)} rows; {source['license']}")


if __name__ == "__main__":
    main()
