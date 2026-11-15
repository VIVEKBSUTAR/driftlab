# DriftLab — project architecture and decisions

Last reviewed: 15 November 2026. This is the maintained reference for the current source code. Update it alongside changes to behavior, architecture, storage, statistical assumptions, setup, or the UI. The former `decision.md` now points here.

## Purpose and scope

DriftLab evaluates whether a candidate local language model behaves differently from a baseline on the same prompts. Candidate changes can include quantization, fine-tuning, prompts, generation settings, or model versions. It separates statistical evidence, practical effect size, and risk policy rather than treating every significant p-value as a deployment regression.

The application runs locally through a Python library, Typer CLI, FastAPI service, and React dashboard. It is an evaluation tool, not a model trainer, hosted inference provider, or automated deployment system. A `block` recommendation is evidence for a human or external gate; DriftLab itself does not block deployments.

## Technology stack

| Layer | Technology and responsibility |
| --- | --- |
| Language/runtime | Python >=3.11; TypeScript and React 18 |
| Backend | FastAPI, Pydantic 2 validation, Uvicorn ASGI server |
| Application service | `driftlab.client.DriftLab`, shared by library, API, and CLI |
| Inference | Requests-based Ollama adapter; seeded synthetic Mock adapter |
| Statistics | NumPy generators and arrays, SciPy bootstrap/permutation operations, statsmodels multiple-testing correction |
| Evaluation | Python text/JSON metrics; sentence-transformers for optional semantic scoring |
| Persistence | SQLAlchemy 2 with local SQLite; raw JSONL and JSON sidecars on disk |
| Frontend | React, Vite 5, TypeScript 5, Tailwind CSS 3, lucide-react icons |
| Visualization | Responsive SVG and CSS charts; no additional charting dependency |
| Packaging | setuptools / pyproject.toml; `driftlab` console entry point |
| Verification | pytest unit/calibration/integration tests; `tsc` plus Vite production build |

Python and frontend dependency ranges are declared in `pyproject.toml` and `frontend/package.json`; the npm lockfile captures the frontend resolution. The current frontend uses a system-font stack with numeric monospace styling.

## Code map and ownership of logic

- `config/schemas.py`: validated shared generation settings.
- `datasets/loader.py`: JSON/JSONL task loading, validation, original built-in functional suite.
- `adapters/`: unified `describe`/`generate` interface, Mock and Ollama implementations.
- `runner/core.py`: prompt/repeat execution, immediate raw logging, metric scoring, aggregation, database synchronization.
- `metrics/functions.py`: named scoring functions and registry.
- `stats/core.py`: numerical functions independent of HTTP and database layers.
- `risk/policy.py`: frozen risk policy defaults and lookup.
- `drift/decision.py`: statistical comparison of prompt scores and ordered verdict rules.
- `fingerprint/hashing.py`: content hashes for reproducible identities.
- `store/`: ORM models, sessions, append-only output and observation ingestion.
- `client.py`: run lifecycle, artifact manifests, compatibility checks, persisted comparison evidence.
- `api/main.py`: REST validation, local background execution, report downloads, dashboard serving.
- `cli/main.py`: run, compare, serve, and version commands using the same service.
- `reporting/`: terminal, Markdown, and JSON formatting helpers.
- `frontend/src/`: application navigation, typed API client, analytics, benchmark studio, run history, and comparisons.

## Backend pipeline

### 1. Validate and prepare

`DriftLab.prepare_run` accepts model, baseline/candidate role, repeats (1–100), registered metrics, tasks, generation settings, seed, and synthetic profile. Metrics must be nonempty, registered, and unique. Reference-dependent metrics require `expected_output` on every task.

Datasets accept a JSON array or JSONL objects. Tasks contain `id`, `task_key`, category, risk tier, prompt, optional system prompt, reference, and output specification. Task IDs and keys must be unique within a dataset. Task identity is content-derived when runs are prepared; dataset digests use sorted validated records. Changing prompt content or scoring context changes identity.

The bundled suite contains 32 original functional prompts: 12 medium-risk arithmetic prompts and 20 high-risk structured-output prompts. It exercises the pipeline; it is not a published benchmark, broad knowledge test, or safety certification.

Default generation settings: temperature 0.7, top_p 1.0, max_tokens 256, timeout 60 seconds. Supported fields also include seed and stop sequences. Pydantic rejects unknown fields and validates bounds.

