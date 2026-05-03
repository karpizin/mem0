# mem0plus: Memory Review Surface V1

## Purpose

Этот документ фиксирует минимальный `memory review surface` для `mem0plus v1`.

Цель review-surface не в том, чтобы превратить память в ручную knowledge base, а в том, чтобы дать пользователю и оператору `минимально достаточный control layer`:

- посмотреть, что агент запомнил;
- исправить неточную или устаревшую запись;
- удалить или скрыть нежелательное воспоминание;
- работать с `private` и `group` памятью без лишней когнитивной нагрузки.

Продуктовый принцип остается тем же, что и в `product definition v1`:

`memory should mostly manage itself; review is a correction layer, not the primary operating mode`

## Product Role

`Memory review surface` — это первый обязательный продуктовый слой поверх memory engine.

Без него память остается сильной backend-capability, но ощущается как black box.
С ним память становится:

- наблюдаемой;
- исправляемой;
- пригодной для real-world trust;
- достаточно управляемой для builder-first self-hosted deployments.

## Primary Users

### Primary

`Developers and operators of agent platforms`

Именно они:

- отлаживают behavior памяти;
- проверяют, что персональная память действительно полезна;
- убирают junk или outdated memories;
- контролируют shared project memory между агентами.

### Secondary

`Power users of personal assistants`

Не главный фокус `v1`, но review-surface уже должен быть достаточно простым, чтобы потом его можно было показать конечному пользователю без полной переработки модели.

## Review Surface Goals

В `v1` review-surface должен решать `4` задачи:

1. `Inspect`
Пользователь может увидеть активные memories в выбранном scope.

2. `Correct`
Пользователь может обновить формулировку memory item без обхода memory pipeline вручную.

3. `Forget / Mark incorrect`
Пользователь может убрать memory item из активного использования.

4. `Scope-aware trust`
Пользователь понимает, в каком memory scope находится запись:
- `private`
- `group`

## Supported Scopes

В `v1` review-surface отражает product scope model:

- `private`
- `group`

### Private

Память, относящаяся к одному агенту или личному контуру ассистента.

### Group

`Project memory`, разделяемая между несколькими агентами, работающими в одном проекте.

### Not in V1

- `global`
- item-level ACL
- сложные share rules между произвольными группами агентов

## Reviewable Memory Objects

На внутреннем уровне система уже различает разные memory objects, но во `v1` review-surface не обязан раскладывать их на сложную онтологию.

Пользователь видит просто `memory items`.

Под капотом это могут быть:

- durable `memory_unit`
- session `episode`

### Why this matters

Это дает простой UX, но при этом позволяет runtime по-разному вести себя на review:

- durable memory можно `обновить` или `мягко убрать` из active слоя;
- session memory можно `обновить` или `удалить` как transient scratchpad.

## Required V1 Actions

### 1. View

Обязательная возможность:

- увидеть список memory items;
- открыть detail view конкретной memory item;
- видеть, является ли она `private` или `group`.

Минимальные поля для списка:

- text preview
- scope
- source kind
- created/updated timestamps
- sensitive marker

Минимальные поля для detail view:

- full text
- scope
- source kind
- created/updated timestamps
- sensitivity state
- status

### 2. Update

Пользователь может исправить memory item.

Ожидаемое поведение:

- old content заменяется новым;
- запись остается в памяти как активная;
- internal metadata и audit trail обновляются автоматически;
- sensitive classification пересчитывается автоматически.

Это нужно для случаев:

- memory сформулирована неудачно;
- агент сохранил неполный факт;
- факт изменился, но объект памяти логичнее обновить, а не удалять.

### 3. Force Forget

Пользователь может принудительно убрать запись из активного использования.

Во `v1` это реализуется через review behavior:

- durable memory: soft-hide / deactivate from active recall surface
- session memory: remove transient item

Важно: UX может называть это `Forget`, даже если под капотом durable запись не физически удаляется сразу, а переводится в неактивное состояние.

### 4. Mark Incorrect

Это отдельное действие от просто удаления.

Ожидаемое поведение:

- memory считается ошибочной;
- она больше не участвует в recall/list/search как active item;
- остается audit trail, что запись была признана неверной.

