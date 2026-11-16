# Contributing

Discuss substantial API, statistical or storage changes in an issue before implementation. Explain the user-visible behavior, assumptions and validation. Keep changes focused; do not add synthetic fallback evidence to live dashboards.

## Development

Use Python 3.11–3.14 and Node 22.22.2+, 24.15+, or 26.x. Create a virtual environment, install `.[dev]`, and run `npm ci --prefix frontend`. For a locked environment with uv installed, use `uv sync --locked --extra dev`; the core deployment export is `requirements.lock`. The optional embedding extra is separate and can require large model downloads.

```bash
venv/bin/ruff check src tests scripts examples
venv/bin/ruff format --check src tests scripts examples
venv/bin/python -m pytest tests/ -m 'not embeddings'
npm test --prefix frontend
npm run build --prefix frontend
venv/bin/python scripts/build_release.py
venv/bin/python scripts/verify_release.py
```

The full `venv/bin/python -m pytest tests/` includes an optional embedding test; it skips when dependencies or cached weights are unavailable. For an offline full test run, set `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` after provisioning its model cache. Tests use temporary workspaces and synthetic adapters; real-model claims require the documented experiment protocol and preserved evidence.

Update `decisions.md` alongside changes to architecture, API/backend/frontend behavior, metrics, storage, dependencies or workflows. Update the checked API schema with `python scripts/export_openapi.py`. For Python dependency changes run `uv lock` and `uv export --frozen --no-dev --no-default-groups --no-emit-project --no-annotate --format requirements-txt --output-file requirements.lock`. Commit both lockfiles. Run `npm install` for frontend dependency changes and commit its lockfile.

Do not commit virtual environments, dependencies, build outputs, database files, credentials, model weights or raw run artifacts. Dataset provenance, license requirements, statistical assumptions and uncertainty must remain explicit. Add meaningful failure/recovery tests when changing job execution or storage.

Contributions are licensed under the repository's MIT license. Report vulnerabilities privately as described in `SECURITY.md`.
