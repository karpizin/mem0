# Agent Memory Runtime: OpenClaw Finding

## Finding

- `id:` `F-2026-04-21-002`
- `title:` `Live continuity scenario now exposes OpenClaw embedded agent/provider timeout as the dominant bottleneck`
- `date:` `2026-04-21`
- `reported by:` `Codex`
- `scenario:` `post-fix live rerun with recallTimeoutMs=15000 and low-value recall skip policy`
- `severity:` `p1`
- `type:` `ops`

## Expected Vs Actual

- `expected behavior:` the post-fix live rerun should complete the full scenario pack so we can measure the effect of the new recall skip policy on recall latency and timeout frequency
- `actual behavior:` the rerun surfaced `agent/embedded` timeout warnings and a surfaced timeout error from the OpenClaw model/provider path before the full pack completed
- `why this matters:` once the memory plugin became more observable, the next dominant bottleneck in continuity-heavy scenarios turned out to be the upstream OpenClaw agent/provider execution budget rather than only the memory plugin

## Evidence

- `query / action that triggered it:` `cd /Users/slava/Documents/mem0-src/memory-runtime && ./.venv/bin/python -m app.openclaw_live_pilot --artifact-run-name recall-skip-policy-rerun`
- `memory brief excerpt:` recall continued to inject the expected memory snippets on successful turns, for example `injecting 1 memories into context (33ms/15000ms budget)`
- `trace excerpt:` not finalized because the full rerun was interrupted after enough live evidence had been collected
- `observability / metrics evidence:` runtime remained healthy during the rerun with `jobs_failed_total=0`, `pending=0`, `running=0`
- `logs or API responses:` `/tmp/openclaw/openclaw-2026-04-21.log` contains `embedded run timeout: ... timeoutMs=120000`, `Profile openrouter:default timed out`, and the surfaced user-facing timeout response

## Repro

- `reproducible:` `yes`
- `repro steps:`
  - keep the live OpenClaw runtime integration enabled for `pilot-user-2`
  - run the live scenario pack with the continuity scenario enabled
  - inspect `/tmp/openclaw/openclaw-2026-04-21.log`
  - observe that continuity-heavy runs can hit the embedded agent/provider timeout even while memory-runtime remains healthy
- `known scope:` `isolated`

## Suspected Layer

- `operational environment`

## Initial Hypothesis

- `suspected cause:` the continuity scenario is now dominated by the OpenClaw agent/model execution path, including very large prompt payloads and upstream provider timeout behavior, so memory improvements alone do not close the end-to-end latency budget
- `confidence:` `high`
- `possible fix direction:` reduce prompt payload size, lower provider latency, or raise `agents.defaults.timeoutSeconds` before the next continuity-heavy live rerun

## Backlog Mapping

- `should create backlog item:` `yes`
- `suggested priority:` `p1`
- `owner:` `openclaw integration`
- `follow-up notes:` rerun the same continuity scenario after adjusting OpenClaw agent timeout and/or provider selection so memory-specific latency improvements can be evaluated cleanly
