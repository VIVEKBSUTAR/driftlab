# Operations and recovery

## Health and diagnostics

`GET /api/livez` checks the process. Authenticated `GET /api/readyz` checks database access and worker availability; a failed worker makes readiness fail. `GET /api/workspace` reports database-wide counts. Request logs include a request ID, method, path, response status and duration; request bodies, authorization headers and query strings are excluded. Exceptions return a generic message with a request ID; correlate it with protected server logs.

If the dashboard reports “Failed to fetch,” verify the API process, browser origin, reverse proxy and TLS certificate. Inspect the browser network response and `docker compose logs --tail=100 driftlab`. A running frontend cannot substitute for an unavailable API. A 401 requires authentication; 413 means the body is too large; 422 means invalid input; 429 means a request or queue limit. Model discovery failures are shown explicitly and do not manufacture installed models.

Monitor readiness, failed/cancelled jobs, queue depth, disk free space, CPU/memory, inference latency and backup age. SQLite and raw output storage grow with every experiment; provision and alert on disk capacity. There is no automatic evidence deletion, archival scheduler or Prometheus endpoint. Apply a reviewed retention procedure after making verified backups; do not manually remove individual database rows or run files.

## Jobs and recovery

POST `/api/runs` returns **202 Accepted** and a `run_id`. Poll `/api/runs/{id}` for pending/running/completed/failed/cancelled. Pending jobs survive restart. The worker recovers interrupted running jobs, verifies model identity, reads completed raw generations and resumes missing work using the recorded seeds. It never regenerates a cached completed generation. An incomplete trailing JSONL write is quarantined; complete malformed records fail closed. Scored evidence is ingested with uniqueness constraints.

Keep model weights and backend versions stable during a run. Model identity changes, missing weights, backend/scoring errors, or corrupt evidence fail visibly. A failure does not silently retry or create a successful job ID. Start a new run after resolving its cause; preserve the failed run for inspection. Cancellation and orderly shutdown retain completed raw work. Shutdown checks occur between generations; allow at least the configured timeout plus storage time. Abrupt termination recovery is covered by tests but storage hardware can still fail.

Lists use `limit` and `offset`; run detail defaults to 200 observations and accepts at most 1000 per page. `observations_total` reports full size. The dashboard labels partial output exports and offers full raw/score downloads. Downloaded artifacts can include confidential prompts and model responses. Historical v0.1 runs remain readable; they lack some new provenance fields and are not relabeled with new seed semantics.

## Backups

Protect backups like the source data. The built-in backup takes a SQLite online snapshot and copies run artifacts, benchmark/study files and effective policies. It requires idle inference through the workspace execution lock; schedule during a maintenance window and stop admission/server activity for a stable operational snapshot. Credentials, model weights, application environment and runtime dependencies are not included.

For a source/wheel installation:

```bash
driftlab backup /secure/backups/workspace-2026-11-15.zip --workspace /srv/driftlab
driftlab restore /secure/backups/workspace-2026-11-15.zip /srv/driftlab-restored
```

The destination archive must not exist. Restore requires a **new** directory. It rejects unsafe paths and verifies checksums, sizes, SQLite integrity and foreign keys before placing the restored workspace. Checksums detect corruption, not malicious replacement of an entire archive; authenticate/encrypt backups using your storage platform.

For Compose, stop the API, use a one-off container on the existing workspace volume, and mount a private backup directory writable by UID10001:

```bash
docker compose stop driftlab
docker compose run --rm --no-deps --entrypoint driftlab \
  -v /secure/backups:/backups driftlab \
  backup /backups/workspace.zip --workspace /var/lib/driftlab
docker compose start driftlab
```

Test restores to an isolated new volume or directory regularly. Configure `DRIFTLAB_POLICY_FILE` to the restored `policies.json` when recovering nondefault policies, restore the separately protected service configuration/secret, and verify run totals, representative outputs, comparisons and readiness before switching traffic. Do not run production and restored workers against the same model workspace during a validation test unless intended.

## Upgrades and rollback

1. Stop admission and wait for or cancel active work. Back up the full workspace and service configuration.
2. Verify the new wheel/image and review `CHANGELOG.md`. Test an isolated restore against the new version first.
3. Stop the old process. Start the new version with the same workspace and one worker. Startup applies additive schema upgrades under a migration lock and refuses a database from a newer schema.
4. Check readiness, counts, existing comparison exports and a small real-backend run before reopening access.

There is no automatic downgrade migration. To roll back, stop the new process and restore the pre-upgrade backup into a new workspace with the prior application version. Never point an older release at a database upgraded by a newer one. Version 0.2 changes seed derivation and asynchronous HTTP behavior; old comparisons remain historical records.

## Security maintenance

Rotate the workspace key by changing its private source and restarting; all existing signed sessions become invalid. Logout clears the browser cookie; a copied cookie remains valid until expiry or key rotation. TLS and access controls must protect every hop exposed to untrusted networks. The shared secret has full workspace privileges; use a separate service or future identity integration if individual authorization is required.

Audit dependencies regularly with `npm audit --prefix frontend` and `pip-audit -r requirements.lock --no-deps --disable-pip`. Advisory-free at one point in time is not a guarantee against future vulnerabilities. Optional embedding dependencies require their own audit and model provisioning. Keep host OS, container base images, proxy and inference server patched. See [SECURITY.md](../SECURITY.md) for private reporting.
