# Agent Memory Runtime: OpenClaw Pre-Live Checklist

Короткий checklist перед живым прогоном `OpenClaw -> memory-runtime`.

## 1. Поднять контур

```bash
cd /Users/slava/Documents/mem0-src/memory-runtime
docker compose up --build
```

## 2. Прогнать preflight

```bash
cd /Users/slava/Documents/mem0-src/memory-runtime
make preflight
```

Проверить:

- отчет вернулся со статусом `pass`
- если нет, смотреть:
  - [OpenClaw Pilot Runbook](./agent-memory-runtime-openclaw-pilot-runbook.md)
  - [OpenClaw Troubleshooting Cheatsheet](./agent-memory-runtime-openclaw-troubleshooting.md)

## 3. Прогнать synthetic gates

```bash
cd /Users/slava/Documents/mem0-src/memory-runtime
make pilot-smoke
make pilot-scenarios
make quality-eval
make lifecycle-eval
```

## 4. Проверить минимальные условия готовности

- `healthz` отвечает
- `/metrics` и `/v1/observability/stats` доступны
- worker реально обрабатывает jobs
- `pilot-smoke` зеленый
- `pilot-scenarios` зеленый
- quality eval зеленый
- lifecycle eval зеленый

## 5. Подготовить live-pilot

Нужно иметь под рукой:

- реальный `OpenClaw` config
- 3-5 сценариев из [OpenClaw Pilot Scenarios](./agent-memory-runtime-openclaw-pilot-scenarios.md)
- шаблоны фиксации результатов:
  - [Pilot Result Template](./agent-memory-runtime-openclaw-pilot-result-template.md)
  - [Finding Template](./agent-memory-runtime-openclaw-finding-template.md)
  - [Post-Pilot Backlog Template](./agent-memory-runtime-openclaw-post-pilot-backlog-template.md)

## 6. Во время live-прогона фиксировать

- что агент должен был вспомнить
- что реально вспомнил
- что вспомнил лишнего
- `trace.selection_explanations`
- snapshot из `/v1/observability/stats`, если был operational issue

## Что уже готово

Контур сейчас достаточно зрелый для первого честного live-pilot:

- `83` теста зеленые
- есть `preflight`
- есть `pilot-smoke`
- есть автоматизированный `pilot-scenarios` subset
- есть quality/lifecycle/adversarial/continuity evals
- есть explainable recall trace
- есть idempotent ingestion
