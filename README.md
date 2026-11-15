# DriftLab

A Python package and local web application for **risk-aware statistical validation of LLM behavioral changes**. Compare a baseline with a candidate on identical prompts, repeat generations to observe variability, and inspect statistical evidence alongside practical margins.

## Install and run

Python 3.11+ is required. Node 18+ is needed only when building the dashboard from source.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
npm ci --prefix frontend
npm run build --prefix frontend
driftlab serve
```

Open **http://127.0.0.1:8000/app/**. Interactive REST documentation is at **http://127.0.0.1:8000/docs**. The dashboard, API, and SQLite store use the same local workspace. For live frontend development, run `npm run dev --prefix frontend` and open its `/app/` URL while the API is running.

The workspace starts empty. **Run a synthetic walkthrough** creates two actual persisted runs and a statistical comparison with an injected regression. Synthetic results are labeled throughout; failed requests never become fabricated evidence.

### Install the submission package

```bash
python scripts/build_release.py
pip install dist/driftlab-0.1.0-py3-none-any.whl
driftlab serve
```

The release builder includes the compiled dashboard in the wheel and source archive. A checkout is not required to use the resulting wheel. Build outputs are ignored by Git. The distribution name is local: this project has not been published to PyPI.

## Python API

```python
from driftlab import DriftLab

lab = DriftLab('./my-experiment')
try:
    baseline = lab.run(model='mock', repeats=5, seed=42)
    candidate = lab.run(model='mock', run_type='candidate', repeats=5,
                        seed=91, mock_profile='regression')
    evidence = lab.compare(baseline.run_id, candidate.run_id)
    print(evidence['recommendation'])
    print(evidence['verdicts'])
finally:
    lab.close()
```

For real inference, start Ollama and pull your chosen model. Replace `model='mock'` with its installed identifier. Supply validated tasks through `tasks=` or use `load_dataset` from `driftlab.datasets.loader`. The library accepts a custom adapter implementing `describe()` and `generate()`; see the abstract interface in `driftlab.adapters.base`.

Optional semantic scoring: `pip install -e '.[embeddings]'`. `embedding_similarity` may download model weights on first use; missing dependencies or scoring failures fail the run visibly. Text and JSON metrics work without embedding dependencies.

## Command line

```bash
driftlab run --model mock --type baseline --seed 42
driftlab run --model mock --type candidate --seed 91 --mock-profile regression
driftlab compare BASELINE_ID CANDIDATE_ID --format json --output evidence.json
driftlab compare BASELINE_ID CANDIDATE_ID --format markdown --output report.md
```

Use `--dataset tasks.json` or `--dataset tasks.jsonl`, `--metrics exact_match,json_validity`, `--repeats 5`, and `--temperature 0.7`. Invalid or missing datasets fail explicitly.

A JSON dataset is an array; JSONL uses one object per line:

```json
{"id":"sum_1","task_key":"sum_1","category":"arithmetic","risk_level":"medium","prompt":"Return only the integer: 2+2","expected_output":"4"}
```

Supported task fields include optional `system_prompt` and `output_spec` with `required_keys`. IDs and task keys must be unique. Every reference-based metric requires an `expected_output`. Both comparison runs must use identical task content and metric coverage. A single prompt is useful for functional testing but cannot satisfy the default statistical sample policy.

## What the analysis does

1. Generate repeated outputs for each task, recording raw output before scoring.
2. Compute per-prompt mean candidate-minus-baseline scores, with equal prompt weighting.
3. Estimate a BCa confidence interval across prompts and a two-sided within-prompt label-permutation p-value.
4. Apply Holm correction across the category × metric × risk hypotheses.
5. Compare effects with an estimated baseline-repeat noise floor and practical risk margins.
6. Report high-risk regression, meaningful drift, detected low impact, equivalence, insufficient data, or inconclusive evidence.

Confidence levels follow the policy: 95% low/medium, 99% high, 99.5% critical. Minimum prompts/repeats are enforced **per group**. Default margins are illustrative, configurable Python policy choices, not validated safety standards. An insignificant test is not proof of equivalence. A `block` recommendation is a review signal; DriftLab does not control deployments.

## Evidence and storage

The workspace contains `driftlab.db` and `data/runs/`. Each run has a raw JSONL file, a configuration/task manifest, a scored JSONL sidecar, and an error file if it fails. Dataset and model snapshot hashes preserve identity. Comparisons and full verdicts are saved in SQLite and downloadable as JSON or Markdown. Back up both the database and artifact directory; raw ingestion alone is not complete database recovery. Append-only file usage is not cryptographic tamper protection.

Background runs are local in-process jobs. Keep one server process running; after a restart, unfinished runs are marked failed and can be started again. The application is designed for a trusted local workspace and binds to loopback by default.

## Verification and submission

```bash
venv/bin/python -m pytest tests/
npm run build --prefix frontend
python scripts/build_release.py
```

- [Architecture and decisions](decisions.md)
- [Review demonstration and submission checklist](docs/SUBMISSION.md)
- [Real-model experiment protocol](docs/EXPERIMENTS.md)
- [Python example](examples/evaluate.py)
- [Real-model study runner](examples/local_model_study.py)

The bundled 32-prompt suite is an original **functional smoke test**, not a published benchmark. Synthetic experiments establish pipeline behavior, not real-model performance or generalizability. Claims covering multiple local model families and benchmark datasets require the real-model experiments described in the study protocol.
