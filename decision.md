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
- **Phase 5 Next**: Implementing runner (task orchestrator, repeat sampler, JSONL writer) and metrics engine (exact match, embedding similarity, format validity).

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
- **`driftlab.api` & `driftlab.cli`**: Thin wrappers invoking runner and querying store.

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
