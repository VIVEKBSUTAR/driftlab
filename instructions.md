# DriftLab Instructions

## Setup and Installation

DriftLab requires Python 3.11+. We recommend setting up a virtual environment to manage dependencies.

### 1. Create a Virtual Environment
Run the following command in the root of the project to create a virtual environment named `venv`:
```bash
python3.11 -m venv venv
```

### 2. Activate the Virtual Environment
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```
- **Windows**:
  ```bash
  .\venv\Scripts\activate
  ```

### 3. Install Dependencies
Install the package in editable mode with development dependencies:
```bash
pip install -e ".[dev]"
```

---

## Running the Project

### Command-Line Interface (CLI)

The CLI can be run either as `driftlab` or `python -m driftlab`:

#### 1. Display Help and Version
```bash
driftlab --help
driftlab version
```

#### 2. Execute a Baseline Benchmark Run
Runs tasks against a model adapter (e.g. `mock` or `llama3:8b`), logs observations directly to an append-only JSONL file, and populates SQLite:
```bash
driftlab run --model mock --type baseline --repeats 3 --metrics exact_match,sequence_similarity
```

#### 3. Execute a Candidate Benchmark Run
```bash
driftlab run --model mock --type candidate --repeats 3 --metrics exact_match,sequence_similarity
```

#### 4. Compare Baseline vs. Candidate Runs for Drift
Compares two runs using the statistical drift decision hierarchy (bootstrap CI, permutation test, noise floor, risk policy margins):
```bash
# Output formatted as a terminal table
driftlab compare <baseline_run_id> <candidate_run_id> --format table

# Output formatted as a complete Markdown report
driftlab compare <baseline_run_id> <candidate_run_id> --format markdown

# Output formatted as raw JSON
driftlab compare <baseline_run_id> <candidate_run_id> --format json
```

---

### Running the FastAPI REST API

Start the local server with `uvicorn`:
```bash
uvicorn driftlab.api.main:app --reload --port 8000
```

- **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`
- **Health Check**:
  ```bash
  curl http://localhost:8000/
  ```

---

### Running the Frontend Dashboard

The frontend is a modern React + TypeScript + Vite application located in `frontend/`.

#### 1. Install Frontend Dependencies
```bash
cd frontend
npm install
```

#### 2. Start the Vite Dev Server
```bash
npm run dev
```
The dashboard will be accessible at `http://localhost:5173`. It connects automatically to the FastAPI backend running on port 8000.

#### 3. Build for Production
```bash
npm run build
```
- **Trigger a Benchmark Run**:
  ```bash
  curl -X POST http://localhost:8000/runs \
    -H "Content-Type: application/json" \
    -d '{
      "model": "mock",
      "run_type": "baseline",
      "repeats": 3,
      "metrics": ["exact_match"]
    }'
  ```
- **Compare Runs**:
  ```bash
  curl -X POST http://localhost:8000/compare \
    -H "Content-Type: application/json" \
    -d '{
      "baseline_run_id": "run_01",
      "candidate_run_id": "run_02",
      "noise_floor": 0.01
    }'
  ```

---

### Running Tests

To run the complete test suite (calibration tests for the statistics engine and all unit tests):
```bash
pytest tests/
```

To run individual test modules:
```bash
# Statistical calibration tests
pytest tests/calibration/test_stats.py

# Drift decision rules
pytest tests/unit/test_drift_decision.py

# Model adapters
pytest tests/unit/test_adapters.py

# Database and JSONL persistence
pytest tests/unit/test_store.py

# CLI and API
pytest tests/unit/test_cli.py tests/unit/test_api.py
```

---

### Architecture & Storage Notes
- **Append-Only JSONL (Source of Truth)**: Every model generation is written immediately to `data/runs/<run_id>.jsonl`.
- **Derived Relational Store (SQLite)**: SQLite database (`driftlab.db`) is derived from JSONL files, allowing queries without sacrificing durability.
- **Model Backends**:
  - `MockAdapter`: Built-in distribution sampler for deterministic tests without a GPU.
  - `OllamaAdapter`: Connects to local Ollama daemon at `http://localhost:11434`.
