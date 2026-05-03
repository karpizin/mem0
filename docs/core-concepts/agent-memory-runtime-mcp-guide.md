# mem0plus MCP Guide

Практическая документация по `MCP`-интерфейсу `mem0plus`.

Этот документ описывает уже реализованный `MCP` facade:

- transport
- JSON-RPC envelope
- поддерживаемые methods
- tools
- resources
- prompts
- примеры запросов
- типовые ошибки и ограничения

Связанные документы:

- [mem0plus-mcp-spec-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/mem0plus-mcp-spec-v1.md)
- [agent-memory-runtime-system-design-v1.md](/Users/slava/Documents/mem0-src/docs/core-concepts/agent-memory-runtime-system-design-v1.md)
- [memory-runtime/README.md](/Users/slava/Documents/mem0-src/memory-runtime/README.md)

## 1. Что это такое

`MCP` в нашем проекте это thin compatibility layer поверх уже существующих runtime services.

Он:

- не заменяет `REST API`
- не вводит отдельную business logic ветку
- использует те же retrieval/observability/repository слои
- нужен для MCP-aware клиентов, которым удобнее работать через standard tools/resources/prompts

## 2. Endpoint

Текущий transport:

- `POST /mcp/{client_name}/http/{user_id}`

Пример полного URL:

- `http://localhost:8080/mcp/openclaw/http/alice`

Где:

- `client_name` — имя интеграции или клиента
- `user_id` — внешний user/session identifier клиента

Транспорт stateless:

- сервер не хранит MCP session state
- `DELETE` на этот endpoint возвращает `405`

## 3. Обязательные заголовки

Для каждого MCP-запроса нужны:

- `Accept: application/json`
- `Content-Type: application/json`

Если `Accept` не содержит `application/json`, сервер вернет `406`.
Если `Content-Type` указан и не является `application/json`, сервер вернет `415`.

## 4. JSON-RPC envelope

Поддерживается `JSON-RPC 2.0`.

Минимальная форма запроса:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {}
}
```

Общий формат ответа:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {}
}
```

Общий формат ошибки:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method '...' is not supported by this MCP server."
  }
}
```

## 5. Поддерживаемые methods

Сейчас реализованы:

- `initialize`
- `tools/list`
- `tools/call`
- `resources/templates/list`
- `resources/read`
- `prompts/list`
- `prompts/get`

## 6. Initialize

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "openclaw",
        "version": "0.1.0"
      }
    }
  }'
```

Ответ содержит:

- `protocolVersion`
- `serverInfo`
- `capabilities`

## 7. Tools

### 7.1 `tools/list`

Возвращает весь текущий реестр MCP tools.

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

### 7.2 Доступные tools

#### `memory.recall`

Назначение:

- собрать `MemoryBrief` для текущего запроса

Аргументы:

- `namespace_id`
- `agent_id`
- `session_id`
- `query`
- `context_budget_tokens`
- optional `space_filter`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "memory.recall",
      "arguments": {
        "namespace_id": "NAMESPACE_ID",
        "agent_id": "AGENT_ID",
        "query": "What architecture context already exists for the memory runtime?",
        "context_budget_tokens": 900
      }
    }
  }'
```

`structuredContent` содержит:

- `brief`
- `trace`

Дополнительно runtime пишет `recall_executed` в `audit_log`, чтобы последний recall был доступен как MCP resource.

#### `memory.search`

Назначение:

- поиск по активной long-term памяти

Аргументы:

- `namespace_id`
- optional `agent_id`
- `query`
- optional `limit`
- optional `space_types`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "memory.search",
      "arguments": {
        "namespace_id": "NAMESPACE_ID",
        "agent_id": "AGENT_ID",
        "query": "What storage stack does the runtime use?",
        "limit": 5
      }
    }
  }'
```

Каждый result содержит:

- `id`
- `summary`
- `content`
- `kind`
- `scope`
- `space_type`
- `score`
- `status`
- `updated_at`

#### `memory.list_spaces`

Назначение:

- перечислить видимые memory spaces

Аргументы:

- `namespace_id`
- optional `agent_id`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "memory.list_spaces",
      "arguments": {
        "namespace_id": "NAMESPACE_ID",
        "agent_id": "AGENT_ID"
      }
    }
  }'
```

#### `memory.get_observability_snapshot`

Назначение:

- получить текущий operational snapshot runtime

Аргументы:

- не обязательны

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "memory.get_observability_snapshot",
      "arguments": {}
    }
  }'
```

Ответ содержит:

- `metrics`
- `jobs`

#### `memory.get_memory_unit`

Назначение:

- получить один конкретный `memory_unit`

Аргументы:

- `namespace_id`
- `memory_unit_id`
- optional `agent_id`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "memory.get_memory_unit",
      "arguments": {
        "namespace_id": "NAMESPACE_ID",
        "agent_id": "AGENT_ID",
        "memory_unit_id": "MEMORY_UNIT_ID"
      }
    }
  }'
```

## 8. Resource templates

### 8.1 `resources/templates/list`

Возвращает поддерживаемые URI templates.

Сейчас доступны:

- `memory://namespaces/{namespace_id}/summary`
- `memory://namespaces/{namespace_id}/agents/{agent_id}/brief`
- `memory://namespaces/{namespace_id}/observability`
- `memory://namespaces/{namespace_id}/agents/{agent_id}/spaces`

### 8.2 `resources/read`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 8,
    "method": "resources/read",
    "params": {
      "uri": "memory://namespaces/NAMESPACE_ID/summary"
    }
  }'
```

Ответ всегда содержит `contents`, внутри которых лежит:

- `uri`
- `mimeType`
- `text`

### 8.3 Resource meanings

#### `memory://namespaces/{namespace_id}/summary`

Возвращает:

- namespace metadata
- agents
- `space_counts`
- `active_memory_unit_count`

#### `memory://namespaces/{namespace_id}/agents/{agent_id}/brief`

Возвращает:

- `last_recall`
- `recorded_at`

Если recall еще не вызывался, `last_recall` будет `null`.

#### `memory://namespaces/{namespace_id}/observability`

Возвращает:

- observability snapshot
- namespace metadata

#### `memory://namespaces/{namespace_id}/agents/{agent_id}/spaces`

Возвращает:

- видимые пространства памяти для агента

## 9. Prompts

### 9.1 `prompts/list`

Возвращает реестр доступных prompts.

Сейчас доступны:

- `debug-memory-miss`
- `prepare-memory-aware-task`
- `inspect-namespace-health`

### 9.2 `prompts/get`

Пример:

```bash
curl -s http://localhost:8080/mcp/openclaw/http/alice \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 9,
    "method": "prompts/get",
    "params": {
      "name": "prepare-memory-aware-task",
      "arguments": {
        "namespace_id": "NAMESPACE_ID",
        "agent_id": "AGENT_ID",
        "task": "prepare the next OpenClaw integration milestone"
      }
    }
  }'
```

Ответ содержит:

- `description`
- `messages`

### 9.3 Prompt meanings

#### `debug-memory-miss`

Нужен для разбора ситуации, когда память не вернула ожидаемое воспоминание.

Аргументы:

- `namespace_id`
- `agent_id`
- `expected_memory`
- optional `query`

#### `prepare-memory-aware-task`

Нужен как scaffold для workflow, где агент сначала делает `memory.recall`, а потом продолжает задачу.

Аргументы:

- `namespace_id`
- optional `agent_id`
- optional `session_id`
- `task`

#### `inspect-namespace-health`

Нужен для operator/debugging сценариев вокруг health и backlog памяти.

Аргументы:

- `namespace_id`

#### `memory.ingest_event`

Нужен для безопасной записи нового события в память через обычный ingestion pipeline.

Аргументы:

- `namespace_id`
- optional `agent_id`
- optional `session_id`
- optional `project_id`
- `event_type`
- `event_origin`
- optional `space_hint`
- `messages`
- optional `metadata`
- optional `dedupe_key`

Guardrails:

- agent-scoped write требует `agent_id`
- namespace-scoped write без `agent_id` разрешен только с `space_hint=shared-space`
- tool не умеет писать напрямую в durable memory в обход ingestion/consolidation

#### `memory.record_feedback`

Нужен для записи positive/negative recall feedback через уже существующий feedback path.

Аргументы:

- `namespace_id`
- optional `agent_id`
- `helpful`
- `episode_ids`
- optional `query`
- optional `notes`

## 10. Ограничения текущей реализации

Сейчас MCP layer:

- stateless
- read-first, но уже с безопасным write-минимумом
- не поддерживает realtime subscriptions
- не реализует отдельную auth model поверх runtime

Пока не поддерживается:

- destructive admin operations
- direct durable-memory write bypass
- lifecycle/admin mutation

## 11. Следующие шаги

Следующие согласованные задачи по MCP:

- расширить safe write MCP tools дополнительными smoke/e2e проверками
- углубить guardrails и namespace-isolation coverage для write-path
- подготовить маленький MCP client smoke script для быстрого подключения и проверки реального `OpenClaw`

Практический смысл smoke script:

- быстро проверить `initialize`
- быстро проверить `tools/list`
- быстро проверить `memory.recall`
- быстро проверить `memory.ingest_event`
- быстро проверить `memory.record_feedback`
- быстро проверить transport/headers без полного live-сценария

## 12. Типовые ошибки

