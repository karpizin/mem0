# Agent Memory Runtime v1 Product Gap Map

Документ фиксирует, чего именно не хватает проекту до цельного `v1`-продукта с точки зрения позиционирования, управляемости и пользовательской ценности.

## Статус

- `Draft v1`
- Основан на текущем runtime-состоянии и зафиксированной продуктовой рамке

## Current Product Read

На сегодня проект выглядит так:

- как `memory engine` — сильный
- как `builder-facing infrastructure product` — уже близкий к реальности
- как `управляемый продукт` — еще неполный

Главный вывод:

`У проекта уже сильное технологическое ядро, но еще не полностью сформирована продуктовая оболочка вокруг памяти как управляемой системы.`

## Gap Categories

### 1. Must-Have Before Productization

#### 1.1. Memory Review Surface

Что нужно:

- список запомненного
- update memory
- force forget
- mark incorrect

Почему это критично:

- без этого память ощущается как black box
- correction loop остается слишком техническим

Что уже закрыто:

- backend adapter review contract уже есть
- `view / update / force forget / mark incorrect` поддержаны на runtime surface
- semantics для durable и session memory уже зафиксированы

Что остается:

- построить минимальный user/operator-facing review UI
- отразить `private / group` scopes как видимую product-сущность
- аккуратно показать sensitive markers

#### 1.2. Scoped Sharing As Product Concept

Что нужно:

- явная пользовательская модель `private / group`
- понятное объяснение, что такое `group`
- понятные правила, куда память попадает по умолчанию

Почему это критично:

- shared memory без ясной модели быстро теряет доверие
- именно scopes определяют границы продукта

#### 1.3. Builder Onboarding Path

Что нужно:

- короткий path “подключил -> получил value”
- safe defaults
- понятный minimal setup
- pilot checklist

Почему это критично:

- основной пользователь — builder
- если onboarding тяжелый, adoption тормозится независимо от качества ядра

#### 1.4. Product Success Measurement

Что нужно:

- product-facing metrics, а не только технические
- прозрачная связь между quality и value

Почему это критично:

- иначе нельзя доказать, что память реально улучшает агентов

#### 1.5. Value Packaging

Что нужно:

- четкие сценарии пользы:
  - continuity
  - preferences
  - procedures
  - project memory
- before/after examples

Почему это критично:

- продукт должен продавать ценность, а не просто архитектуру

### 2. Important For v1

#### 2.1. Governance Model As Product Policy

Что нужно:

- ясная продуктовая политика для:
  - durable memory
  - session-only memory
  - sensitive memory
  - shared memory

Почему важно:

- сейчас логика уже есть внутри engine, но не полностью оформлена как продуктовая политика

#### 2.2. Operator / Admin Experience

Что нужно:

- memory health
- backlog / drain visibility
- cleanup workflows
- contamination workflows
- scope debugging

Почему важно:

- builder-first продукт почти всегда требует operator layer

#### 2.3. Sensitive Memory UX

Что нужно:

- не только technical masking
- но и понятная product story:
  - что сохраняется
  - что маскируется
  - где policy задается

Почему важно:

- sensitive memory влияет на доверие и adoption

#### 2.4. Long-Horizon Behavior Story

Что нужно:

- как память стареет
- как обновляются факты
- как разрешаются конфликты
- как работает forgetting на дистанции

Почему важно:

- память ценна именно во времени, а не только на коротких demo-сценариях

### 3. Nice To Have Later

#### 3.1. Rich Explainability UX

Не must-have для `v1`, но likely important later.

#### 3.2. Global Memory Scope

Пока осознанно вне `v1`, потому что увеличивает риск неправильного шаринга.

#### 3.3. User-Facing Memory Typing

Внутренне типизация уже важна, но как UX-сущность это пока можно оставить под капотом.

#### 3.4. Graph UI

Graph memory важна как future architecture direction, но не как обязательный `v1` surface.

## Gap Matrix

| Gap | Severity | Why It Matters | Recommended Timing |
| --- | --- | --- | --- |
| Memory review surface | `high` | Без этого память плохо контролируется человеком | `before productization` |
| Scoped sharing UX/model | `high` | Shared memory без ясных границ быстро теряет доверие | `before productization` |
| Builder onboarding | `high` | Основной пользователь — builder | `before productization` |
| Product success metrics | `high` | Нельзя доказать value without them | `before productization` |
| Value packaging | `high` | Иначе продукт выглядит как engine, а не solution | `before productization` |
| Governance policy as product | `medium-high` | Важна для trust и predictability | `v1` |
| Operator/admin experience | `medium-high` | Нужна для живого использования | `v1` |
| Sensitive-memory product story | `medium` | Влияет на trust | `v1` |
| Long-horizon product behavior | `medium` | Важна для memory credibility | `v1` |
| Rich explainability UX | `medium-low` | Полезна, но не блокер для `v1` | `later` |
| Global scope | `low` | Сейчас скорее risk than value | `later` |
| Graph UI | `low` | Nice enhancement, not core blocker | `later` |

## What The Product Already Has

Важно явно зафиксировать, что gaps не означают “продукта еще нет”.

У проекта уже есть:

- сильное memory core
- recall / consolidation / lifecycle
- shared runtime architecture
- OpenClaw integration
- MCP surface
- sensitive memory policy foundation
- quality / performance / observability foundation

То есть продукт уже не “идея”, а `сильный engine, которому нужно дорастить user/control/value layer`.

## Recommended Build Order

### Next Product Layer

1. `Memory review surface`
2. `Scoped sharing model`
3. `Builder onboarding story`
4. `Success metrics framework`
5. `Value packaging`

### After That

6. operator/admin console layer
7. richer governance UX
8. long-horizon trust / lifecycle productization

### Later

9. explainability surface
10. graph memory UX
11. more advanced sharing / ACL logic

Отдельный spec для следующего шага уже зафиксирован:

- [agent-memory-runtime-memory-review-surface-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-memory-review-surface-v1.md)

## Practical Definition Of “Good v1 Product”

`Good v1` для этого проекта — это не “максимально умная память”, а:

- builder может быстро встроить ее в агентную платформу
- персональная память реально помогает continuity
- shared memory работает на уровне проекта
- sensitive data обрабатывается предсказуемо
- память можно просмотреть, исправить и забыть
- ценность продукта можно объяснить и измерить

Если эти условия выполняются, продукт уже выглядит как сильный `v1`, даже без rich explainability, graph UI и глобальных memory scopes.
