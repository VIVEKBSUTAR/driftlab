# DriftLab Architecture and Decisions

## Project Overview
DriftLab is a statistical framework for behavioral drift detection and validation in local LLMs. It determines if a candidate LLM state has meaningfully drifted from a baseline, distinguishing true drift from natural run-to-run variability.

## Architectural Principles
1. **Separation of Concerns**: Core statistics, drift decisions, and risk logic live in a plain Python package (`driftlab.stats`, `driftlab.drift`, `driftlab.risk`). They have zero dependencies on web frameworks (FastAPI) or databases (SQLAlchemy).
2. **Deterministic Stochasticity**: Every statistical function must be pure and take a `numpy.random.Generator` explicitly to guarantee testability.
3. **Data Source of Truth**: Raw model outputs are written to an append-only JSONL file per run before touching the database. The SQLite database is derived from this JSONL file, ensuring reproducibility and tamper-evident observation storage.
4. **No Premature Complexity**: No Redis, Celery, RabbitMQ, or microservices. Background runs are local processes tracked in SQLite.

## Current Development State
- **Phase 0 & 1 Completed**: Folder structure, dependencies (`pyproject.toml`), and skeletons for all 13 modules initialized.
- **Phase 2 Completed**: Core statistics engine (`driftlab.stats`) implemented and calibrated for false positive rates and nominal coverage.
- **Phase 3 Completed**: Model Adapters (`MockAdapter` and `OllamaAdapter`) implemented with unit tests.
- **Phase 4 Completed**: Database schemas (SQLAlchemy/SQLite) and JSONL append-only persistence implemented and tested.
- **Phase 5 Completed**: Runner orchestration with repeat sampling and pure evaluation metrics (`exact_match`, `embedding_similarity`, `json_validity`, `sequence_similarity`).
- **Phase 6 Completed**: Fingerprinting (`driftlab.fingerprint`), Reporting formatters (`driftlab.reporting`), CLI (`driftlab.cli`), and API wrappers (`driftlab.api`).
- **Phase 7 Completed**: Drift decision engine rules (`driftlab.drift`) and Risk policies (`driftlab.risk`) implemented adhering to the 6-level ordered decision hierarchy.
- **Phase 8 Completed**: Interactive Frontend Dashboard (`frontend/`) built with React, TypeScript, Vite, and Tailwind CSS. Fully integrated with the FastAPI backend.

## Module Connectivity
- **`driftlab.config`**: Validates configuration schemas across tasks, experiments, and policies.
- **`driftlab.datasets`**: Loads, validates, and hashes prompt datasets.
- **`driftlab.adapters`**: Interacts with LLM backends (Mock, Ollama) via unified interface.
- **`driftlab.runner`**: Executes prompts against adapters, logs raw outputs to JSONL (`driftlab.store.jsonl`), and triggers metric calculations.
- **`driftlab.metrics`**: Pure functions computing numerical differences/scores from model outputs.
- **`driftlab.store`**:
  - `jsonl.py`: Append-only raw output recorder (source of truth).
  - `models.py`: SQLAlchemy ORM definitions for experiment tracking, runs, tasks, observations, metric results, statistical tests, risk policies, and drift results.
  - `db.py`: Engine, session factories, and ingestion utilities mapping JSONL to SQLite.
- **`driftlab.stats`**: Pure functions for hypothesis testing, noise floor calculation, and multiple testing adjustments.
- **`driftlab.risk`**: Defines risk tiers, policy thresholds, and practical margins.
- **`driftlab.drift`**: Combines stats and risk policy to produce actionable drift verdicts.
- **`driftlab.fingerprint`**: Produces cryptographic digests of models and datasets.
- **`driftlab.reporting`**: Formats summaries into tables, markdown, or JSON.
- **`driftlab.api` & `driftlab.cli`**: Thin wrappers invoking runner, drift analysis, and querying store.
- **`frontend/`**: Single-Page React Application serving the interactive dashboard. Consumes the REST API to visualize confidence interval plots, risk badges, run comparisons, and benchmark execution.

## Feature Log & Reasoning
### Phase 1: Module Skeletons
- **Feature**: Initialized package layout and module skeletons.
- **Reasoning**: Enforces strict boundary separation from day one. Keeps domain logic independent from infrastructure.

### Phase 2: Statistics Engine
- **Feature**: Pure statistical functions (`bootstrap_ci`, `permutation_test`, `naive_mannwhitney_comparator`, `equivalence_check`, `noise_floor`, `holm_correction`, `benjamini_hochberg`, `simulate_power`) and calibration tests.
- **Reasoning**: Ensures all statistical evaluation is cluster-aware (clustered by prompt), reproducible, and calibrated to avoid false positives.

