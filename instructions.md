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

## Running the Project

### Running Tests
To run the full test suite (including statistical calibration tests and store unit tests):
```bash
pytest tests/
```

To run only the store/database tests:
```bash
pytest tests/unit/test_store.py
```

### Database & Storage Architecture
- **Raw Observations (Source of Truth)**: Runs write their raw generation outputs directly into an append-only JSONL file (e.g. `data/runs/<run_id>.jsonl`).
- **Relational Store (Derived)**: SQLite database (`driftlab.db`) is derived from the JSONL files using `driftlab.store.db.create_tables()` and `driftlab.store.jsonl.ingest_jsonl_to_db()`.
- **Zero Overhead**: No external database server (PostgreSQL/MySQL) is needed. Everything runs locally on SQLite.

### Model Backends
- **Mock Backend**: `MockAdapter` is used for in-memory, reproducible testing without requiring local GPUs or model weights.
- **Ollama Backend**: For actual local LLM runs, ensure Ollama is installed and running locally on `http://localhost:11434`.

### Starting the API (Future)
When the FastAPI app is ready, it will be started using `uvicorn`:
```bash
uvicorn driftlab.api.main:app --reload
```
