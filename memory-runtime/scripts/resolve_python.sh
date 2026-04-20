#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${PYTHON:-}" ]]; then
  printf '%s\n' "$PYTHON"
  exit 0
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  printf '%s\n' "$ROOT_DIR/.venv/bin/python"
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  command -v python3
  exit 0
fi

if command -v python >/dev/null 2>&1; then
  command -v python
  exit 0
fi

printf 'No Python interpreter found. Set PYTHON=/path/to/python or create %s/.venv.\n' "$ROOT_DIR" >&2
exit 1