### Phase 3: Model Adapters
- **Feature**: `ModelAdapter` base class, `OllamaAdapter`, and distribution-sampling `MockAdapter`.
- **Reasoning**: Enables deterministic, GPU-less end-to-end testing and CI/CD while isolating external LLM HTTP APIs.

### Phase 4: Database Schemas and JSONL Persistence
- **Feature**: SQLAlchemy ORM models (`Experiment`, `ModelSnapshot`, `DatasetVersion`, `Task`, `Run`, `Observation`, `MetricResult`, `PromptAggregate`, `StatisticalTest`, `RiskPolicy`, `DriftResult`) and append-only JSONL logging.
- **Reasoning**: Per specification, the database is derived; the append-only JSONL file is the immutable source of truth for all raw observations. SQLite provides local, zero-config relational queries without operational overhead.

### Phase 5: Runner and Metrics Engine
- **Feature**: Task execution orchestration (`driftlab.runner.core`) with repeat sampling, JSONL append-only persistence, and pluggable metrics calculation (`driftlab.metrics.functions`).
- **Reasoning**: Prompts are the primary unit of analysis; repeats estimate within-prompt noise. Writing each output immediately to JSONL ensures resilience against process interruption. Metric calculation is kept functionally pure to decouple scoring from execution and statistics.

### Phase 6: Fingerprinting, Reporting, CLI & API Wrappers
- **Feature**: Cryptographic hashing (`driftlab.fingerprint`), rich report formatters in Markdown/JSON (`driftlab.reporting`), Typer CLI commands (`driftlab.cli`), and FastAPI endpoints (`driftlab.api`).
- **Reasoning**: Provides reproducible asset versioning and clean user interfaces as thin callers over the decoupled core engine.

### Phase 7: Drift Decision Rules and Risk Policies
- **Feature**: Ordered decision hierarchy (`evaluate_drift` and `compare_runs_for_drift`) with configurable risk policies (`RiskPolicyConfig` across low, medium, high, and critical risk tiers).
- **Reasoning**: Ensures that differences are not blindly labeled as drift. Adheres strictly to the 6 ordered rules:
  1. Insufficient data if prompt/repeat count below minimum.
  2. High-risk regression if high/critical tier, harmful direction, statistically significant, and beyond margin.
  3. Meaningful drift if significant and beyond practical margin.
  4. Statistically detected but low practical impact if significant and within margin.
  5. No meaningful drift if entire confidence interval lies inside margin.
  6. Insufficient evidence otherwise (absence of statistical significance is never reported as proof of no drift).

### Phase 8: Interactive Frontend Dashboard
- **Feature**: React, TypeScript, Vite, and Tailwind CSS SPA with visual confidence interval and equivalence corridor plots, run explorer, benchmark studio, and risk tier inspectors.
- **Reasoning**: Gives AI engineers an intuitive visual tool to inspect complex statistical metrics (BCa bootstrap CI, permutation p-values, equivalence margins) without reading raw terminal numbers. Connected directly via REST API with complete fallback resilience.

### Phase 9: Enterprise Obsidian Telemetry Redesign via Stitch MCP
- **Feature**: Complete frontend redesign using Stitch MCP server (`Obsidian Telemetry` design system). Replaced rounded generic cards and neon gradients with high-density, technical, disciplined layout:
  - Deep obsidian base surfaces (`#0a0e16` / `#0f131c`), 1px borders (`#1e293b`), and surgical status accents (Emerald `#10b981`, Indigo `#6366f1`, Violet `#a855f7`).
  - Strict typographic system using `Geist` for headers and `JetBrains Mono` for all numbers, tables, p-values, CI intervals, and model hashes. Tabular figure alignment enforced (`font-variant-numeric: tabular-nums`).
  - High-precision Forest Plot (`IntervalChart.tsx`) displaying equivalence corridors $[-\delta, +\delta]$, noise floor bands $[-\sigma_0, +\sigma_0]$, zero drift reference, and empirical 95% BCa Bootstrap CI brackets.
  - New **Prompt Divergence & Output Diff Explorer** (`PromptDiffExplorer.tsx`): side-by-side completion inspection (Baseline FP16 vs Candidate Quantized) with token-level diff highlights and AST validation summaries.
  - Fixed `pyproject.toml` console script entrypoint so `driftlab` CLI binary installs automatically in `venv/bin/driftlab`.
- **Reasoning**: Addresses the "AI-generated" look by elevating the interface to an authentic, high-density scientific observability tool comparable to Weights & Biases, Sentry, and Linear.

