# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS wheel
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY --from=frontend /build/frontend/dist ./src/driftlab/api/static
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DRIFTLAB_WORKSPACE=/var/lib/driftlab DRIFTLAB_MODE=server \
    DRIFTLAB_COOKIE_SECURE=true HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN groupadd --gid 10001 driftlab && useradd --uid 10001 --gid driftlab --create-home driftlab \
    && install -d -o driftlab -g driftlab -m 0700 /var/lib/driftlab
COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && rm /tmp/requirements.lock
COPY --from=wheel /wheels /wheels
RUN python -m pip install --no-cache-dir --no-deps /wheels/*.whl && rm -r /wheels
USER 10001:10001
WORKDIR /var/lib/driftlab
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-m", "driftlab.healthcheck"]
ENTRYPOINT ["driftlab", "serve", "--host", "0.0.0.0", "--port", "8000"]
