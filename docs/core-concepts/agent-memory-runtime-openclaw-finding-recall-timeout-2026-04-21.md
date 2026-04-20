# Agent Memory Runtime: OpenClaw Finding

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
- `actual behavior:` the live contour still logs `openclaw-mem0: recall timed out after 8000ms, skipping` while the post-turn runtime checks remain green
- `why this matters:` the runtime can be healthy and still fail to improve the live user experience if the plugin abandons recall before prompt construction completes

## Evidence

- `query / action that triggered it:` `make openclaw-live-pilot` / run `post-docs-rerun`
- `memory brief excerpt:` durable architecture recall returned the correct runtime stack in `active_project_context`
- `trace excerpt:` `project_infrastructure` and `semantic_overlap` selected the correct `project-space` memories
- `observability / metrics evidence:` runtime processed jobs successfully with no backlog or failures, so the timeout is not explained by worker starvation
- `logs or API responses:` `/tmp/openclaw/openclaw-2026-04-21.log` repeatedly contains `openclaw-mem0: recall timed out after 8000ms, skipping`

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

- `suspected cause:` the plugin-side pre-prompt recall budget is too tight for the current live OpenClaw prompt/context size and recall strategy
- `confidence:` `high`
- `possible fix direction:` make the timeout configurable, add plugin-side latency instrumentation, and reduce unnecessary recall work on the cold-start path
- `current mitigation status:` `implemented baseline fix on 2026-04-21 via configurable recallTimeoutMs plus success/timeout telemetry; rerun confirmed partial improvement but not full closure`
- `rerun evidence:` `after rebuilding the plugin and setting recallTimeoutMs=15000, logs showed both successful injections like "injecting 1 memories into context (31ms/15000ms budget)" and remaining warnings "recall timed out after 15000ms ..."`
- `follow-up mitigation status:` `added low-value skip policy so recall no longer runs on short acknowledgement turns and on rapid repeated turns without continuity markers`

## Backlog Mapping

- `should create backlog item:` `yes`
- `suggested priority:` `p1`
- `owner:` `memory-runtime + openclaw integration`
- `follow-up notes:` validate before/after with the same live scenario pack and compare user-facing recall behavior, not only post-turn runtime evidence