For `mock`, the service uses reference outputs with seeded success probability 0.95 (`stable`) or 0.45 (`regression`). Other model names use Ollama at `http://localhost:11434`. Ollama metadata includes family, identifier, full digest, and quantization. The complete digest is retained for identity; display shortening must not change stored identity.

Preparation allocates a unique run ID, writes a manifest, stores/reuses model and dataset records, and creates a pending run. Existing output paths are rejected to preserve evidence.

### 2. Execute and record

Lifecycle: `pending → running → completed`, or `failed` on execution/scoring errors. Each prompt executes sequentially for the requested repeats. The runner derives repeat seeds as `seed_base + task_index * 1000 + repeat_index` and records the actual seed. External backends and hardware can still introduce nondeterminism.

For every generation, the runner writes raw output, task ID, repeat index, seed, latency, and errors to JSONL **before scoring**. It computes all selected metrics, rejects nonfinite scores, and appends a scored sidecar record. Prompt aggregates contain mean, sample standard deviation, and repeat count. Successful runs synchronize observations, individual metric results, and aggregates to SQLite.

Generation failures are recorded as observations and then stop the run. The service marks failure, ingests available raw evidence, and writes an error sidecar. No failed run is silently replaced with synthetic success. During API startup, pending/running records are marked failed because in-process background jobs cannot survive restarts.

### 3. Compare compatible runs

A comparison requires distinct, completed runs in baseline/candidate order. Both must have matching category/metric/risk groups and identical prompt content identities within each group. Empty scores, generation errors, and incompatible prompt/metric coverage are rejected.

For each category × metric × risk hypothesis:

1. Compute each prompt's mean candidate score minus mean baseline score. Average these differences with equal prompt weight.
2. Bootstrap the prompt differences using SciPy BCa intervals, at confidence `1 − policy.alpha`. Constant differences produce a point interval; nonfinite BCa results fall back to percentile bootstrap.
3. Obtain a two-sided permutation p-value by pooling and relabeling repeats **within each prompt**, preserving each run's repeat counts. The Monte Carlo correction is `(extreme + 1) / (permutations + 1)`.
4. Unless overridden, estimate the noise floor from the 95th percentile of absolute differences between two repeat-resampled baseline means, conditional on the observed prompts.
5. Apply Holm correction across all category/metric/risk hypotheses in this comparison and evaluate the final policy rules again with adjusted p-values.
6. Save the complete comparison, selected run records, verdicts, reproducibility settings, and recommendation.

Default service resampling counts are 2,000 bootstrap samples and 2,000 permutations; API bounds are 100–50,000. Default comparison seed is 42. The statistical utilities also expose Benjamini–Hochberg, power simulation, and an intentionally naive Mann–Whitney comparator; these are not the production decision path.

## Metrics and interpretation

| Metric | Definition | Scale |
| --- | --- | --- |
| exact_match | Strips surrounding whitespace and compares text case-insensitively by default | 0 or 1 |
| contains | Reference substring occurs in output, case-insensitive by default | 0 or 1 |
| sequence_similarity | Python difflib SequenceMatcher character ratio; not edit distance | 0 to 1 |
| json_validity | Parseable JSON, optional required top-level keys; accepts fenced JSON | 0 or 1 |
| embedding_similarity | Cosine similarity using cached all-MiniLM-L6-v2 embeddings | −1 to 1 |

Higher is better for these metrics under current policies. JSON validity does not prove semantic correctness or full JSON Schema compliance. Exact text matching can penalize correct paraphrases and alternate JSON formatting. Embedding scoring may need an initial model download and has materially different resource requirements from text metrics. It is deliberately not selected by default in the studio.

## Risk policies and verdict hierarchy

| Tier | Practical margin ±δ | Alpha | Confidence | Minimum prompts per group | Minimum repeats |
| --- | --- | --- | --- | --- | --- |
| Low | 0.08 | 0.05 | 95% | 5 | 3 |
| Medium | 0.05 | 0.05 | 95% | 10 | 3 |
| High | 0.03 | 0.01 | 99% | 20 | 5 |
| Critical | 0.015 | 0.005 | 99.5% | 30 | 5 |

Minimums apply within each comparison group, not to the total number of observations. The minimum repeat count across matched prompts is used. Defaults treat negative effects as harmful. Python policy lookup falls back to medium for unknown strings; validated datasets restrict tiers to the four known values.

The ordered rules are:

1. `insufficient_data`: group prompt or repeat count is below policy minimum.
2. `high_risk_regression`: high/critical tier, adjusted p < alpha, absolute effect > noise floor, harmful change beyond margin.
3. `meaningful_drift`: significance/noise conditions pass and absolute effect > margin.
4. `statistically_detected_low_impact`: significance/noise conditions pass but effect remains within margin.
5. `no_meaningful_drift`: entire interval lies within ±margin.
6. `insufficient_evidence`: all remaining cases.

Lack of statistical significance does not prove equivalence. A significant improvement can be meaningful drift without being harmful. Overall recommendation is `block` for high-risk regression, `review` for other unresolved/material verdicts, and `within_policy` when every verdict is equivalent or low-impact. Recommendations do not establish general deployment safety.

## Storage and recovery boundaries

Per-run artifacts under `data/runs/`:

- `<run_id>.manifest.json`: tasks, model metadata, dataset digest, generation configuration, metrics, seed, repeats, role, synthetic flag.
- `<run_id>.jsonl`: raw observations, append-only in the application path.
- `<run_id>.jsonl.scores.jsonl`: raw fields plus computed scores.
- `<run_id>.error.txt`: error detail when a run fails.

SQLite stores ModelSnapshot, DatasetVersion, Task, Run, Observation, MetricResult, PromptAggregate, StatisticalTest, DriftResult, and Comparison. Experiment and RiskPolicy tables exist as foundations; defaults currently come from Python policies, and no experiment/policy editing workflow is exposed by the active dashboard.

Raw JSONL is the output source of truth; relational rows support queries and comparisons. Writes flush after each observation but do not call `fsync`, so power-loss durability is not guaranteed. Append-only usage is not cryptographic tamper protection. The ingestion utility restores raw observations idempotently by run/task/repeat identity; it is not a complete database reconstruction tool for manifests, metrics, or comparisons. Back up SQLite and all sidecars together. No automated migration framework is present: `create_all` creates missing tables but does not migrate existing columns.

## API and execution model

| Endpoint | Responsibility |
| --- | --- |
| GET `/` | Health and version |
| GET `/catalog` | Tasks, metric registry, policy defaults, suite description |
| GET `/models` | Local Ollama availability and model list |
| GET `/runs` | Run metadata and progress from saved raw observations |
| POST `/runs` | Validate/prepare/execute a run; optional local background task |
| GET `/runs/{id}` | Model details, aggregates, observations, scores, failure details |
| POST `/compare` | Compute and persist evidence |
| GET `/comparisons` | Saved comparison history, newest first |
| GET `/comparisons/{id}` | Full saved comparison |
| GET `/comparisons/{id}/report` | Download Markdown evidence |

The same application routes are reachable under `/api`; OpenAPI/Swagger is at `/docs`. Errors map missing records to 404, validation failures to 422, unavailable evaluation dependencies/backends to 503, and unexpected failures to 500.

The service uses local FastAPI BackgroundTasks when requested; the active studio submits background runs and polls details. There is no durable worker queue, multi-worker coordination, cancellation, or resume support. Prefer one local server process. `DRIFTLAB_WORKSPACE`, `DRIFTLAB_DB_URL`, and `DRIFTLAB_FRONTEND` configure workspace, database, and frontend directory. Default binding is loopback. API allows local Vite origins; it has no authentication or multi-tenant authorization. Model outputs, prompts, and local paths are available to API clients, and database URLs can be supplied by API callers. Do not expose this local development service publicly without redesigning these boundaries.

## Frontend and visualization decisions

`App.tsx` controls six views without a routing dependency; the shared `BenchmarkMetrics` component in `components/dashboard/Overview.tsx` supplies the analytics panels:

- Overview: recorded run/model/observation/comparison counts, latest drift forest plot, synthetic walkthrough, recent run table, last 12 runs' observation volume, execution-status bars, completed-run quality selector, and mean/P95 latency.
- Drift analysis: completed baseline/candidate selection, dataset mismatch feedback, explicit analysis, recommendation banner, forest plot, reproducibility record, expandable verdict evidence, JSON/Markdown export, and saved comparison history. The active UI uses estimated baseline noise; manual overrides remain available through the API and the older unmounted CompareView.
- Run explorer: search, status filters, run details, output/reference inspection, per-repeat scores, latency, fingerprints, progress polling, and JSON export.
- Benchmark studio: discovered or custom Ollama model identifiers, synthetic stable/regression profiles, baseline/candidate role, JSON/JSONL dataset import or editing, registered metrics, repeat count, seed, temperature, sample-size preview, and background run submission.
- Datasets: searchable original functional prompts, references, risk tiers, and dataset download.
- Methodology: explanation of the inference pipeline, risk-policy table, interpretation limits, and local installation guidance.

