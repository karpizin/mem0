# mem0plus Long-Term Memory Roadmap

Документ фиксирует долгосрочные направления развития памяти за пределами текущего `MVP / live-pilot` объема.

Назначение:

- собрать будущие типы памяти в одну карту решений
- отделить `высокий ROI` направления от просто интересных идей
- заранее оценить полезность, реалистичность и трудоемкость
- не смешивать `v1 runtime hardening` и `next-gen memory stack`

Важно:

- это не обязательный delivery plan ближайших недель
- это `long-term roadmap / research map`
- высокий балл полезности не означает, что идею нужно делать немедленно
- приоритет определяется не только ценностью, но и timing'ом относительно зрелости core runtime

## 1. Executive Summary

Если смотреть на будущее проекта прагматично, то наиболее сильные направления такие:

1. `Relationship / entity graph memory`
2. `Document and artifact memory`
3. `Trust / evidence-scored memory`
4. `External cold archive memory`
5. `Tabular / structured record memory`

Именно они выглядят наиболее:

- актуальными для реальных агентных workflows
- полезными для качества recall и explainability
- реалистичными относительно нашей текущей архитектуры

Наоборот, такие идеи как `full visual memory`, `counterfactual memory`, `causal modeling as core memory primitive` интересны, но сейчас выглядят скорее как research track, а не как следующий продуктовый шаг.

## 2. Evaluation Model

Для каждого направления используются 4 оценки:

- `Актуальность`
  Насколько это решает реальную боль ближайших или среднесрочных пользователей.
- `Полезность`
  Насколько заметно это может улучшить agent outcomes, continuity, retrieval quality и operator experience.
- `Реалистичность`
  Насколько это естественно ложится на текущий runtime без полного архитектурного переворота.
- `Трудоемкость`
  Сколько инженерной, продуктовой и evaluation-работы потребуется.

Шкала:

- `1-3` — низко
- `4-6` — средне
- `7-8` — высоко
- `9-10` — очень высоко

Для `трудоемкости` высокий балл означает, что делать сложно.

## 3. Master Matrix

| Направление | Что это такое | Актуальность | Полезность | Реалистичность | Трудоемкость | Итоговая оценка |
|---|---|---:|---:|---:|---:|---|
| `Semantic / episodic memory` | Факты, решения, процедуры, рабочий контекст, continuity | `10` | `10` | `10` | `already core` | Основа системы, уже реализуется |
| `Relationship / entity graph memory` | Связи между людьми, проектами, решениями, артефактами и системами | `9` | `9` | `8` | `7` | Сильнейший кандидат на next-gen layer |
| `Document memory` | Память о документах, runbooks, RFC, PRD, заметках, страницах | `9` | `9` | `9` | `6` | Очень практичный и реалистичный следующий шаг |
| `Artifact memory` | Память о файлах, коммитах, логах, отчетах, dashboards, traces | `8` | `9` | `9` | `6` | Особенно сильна для coding / operations agents |
| `Trust / evidence-scored memory` | Каждое воспоминание хранит происхождение, подтвержденность и confidence | `9` | `9` | `8` | `6` | Прямо усиливает quality, safety и explainability |
| `External cold archive memory` | Холодная, редко поднимаемая, но очень долгая память | `8` | `8` | `8` | `7` | Естественное развитие lifecycle и archive semantics |
| `Tabular / structured record memory` | Таблицы, списки, inventories, budgets, checklists как структуры, а не plain text | `8` | `8` | `8` | `7` | Сильный, но требует аккуратной модели |
| `Preference memory` | Вкусы, привычки, стиль, операционные правила пользователя | `9` | `8` | `9` | `5` | Очень полезно и дешево, но это скорее specialization current model |
| `Skill / procedure memory` | Пошаговые инструкции “как делать”, а не просто “что знать” | `9` | `9` | `8` | `6` | Сильный pragmatic layer, близок к current roadmap |
| `Temporal / timeline memory` | Временная лента событий и зависимостей “что за чем происходило” | `8` | `8` | `7` | `7` | Полезно для incident, project continuity и postmortem flows |
| `Multi-agent shared memory` | Коллективная память команды агентов с ролями и boundaries | `8` | `8` | `7` | `8` | Очень интересно, но governance сложен |
| `Visual / graphic memory` | Скриншоты, UI states, схемы, фото, image-grounded recall | `7` | `8` | `6` | `8` | Высокая ценность для некоторых доменов, но дорого |
| `Causal memory` | Не только факт, но и “почему мы решили именно так” | `8` | `8` | `6` | `8` | Ценно, но трудно надежно извлекать и поддерживать |
| `Counterfactual memory` | Память о вариантах “пробовали X, не подошло, потому что...” | `6` | `7` | `5` | `8` | Скорее исследовательский трек |
| `Super-long-lived personal archive` | Внешняя память в стиле альбомов, личных архивов, knowledge vaults | `7` | `8` | `7` | `7` | Полезно, но лучше строить после strong archive layer |

