#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENCV_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false
export MALLOC_ARENA_MAX=2

# Address-space cap includes native ONNX/OpenCV allocations. Default: 3 GiB.
ulimit -v "${CUTLINE_MEMORY_KIB:-3145728}"
cd "$ROOT_DIR/backend"
exec "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
