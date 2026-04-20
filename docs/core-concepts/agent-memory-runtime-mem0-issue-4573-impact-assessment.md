# Mem0 Issue 4573: Impact Assessment For Agent Memory Runtime

Документ фиксирует оценку влияния обсуждаемой проблемы из `mem0` issue `#4573` на текущий проект `Agent Memory Runtime`.

Исходный контекст:

- [mem0 issue #4573](https://github.com/mem0ai/mem0/issues/4573)
- [comment 4146341455](https://github.com/mem0ai/mem0/issues/4573#issuecomment-4146341455)

Связанные внутренние документы:

- [agent-memory-runtime-common-problems.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-common-problems.md)
- [agent-memory-runtime-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-v1.md)
- [agent-memory-runtime-system-design-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-system-design-v1.md)
- [agent-memory-runtime-implementation-plan-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-implementation-plan-v1.md)

## 1. Краткий вывод

Проблема из issue `#4573` для нас:

- `стратегически`: `high`
- `в текущей реализации`: `medium-high`
- `при более глубокой опоре на mem0 core/add path и local LLMs`: `high`

Главный вывод:

`Agent Memory Runtime` уже защищен лучше, чем “чистый mem0 как память по умолчанию”, но ключевой риск `feedback-loop / recalled-memory re-ingestion` у нас пока не закрыт как first-class механизм.

Это не emergency-блокер для текущего MVP, но это серьезный риск для реального долговременного использования памяти и для качества long-term store на горизонте недель и месяцев.

## 2. О чем проблема в issue

Суть обсуждаемой проблемы:

- память быстро загрязняется некачественными или бессмысленными записями
- однажды извлеченные и подмешанные в контекст memories могут снова попадать в память как будто это новый факт
- system/boot/prompt scaffolding может ошибочно извлекаться как “пользовательская память”
- transient task state может становиться durable memory
- возможны fabricated identity/profile memories
- происходит amplification: плохая память усиливает саму себя

На практике это приводит к нескольким опасным последствиям:

- long-term store становится шумным
- retrieval становится менее полезным
- память начинает подкреплять свои собственные ошибки
- пользователь и агент теряют доверие к memory layer

## 3. Почему это важно именно для нас

Наш проект строится не как “еще один vector store”, а как долгоживущая память агента.

Значит для нас особенно опасны:

1. `self-reinforcing loops`
   Извлеченная память снова заезжает в ingestion и становится “новой правдой”.

2. `system-context leakage into memory`
   Boot files, operational prompts, recall briefs, operator instructions и служебный контекст превращаются в durable memory.

3. `transient-to-durable pollution`
   Временные статусы, текущие шаги, scratch-work и локальные task details ошибочно продвигаются в long-term.

4. `identity confusion`
   Система может хранить “профиль” субъекта там, где должна хранить рабочую память агента или проекта.

## 4. Что уже защищает нас сегодня

Текущая архитектура уже снижает часть риска.

### 4.1 Разделение memory spaces

У нас есть:

- `session-space`
- `project-space`
- `agent-core`
- `shared-space`

Это уже лучше, чем один общий memory bag.

### 4.2 Delayed promotion

Мы не пишем все подряд сразу в long-term.

Текущий путь:

`event -> episode -> consolidation -> memory_unit`

Это важное отличие от наивного “each message -> add memory”.

### 4.3 Dedupe and merge baseline

У нас уже есть:

- `dedupe_key` на ingestion
- `merge_key` в consolidation
- `create / merge`
- `supersede` для части противоречий

### 4.4 Low-trust rejection

В consolidation уже есть rejection для:

- instruction override
- prompt exfiltration
- explicit memory poisoning patterns

### 4.5 Session vs long-term boundaries

Мы уже добавили:

- negative pilot scenarios на `session-noise-not-promoted`
- quality gates на отсутствие session leakage в long-term recall

## 5. Что не закрыто

Вот реальные пробелы.

### 5.1 Нет provenance firewall

Система пока не различает на уровне policy:

- user-originated content
- agent output
- tool output
- recalled memory
- system boot context
- heartbeat / cron content
- operator templates

Это главный gap.

Пока ingestion не знает, что часть текста могла быть `recalled_memory`, а значит возможно повторное продвижение ранее извлеченного знания.

### 5.2 Нет explicit promotion decision layer

Сейчас главный gating идет через:

- `space_type`
- `event_type`
- `low_trust_reason`

Но нет отдельного семантического решения:

- `promote`
- `session_only`
- `reject`

То есть отсутствует полноценный storage quality gate.

### 5.3 Слабый identity policy

У нас пока нет явных правил, что нельзя формировать:

- fabricated personal profile
- inferred demographics/lifestyle
- host/system/operator pseudo-memory

### 5.4 Нет anti-recursive memory policy

Recall уже логируется как `recall_executed`, но нет жесткого правила:

- recalled memory нельзя автоматически снова консолидировать в long-term

### 5.5 Нет cleanup strategy для historical contamination

Если junk уже накопился в памяти, у нас нет отдельного remediation pass, который бы:

- находил loop-generated memories
- чистил boot/system noise
- переоценивал слабые durable memories

## 6. Текущая severity-оценка

### Severity for MVP pilot

- `medium`

Почему не `critical`:

- у нас mem0 не является единственным memory path
- long-term идет через наш собственный pipeline
- часть проблем уже снижена существующими guardrails

### Severity for real sustained usage

- `high`

Почему:

- на длинной дистанции без provenance policy память начнет усиливать шум
- при live OpenClaw usage риск feedback loops становится реальным
- при local models через `Ollama / LM Studio` extraction noise обычно выше

## 7. Особый риск: local LLMs

Для нас это особенно важно, потому что мы планируем использовать:

- `Ollama`
- `LM Studio`
- семейства `Qwen`
- семейства `Gemma`

Для таких моделей чаще встречаются:

- noisy outputs
- restated instructions
- markdown-wrapped structure
- partial formatting failures
- semantically plausible, but low-quality extraction candidates

Это увеличивает вероятность, что memory pipeline примет в durable store то, что должно было остаться transient или быть rejected.

## 8. Влияние на mem0 bridge

Наш `mem0 bridge` сейчас не самый опасный участок, потому что:

- sync идет из уже сформированных `memory_units`
- в bridge sync мы используем `infer=False`

То есть bridge не просит mem0 заново “извлекать память” из уже curated memory units.

Но риск все равно есть:

- если сам upstream mem0 search/sync path будет использовать polluted store
- если мы позже усилим роль mem0 в основном retrieval path
- если mem0 станет более активным write-path, а не только bridge

## 9. Рекомендуемое решение

### 9.1 Ввести provenance firewall

Нужно добавить явный origin/source-class на ingestion:

- `user_input`
- `agent_output`
- `tool_output`
- `recalled_memory`
- `system_boot`
- `heartbeat`
- `cron`
- `operator_template`

Правило:

- `recalled_memory`, `system_boot`, `heartbeat`, `cron`, `operator_template` по умолчанию не могут продвигаться в long-term

### 9.2 Ввести storage quality gate

Перед `memory_unit` creation/merge/supersede должен быть отдельный decision step:

- `promote`
- `session_only`
- `reject`

Минимальные сигналы:

- novelty
- trust
- source class
- durability likelihood
- transientness
- identity fit

### 9.3 Ввести identity-aware rejection policy

Явно запрещать или понижать confidence для:

- fabricated profile statements
- broad personality/demographic inference
- host/system bootstrap facts вне allowlist
- prompt scaffolding

### 9.4 Ввести anti-recursive memory policy

Явное правило:

- memories injected by recall never become durable just because they reappeared in the next prompt context

### 9.5 Добавить cleanup/remediation pass

Нужен отдельный maintenance flow для:

- loop-generated duplicates
- boot/system contamination
- weak long-term memories with low usefulness

## 10. Предлагаемый implementation plan

### Phase 1. Provenance model

- расширить schemas/events/adapters полем `event_origin`
- добавить propagation этого поля из интеграций
- обновить ingestion tests

### Phase 2. Promotion gate

- добавить отдельный `promotion_decision` layer в consolidation
- реализовать `promote / session_only / reject`
- покрыть unit/component tests

### Phase 3. Feedback-loop protection

- явно блокировать long-term promotion для `recalled_memory`
- добавить regression scenarios на recursive memory injection

### Phase 4. Identity and boot-noise policy

- добавить heuristics и allow/deny policy
- покрыть negative scenarios

### Phase 5. Historical cleanup

- maintenance script/job для existing memory store
- report on suspicious durable memories

## 11. Какие тесты нужны

Обязательно добавить:

1. `recalled-memory-not-promoted`
2. `system-boot-not-promoted`
3. `heartbeat-not-promoted`
4. `transient-task-state-stays-session-only`
5. `fabricated-profile-rejected`
6. `operator-template-not-promoted`
7. `memory-loop-does-not-amplify-over-multiple-cycles`

## 12. Итоговая позиция

Issue `#4573` не означает, что наш проект уже “сломанный”.

Но он очень точно подсвечивает класс проблем, который:

- уже частично актуален для нас
- станет еще важнее при live usage
- почти наверняка усилится при local LLM deployments

Поэтому правильная позиция такая:

- признать риск серьезным
- не паниковать
- не считать существующие low-trust filters достаточными
- добавить provenance-first and anti-recursive memory policy как ближайший hardening step

## 13. Рекомендация по приоритету

Приоритет:

- `high`

Рекомендованный порядок:

1. provenance firewall
2. promotion decision layer
3. anti-recursive memory tests
4. identity / boot-noise policy
5. cleanup tooling
