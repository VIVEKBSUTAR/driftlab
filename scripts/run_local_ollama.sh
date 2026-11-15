#!/bin/sh
# Optional portable runtime: official release files must already be extracted here.
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export OLLAMA_MODELS="$PROJECT_ROOT/.runtime/models"
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=true
exec "$PROJECT_ROOT/.tools/ollama/ollama" serve
