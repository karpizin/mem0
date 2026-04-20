#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/.artifacts"
REPORT_PATH="$REPORT_DIR/openclaw_live_pilot_report.json"
TMP_REPORT_PATH="$REPORT_PATH.tmp"
PYTHON_BIN="$(bash "$ROOT_DIR/scripts/resolve_python.sh")"
RUN_NAME="live-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$REPORT_DIR"

cd "$ROOT_DIR"
"$PYTHON_BIN" -m app.openclaw_live_pilot --artifact-run-name "$RUN_NAME" "$@" > "$TMP_REPORT_PATH"
mv "$TMP_REPORT_PATH" "$REPORT_PATH"

printf 'OpenClaw live pilot report saved to %s\n' "$REPORT_PATH"
if command -v jq >/dev/null 2>&1; then
  jq . "$REPORT_PATH"
else
  cat "$REPORT_PATH"
fi
