# DriftLab architecture and decisions

Last reviewed: 16 November 2026. This document describes version 0.2.0. Update it alongside changes to architecture, behavior, metrics, storage, dependencies or workflows.

## Purpose and supported scope

DriftLab compares baseline and candidate model behavior on identical application tasks. It records repeated generations, scores outputs and reports statistical evidence against practical risk policies. A recommendation informs human review; the tool does not approve or block a deployment itself.

The supported operational unit is one shared, authenticated workspace on one host, local disk and SQLite, one API process and one worker. This is not a multi-tenant SaaS, distributed job system, general code sandbox or high-availability database. API users share full workspace privileges. SDK/CLI and custom adapters are trusted local interfaces.

## Stack and code ownership

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.11–3.14; React 18 and TypeScript |
| Service | `client.DriftLab`, shared by SDK, CLI and HTTP |
| HTTP | FastAPI/Pydantic 2/Uvicorn, explicit app factory/lifespan |
| Inference | Local Ollama over Requests; custom Python adapters; explicit synthetic adapter |
| Analysis | NumPy, SciPy, statsmodels; pure numerical functions in `stats/core.py` |
| State | SQLAlchemy 2, SQLite WAL/FULL synchronous, foreign keys and busy timeout |
| Evidence | Raw JSONL, scored sidecars, atomic task/config manifests, SQLite observation/aggregate/comparison rows |
| Jobs | SQLite job payloads/status, local file locks and one worker thread |
| UI | React, Vite 8, Tailwind 3, lucide icons, SVG/CSS charts |
| Verification | pytest, Ruff, Vitest/Testing Library, TypeScript build, wheel/container smoke checks |
| Release | setuptools wheel/sdist with compiled dashboard; nonroot Docker image and optional Caddy TLS proxy |

`config/settings.py` owns operator settings; `config/schemas.py` generation settings; `datasets/loader.py` validates tasks; `adapters/` owns inference identity/generation; `runner/` records and scores; `store/` handles persistence/upgrades; `client.py` manages run and comparison lifecycles; `jobs.py` owns queued recovery/cancellation. `api/main.py` is transport and admission control; `api/security.py` handles HTTP guards; `maintenance.py` manages backup/restore. The frontend's mounted views are composed in `App.tsx`; unused prototypes with sample data were removed.

## HTTP and security boundary

Infrastructure is selected by the operator at startup. Requests cannot supply a database URL, artifact path, arbitrary inference endpoint or server policy file. Local mode without a key allows only loopback clients; the CLI refuses non-loopback binding without server mode. Server mode requires a 32–256-character key and secure cookies, explicit hosts/origins and an HTTPS reverse proxy.

Bearer keys and HMAC-signed, expiring session cookies grant shared workspace access. Browser keys remain transient React state and are cleared after login, never browser storage. Cookies are HttpOnly/SameSite=Strict and secure in server mode. Key rotation invalidates all sessions; logout clears the current cookie but is not server-side token revocation. No individual account/RBAC system is claimed.

Middleware validates hosts, origins and JSON content types, bounds content-length and streamed request bodies, supplies request IDs/CSP/security headers, and limits login/API requests in bounded process-local windows. The API limits tasks, observations, token budget, queued jobs and resampling; a semaphore allows one comparison at a time. Requests from a reverse proxy can share its IP-based rate bucket unless the operator safely configures trusted forwarding. Static assets and liveness are public; evidence and OpenAPI are protected. Logs omit bodies, query strings, keys and cookies; operator-only stack traces can still contain backend diagnostics.

The API never silently falls back to sample data. Discovery errors are reported. Swagger/Redoc are disabled to avoid external CDN requirements and CSP exceptions; `/openapi.json` is the contract, exported to `docs/openapi.json` and checked by CI. Typed response models exclude internal artifact paths. Known run IDs and artifact kinds drive confined downloads. Lists use bounded limit/offset; observations have a default 200/max1000 page and total count.

## Run preparation and identity

Tasks require unique IDs, keys and prompt/system contexts; nonblank bounded prompt/reference text; valid risk tiers and structured output specifications. Reference metrics require references. The original 32-prompt functional suite exercises arithmetic/JSON handling, not benchmark coverage or safety. User datasets and prepared GSM8K/BoolQ samples share the validation pipeline.

