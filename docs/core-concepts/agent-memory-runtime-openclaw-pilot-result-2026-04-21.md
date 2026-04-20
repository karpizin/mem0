# Agent Memory Runtime: OpenClaw Pilot Result

## Pilot Metadata

- `date:` `2026-04-21`
- `operator:` `Codex`
- `runtime commit:` `1b818397`
- `openclaw commit/config version:` `local linked plugin, OpenClaw 2026.3.22 runtime mode`
- `environment:` `local live contour, OpenClaw on host + memory-runtime in Docker`
- `namespace mode:` `isolated`
- `notes:` `Run name: post-docs-rerun. Live pack executed through openclaw agent --local against pilot-user-2.`

## Scenario Summary

| Scenario | Expected | Actual | Status |
|---|---|---|---|
| Bootstrap scope | Existing runtime namespace/agent scope resolves and remains usable | Existing scope reused successfully for `pilot-user-2` | `passed` |
| Durable architecture decision | Durable project fact about runtime stack is recalled and visible in long-term surface | Returned through durable project context; long-term surface stayed durable-only | `passed` |
| Standing procedure recall | Procedural guidance survives consolidation and comes back on demand | Procedure recalled correctly | `passed` |
| Active session carryover | Current work context is available during the same live session | Relevant live pilot context recalled successfully | `passed` |
| Cross-session continuity | New session recalls prior checkpoint from earlier work | Prior checkpoint returned via project context | `passed` |
| Noise resistance | Scratch/session noise does not pollute durable long-term list/search | `noise-resistance` passed after adapter guardrail fix | `passed` |

## Key Evidence

- `healthz:` `200 OK` on `http://127.0.0.1:8080/healthz`
- `observability snapshot:` `jobs_processed_total=61`, `jobs_failed_total=0`, `consolidation_created_total=13`, `consolidation_merged_total=15`
- `metrics snapshot:` `recall_requests_total=9`, `recall_candidates_total=179`, `recall_selected_total=10`
- `last smoke report:` synthetic gates already green before live run
- `last quality-eval report:` quality/eval contour green before live run

## Recall Quality Notes

- `best recall behavior observed:` durable architecture, standing procedure, continuity, and noise-resistance all returned the expected project context on the live contour
- `worst recall behavior observed:` recall is still sometimes packed as `active_project_context` rather than cleaner `critical_facts` / `prior_decisions`
- `missing memories:` none at scenario verdict level in `post-docs-rerun`
- `unexpected memories:` none in durable adapter `list/search`; raw `episode` leakage no longer reproduced
- `trace patterns worth noting:` selected items consistently came from `project-space`; `project_infrastructure` and `semantic_overlap` dominated decisive signals

## Operational Notes

- `startup issues:` none during this run after migration-aware startup hardening
- `worker issues:` none observed; queue stayed healthy with `pending=0`, `running=0`
- `queue/backlog issues:` none observed
- `adapter contract issues:` long-term adapter surface behaved correctly after durable-only guardrail fix
- `debuggability notes:` trace bundles and structured logs were sufficient to explain scenario selection

## Findings Created

- `finding-1:` [agent-memory-runtime-openclaw-finding-recall-timeout-2026-04-21.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-openclaw-finding-recall-timeout-2026-04-21.md)

## Final Assessment

- `pilot outcome:` `conditional-go`
- `main blockers before next pilot:` inline plugin recall still logs `recall timed out after 8000ms`, which can reduce user-facing benefit even though the runtime itself is healthy
- `recommended next actions:`
  - make plugin recall timeout configurable or more tolerant for live contexts
  - measure end-to-end recall latency inside the plugin path
  - tighten prompt/build payload size or reduce cold-start broadening when it does not materially help
