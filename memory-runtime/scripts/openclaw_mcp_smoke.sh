#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/.artifacts"
REPORT_PATH="$REPORT_DIR/openclaw_mcp_smoke_report.json"
RUN_NAME="manual-$(date +%Y%m%d-%H%M%S)"
PYTHON="$(bash "$ROOT_DIR/scripts/resolve_python.sh")"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

cd "$ROOT_DIR"
docker compose up -d --build

for _ in $(seq 1 30); do
  if docker compose exec -T memory-api python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/healthz')" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

"$PYTHON" -m app.mcp_smoke \
  --base-url http://127.0.0.1:8080 \
  --client-name openclaw \
  --user-id alice \
  --artifact-run-name "$RUN_NAME" > "$REPORT_PATH"

jq -e '
  (.initialize_ok == true) and
  (.tools_ok["memory.ingest_event"] == true) and
  (.tools_ok["memory.recall"] == true) and
  (.tools_ok["memory.record_feedback"] == true) and
  (.feedback_recorded_count >= 1) and
  (.recall_selected_episode_ids | length >= 1) and
  (.jobs_by_status.pending == 0)
' "$REPORT_PATH" >/dev/null

printf 'OpenClaw MCP smoke passed. Report: %s\n' "$REPORT_PATH"
cat "$REPORT_PATH"