A task ID derives from full scoring context, including system prompt, reference and output specification. Dataset hashes derive from sorted validated task records. Model identity includes full backend digest and metadata. Ollama names are canonicalized; missing digests fail preparation. Redirects are refused by the adapter. Model identity is verified at submission, worker claim and after execution; changed identity fails rather than combining provenance under a successful run.

Manifests record tasks, dataset hash, model identity, metrics, repeats, generation parameters, root seed and environment version. Schema 2 uses deterministic 63-bit NumPy SeedSequence seeds per task/repeat. Version 0.1 used different seed derivation; historical evidence is not relabeled or claimed exactly reproducible under v0.2. Synthetic stable/regression profiles use a per-generation generator, including after resume. Custom adapters retain their supplied identity; built-in `mock` is always labeled synthetic.

## Execution, durability and recovery

HTTP POST `/runs` returns 202 and a real queued run ID after run/job rows commit together. SDK/CLI runs are synchronous. Admission/worker/execution locks prevent competing local ownership. Inference does not hold a database transaction open. The runner records raw output immediately, then scores it; it records errors before failing. Raw evidence includes text, latency, seed, available token counts and finish reason. Scores must be finite. Failed output is not scored as a zero or promoted into a completed run.

The worker recovers interrupted running jobs into the queue, verifies model identity and reuses cached generations by run/task/repeat/seed. A partial trailing raw write is quarantined before truncation. Complete malformed records fail closed. Unique database indexes prevent duplicate observations, scores and aggregates; model/dataset digest indexes prevent duplicate identities. Cached outputs can be rescored on resume; sidecar duplication is avoided.

Cancellation and shutdown are cooperative between generations; outstanding backend requests may take their timeout to finish. Shutdown waits up to 130 seconds, and readiness fails if the worker dies. Failed backend jobs are not automatically retried. Worker state and raw evidence allow resumption after abrupt termination, but do not eliminate hardware loss or make arbitrary custom metrics interruptible. Disk capacity and evidence retention remain operator responsibilities.

Manifests use private temporary files, fsync and atomic replace; JSONL appends are flushed/fsynced. This improves crash behavior, not cryptographic integrity or a guarantee against every filesystem/power-loss failure. SQLite and artifacts together constitute evidence; copying only the database or reingesting only raw JSONL is not full recovery.

Schema upgrades are additive and versioned under a lock. Version 1 adds uniqueness constraints/job tables; version 2 adds optional generation provenance columns. Newer schemas are refused. Duplicate historical rows cause an explicit migration failure rather than deletion. Back up before upgrades; downgrade requires restoring a compatible backup.

## Comparisons and statistical meaning

Only completed runs with matching task/scoring content and full manifest metric/repeat coverage are compared. SQL queries load metric rows with deterministic ordering, avoiding per-observation score queries. Per-prompt mean candidate-minus-baseline effects get equal prompt weighting.

The interval is a BCa bootstrap across prompt differences, with explicit degenerate/constant fallbacks. The two-sided permutation test shuffles baseline/candidate labels within each prompt. Holm correction spans category × metric × risk hypotheses in that comparison. The default noise floor is the 95th percentile of absolute average differences from independent resamples of baseline repeats, conditional on the observed prompts. A finite nonnegative manual override is supported and recorded.

Rules are ordered: insufficient prompt/repeat count; high/critical harmful significant regression beyond margin; meaningful significant drift; significant low-impact change; interval entirely inside the equivalence margin; otherwise inconclusive. Significance also requires effect beyond the noise floor. Effective policy settings, resampling settings, seeds, raw/adjusted p-values, intervals, counts and noise source are preserved with evidence. Policy validation requires all four risk tiers. Defaults are illustrative, not application-specific safety thresholds.

Confidence levels follow each policy. The permutation resolution, prompt independence, dataset representativeness and grading quality constrain conclusions. Nonsignificance is not equivalence. `answer_match` uses explicit numeric/Boolean extraction (numeric final answer, preferring text after `####`; Boolean first yes/no/true/false token); it does not measure reasoning quality. JSON parsing rejects nonfinite pseudo-JSON. Optional sentence-transformers scoring requires separately provisioned dependencies and weights; its model revision is not currently fingerprinted, so pin/cache it externally for controlled studies.

