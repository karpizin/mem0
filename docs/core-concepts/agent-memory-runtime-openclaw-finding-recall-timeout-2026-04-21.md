# mem0plus: OpenClaw Finding

## Finding

- `id:` `F-2026-04-21-001`
- `title:` `Inline plugin recall still times out at 8000ms on live OpenClaw turns`
- `date:` `2026-04-21`
- `reported by:` `Codex`
- `scenario:` `observed across the live pack, including durable architecture and noise-resistance`
- `severity:` `p1`
- `type:` `adapter`

## Expected Vs Actual

- `expected behavior:` `openclaw-mem0` should finish pre-prompt recall often enough that relevant memory is injected into the model context during the live turn
- `actual behavior:` the live contour logged `openclaw-mem0: recall timed out after 8000ms, skipping` while the post-turn runtime checks remained green; later live debugging showed that part of this pattern was a false-positive timeout branch that could still fire after a successful recall injection
- `why this matters:` the runtime can be healthy and still fail to improve the live user experience if the plugin abandons recall before prompt construction completes

## Evidence

- `query / action that triggered it:` `make openclaw-live-pilot` / run `post-docs-rerun`
- `memory brief excerpt:` durable architecture recall returned the correct runtime stack in `active_project_context`
- `trace excerpt:` `project_infrastructure` and `semantic_overlap` selected the correct `project-space` memories
- `observability / metrics evidence:` runtime processed jobs successfully with no backlog or failures, so the timeout is not explained by worker starvation
- `logs or API responses:` `/tmp/openclaw/openclaw-2026-04-21.log` first showed repeated `openclaw-mem0: recall timed out after 8000ms, skipping`; after raising the budget to `30000ms`, it also showed the more revealing pattern `injecting 1/1 memories into context ...` followed later by `recall timed out after 30000ms [legacy-1]`

## Repro

- `reproducible:` `yes`
- `repro steps:`
  - run `cd /Users/slava/Documents/mem0-src/memory-runtime && ./.venv/bin/python -m app.openclaw_live_pilot --artifact-run-name post-docs-rerun`
  - inspect `/tmp/openclaw/openclaw-2026-04-21.log`
  - observe successful runtime evidence together with plugin timeout warnings
- `known scope:` `isolated`

## Suspected Layer

- `adapter contract`

## Initial Hypothesis

- `suspected cause:` the first hypothesis was a too-tight plugin-side pre-prompt recall budget; later debugging showed a more specific bug where the legacy timeout branch could still log after a successful recall
- `confidence:` `high`
- `possible fix direction:` make the timeout configurable, add plugin-side latency instrumentation, reduce unnecessary recall work, and ensure the timeout branch is cancelable enough to distinguish true slow recall from false-positive timeout logging
- `current mitigation status:` `implemented in multiple steps on 2026-04-21: configurable recallTimeoutMs, success/timeout telemetry, low-value skip policy, compact recall injection, abortable runtime requests, per-attempt recall ids, process-wide single-flight dedupe, and a fix for false-positive timeout logging after successful recall`
- `rerun evidence:` `after rebuilding the plugin and setting recallTimeoutMs=30000, early logs showed "injecting 1/1 memories ..." followed later by a timeout for the same recall id; after fixing the timer-side-effect bug, fresh probes completed with fast recall injection and no trailing false timeout`
- `follow-up mitigation status:` `the remaining question is no longer "is 15s too short?" but "do any true memory-side timeout cases remain after the false-positive timeout path is removed?"`

## Backlog Mapping

- `should create backlog item:` `yes`
- `suggested priority:` `p1`
- `owner:` `memory-runtime + openclaw integration`
- `follow-up notes:` validate before/after with the same live scenario pack and compare user-facing recall behavior, plugin log structure, and whether any remaining timeout cases survive after the timeout-branch fix
