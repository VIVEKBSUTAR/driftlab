# DriftLab Architecture and Decisions

## Project Overview
DriftLab is a statistical framework for behavioral drift detection and validation in local LLMs. It determines if a candidate LLM state has meaningfully drifted from a baseline, distinguishing true drift from natural run-to-run variability.

## Architectural Principles
1. **Separation of Concerns**: Core statistics, drift decisions, and risk logic live in a plain Python package (`driftlab.stats`, `driftlab.drift`, `driftlab.risk`). They have zero dependencies on web frameworks (FastAPI) or databases (SQLAlchemy).
2. **Deterministic Stochasticity**: Every statistical function must be pure and take a `numpy.random.Generator` explicitly to guarantee testability.
3. **Data Source of Truth**: Raw model outputs are appended to a JSONL file per run. The SQLite database is derived from this JSONL file, ensuring the database is reconstructable and the JSONL is the ultimate source of truth.

## Current Development State
- **Phase 0 & 1 Completed**: Basic folder structure, project dependencies (`pyproject.toml`), and empty module skeletons initialized.
- **Phase 2 Completed**: Implemented the core statistics engine (`driftlab.stats`) with exact signatures, calibrated for false-positive rates and nominal coverage.
- **Phase 3 Completed**: Implemented Model Adapters (`MockAdapter` and `OllamaAdapter`) with unit tests.
- **Phase 4 Next**: Implementing Database schemas and JSONL persistence.

## Module Connectivity
- **`driftlab.config`**: Used globally to validate and load configurations.
- **`driftlab.datasets`**: Loads prompts to be fed to the `runner`.
- **`driftlab.adapters`**: Used by the `runner` to generate outputs via Mock or Ollama backends.
- **`driftlab.runner`**: Calls `adapters`, computes `metrics`, and outputs JSONL observations.
- **`driftlab.metrics`**: Feeds metric values into `driftlab.stats`.
- **`driftlab.stats`**: Pure functions called by `driftlab.drift` to test for significance.
- **`driftlab.drift`**: Uses outputs from `stats` and policies from `risk` to make a final decision.
- **`driftlab.api` & `driftlab.cli`**: Top-level wrappers that invoke the `runner`, query the `store`, and present `reporting`.

## Feature Log & Reasoning
### Phase 1: Module Skeletons
- **Feature**: Initializing packages with strict separation of concerns.
- **Reasoning**: Ensures the non-negotiable architectural rule is maintained from day one. By separating the API/Store from the Stats engine, the statistics logic remains pure, lightweight, and easily testable without needing a database connection or HTTP server.

### Phase 2: Statistics Engine
- **Feature**: Developed pure statistical functions (bootstrap CI, permutation test, noise floor, etc.) and their calibration tests.
- **Reasoning**: To distinguish meaningful drift from natural variability, the stats functions were kept functionally pure and injected with a random generator to allow full reproducibility and calibration testing on simulated distributions.

### Phase 3: Model Adapters
- **Feature**: Created `ModelAdapter` base class and implemented `MockAdapter` and `OllamaAdapter`.
- **Reasoning**: Using the Adapter pattern isolates the runner and stats pipeline from specific model backends. `MockAdapter` supports robust E2E testing without GPUs, keeping CI/CD pipelines fast and deterministic. `requests` was added to `pyproject.toml` to interface with the Ollama local API.

### Phase 2: Statistics Engine
- **Feature**: Developed pure statistical functions (bootstrap CI, permutation test, noise floor, etc.) and their calibration tests.
- **Reasoning**: To distinguish meaningful drift from natural variability, the stats functions were kept functionally pure and injected with a random generator to allow full reproducibility and calibration testing on simulated distributions.

### Phase 3: Model Adapters
- **Feature**: Created `ModelAdapter` base class and implemented `MockAdapter` and `OllamaAdapter`.
- **Reasoning**: Using the Adapter pattern isolates the runner and stats pipeline from specific model backends. `MockAdapter` supports robust E2E testing without GPUs, keeping CI/CD pipelines fast and deterministic. `requests` was added to `pyproject.toml` to interface with the Ollama local API.