## 4. Recommended Prioritization Bands

### 4.1 Build Sooner

Это направления, которые имеют сильный `ROI / realism` баланс и естественно развивают текущую архитектуру:

1. `Relationship / entity graph memory`
2. `Document memory`
3. `Artifact memory`
4. `Trust / evidence-scored memory`
5. `External cold archive memory`

### 4.2 Explore After Core Maturity

Это направления, которые уже могут быть очень полезны, но требуют сначала более зрелого baseline:

1. `Tabular / structured record memory`
2. `Temporal / timeline memory`
3. `Skill / procedure memory` как отдельный слой, а не просто improved semantic memory
4. `Multi-agent shared memory`
5. `Visual / graphic memory`

### 4.3 Research, Not Product Priority Yet

Это хорошие идеи, но пока они выглядят как слишком дорогой research compared to expected near-term value:

1. `Causal memory`
2. `Counterfactual memory`
3. `rich autobiographical / super-personal long-horizon identity memory`

## 5. Detailed Analysis By Direction

### 5.1 Relationship / Entity Graph Memory

`Что это`

Вместо хранения только изолированных memory units система хранит и связи:

- `OpenClaw -> uses -> memory-runtime`
- `memory-runtime -> depends_on -> Postgres`
- `pilot-result-2026-04-21 -> found_issue -> recall-timeout`
- `user -> prefers -> concise-status-format`

`Почему это важно`

- резко улучшает explainability
- помогает retrieval по смысловым связям, а не только по текстовому overlap
- делает contradiction handling и supersede logic богаче
- позволяет лучше строить answer paths для “что связано с X?”

`Практическая ценность`

Особенно полезно для:

- coding agents
- incident / ops workflows
- project continuity
- memory inspection and debugging

`Реалистичность`

Высокая, потому что у нас уже есть:

- `namespaces`
- `agents`
- `memory_units`
- `episodes`
- `audit_log`

То есть граф можно вводить как `enhancement layer`, а не как обязательное ядро.

`Основные риски`

- слишком ранний переход к graph-first architecture
- переусложнение ingestion и consolidation
- сложность тестов и reasoning over graph edges

`Рекомендация`

Один из лучших кандидатов на `v2 / v2.5` слой.

### 5.2 Document Memory

`Что это`

Память не только о “выжатых фактах”, но и о самих документах:

- runbook
- RFC
- PRD
- markdown notes
- knowledge pages
- external docs references

`Почему это важно`

В реальной работе агенту часто нужно помнить:

- не только сам факт
- но и `откуда он взялся`
- и где лежит canonical source

`Практическая ценность`

Очень высокая для:

- coding
- product work
- research agents
- operational assistants

`Реалистичность`

Очень высокая.
Можно строить на текущей модели:

- document as source artifact
- extracted memory units as derivatives
- evidence links from memory to source document

`Рекомендация`

Один из самых практичных направлений после stabilization current runtime.

### 5.3 Artifact Memory

`Что это`

