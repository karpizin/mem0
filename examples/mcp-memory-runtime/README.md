# MCP Memory Runtime Examples

Набор минимальных примеров для `Agent Memory Runtime MCP facade`.

Что внутри:

- `curl_smoke.sh`
- `python_client.py`
- `typescript_client.mjs`

Все примеры показывают один и тот же базовый flow:

1. `initialize`
2. `tools/list`
3. `memory.ingest_event`
4. `memory.recall`
5. `memory.record_feedback`

## Перед запуском

Нужен поднятый `memory-runtime`, по умолчанию:

- `http://127.0.0.1:8080`

Если сервис уже запущен локально:

```bash
cd /Users/slava/Documents/mem0-src/memory-runtime
make preflight
```

## Общие переменные

Во всех примерах можно переопределить:

- `MCP_BASE_URL`
- `MCP_CLIENT_NAME`
- `MCP_USER_ID`

Значения по умолчанию:

- `MCP_BASE_URL=http://127.0.0.1:8080`
- `MCP_CLIENT_NAME=openclaw`
- `MCP_USER_ID=alice`

## Namespace / agent scope

Примеры не создают namespace автоматически.
Перед запуском нужен уже существующий `namespace_id` и обычно `agent_id`.

Самый удобный путь для быстрого живого прогона:

1. создать scope через bootstrap OpenClaw adapter
2. передать `NAMESPACE_ID` и `AGENT_ID` в пример

## Быстрый старт

### Curl

```bash
cd /Users/slava/Documents/mem0-src/examples/mcp-memory-runtime
NAMESPACE_ID=... AGENT_ID=... ./curl_smoke.sh
```

### Python

```bash
cd /Users/slava/Documents/mem0-src/examples/mcp-memory-runtime
NAMESPACE_ID=... AGENT_ID=... python3 python_client.py
```

### TypeScript / Node

```bash
cd /Users/slava/Documents/mem0-src/examples/mcp-memory-runtime
NAMESPACE_ID=... AGENT_ID=... node typescript_client.mjs
```

## Что возвращают примеры

Каждый пример печатает:

- текущий MCP handshake result
- список tools
- id созданного event и episode
- selected episode ids из recall
- feedback result

## Связанные документы

- [MCP guide](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-mcp-guide.md)
- [memory-runtime README](/Users/slava/Documents/mem0-src/memory-runtime/README.md)
