# Agent Memory Runtime Product Definition v1

Продуктовый документ, фиксирующий `v1`-рамку для `Agent Memory Runtime` с приоритетом на реальную пользовательскую ценность, а не только на архитектурную полноту.

## Статус

- `Draft v1`
- Основан на текущем состоянии `memory-runtime`, живых интеграциях с `OpenClaw` и `BunkerAI`, а также на серии продуктовых обсуждений
- Горизонт: ближайшая продуктовая версия и первые пилоты

## Product Statement

`Agent Memory Runtime` — это `self-hosted`, часто `offline-first` memory layer для агентных платформ, который в первую очередь улучшает `персональную память ассистента`, а также поддерживает `scoped shared memory` на уровне проектов, разделяемую между несколькими агентами.

Система должна:

- сама запоминать полезное
- сама извлекать это по смыслу и контексту
- скрывать внутреннюю сложность
- давать человеку минимально необходимые инструменты контроля

## Primary Persona

### Основной пользователь

`Разработчик агентной платформы`

Это команда, которая строит собственных ассистентов и агентные системы и хочет подключить к ним качественную память без необходимости изобретать memory-layer с нуля.

### Dogfooding-first targets

- `OpenClaw`
- `BunkerAI`

### Secondary persona

`Оператор / владелец агентной системы`

Этот пользователь важен для:

- настройки memory policies
- мониторинга
- cleanup
- debugging

Но он не является главным entry point для `v1`.

## Core Product Goal

Главная цель продукта в `v1`:

`Сделать персональную память ассистента достаточно качественной, чтобы пользователю не приходилось постоянно повторять контекст, а агент реально сохранял и вспоминал важное между сессиями.`

`Shared memory` в `v1` — важное расширение, но не главный фокус.

## Jobs To Be Done

Продукт должен помогать платформе решать следующие задачи:

1. автоматически помнить важный пользовательский и проектный контекст
2. извлекать релевантную память позже без ручного поиска
3. сохранять continuity между сессиями
4. делиться проектной памятью между несколькими агентами, если это нужно
5. не засорять память мусором
6. позволять человеку исправлять неверную, устаревшую или нежелательную память

## Delivery Model

`v1` ориентирован на:

- `self-hosted` deployment
- частый `offline-first` usage
- embedding в собственные агентные платформы

Это не `managed cloud memory product` в первой итерации.

## Product Principles

### 1. Quality First

Главный приоритет — не максимальная функциональная широта, а качество памяти:

- recall должен быть полезным
- continuity должна реально работать
- мусор не должен доминировать

### 2. Complexity Stays Under The Hood

Продукт не должен требовать от пользователя ручного memory-management как основной модели.

Это значит:

- без ручного тэгирования как обязательного режима
- без сложных пользовательских онтологий памяти
- без необходимости “обслуживать” память вручную ради базовой пользы

### 3. Personal Memory First

`v1` оптимизируется прежде всего под максимальное качество `персональной памяти ассистента`.

`Shared memory` поддерживается, но не должна размывать главный продуктовый фокус.

### 4. Semantic Retrieval Over Mechanical Storage

Ценность продукта не в том, что он “что-то хранит”, а в том, что он:

- организует воспоминания семантически
- находит по смыслу
- умеет учитывать ключевые слова, аналогии, контекст и связь между воспоминаниями

## Memory Model v1

На пользовательском уровне память пока может оставаться `simple`.

В `v1` продуктовая модель выглядит так:

- память состоит из `memory items`
- эти memory items могут содержать:
  - факты
  - предпочтения
  - процедуры
  - решения
  - активный контекст

Внутренняя классификация памяти остается внутри engine.

Пользовательская модель не обязана раскрывать сложную внутреннюю онтологию.

### Почему это правильно для v1

- меньше UX-сложности
- меньше когнитивной нагрузки
- продукт выглядит как “умная память”, а не как ручная knowledge system

### Что это значит для engine

Внутренняя типизация все равно нужна для:

- ranking
- promotion / rescue
- lifecycle
- sensitive handling
- future graph memory

## Scope Model v1

Для `v1` выбирается `scoped sharing`, без `global`.

### Поддерживаемые scopes

- `private`
- `group`

### Что такое `group`

`Group` = `project memory`, разделяемая между несколькими агентами, работающими над одним и тем же проектом.

Это означает:

- нет global memory для всех по умолчанию
- shared memory всегда привязана к проектному контуру
- границы шаринга определяются проектом, а не абстрактной “общей памятью для всех”

### Почему это хороший v1-компромисс

- shared capability уже есть
- global-risk пока не вводится
- модель хорошо соответствует реальному multi-agent project workflow

## Sensitive Memory Policy v1

Базовая продуктовая модель:

- `save but mask`
- policy configurable per deployment

### Practical behavior

- sensitive memory может сохраняться
- по умолчанию маскируется в выдаче
- конкретная политика задается на уровне deployment/config

### Почему это соответствует продукту

- не навязывает слишком жесткую политику
- подходит для self-hosted/offline usage
- оставляет контроль владельцу системы

## User Control Surface v1

Обязательные пользовательские действия:

- `view`
- `update`
- `force forget`
- `mark incorrect`

### Что не требуется как must-have в v1

- `force remember`
- rich explainability UI
- сложная ручная классификация памяти

### Продуктовый смысл

Память должна работать сама.

Ручные действия нужны как `correction layer`, а не как основной режим использования.

## Explainability Position v1

Полноценная explainability не является обязательной фичей `v1`.

### Почему ею можно пожертвовать в первой версии

- primary persona — builder, а не end-user
- главная задача сейчас — качество memory core
- обязательные manual controls уже дают минимально достаточный user control

### Когда explainability станет важнее

- при ошибках памяти
- при shared memory
- при работе с sensitive data
- при более широком командном использовании

### Решение для v1

- rich explainability UX не делаем
- внутренние explanation hooks и traces сохраняем как future enabler

## Success Metrics v1

### Primary product metrics

1. `Repeated context reduction`
   Насколько реже пользователю приходится заново объяснять уже известный контекст.

2. `Continuity success rate`
   Насколько часто агент правильно продолжает работу между сессиями.

3. `Must-remember hit rate`
   Насколько часто система вспоминает то, что обязана помнить.

4. `Noise leakage rate`
   Насколько редко мусор попадает в durable memory или recall.

### Secondary quality metrics

- memory correction rate
- scope violation rate
- sensitive handling correctness

### Operational metrics

- recall `p95 latency`
- backlog drain time
- failure / timeout rate

## What Is In Scope For v1

- high-quality personal assistant memory
- semantic retrieval
- `private / group` memory scopes
- self-hosted / offline-friendly deployment
- masking for sensitive memory
- memory review controls
- builder-facing integration surface
- operator-facing observability / cleanup primitives

## What Is Out Of Scope For v1

- global memory scope
- rich explainability UI
- fine-grained ACL per memory item
- explicit user-facing memory taxonomy
- graph UI
- heavy enterprise governance layer
- manual-first memory management workflows

## Product Read

Сейчас проект выглядит так:

- как `memory engine` — сильный
- как `builder-facing infrastructure product` — уже близкий к реальности
- как `end-user-facing memory product` — еще рано
- как `productionized memory platform` — нужен еще product layer поверх сильного ядра

## Near-Term Product Priorities

Следующие продуктовые приоритеты после фиксации `v1`-рамки:

1. memory review surface
2. scoped sharing как явная продуктовая сущность
3. builder onboarding path
4. user-facing value stories
5. success measurement framework