Специализированная память про:

- файлы
- commits
- logs
- metrics snapshots
- trace bundles
- reports
- builds

`Почему это важно`

Для агентных систем это часто полезнее, чем generic chat memory.
Агенту нужно помнить:

- какой лог уже смотрели
- какой файл меняли
- какой отчет дал важный сигнал
- какой commit исправил проблему

`Практическая ценность`

Максимальна для:

- code agents
- SRE / ops agents
- audit / compliance assistants

`Реалистичность`

Высокая.
Это хорошо ложится на наш текущий ecosystem:

- pilot artifacts
- reports
- traces
- docs

`Рекомендация`

Практически такой же сильный следующий трек, как document memory.

### 5.4 Trust / Evidence-Scored Memory

`Что это`

Каждое воспоминание хранит:

- source provenance
- confidence
- confirmation count
- contradiction count
- freshness / staleness
- last successful recall usage

`Почему это важно`

Это один из лучших способов одновременно улучшить:

- junk resistance
- explainability
- operator trust
- safe future automation

`Практическая ценность`

Очень высокая.
Это не новая “экзотическая” память, а multiplier для всей existing memory system.

`Реалистичность`

Высокая.
Мы уже движемся в эту сторону через:

- provenance firewall
- low-trust rejection
- feedback-aware rescue loop
- audit log

`Рекомендация`

Не просто исследовать, а планировать как один из центральных next-gen quality tracks.

### 5.5 External Cold Archive Memory

`Что это`

Часть памяти хранится не как активный recall pool, а как внешний холодный архив:

- редко поднимаемый
- дольше живущий
- менее дорогой для hot-path recall

Аналогия:

- `hot memory` — то, что может попасть в immediate brief
- `warm memory` — durable pool для обычного retrieval
- `cold archive` — “папки и альбомы”

`Почему это важно`

Если система будет жить долго, без cold archive hot memory layer начнет:

- дорожать
- шуметь
- размывать recall quality

`Практическая ценность`

Высокая для:

- long-running agents
- personal companions
- enterprise assistants с долгой историей

`Реалистичность`

Высокая, потому что lifecycle и archive semantics у нас уже есть.

`Рекомендация`

Очень разумный `v2+` трек.

### 5.6 Tabular / Structured Record Memory

`Что это`

Память не как prose-only text, а как structured records:

- контакты
- инвентарь
- budgets
- tracking tables
- recurring checklists

`Почему это важно`

Некоторые виды знаний портятся при хранении в свободном тексте.
Табличная форма дает:

- стабильность
- queryability
- better update semantics
- меньше ambiguity

`Практическая ценность`

Высокая, особенно для business / ops / personal organization scenarios.

`Основной риск`

Это уже не просто “память”, а почти mini data model layer.

`Рекомендация`

Стоит исследовать после document/artifact/trust tracks.

### 5.7 Preference Memory

`Что это`

Выделенная память на:

- вкусы
- привычки
- preferred formats
- forbidden styles
- recurring user rules

`Почему это важно`

Это один из самых часто встречающихся real-world use cases memory.

`Почему не стоит делать это отдельным большим track слишком рано`

Часть этого уже покрывается текущей semantic/procedural memory.
Поэтому это скорее specialization of current model than a wholly separate subsystem.

`Рекомендация`

Развивать постепенно через schemas/policies, а не через большой параллельный memory engine.

### 5.8 Skill / Procedure Memory

`Что это`

Хранить именно reusable procedures:

- “как делать релиз”
- “как готовить pilot findings”
- “как triage memory issue”

`Почему это важно`

Для productivity agents часто важнее “как делать”, чем “что было”.

`Реалистичность`

Высокая, потому что часть этого уже видна в:

- standing procedures
- policy updates
- agent-core memory

`Рекомендация`

Стоит усиливать, но сначала как evolution current procedural memory, а не как новый completely separate engine.

### 5.9 Temporal / Timeline Memory

`Что это`

Фокус на временной структуре:

