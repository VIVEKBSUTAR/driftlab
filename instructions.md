# Running DriftLab

The maintained setup, Python API, CLI commands, dataset format, and submission package workflow are in [README.md](README.md). Architecture and statistical decisions are in [decisions.md](decisions.md).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
npm ci --prefix frontend
npm run build --prefix frontend
driftlab serve
```

Dashboard: http://127.0.0.1:8000/app/

API reference: http://127.0.0.1:8000/openapi.json

Run `python scripts/build_release.py` to produce the wheel and source archive, including the dashboard. Install the resulting wheel outside the checkout to use the final Python package.

For frontend development, run `npm run dev --prefix frontend` alongside the backend. The Vite `/app/` page proxies `/api` to port 8000.

For real local-model experiments, start Ollama and install the chosen models. Follow [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md). Synthetic experiments remain explicitly labeled and cannot substitute for research validation.

Verification: `venv/bin/python -m pytest tests/` and `npm run build --prefix frontend`. Optional embedding tests require the `embeddings` extra and model weights; use `-m 'not embeddings'` for an offline core-only check.

For network operation, use [the deployment guide](docs/DEPLOYMENT.md) and [the recovery runbook](docs/OPERATIONS.md). Local mode is for loopback access.