Это особенно важно для:

- hallucinated profile facts;
- устаревших project assumptions;
- неверных shared memories.

## V1 UX Model

### List View

Основной вход:

- scope toggle: `private / group`
- searchable list
- light filtering by state and sensitivity
- inline actions:
  - `Edit`
  - `Forget`
  - `Mark incorrect`

### Detail View

Detail нужен для:

- чтения полного текста;
- редактирования длинных memories;
- просмотра review metadata;
- future extensions вроде history или related items.

### Why this is enough for V1

Такой surface закрывает реальные product jobs, но не перегружает пользователя:

- не требует manual tagging;
- не раскрывает внутреннюю taxonomy;
- не превращает memory system в админку на каждый день.

## Sensitive Memory Handling

Во `v1` review-surface должен учитывать новую configurable policy:

- `reject`
- `mark`

### Required behavior when policy = mark

- sensitive item может существовать в review list;
- UI должен явно показывать, что memory sensitive;
- content по умолчанию можно маскировать;
- reveal может быть отложен на `v1.5/v2`, если deployment не требует этого сразу.

### Product expectation

Даже если reveal UI в `v1` нет, review-surface уже должен:

- не смешивать sensitive и ordinary memories без маркера;
- поддерживать корректные update/forget flows для sensitive entries.

## Session vs Durable Review Behavior

Это важная часть `v1`, потому что review surface работает поверх двух разных классов памяти.

### Durable memory

Expected review semantics:

- `update` modifies the durable item
- `mark incorrect` removes it from active recall/list/search
- `forget` may map to the same active-surface removal path

### Session memory

Expected review semantics:

- `update` modifies current scratch/session item
- `mark incorrect` or `forget` removes the transient item

### Why the user should not care

Пользователь не обязан знать, durable это объект или session object.

Но review surface обязан вести себя консистентно:

- “исправить” действительно исправляет;
- “убрать” действительно убирает.

## Explainability in V1

Полная explainability не является must-have для `v1`.

### What we do need

Минимально полезные признаки:

- scope
- source kind
- status
- sensitive marker

### What we postpone

- why this memory was promoted
- why this memory was recalled
- promotion/rescue timeline UI
- merge/supersede visual history

### Why this is acceptable

На текущем этапе product priority — не advanced interpretability, а:

- usable control
- trust through correction
- low-friction memory operations

## Runtime Mapping

На backend уровне `v1 review surface` уже опирается на adapter contract:

- `GET /v1/adapters/openclaw/memories`
- `GET /v1/adapters/openclaw/memories/{memory_id}`
- `PATCH /v1/adapters/openclaw/memories/{memory_id}`
- `DELETE /v1/adapters/openclaw/memories/{memory_id}`

`PATCH` already supports:

- content update
- `mark_incorrect`

Current runtime semantics:

- durable `memory_unit`:
  - update content/summary/merge key/sensitivity
  - mark incorrect -> remove from active layer
- session `episode`:
  - update scratchpad content
  - mark incorrect -> remove transient item

## Out of Scope for V1

Не входит в обязательный `v1 review surface`:

- global scope
- per-item ACL
- manual categorization UI
- graph visualization
- history diff viewer
- rescue/promotion explainability UI
- force remember
- bulk curation workflows as primary UX

## Success Criteria

`V1 memory review surface` успешен, если:

1. Пользователь может быстро найти и исправить неудачную memory item.
2. Пользователь может убрать неправильную или нежелательную memory item без сложного mental model.
3. Shared project memory можно просматривать и корректировать без риска перепутать ее с personal memory.
4. Sensitive items не теряются в UI как обычные memories.
5. Review layer не заставляет пользователя заниматься manual knowledge management ежедневно.

## Recommended Next Implementation Step

Следующий практический шаг после этого spec:

1. сделать `runtime review UI adapter` поверх нового backend contract;
2. начать с `list + detail + edit + forget/mark incorrect`;
3. сразу встроить `private / group` scope toggle;
4. только потом добавлять richer signals вроде history или explainability.

Это даст первый настоящий product surface поверх уже сильного memory engine без преждевременного усложнения.
