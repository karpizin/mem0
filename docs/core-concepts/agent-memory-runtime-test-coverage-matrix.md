# Agent Memory Runtime: Test Coverage Matrix

Документ фиксирует текущую полноту тестового контура `memory-runtime` перед первым живым `OpenClaw` пилотом.

Оценка делается не относительно “идеального будущего production-grade memory platform”, а относительно двух горизонтов:

- `MVP Pilot Readiness`
- `Production / Release Hardening`

## Executive Summary

Текущий тестовый контур сильный для `MVP pilot` и уже заметно выше среднего для молодого memory-runtime проекта.

Грубая оценка полноты:

- `75-80%` относительно потребностей первого живого `OpenClaw` пилота
- `50-60%` относительно более строгого production-grade релизного уровня

Сильные стороны:

- многоуровневый контур: `unit`, `component`, `integration`, `e2e`, `golden`, `eval`, `synthetic pilot`
- покрыты ключевые доменные механизмы: `ingestion`, `recall`, `consolidation`, `lifecycle`
- есть quality-oriented tests, а не только correctness-oriented tests
- есть pilot-facing automation: `preflight`, `pilot-smoke`, `pilot-scenarios`, `quality-eval`, `continuity-benchmark`

Основные пробелы:

- живой `OpenClaw` behavioral E2E на реальном конфиге
- performance / load / soak coverage
- fault-injection / failure-mode coverage
- long-horizon memory semantics
- более глубокие multi-agent / shared-memory edge cases

---

## Coverage Matrix

| Area | What It Covers | Current Coverage | Confidence | Why This Rating |
|---|---|---:|---:|---|
| API baseline | health, namespaces, events, recall, adapters, observability | 90% | High | Core API routes покрыты component tests и регулярно проходят в полном suite |
| Data model / repositories | repositories, migrations, core persistence behavior | 80% | High | Есть migration tests, repository integration tests и косвенное покрытие через component/e2e |
| Ingestion correctness | normalization, project extraction, default space routing, dedupe key computation | 85% | High | Unit + component tests есть, недавно усилено idempotency guard |
| Ingestion idempotency | duplicate delivery on same dedupe key | 85% | High | Есть явный component test и runtime guard, но нет stress/retry burst scenarios |
| Episode formation | event -> episode linkage and summary/raw text generation | 75% | Medium-High | Покрыто через events API и ingestion path, но мало edge-case tests на сложные message bundles |
| Consolidation pipeline | episode -> memory unit, create/merge/supersede behavior | 75% | Medium-High | Есть unit/component tests и tuning, но не исчерпаны длинные contradiction chains и compaction-heavy cases |
| Recall ranking | query overlap, procedural boosts, integration/storage intent, usefulness feedback | 80% | High | Сильный unit layer + quality evals, trace explainability тоже покрыта |
| Brief packing | slotting, compactness, selected_count discipline | 75% | Medium-High | Есть golden brief, compactness regression, но budget behavior еще можно расширять |
| Lifecycle behavior | decay/archive/evict/no-op decisions | 75% | Medium-High | Есть lifecycle unit tests и отдельный lifecycle eval harness |
| Observability | stats, metrics exposure, worker shared counters | 70% | Medium | API и counters покрыты, но нет глубоких тестов на metric consistency under failure/load |
| Worker behavior | startup, retry on DB availability, pending jobs processing | 75% | Medium-High | Есть startup hardening, worker main tests и pipeline tests, но мало crash/restart scenarios |
| Adapter contracts | OpenClaw/BunkerAI adapter shape, shared namespace contract | 75% | Medium-High | OpenClaw path сильнее, shared adapter baseline есть, BunkerAI live-side пока не доведен |
| Shared memory semantics | shared namespace recall + private agent-core isolation | 65% | Medium | Основа покрыта integration tests, но edge cases и contamination scenarios еще умеренно покрыты |
| Security / poisoning baseline | low-trust rejection, adversarial memory inputs | 70% | Medium | Для MVP хороший baseline, но это не полноценный security contour |
| Quality evaluation | recall quality, lifecycle quality, adversarial acceptance/rejection | 85% | High | Есть eval fixtures, metrics, regression harness и automation |
| Continuity / pilot readiness | smoke, continuity benchmark, pilot subset, preflight | 90% | High | Очень сильный слой именно для MVP pilot readiness |
| Real-world operational resilience | real docker orchestration, degraded dependencies, partial failure, live OpenClaw config | 45% | Low-Medium | Часть smoke есть, но много еще synthetic и не на боевом контуре |
| Performance / scalability | throughput, queue backlog growth, latency under load | 20% | Low | Почти не покрыто |
| Long-run memory hygiene | long-horizon forgetting, repeated compression over time, memory drift | 35% | Low | Есть lifecycle baseline, но нет длинных сценариев и soak-like evals |

