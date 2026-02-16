#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SKIP_TESTS="${SKIP_TESTS:-0}"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e .[dev]

alembic upgrade head

if [ "$SKIP_TESTS" != "1" ]; then
  pytest -q
fi

exec uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
