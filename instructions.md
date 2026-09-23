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

Currently, the CLI and API are under development. 

### Running Tests
To run the test suite, specifically calibration tests for the statistics engine, run:
```bash
pytest tests/
```

### Starting the API (Future)
When the FastAPI app is ready, it will be started using `uvicorn`:
```bash
uvicorn driftlab.api.main:app --reload
```

## Workflows
- **Model Inference**: Model interactions are handled locally via Ollama (or a mock adapter). You will need `ollama` installed and running locally to use real models in the future.
