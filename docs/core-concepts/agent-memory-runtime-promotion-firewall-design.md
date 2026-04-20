# Agent Memory Runtime Promotion Firewall Design

## Why This Exists

The memory-junk problem is not only a duplicate problem.

The more dangerous class of failures is:

- recalled memory gets re-ingested and amplified
- system/bootstrap text is promoted into long-term memory
- transient task state becomes durable project knowledge
- valid-looking but low-value procedural text crowds out durable facts
- aggressive filtering removes useful knowledge too early

The right response is not a single rejection heuristic.

We need a promotion system that is:

- strict about provenance
- conservative about rejection
- biased toward `session-only` over hard discard
- explicit about why something was promoted or blocked

## Design Principles

1. `Provenance before semantics`
Source class matters before content ranking.
If content came from recalled memory or a heartbeat, semantic quality alone should not make it durable.

2. `Session-only is safer than reject`
If the system is unsure, it should prefer to keep the signal in short-term memory rather than fully discard it.

3. `Promotion must be explicit`
The system should make an explicit decision:

- `promote`
- `session_only`
- `reject`

This should eventually become a first-class internal decision layer.

4. `Audit every blocked promotion`
If the system blocks or demotes a candidate, we must know why.

5. `Useful memory rescue must remain possible`
The system should avoid hard rejection except for clearly unsafe or clearly low-trust cases.

## Planned Model

### Event Origin

Every ingested event should carry an `event_origin`.

Initial allowed origins:

- `user_input`
- `agent_output`
- `tool_output`
- `recalled_memory`
- `system_boot`
- `heartbeat`
- `cron`
- `operator_template`
- `external_import`

This is not a trust score.
It is provenance.

### Promotion Decisions

Future target model:

| Decision | Meaning |
| --- | --- |
| `promote` | Durable memory candidate is eligible for long-term consolidation |
| `session_only` | Keep only as short-lived/episodic signal; do not create durable memory |
| `reject` | Do not keep as memory candidate |

### Baseline Policy

For the first implementation step:

- `recalled_memory` -> `session_only`
- `system_boot` -> `session_only`
- `heartbeat` -> `session_only`
- `cron` -> `session_only`

Rationale:

- these origins are important for immediate context or system operation
- they should not be durable by default
- they are not necessarily malicious, so hard rejection would be too aggressive

Low-trust poisoning patterns remain a separate rejection path.

## Step-by-Step Rollout

### Step 1: Provenance Firewall Baseline

Scope:

- add `event_origin` to `memory_events`
- carry it through ingestion and adapters
- infer safe defaults when origin is not provided explicitly
- consult origin during consolidation
- demote blocked origins to `session_only`
- write audit records for blocked promotion

Expected behavior:

- dangerous self-amplifying sources stop entering durable memory
- useful user/agent/tool content still follows the normal pipeline
- mixed `system + user + assistant` capture payloads no longer let the `system` portion dominate summary/consolidation when non-system content is present

This is the step being implemented now.

### Step 2: Promotion Decision Layer

Add a dedicated internal decision function that combines:

- provenance
- scope
- novelty
- durability
- transientness
- low-trust signals
- identity fit

This should return one of:

- `promote`
- `session_only`
- `reject`

Current implementation status:

- implemented as an explicit internal decision layer in consolidation
- provenance, low-trust, and transientness are now evaluated in one place
- low-value assistant/tool operational notes are also demoted through the same decision layer
- long-term candidates can now be:
  - promoted
  - demoted to `session_only`
  - rejected
- `session-space` / inferred short-term candidates continue to materialize as short-term memory units
  so existing short-term lifecycle behavior is preserved
- structured logs should capture:
  - incoming event provenance
  - promotion decision and signals
  - final consolidation outcome
  - worker job execution path

### Step 3: Rescue Loop

Add signals that allow useful `session_only` content to be promoted later, for example:

- repeated recurrence across sessions
- positive recall usefulness feedback
- merge pressure from multiple similar episodes

### Step 4: False-Negative Evaluation Layer

Add dedicated tests for useful memories that must not be filtered out:

- durable project decisions
- stable procedures
- important tool-state summaries
- long-lived preferences

## Default Inference Rules for Step 1

If `event_origin` is not provided explicitly:

- all-system messages -> `system_boot`
- tool-only event -> `tool_output`
- assistant-only event -> `agent_output`
- otherwise -> `user_input`

Additionally:

- `event_type == heartbeat` -> `heartbeat`
- `event_type == cron` -> `cron`

These defaults are intentionally conservative.
They should minimize accidental demotion of useful content.

## Why This Helps Without Over-Filtering

This design is intentionally biased against early hard rejection.

It helps preserve useful memory because:

- user/agent/tool content still flows through the normal pipeline
- blocked origins are demoted to `session_only`, not deleted
- low-trust rejection remains reserved for clearly harmful patterns

In other words:

- provenance handles junk amplification
- low-trust handles poisoning
- low-value heuristics handle truthful-but-noisy operational chatter
- later promotion logic handles usefulness

## Initial Test Plan

Step 1 should add regression coverage for:

- explicit `recalled_memory` origin is stored on the event
- default origin inference works for normal user/assistant events
- `recalled_memory` project-space candidate does not create a durable `memory_unit`
- `system_boot` and `heartbeat` durable candidates are demoted
- normal durable project decisions still consolidate correctly

## Non-Goals of Step 1

This first step does not try to solve:

- final confidence scoring
- learned promotion policies
- rescue from `session_only` to `promote`
- identity hallucination filtering
- privacy classification

Those come next.
