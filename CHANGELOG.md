# Changelog

## 0.2.0

Production-oriented single-workspace release. This is not a multi-tenant or high-availability platform.

### Added

- Shared bearer authentication and signed, expiring HttpOnly browser sessions; secure server mode, host/origin validation, body and admission limits, request IDs and JSON logs.
- Persistent SQLite jobs, one-worker ownership, resumable generations, cancellation, partial evidence preservation and worker-aware readiness.
- Versioned additive schema upgrades, unique evidence constraints, atomic manifests, synced JSONL writes and interrupted-tail quarantine.
- Portable checksum-verified backups and safe restore into new workspaces.
- Configurable risk policies preserved with comparison evidence; token/finish provenance and truncation warnings.
- Packaged dashboard authentication, actual workspace-wide metrics, artifact downloads and explicit partial-page exports.
- Nonroot container, TLS proxy example, lockfiles, dependency checks, frontend tests and container workflow checks.

### Compatibility changes

- HTTP `POST /runs` returns **202** and a queued `run_id`; poll for completion before comparing. Synchronous HTTP execution is removed. SDK/CLI calls remain synchronous.
- HTTP database URLs and filesystem output paths are rejected. Infrastructure is operator configured.
- Python support is 3.11–3.14. Frontend builds require Node 22.12+ in supported majors 22/24/26.
- Generation seeds use a 63-bit NumPy SeedSequence scheme. v0.1 runs remain readable but exact historical replay requires their recorded prior revision.
- `/docs` and `/redoc` are disabled; authenticated `/openapi.json` provides the contract without external CDN dependencies.
- Repeated identical prompt/system contexts are rejected to prevent inflated prompt sample counts.
- Upgrade storage from backup; schema downgrade is unsupported. Old evidence lacks new optional provenance fields.

## 0.1.0

Local research implementation with Python SDK/CLI, dashboard, statistical comparisons, evidence exports and a small two-family/two-dataset Ollama pilot. Historical results and limitations are recorded in `docs/VALIDATION.md`.
