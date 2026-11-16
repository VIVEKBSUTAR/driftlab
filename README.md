# DriftLab

**Measure whether an LLM update changes the behavior your application depends on.**

DriftLab is a Python package, command-line tool, and web dashboard for repeatable, risk-aware LLM evaluation. It compares baseline and candidate outputs on the same tasks, separates sampling variability from behavioral change, and preserves the evidence behind each recommendation.

[Getting started](#getting-started) · [Deployment](docs/DEPLOYMENT.md) · [Operations](docs/OPERATIONS.md) · [API schema](docs/openapi.json) · [Validation](docs/VALIDATION.md) · [Security](SECURITY.md)

## Capabilities

- Run repeated evaluations through local Ollama models or a Python adapter.
- Score reference answers, numeric answers, structured JSON, text similarity, and optional semantic similarity.
- Compare prompt-level effects with bootstrap confidence intervals, permutation tests, Holm correction, and configurable risk margins.
- Queue jobs durably, resume interrupted generations, cancel work, and retain partial failure evidence.
- Inspect live API-backed metrics, individual outputs, model identities, token-limit warnings, and downloadable reports in the dashboard.
- Operate one authenticated workspace with secure browser sessions, bearer-token API access, explicit resource limits, health probes, and consistent backups.

The supported deployment is **one trusted team, one workspace, one host, one server process and one worker**, using local SQLite and local disk. Version 0.2.0 does not provide tenant isolation, per-user permissions, distributed workers, or a high-availability service. Read the [deployment boundaries](docs/DEPLOYMENT.md) before exposing it to a network.

## Getting started

Requirements: Python **3.11–3.14**, Node **22.22.2+, 24.15+, or 26.x** for building the dashboard, and npm. Ollama and downloaded model weights are needed only for real inference.

```bash
git clone https://github.com/VIVEKBSUTAR/driftlab.git
cd driftlab
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
npm ci --prefix frontend
npm run build --prefix frontend
driftlab serve
```

Open [the dashboard](http://127.0.0.1:8000/app/). Local mode binds to loopback and is intended for your own computer. The workspace starts empty. The synthetic walkthrough executes two real, persisted evaluation jobs with an injected regression; its outputs are visibly labeled synthetic. Request failures never produce fabricated metrics.

For frontend development, run `npm run dev --prefix frontend` alongside the API and open the Vite URL at `/app/`. The development proxy forwards `/api` to port 8000.

### Build an installable package

```bash
python scripts/build_release.py
python scripts/verify_release.py
pip install dist/driftlab-0.2.0-py3-none-any.whl
driftlab serve
```

The wheel includes the compiled dashboard and runs without a checkout or Node. The source archive includes development and deployment files. SHA-256 checksums are generated in `dist/SHA256SUMS`. The package has **not been published to PyPI**; use a locally built wheel or source checkout. Public publication requires ownership of the distribution name and a configured release publisher.

## Python API

```python
from driftlab import DriftLab

lab = DriftLab("./experiment")
try:
    baseline = lab.run(model="mock", repeats=5, seed=42)
    candidate = lab.run(
        model="mock", run_type="candidate", repeats=5,
        seed=91, mock_profile="regression",
    )
    evidence = lab.compare(baseline.run_id, candidate.run_id)
    print(evidence["recommendation"])
    print(evidence["verdicts"])
finally:
    lab.close()
```

`mock` explicitly selects synthetic inference. For a real model, pull it into Ollama and use its installed name, for example `model="qwen2.5:0.5b"`. Supply application-specific tasks through `tasks=` and an operator-controlled Ollama endpoint through `ollama_url=`. Custom integrations implement [`ModelAdapter`](src/driftlab/adapters/base.py), including a stable model identifier and digest.

The SDK and CLI are trusted local interfaces and execute runs synchronously. HTTP runs use the persistent background queue. The API server owns its workspace and inference endpoint; HTTP callers cannot supply database URLs or filesystem output paths.

Optional semantic scoring: install `.[embeddings]` and provision the required embedding model before going offline. Model loading or scoring failures fail the job visibly. Optional embedding dependencies are outside the minimal container runtime and its core dependency audit.

## CLI and datasets

```bash
driftlab run --model mock --type baseline --seed 42
driftlab run --model mock --type candidate --seed 91 --mock-profile regression
driftlab compare BASELINE_ID CANDIDATE_ID --format markdown --output report.md
```

Use `--dataset tasks.jsonl`, `--metrics answer_match,json_validity`, `--repeats 5`, and `--temperature 0.7` as appropriate. Run CLI experiments from the desired workspace directory. JSON datasets contain an array; JSONL contains one object per line:

```json
{"id":"sum_1","task_key":"sum_1","category":"arithmetic","risk_level":"medium","prompt":"Return only the integer: 2+2","expected_output":"4"}
```

Tasks support `system_prompt` and an `output_spec` with `required_keys` or `answer_type`. IDs, task keys, and prompt/system contexts must be unique. Reference metrics require `expected_output`. Comparisons require identical task content and complete metric coverage. A single prompt tests functionality but cannot satisfy the default statistical sample policy.

Prepared benchmark JSONL files in `data/benchmarks/` appear in the dashboard. See [models and data](docs/MODELS_AND_DATA.md) and [the experiment protocol](docs/EXPERIMENTS.md) for reproducible GSM8K and BoolQ samples. Respect upstream dataset and model licenses.

## Statistical interpretation

1. Generate multiple outputs per prompt and record each raw result before scoring.
2. Compute candidate-minus-baseline score changes with equal weighting across prompts.
3. Estimate a BCa bootstrap interval across prompts and a two-sided within-prompt label-permutation p-value.
4. Apply Holm correction across category × metric × risk hypotheses.
5. Assess statistical evidence against practical risk margins and estimated baseline-repeat variability.

Outcomes distinguish meaningful drift, high-risk regression, low-impact change, equivalence, insufficient data, and inconclusive evidence. Confidence levels default to 95% for low/medium, 99% for high, and 99.5% for critical risk. Minimum prompt and repeat counts apply to each group. Policies can be configured in [`deploy/policies.json`](deploy/policies.json); the effective configuration is saved with comparisons.

Default margins are illustrative choices, **not validated safety standards**. A nonsignificant result does not establish equivalence. A `block` recommendation is an input to human deployment review; DriftLab does not approve or control deployments. Independence assumptions, dataset coverage, grading validity, inference backend behavior, and sample size limit every conclusion.

## Deployment and evidence

For a network deployment, use the [Docker/TLS instructions](docs/DEPLOYMENT.md). Server mode requires a strong secret, secure cookies, explicit hosts and origins, persistent storage, and a private inference backend. The dashboard, API, database, and artifact downloads share the same workspace. List endpoints are bounded and paginated; the UI identifies recent history and partial output pages.

The workspace contains SQLite state and `data/runs/` manifests, raw JSONL outputs, score sidecars, and failure records. Completed evidence includes model digests, generation settings, independent generation seeds, dataset hashes, metric values, finish reasons, and available token counts. Treat prompts, outputs, backups, and reports as sensitive. Hashes support identity and corruption detection; they do not provide tamper-proof auditing.

Use `driftlab backup` and `driftlab restore` together with the [recovery runbook](docs/OPERATIONS.md). Back up before upgrading; schema upgrades are additive, and restoring a backup is the rollback path. Failed inference is not automatically retried; interrupted queued work resumes under the same identity and seed scheme.

## Verification and research status

```bash
venv/bin/python -m pytest tests/
venv/bin/ruff check src tests scripts examples
npm test --prefix frontend
npm run build --prefix frontend
python scripts/build_release.py
python scripts/verify_release.py
```

CI checks Python compatibility, frontend behavior, release installation, dependency advisories, and an authenticated container workflow. See [contributing](CONTRIBUTING.md) for locked installs and offline embedding tests.

The bundled 32-prompt suite is an original functional smoke test. The historical **v0.1** local pilot evaluated Qwen2.5 0.5B and SmolLM2 360M on GSM8K/BoolQ samples: six runs, 900 generations, and four comparisons. Three were inconclusive; one met its configured equivalence margin at low absolute accuracy. This demonstrates the evaluation path, not broad model equivalence, clinical/financial safety, or generalizability. Version 0.2 changes generation seed derivation; reproduce historical results with their recorded v0.1 revision. [Validation and limitations](docs/VALIDATION.md) contain the evidence.

## Project resources

- [Architecture and decisions](decisions.md)
- [Release notes and compatibility changes](CHANGELOG.md)
- [Submission and review guide](docs/SUBMISSION.md)
- [Security reporting](SECURITY.md)
- [License](LICENSE) — MIT; dependencies, datasets, and model weights retain their own licenses.
