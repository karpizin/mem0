# Agent Memory Runtime Upstream Sync Plan

## Goal

Safely rebase our project direction onto the current `upstream/main` of `mem0ai/mem0` without losing the work already done in `codex/local-model-compat-docs`.

## Current State

- `main` has been moved to track `upstream/main`
- integration branch created: `codex/upstream-sync-integration`
- source branch with our work remains intact: `codex/local-model-compat-docs`
- `codex/local-model-compat-docs` is ahead of the old base by `55` commits
- `upstream/main` is ahead of the old base by `115` commits

## Important Working Tree Note

After switching to `codex/upstream-sync-integration` inside the same directory, files that do not exist in `upstream/main` remained as untracked paths in the working tree, including `memory-runtime/`.

That means the branch structure is correct, but actual transfer work should continue either:

1. in a clean git worktree created from `codex/upstream-sync-integration`, or
2. after explicitly cleaning untracked carry-over files in this directory.

The recommended path is a clean worktree, because it preserves safety and makes conflicts easier to reason about.

## Sync Strategy

### Layer 1: Core Runtime and Core Documentation

Status: completed on `codex/upstream-sync-integration`

Transfer first:

- `ad5bd379` Add agent memory runtime phase A scaffold
- `66f12aa1` Add memory runtime phase B data model and namespace API
- `f39e0ac6` Add memory unit lifecycle diagram
- `194f8e33` Add memory runtime phase C event ingestion
- `a6970d02` Add memory runtime phase D recall MVP
- `998ff78f` Add memory runtime phase E consolidation pipeline
- `0f5b16b7` Add memory runtime phase F lifecycle management
- `db4f2ce7` Add memory runtime phase G adapters
- `32155cb6` Add memory runtime phase H observability
- `7bf2d761` Add memory runtime phase I quality loop
- `c7bfe899` Add agent memory runtime common problems document

Why first:

- this is the main body of the new project
- it mostly lives in `memory-runtime/` and `docs/core-concepts/`
- overlap with upstream is limited compared to `openclaw/` and `mem0/`

Expected conflict level: low to medium

### Layer 2: OpenClaw Integration and Pilot Hardening

Status: completed on `codex/upstream-sync-integration`

Transfer second:

- `4a245d5a` Add memory runtime phase J openclaw integration
- `7fef6420` Add OpenClaw pilot readiness flow
- `ad64e617` Harden worker startup for synthetic pilot
- `3dae0213` Fix adapter long-term scope leakage
- `486c368b` Use shared observability metrics for worker
- `3660de9a` Add worker readiness diagnostics
- `5dd728a9` Automate OpenClaw pilot smoke flow
- `281575eb` Add recall quality eval harness
- `4c5c1709` Tune retrieval selection for quality eval
- `4dde1c0c` Add OpenClaw pilot scenario pack
- `a4b6c8e5` Tune consolidation merge and contradiction handling
- `c4713a61` Add pilot operational polish helpers
- `9e66ceb3` Expand pre-pilot quality regression pack
- `951c4a56` Add low-trust consolidation baseline
- `a098d3d4` Add post-pilot documentation templates
- `40096511` Expand recall evaluation scenario pack
- `dadb725a` Add quality evaluation scoring metrics
- `76f34c14` Add lifecycle evaluation harness
- `5f0c4a82` Add adversarial memory evaluation suite
- `8c3ded5a` Add continuity benchmark scenarios
- `64eef68c` Add evaluation regression comparison harness
- `ace912e0` Automate OpenClaw pilot scenario subset
- `10ff1a08` Add unified OpenClaw preflight check
- `42cef188` Add ingestion idempotency guard
- `1b8b53fd` Add recall trace explainability
- `e9375ac6` Add low-budget brief compactness regression
- `7f5a8362` Add failure-mode end-to-end coverage
- `898a2a97` Add shared-memory edge case coverage
- `c4ac50b2` Add long-horizon memory evolution coverage
- `0ebeed40` Add pilot snapshot and restore workflow
- `77e51a24` Export pilot trace artifact bundles
- `f3bfeb71` Add live pilot memory inspection helpers
- `26803a83` Add negative pilot scenario gate
- `ddcab7fc` Add live pilot scoring helper
- `e3248cc5` Add pilot checklist, coverage matrix, and mem0 issue assessment