### `406`

Причина:

- нет `Accept: application/json`

### `415`

Причина:

- неправильный `Content-Type`

### `400`

Причина:

- невалидный JSON body
- JSON-RPC payload не является object

### JSON-RPC `-32601`

Причина:

- неизвестный `method`

### JSON-RPC `-32602`

Причина:

- отсутствует обязательный аргумент
- невалидный URI resource
- невалидный tool arguments payload

### JSON-RPC `-32004`

Причина:

- не найден namespace
- не найден agent
- не найден memory unit

## 13. Наблюдаемость

Через `/metrics` экспортируются:

- `memory_runtime_mcp_requests_total`
- `memory_runtime_mcp_tool_calls_total`
- `memory_runtime_mcp_write_tool_calls_total`
- `memory_runtime_mcp_resource_reads_total`
- `memory_runtime_mcp_prompt_requests_total`
- `memory_runtime_mcp_errors_total`
- `memory_runtime_mcp_request_by_method_total{method,status}`
- `memory_runtime_mcp_tool_call_by_name_total{tool_name,status}`
- `memory_runtime_mcp_resource_read_by_name_total{resource_name,status}`
- `memory_runtime_mcp_prompt_request_by_name_total{prompt_name,status}`
- `memory_runtime_mcp_request_by_client_total{client_name}`
- `memory_runtime_mcp_request_latency_bucket_total{bucket_ms}`
- `memory_runtime_mcp_tool_latency_bucket_total{bucket_ms}`

Это полезно для:

- проверки, что MCP-клиент реально ходит в runtime
- оценки интенсивности tool/resource/prompt usage
- диагностики protocol-level ошибок
- разделения transport-level ошибок и tool-level ошибок
- понимания, какие MCP methods/tools реально используются чаще всего
- оценки, где именно MCP surface начинает тормозить

## 14. Рекомендуемый flow интеграции

Практически для нового MCP-aware клиента я бы рекомендовал такой порядок:

1. `initialize`
2. `tools/list`
3. `resources/templates/list`
4. `prompts/list`
5. использовать `memory.recall` как основной operational tool
6. использовать `memory.search` и `memory.get_memory_unit` для debugging и inspection
7. использовать `memory.ingest_event` и `memory.record_feedback` для guarded write workflows
8. использовать resources для read-only context и operator workflows

## 15. MCP Smoke Flow

Для быстрой живой проверки MCP surface теперь есть отдельный smoke flow:

- `cd /Users/slava/Documents/mem0-src/memory-runtime`
- `make mcp-smoke`

Что он делает:

1. поднимает локальный compose-контур
2. создает isolated namespace и agent
3. выполняет `initialize`
4. выполняет `tools/list`
5. пишет событие через `memory.ingest_event`
6. ждет обработки jobs
7. вызывает `memory.recall`
8. записывает positive feedback через `memory.record_feedback`
9. сохраняет артефакты в `.artifacts/pilot_traces/mcp-smoke/...`
10. сохраняет компактный отчет в `.artifacts/openclaw_mcp_smoke_report.json`

## 16. Client Examples

Готовый examples pack лежит здесь:

- [examples/mcp-memory-runtime](/Users/slava/Documents/mem0-src/examples/mcp-memory-runtime)

Что внутри:

- [README.md](/Users/slava/Documents/mem0-src/examples/mcp-memory-runtime/README.md)
- [curl_smoke.sh](/Users/slava/Documents/mem0-src/examples/mcp-memory-runtime/curl_smoke.sh)
- [python_client.py](/Users/slava/Documents/mem0-src/examples/mcp-memory-runtime/python_client.py)
- [typescript_client.mjs](/Users/slava/Documents/mem0-src/examples/mcp-memory-runtime/typescript_client.mjs)

Все примеры показывают один и тот же guarded flow:

1. `initialize`
2. `tools/list`
3. `memory.ingest_event`
4. `memory.recall`
5. `memory.record_feedback`

## 17. Текущий статус

Текущая реализация уже покрыта component tests:

- MCP transport validation
- tool calls
- resource reads
- prompt responses
- metrics export
- MCP smoke runner для safe write/read flow
- shared-space write без `agent_id`
- изоляция private `project-space` memory между агентами в shared namespace
- guardrail на `session_id + agent-core` для `memory.ingest_event`
- готовый examples pack для `curl`, `Python` и `TypeScript`

Текущий рабочий baseline:

- пригоден для MCP-aware read-first интеграций
- пригоден для guarded write/read smoke через `memory.ingest_event` и `memory.record_feedback`
- не заменяет REST adapters
- хорошо подходит как compatibility layer и inspection surface
- уже имеет неплохое edge-case покрытие по namespace isolation и write guardrails