## Frontend behavior

An access gate checks the actual session before loading protected data. Offline/API failures expose a retry/error state and no fake metrics. Session expiry returns to authentication. The same-origin API client has timeouts, credentials and request-ID error reporting. The synthetic walkthrough awaits queued completion before requesting comparison; failed/cancelled jobs stop the workflow.

The dashboard shows database-wide totals from `/workspace`, recent API-backed history, per-metric quality and latency, run inspection, comparison forest plots, studio task/model configuration, datasets, policies and methodology. Aggregate quality is the equal-weight mean of prompt means; unrelated metrics are not blended into one score. Latency is in milliseconds and synthetic latency is labeled. Graphs expose units, empty states, legends and accessible descriptions. Forest domains include interval, effect, noise and margin without clipping; confidence labels follow risk tiers.

Run detail identifies partial observation pages; UI exports say visible page and full raw/score links are available. API limit/offset supports full external pagination; the current dashboard shows a bounded recent history rather than a virtualized large-workspace explorer. Cancellation controls report actual backend outcomes. Token-limit finish reasons produce a warning. Sample-size previews come from current catalog policies, while final analysis always uses backend policy logic.

## Deployment, release and maintenance

Docker stages frontend compilation and wheel construction, then installs hash-pinned core dependencies into Python 3.13-slim. Runtime UID10001, read-only root, persistent workspace, dropped capabilities and resource bounds are supported by Compose. The optional proxy provides HTTPS. Environment/secret delivery, DNS, TLS, base-image updates, access controls, monitoring, retention, backend provisioning and capacity planning remain deployment responsibilities.

Backups acquire the execution lock, snapshot SQLite online and include artifacts, datasets/study files and effective policies. They normalize local artifact paths for relocation and reject external artifacts/symlinks. Restore rejects unsafe/archive-bomb paths, verifies checksums/size and database integrity, then renames into a new destination. Secrets, runtime dependencies and weights are excluded. Operators stop admission for operational snapshots and test restores in isolation. Checksums are not signatures.

`uv.lock` records Python resolutions, including optional extras; `requirements.lock` exports hash-pinned core runtime dependencies. npm has its own lockfile. Optional embeddings are excluded from minimal deployment/audit and require separate review. Frontend advisory fixes include Vite8/Vitest5 and transitive updates. Node engine ranges match jsdom: 22.22.2+, 24.15+ or 26.x. The frontend test suite covers real request/session/job-failure behavior. Python tests cover statistics, SDK/CLI/API, migration guards, security, queue recovery, cancellation and backup restore.

`scripts/build_release.py` stages bundled UI and builds wheel/sdist/checksums. The source archive includes source, docs, tests, deployment/workflow files and locks. `verify_release.py` installs the wheel outside the checkout and checks its assets and persisted synthetic workflow. CI tests Python3.11/3.13/3.14, frontend behavior/build/advisories, core Python advisories, schema/lock consistency, release installation, and authenticated container execution/restart. Optional embedding tests need provisioned caches. A manual OIDC publication workflow requires an owned PyPI name and configured protected `pypi` environment; ordinary pushes do not publish.

## Research evidence and remaining limits

The v0.1 pilot used Qwen2.5 0.5B and SmolLM2 360M through local Ollama on Apple M4, 30 prompts each from GSM8K and BoolQ, five repeats and a 128-token cap. Six real runs produced 900 generations. Three comparisons were inconclusive; one GSM8K comparison met its equivalence margin at very low absolute accuracy. See `docs/VALIDATION.md` and its recorded revision. Model/data licenses and exact samples are documented; raw weights/evidence remain ignored local artifacts.

Production engineering checks do not validate generalizability, domain safety, statistical power for a particular application or all model families. Remaining platform boundaries include individual identities/authorization, distributed jobs, HA, external retention/monitoring and fingerprinting optional embedding model revisions. The supported release does not claim those features. Do not describe protocol plans as completed experiments or promise zero bugs.

## Repository synchronization

After verified requested changes, commit source and lockfiles and push the current branch to its configured GitHub remote. Never force push, discard work or commit databases, secrets, dependencies, generated builds, environments, weights or raw evaluations. Report push failures accurately. The project instructions are preserved in `AGENTS.md`.