The API client uses relative `/api` URLs and surfaces failures; it never substitutes fabricated runs, comparisons, or successful job IDs. The request layer supports `VITE_API_URL` or relative `/api`, uses a 180-second default timeout, and uses a 3-second health timeout. The active studio uses background submission and run-detail polling rather than holding a request open for all generations.

Charts use the existing dark theme, restrained status colors, numeric typography, visible units, legends, accessible descriptions, and explicit empty/loading/error states. The volume chart exposes an underlying data table and hover titles. Run-quality bars show each metric independently, including a zero marker and −1 to 1 scale for embedding similarity. Mean quality is an equal-weight average of prompt means; there is no combined score across unrelated metrics. Latency excludes failed observations, uses milliseconds, and P95 uses nearest rank. Mock latency measures synthetic execution rather than LLM inference performance. Synthetic runs are labeled.

Forest plots share a symmetric delta domain large enough for every interval, margin, estimate, and noise floor, with padding. They show green equivalence bands, gray noise bands, zero reference, interval caps, and point estimates without clipping. Confidence follows each risk tier rather than a universal 95% label. Analysis is explicitly requested so viewing the page does not create saved comparisons. Saved evidence identifies its own baseline and candidate IDs independently of the next comparison selection.

Older separate view components (`CompareView`, `RunStudio`, `RunsList`, `RunDetailModal`, `IntervalChart`, `VerdictCard`, `PromptDiffExplorer`, `PoliciesView`, and common widgets) remain in the source tree; App currently mounts its composed views and the shared BenchmarkMetrics component. Sample data in inactive prototype components is not current dashboard functionality. No historical quality trend, token-throughput, inference cost, live streaming, or deployment integration is claimed without supporting data and UI wiring.

## Local setup and workflows

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
npm ci --prefix frontend
npm run build --prefix frontend
driftlab serve
```

Open `http://127.0.0.1:8000/app/`. The API serves `frontend/dist` if available, otherwise packaged API static assets if present. Vite uses `/app/` as its base asset path. `python scripts/build_release.py` compiles the frontend, stages it under the API static package directory, and builds wheel/source artifacts under `dist/`. Direct Python-only builds do not run that frontend staging step; use the release script for distributable dashboard assets. The script includes README, license, docs, and examples. Install semantic scoring with `pip install -e '.[embeddings]'` when required; it is an optional extra.

For frontend development run the API and `npm run dev --prefix frontend` in separate terminals. Vite on port 5173 proxies `/api` to backend port 8000. `vite preview` alone does not provide that development API proxy; use FastAPI to verify the integrated production build.

```bash
driftlab run --model mock --type baseline --repeats 5
driftlab run --model mock --type candidate --repeats 5 --mock-profile regression
driftlab compare BASELINE_ID CANDIDATE_ID --format json
driftlab compare BASELINE_ID CANDIDATE_ID --format markdown --output report.md
pytest tests/
npm run build --prefix frontend
```

Use `--dataset path.jsonl` to supply real evaluation tasks, `--model` for an installed Ollama model, and `--seed`/`--temperature` for controlled settings. Python users can call `from driftlab import DriftLab`, create a workspace, run benchmarks, compare IDs, list records, and close the service. Keep the same dataset and metrics for both sides.

## Verification, limitations, and next work

Tests cover statistical calibration, drift rules, adapters, runner, storage, fingerprints, reporting, CLI/API, and persisted application-service workflows. Calibration is evidence about simulated conditions, not a guarantee for every deployment distribution. Seeded resampling enables repeatability with the same data and numerical stack; it does not guarantee identical output across different inference environments.

Important open work: durable background jobs, cancellation, and resume; full database/artifact recovery and migrations; model/version provenance including embedding model revisions; production authentication and resource limits; pagination for large run/observation histories; continuous integration and hosted deployment hardening. The built-in suite and selected metrics must be expanded and validated for any real application domain.

## Repository synchronization policy

Keep local source and GitHub synchronized after completed, verified changes. Include the user's existing project changes when they explicitly request all changes, inspect the diff, run relevant checks, commit with a descriptive message, and push the current branch to its configured GitHub remote. Never force-push or discard unrelated work. Report push/authentication failures accurately. Generated dependencies, build bundles, virtual environments, databases, and run artifacts remain ignored; source and lockfiles belong in Git. Keep this document current in the same commit as behavioral or architectural changes. `AGENTS.md` preserves this project instruction for future work.
