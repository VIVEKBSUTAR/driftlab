# Deployment

## Supported operating model

Deploy one workspace on one host with local persistent disk and one API process. A file lock permits exactly one local background worker. SQLite WAL is not a distributed database; do not use NFS, multiple replicas, multiple Uvicorn workers, or multiple independent services writing the same workspace. This release supplies a shared workspace secret, not individual accounts or tenant isolation. All authenticated users can read and modify workspace evidence and submit inference work.

The service supplies application-level request bounds and local rate limits. Put it behind HTTPS and your organization's network access controls. Keep Ollama private; model installation is an operator action. Do not expose Ollama directly to the internet. GPU/model memory is separate from the API container budget. Benchmark realistic task sizes and model runtimes before setting service objectives; no throughput or availability SLA is claimed.

## Docker Compose with HTTPS

Docker Engine and Compose v2 are required. Arrange DNS for your domain and permit inbound TCP 80/443 for Caddy's certificate provisioning. Existing infrastructure may supply TLS instead of Caddy.

```bash
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
```

Edit `.env` privately. Set the generated value as `DRIFTLAB_API_KEY`, your domain, explicit allowed hosts (include `127.0.0.1` for health checks), and your HTTPS origin. Configure the private Ollama endpoint and review `deploy/policies.json`. Never commit the secret. `DRIFTLAB_API_KEY_FILE` is also supported by the application when deploying with your own secret-file mount; set only one key source. The supplied Compose file uses the environment variable.

```bash
docker compose config --quiet
docker compose --profile tls up --build -d
docker compose ps
```

Open `https://YOUR_DOMAIN/app/` and enter the workspace key. Browser sessions use an HttpOnly, SameSite=Strict, secure cookie, expire after eight hours by default, and are invalidated by changing the key and restarting. The key is not persisted in browser storage. Bearer clients use `Authorization: Bearer KEY`. Do not put keys in URLs or shell command history. Static assets and liveness are public; evidence endpoints and the OpenAPI schema require authentication.

Compose binds the direct API port to host loopback; Caddy forwards traffic on the internal network. Direct HTTP browser login is unsupported in server mode because cookies require HTTPS. Readiness uses an authenticated internal HTTP request. The image runs as UID/GID 10001 with a read-only root filesystem, a writable persistent workspace, bounded temporary storage, dropped capabilities, and a shutdown grace period.

Named volumes retain evidence when containers are replaced. Do not run `docker compose down --volumes` on a workspace you need to keep. Images and proxy tags should be pinned to reviewed digests in your deployment inventory. The repository's versioned image name is built locally; no public image registry publication is implied.

## Configuration

Settings are read at process startup. Prefix each name with `DRIFTLAB_`. Invalid settings fail startup; server mode requires an API key of at least 32 characters and `COOKIE_SECURE=true`.

| Setting | Default | Purpose |
| --- | --- | --- |
| `MODE` | `local` | `server` for non-loopback service binding |
| `WORKSPACE` | working directory | SQLite, jobs, manifests and artifacts |
| `API_KEY` / `API_KEY_FILE` | unset | shared bearer/session secret |
| `COOKIE_SECURE` | `false` locally | mandatory `true` in server mode |
| `ALLOWED_HOSTS` | localhost and loopback | comma-separated or JSON hostname list; no wildcard |
| `ALLOWED_ORIGINS` | local Vite origins | explicit HTTPS frontend origin in production |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | trusted operator-selected inference endpoint |
| `POLICY_FILE` | bundled defaults | validated JSON risk policy file |
| `MAX_BODY_BYTES` | 2097152 | request-body limit, including chunked bodies |
| `MAX_TASKS` | 500 | tasks per HTTP run |
| `MAX_OBSERVATIONS` | 10000 | tasks × repeats per HTTP run |
| `MAX_PENDING_JOBS` | 16 | queued/running job admission limit |
| `REQUESTS_PER_MINUTE` | 600 | per-client process-local API request limit |
| `SESSION_SECONDS` | 28800 | browser session lifetime |
| `WORKER_ENABLED` | `true` | disable only for maintenance/testing |

HTTP generation timeouts are bounded to 120 seconds per request, output limits to 4096 tokens, and a submitted run's total requested output budget to two million tokens. Comparison resampling and concurrent comparisons are bounded. Timeout is an HTTP client bound, not proof that the inference backend stopped computation. Cancellation is checked between generations and may wait for an outstanding inference request.

Without Compose, install the built wheel, supply the same environment, and run `driftlab serve --host 0.0.0.0 --port 8000` behind a TLS proxy. Do not enable reload or multiple workers. Logs are structured JSON on stderr; use your platform's log rotation and retention controls.

## Release and publication

`python scripts/build_release.py` creates the wheel, source archive, and checksums; `python scripts/verify_release.py` checks the installed wheel and bundled UI outside the checkout. CI also tests the container with bearer authentication, queued synthetic runs, persisted comparison evidence, and dashboard delivery. Synthetic checks do not validate your model backend.

A PyPI release needs an owned project name, review of distribution metadata/licenses, and a configured trusted publisher. The optional manual publication workflow uses the GitHub `pypi` environment and OIDC; configure that protected environment and PyPI trusted publishing before invoking it. No package is automatically published on ordinary pushes. Configure your DNS, TLS, secret delivery, backup retention and inference capacity before treating a deployed instance as available to users.