- что было сначала
- что было потом
- что зависело от чего
- когда именно правило или решение стало актуальным

`Почему это важно`

Сильно помогает для:

- incidents
- rollouts
- project continuity
- postmortem reconstruction

`Реалистичность`

Средне-высокая, потому что timestamps у нас уже есть, но нужна richer model of temporal relationships.

`Рекомендация`

Хороший middle-term track после graph/evidence layers.

### 5.10 Multi-Agent Shared Memory

`Что это`

Память, предназначенная не только одному агенту, а группе:

- командная память
- shared procedures
- cross-agent operational context

`Почему это важно`

При росте числа агентов это очень мощный multiplier.

`Основной риск`

Governance:

- privacy boundaries
- ownership
- write conflicts
- contamination between agents

`Рекомендация`

Стоит делать только после того, как private/shared semantics current system станут очень зрелыми.

### 5.11 Visual / Graphic Memory

`Что это`

Память про изображения, UI states, screenshots, diagrams, photos.

`Почему это интересно`

Для некоторых доменов это дает huge value:

- UI agents
- support
- design review
- field inspection

`Почему пока не top priority`

- expensive multimodal indexing
- сложное retrieval ranking
- более дорогая evaluation strategy

`Рекомендация`

Позже, как domain-specific expansion.

### 5.12 Causal And Counterfactual Memory

`Что это`

- `causal memory`: “решили X, потому что Y”
- `counterfactual memory`: “пробовали X, но не подошло из-за Z”

`Почему это ценно`

Это сильно улучшает quality of future decisions.

`Почему сложно`

- extraction reliability
- contradiction handling
- evaluation is hard
- высокий риск hallucinated causality

`Рекомендация`

Research track, не near-term build priority.

## 6. Recommended Sequencing

### Wave 1: Strong Next-Gen Extensions

1. `Trust / evidence-scored memory`
2. `Document memory`
3. `Artifact memory`

Почему:

- максимальный practical ROI
- высокая совместимость с current architecture
- прямо усиливают quality and debuggability

### Wave 2: Structural Intelligence

1. `Relationship / entity graph memory`
2. `External cold archive memory`
3. `Temporal / timeline memory`

Почему:

- дают memory system вторую глубину
- но требуют уже зрелого core and evidence model

### Wave 3: Specialized Memory Modalities

1. `Tabular / structured record memory`
2. `Multi-agent shared memory`
3. `Visual / graphic memory`

Почему:

- они дают большой upside
- но domain/design complexity заметно выше

### Wave 4: Research / Experimental

1. `Causal memory`
2. `Counterfactual memory`
3. `rich autobiographical archive`

## 7. What Not To Do Too Early

Ниже идеи, которые выглядят привлекательно, но могут сильно замедлить проект, если брать их слишком рано:

- делать graph layer обязательным ядром до полной зрелости baseline memory quality
- строить multimodal visual memory до того, как text memory доказала стабильную пользу на длинной дистанции
- вводить слишком много specialized memory engines одновременно
- смешивать archive, retrieval, trust scoring и graph semantics в один mega-refactor

## 8. Concrete Long-Term Recommendation

Если перевести все вышесказанное в pragmatic recommendation, то best long-term path выглядит так:

1. `Укрепить текущую semantic / procedural / episodic memory`
2. `Добавить trust/evidence layer`
3. `Добавить document + artifact memory`
4. `Поверх этого ввести graph relationships`
5. `Затем строить cold archive and richer temporal behavior`
6. `И только потом идти в specialized modalities`

## 9. Final Verdict

Да, будущая память агента почти наверняка должна быть не одной системой, а `memory stack`.

Наиболее реалистичная и сильная долгосрочная картина:

- `episodic memory`
- `semantic memory`
- `procedural memory`
- `trust / evidence layer`
- `document memory`
- `artifact memory`
- `relationship graph`
- `cold archive`

Это выглядит и полезнее, и реалистичнее, чем попытка сразу строить “универсальный искусственный мозг”.
