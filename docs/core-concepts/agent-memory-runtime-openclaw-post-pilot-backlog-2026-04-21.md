# Agent Memory Runtime: OpenClaw Post-Pilot Backlog

## Pilot Context

- `pilot date:` `2026-04-21`
- `pilot outcome:` `conditional-go`
- `result document:` [agent-memory-runtime-openclaw-pilot-result-2026-04-21.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-openclaw-pilot-result-2026-04-21.md)

## Backlog Table

| ID | Title | Priority | Layer | Source finding | Reproducible | Next action | Owner |
|---|---|---|---|---|---|---|---|
| `BL-001` | Make OpenClaw plugin recall timeout configurable and instrumented | `p1` | `Adapters / OpenClaw Contract` | `F-2026-04-21-001` | `yes` | Add config knob, latency logs, and rerun live pack | `integration` |
| `BL-002` | Improve live recall packing so durable architecture facts land in cleaner slots | `p2` | `Retrieval` | `pilot result notes` | `yes` | Tune slot assignment for infrastructure-oriented facts | `runtime` |
| `BL-003` | Silence or formalize `plugins.allow` warning for trusted local plugin setup | `p3` | `Documentation / Runbooks` | `pilot logs` | `yes` | Document recommended allowlist config for live pilots | `docs` |

## Priority Rules

- `p0`:
  блокирует пилот или делает память опасно/явно некорректной
- `p1`:
  сильно бьет по качеству recall или continuity
- `p2`:
  заметно ухудшает UX/операционку, но не блокирует прогон
- `p3`:
  улучшение качества, удобства или ясности без срочности

## Grouping By Layer

### Retrieval

- `items:` `BL-002`

### Consolidation

- `items:` `none from this pilot`

### Lifecycle

- `items:` `none from this pilot`

### Adapters / OpenClaw Contract

- `items:` `BL-001`

### Worker / Observability / Ops

- `items:` `none blocking after current live run`

### Documentation / Runbooks

- `items:` `BL-003`

## Recommended Next Sprint Slice

- `must fix before next pilot:` `BL-001`
- `should fix soon after next pilot:` `BL-002`
- `can defer:` `BL-003`

## Validation Plan

- `which scenarios must be rerun after fixes:` `durable architecture decision`, `active session carryover`, `cross-session continuity`
- `which quality-eval checks must stay green:` full `memory-runtime` suite, `pilot-scenarios`, `pilot-negative-scenarios`, `openclaw-live-pilot`
- `which metrics / traces should be compared before vs after:` plugin timeout frequency, recall trace selection patterns, live scenario pass rate, and user-facing injected memory quality