Why second:

- these are high-value runtime and pilot features
- they touch `openclaw/` contracts and test harnesses more often
- upstream has changed `openclaw/` significantly, so this layer should come after the runtime baseline is stable

Expected conflict level: medium to high

Validation completed:

- `memory-runtime`: `101 passed`
- `memory-runtime`: `ruff check .`
- `openclaw`: `vitest runtime-provider.test.ts`
- `openclaw`: `tsc --noEmit`

### Layer 3: MCP Facade

Status: completed on `codex/upstream-sync-integration`

Transfer third:

- `67f0ee12` Add MCP facade specification and roadmap phase
- `841fb9d8` Implement memory runtime MCP facade
- `57f44812` Add MCP usage guide
- `6c430be2` Add MCP next steps and guardrails plan

Why third:

- depends on the runtime surface already being present
- mostly isolated inside `memory-runtime/` and docs
- lower merge risk than direct `openclaw/` changes

Expected conflict level: low to medium

Validation completed:

- `memory-runtime`: `108 passed`
- `memory-runtime`: `pytest tests/component/test_mcp_api.py -q`
- `memory-runtime`: `ruff check .`

### Layer 4: Local LLM Hardening

Status: completed on `codex/upstream-sync-integration`

Transfer fourth, manually:

- `76f3aef6` Add local model compatibility guide
- `f30f6798` Harden local LLM parsing for Ollama

Why manual handling is required:

- upstream changed `mem0/`, `tests/memory/`, `tests/llms/`, and docs in overlapping areas
- this should not be cherry-picked blindly
- these commits should be ported as a manual reconcile against current upstream implementations

Expected conflict level: high

Applied scope:

- robust `remove_code_blocks` / `extract_json` behavior for local-model wrappers
- `OllamaLLM` JSON-path hardening for chatty local outputs
- editable-install `__version__` fallback
- targeted docs note for Ollama local-companion guide

Intentionally not included:

- `chunk mode`
- entry granularity changes in `mem0.memory.main`
- prompt/config changes related to chunk extraction

Validation completed:

- `tests/test_chatty_llm_parsing.py`: green
- `tests/llms/test_ollama.py`: green
- targeted lint on touched files: green

### Layer 5: Presentations and Analytics

Status: pending

Transfer last:

- `5aff9bab` Add project presentation decks
- `0736642d` Polish presentation styling and add short deck
- `a579f8a1` Add 10-hour work summary

Also decide separately whether to retain older time-boxed analytics documents:

- `agent-memory-runtime-last-7-hours-work-summary.md`
- `agent-memory-runtime-last-9-hours-work-summary.md`

Why last:

- not on the runtime critical path
- low product risk if delayed
- can be restored anytime after the core sync is stable

Expected conflict level: low

## Recommended Execution Sequence

1. create a clean worktree for `codex/upstream-sync-integration`
2. port Layer 1 and run runtime tests
3. port Layer 2 and run runtime plus OpenClaw-oriented tests
4. port Layer 3 and run MCP tests
5. manually reconcile Layer 4 and run targeted `mem0` parser/Ollama tests
6. restore Layer 5 as final polish

## Definition of Success

- our runtime architecture survives on top of current `upstream/main`
- the new branch contains the same project direction without force-merging old assumptions into new upstream code
- `memory-runtime` tests pass on the integrated branch
- `openclaw` integration remains functional on top of upstream’s latest state
- local-model hardening is ported carefully instead of being overwritten or lost