---

## Detailed Assessment By Layer

## 1. Unit Layer

Текущее состояние: `сильное`

Что покрыто хорошо:

- `config`
- `ingestion` normalization и deterministic `dedupe_key`
- `retrieval` ranking and slot behavior
- `consolidation` service semantics
- `lifecycle` decisions
- `mem0 bridge` seam
- `metrics`/telemetry helpers
- `worker main` startup behavior
- `regression compare` harness

Сильные стороны:

- unit tests проверяют именно доменные правила, а не только trivial helpers
- retrieval logic покрыта заметно лучше, чем обычно бывает на раннем этапе
- lifecycle and consolidation имеют собственный unit contour, а не висят только на e2e

Ограничения:

- мало pure-unit coverage для explainability scoring internals beyond one focused test
- почти нет property-style tests на ranking stability
- нет fuzz-style tests на normalization/edge payload forms

Оценка:

- `85%` для MVP
- `65%` для production-grade confidence

## 2. Component Layer

Текущее состояние: `очень сильное`

Что покрыто:

- `health`
- `namespaces`
- `events`
- `recall`
- `observability`
- `adapters`
- `consolidation pipeline`
- `lifecycle pipeline`
- `quality eval`
- `adversarial eval`
- `pilot smoke`

Сильные стороны:

- component tests проверяют реальные HTTP контракты
- доменные пайплайны тестируются через API, а не только через внутренние вызовы
- есть полезные product-like assertions, а не только `status_code == 200`

Ограничения:

- пока мало component tests на intentionally broken operational states
- нет отдельного слоя на malformed-but-valid high-noise workloads

Оценка:

- `90%` для MVP
- `70%` для production

## 3. Integration Layer

Текущее состояние: `хорошее, но не глубокое`

Что покрыто:

- `migrations`
- `repositories`
- `shared recall` semantics

Сильные стороны:

- интеграции persistence-layer не оставлены без внимания
- shared namespace contract уже имеет базовую проверку

Ограничения:

- integration layer пока сравнительно узкий
- мало tests на multi-step upgrade semantics
- мало tests на repository behavior under unusual state transitions

Оценка:

- `70%` для MVP
- `55%` для production

## 4. End-to-End Layer

Текущее состояние: `сильное для synthetic MVP, умеренное для real-world`

Что покрыто:

- `OpenClaw pilot flow`
- `continuity benchmark`
- `pilot scenarios`
- `preflight`

Сильные стороны:

- e2e не ограничены “smoke for smoke’s sake”
- есть continuity-centric сценарии, что особенно важно для memory-runtime
- есть preflight и operator-facing automation

Ограничения:

- пока это synthetic e2e, а не real OpenClaw runtime behavior на вашем реальном конфиге
- нет end-to-end на real mem0 server dependency path under real environment
- нет long-run multi-session repeated pilot loops

Оценка:

- `85%` для MVP
- `50%` для production

## 5. Quality / Eval Layer

Текущее состояние: `очень сильное`

Что покрыто:

- `recall_quality_scenarios`
- `lifecycle_quality_scenarios`
- `adversarial_memory_scenarios`
- continuity benchmark
- before/after report comparison
- compactness regression

Сильные стороны:

- это уже не просто test suite, а quality measurement layer
- есть machine-readable metrics:
  - `required_hit_rate`
  - `forbidden_leak_rate`
  - `mean_scenario_score`
  - `action_match_rate`
  - `status_match_rate`
  - `rejection_rate`
  - `false_accepts`
  - `false_rejects`
  - `avg_selected_count`
- есть regression harness для сравнения before/after

Ограничения:

- recall eval pack еще не очень большой
- мало сценариев на very subtle ambiguity
- пока не сравниваем agent outcome with/without memory на реальном agent loop

Оценка:

- `90%` для MVP
- `70%` для production

## 6. Operational Readiness Layer

Текущее состояние: `хорошее перед пилотом`

Что покрыто:

- `preflight`
- `pilot-smoke`
- `show-last-*`
- `reset-pilot`
- runbook + troubleshooting docs

Сильные стороны:

- есть operator-facing commands, а не только developer tests
- live-debugging сильно облегчен
- preflight проверяет functional round-trip, а не только endpoint liveness

Ограничения:

- нет настоящих chaos/dependency interruption checks
- нет explicit SLO/SLA style assertions
- нет automated soak/recovery tests

Оценка:

- `80%` для MVP
- `45%` для production

---

## What Is Covered Well

Эти зоны можно считать хорошо закрытыми для первого live pilot:

- базовый API contract
- основная persistence semantics
- event ingestion
- duplicate event guard
- recall ranking baseline
- memory brief structure
- consolidation baseline
- lifecycle baseline
- observability basics
- pilot smoke and continuity
- quality regression flow
- adversarial ingestion baseline
- operator preflight

---

## What Is Covered Partially

Эти зоны уже не пустые, но confidence пока средний:

- shared-memory isolation
- contradiction-heavy consolidation
- long-term memory evolution over many cycles
- observability correctness under unusual states
- worker failure semantics
- adapter behavior beyond main OpenClaw path
- compactness under multiple query styles
- explainability stability across ranking changes

---

## What Is Weakly Covered Or Barely Covered

Эти зоны пока остаются главными blind spots:

- real OpenClaw live configuration behavior
- performance / load
- queue backlog stress
- dependency degradation mid-run
- crash recovery after job pickup
- large namespace / many-agent scenarios
- long-horizon retention drift
- release compatibility across multiple migration generations

---

## Risk Matrix

| Risk | Current Detection Ability | Residual Risk |
|---|---:|---:|
| Basic API regression | High | Low |
| Wrong recall ranking on common prompts | High | Medium-Low |
| Duplicate ingestion via retry | High | Low |
| Long-term memory pollution by simple prompt poisoning | Medium-High | Medium |
| Worker not processing jobs at all | High | Low |
| Shared-memory contamination edge case | Medium | Medium-High |
| Contradiction merge regression | Medium | Medium |
| Performance collapse under burst traffic | Low | High |
| Latent bug appearing only in real OpenClaw config | Low-Medium | High |
| Slow memory drift over days of use | Low | High |

---

## Coverage By Pilot-Relevance

### Critical For Tomorrow’s Live Pilot

These are already in good shape:

- preflight readiness
- OpenClaw synthetic flow
- continuity
- recall quality baseline
- low-trust baseline
- observability basics
- troubleshooting docs

### Important But Not Blocking For Tomorrow

- deeper shared-memory semantics
- advanced contradiction handling tests
- richer compactness scenarios
- more explainability regression checks

### Important After First Live Pilot

- real-world OpenClaw outcome benchmarks
- fault injection
- soak tests
- load tests
- migration upgrade path hardening
- long-horizon memory hygiene evaluations

---

## Recommended Post-Pilot Test Backlog

### Priority 1

- live `OpenClaw` behavioral E2E on your real config
- failure-mode tests for worker/database degradation
- shared-memory privacy edge-case tests

### Priority 2

- performance smoke/load baseline
- contradiction-chain consolidation scenarios
- longer recall eval pack with more ambiguous prompts

### Priority 3

- soak tests across repeated sessions
- release migration matrix
- multi-agent scale scenarios

---

## Final Verdict

Текущий test suite:

- `достаточно полный для первого честного live OpenClaw pilot`
- `сильный по продуктовой и доменной валидации`
- `еще не достаточный для claims уровня production-hard memory platform`

Если формулировать совсем прямо:

- как `MVP pilot gate` тестовый контур уже хороший
- как `release confidence system` он пока хороший, но еще не зрелый
- главный remaining uncertainty теперь уже не в “покрыли ли мы синтетику”, а в том, как это поведение проявится на вашем реальном `OpenClaw` конфиге и живых рабочих сценариях
