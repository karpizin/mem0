from __future__ import annotations

from collections import Counter
from time import perf_counter
from threading import Lock


_METRIC_DEFINITIONS = {
    "consolidation_created_total": (
        "counter",
        "Total memory units created by consolidation.",
    ),
    "consolidation_merged_total": (
        "counter",
        "Total memory units merged by consolidation.",
    ),
    "jobs_processed_total": (
        "counter",
        "Total jobs processed successfully by the worker.",
    ),
    "jobs_failed_total": (
        "counter",
        "Total jobs failed during worker processing.",
    ),
    "lifecycle_decayed_total": (
        "counter",
        "Total memory units decayed by lifecycle rules.",
    ),
    "lifecycle_archived_total": (
        "counter",
        "Total memory units archived by lifecycle rules.",
    ),
    "lifecycle_evicted_total": (
        "counter",
        "Total memory units evicted by lifecycle rules.",
    ),
    "recall_requests_total": (
        "counter",
        "Total recall requests handled by the runtime.",
    ),
    "recall_feedback_positive_total": (
        "counter",
        "Total positive recall feedback signals recorded by the runtime.",
    ),
    "recall_feedback_negative_total": (
        "counter",
        "Total negative recall feedback signals recorded by the runtime.",
    ),
    "recall_candidates_total": (
        "counter",
        "Total recall candidates considered by the runtime.",
    ),
    "recall_selected_total": (
        "counter",
        "Total recall items selected into memory briefs.",
    ),
    "mem0_search_requests_total": (
        "counter",
        "Total mem0 bridge search requests issued by the runtime.",
    ),
    "mem0_sync_attempts_total": (
        "counter",
        "Total mem0 bridge sync attempts issued by the runtime.",
    ),
    "mem0_sync_success_total": (
        "counter",
        "Total successful mem0 bridge sync operations.",
    ),
    "mcp_requests_total": (
        "counter",
        "Total MCP JSON-RPC requests handled by the runtime.",
    ),
    "mcp_tool_calls_total": (
        "counter",
        "Total MCP tool calls handled by the runtime.",
    ),
    "mcp_write_tool_calls_total": (
        "counter",
        "Total MCP write-oriented tool calls handled by the runtime.",
    ),
    "mcp_resource_reads_total": (
        "counter",
        "Total MCP resource reads handled by the runtime.",
    ),
    "mcp_prompt_requests_total": (
        "counter",
        "Total MCP prompt requests handled by the runtime.",
    ),
    "mcp_errors_total": (
        "counter",
        "Total MCP request errors returned by the runtime.",
    ),
}
_KNOWN_COUNTERS = set(_METRIC_DEFINITIONS)
_COUNTERS: Counter[str] = Counter()
_MCP_METHOD_COUNTERS: Counter[tuple[str, str]] = Counter()
_MCP_TOOL_COUNTERS: Counter[tuple[str, str]] = Counter()
_MCP_RESOURCE_COUNTERS: Counter[tuple[str, str]] = Counter()
_MCP_PROMPT_COUNTERS: Counter[tuple[str, str]] = Counter()
_MCP_CLIENT_COUNTERS: Counter[str] = Counter()
_MCP_REQUEST_LATENCY_BUCKETS: Counter[str] = Counter()
_MCP_TOOL_LATENCY_BUCKETS: Counter[str] = Counter()
_LOCK = Lock()

_LATENCY_BUCKETS_MS = (50, 250, 1000, 5000, 10000)


def increment_metric(name: str, value: int = 1) -> None:
    with _LOCK:
        _COUNTERS[name] += value


def monotonic_timer() -> float:
    return perf_counter()


def elapsed_milliseconds(start: float) -> int:
    return max(0, int((perf_counter() - start) * 1000))


def record_mcp_request(*, method: str, status: str, client_name: str, latency_ms: int) -> None:
    with _LOCK:
        _MCP_METHOD_COUNTERS[(method, status)] += 1
        _MCP_CLIENT_COUNTERS[client_name] += 1
        _MCP_REQUEST_LATENCY_BUCKETS[_latency_bucket(latency_ms)] += 1


def record_mcp_tool_call(*, tool_name: str, status: str, latency_ms: int) -> None:
    with _LOCK:
        _MCP_TOOL_COUNTERS[(tool_name, status)] += 1
        _MCP_TOOL_LATENCY_BUCKETS[_latency_bucket(latency_ms)] += 1


def record_mcp_resource_read(*, resource_name: str, status: str) -> None:
    with _LOCK:
        _MCP_RESOURCE_COUNTERS[(resource_name, status)] += 1


def record_mcp_prompt_request(*, prompt_name: str, status: str) -> None:
    with _LOCK:
        _MCP_PROMPT_COUNTERS[(prompt_name, status)] += 1


def snapshot_mcp_metrics() -> dict[str, dict]:
    with _LOCK:
        return {
            "requests_by_method": _pair_counter_snapshot(_MCP_METHOD_COUNTERS),
            "tool_calls_by_name": _pair_counter_snapshot(_MCP_TOOL_COUNTERS),
            "resource_reads_by_name": _pair_counter_snapshot(_MCP_RESOURCE_COUNTERS),
            "prompt_requests_by_name": _pair_counter_snapshot(_MCP_PROMPT_COUNTERS),
            "requests_by_client": dict(sorted(_MCP_CLIENT_COUNTERS.items())),
            "request_latency_buckets_ms": dict(sorted(_MCP_REQUEST_LATENCY_BUCKETS.items())),
            "tool_latency_buckets_ms": dict(sorted(_MCP_TOOL_LATENCY_BUCKETS.items())),
        }


def snapshot_metrics() -> dict[str, int]:
    with _LOCK:
        snapshot = {name: 0 for name in _KNOWN_COUNTERS}
        snapshot.update(_COUNTERS)
        return snapshot


def reset_metrics() -> None:
    with _LOCK:
        _COUNTERS.clear()
        _MCP_METHOD_COUNTERS.clear()
        _MCP_TOOL_COUNTERS.clear()
        _MCP_RESOURCE_COUNTERS.clear()
        _MCP_PROMPT_COUNTERS.clear()
        _MCP_CLIENT_COUNTERS.clear()
        _MCP_REQUEST_LATENCY_BUCKETS.clear()
        _MCP_TOOL_LATENCY_BUCKETS.clear()


def render_prometheus_metrics(
    *,
    counters: dict[str, int] | None = None,
    job_status_counts: dict[str, int] | None = None,
    job_type_status_counts: dict[tuple[str, str], int] | None = None,
    mcp_metrics: dict[str, dict] | None = None,
) -> str:
    metric_values = counters or snapshot_metrics()
    job_status_counts = job_status_counts or {}
    job_type_status_counts = job_type_status_counts or {}
    mcp_metrics = mcp_metrics or snapshot_mcp_metrics()

    lines: list[str] = []
    for name in sorted(_METRIC_DEFINITIONS):
        metric_type, description = _METRIC_DEFINITIONS[name]
        metric_name = f"memory_runtime_{name}"
        lines.append(f"# HELP {metric_name} {description}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        lines.append(f"{metric_name} {metric_values.get(name, 0)}")

    lines.append("# HELP memory_runtime_job_status Current job count by status.")
    lines.append("# TYPE memory_runtime_job_status gauge")
    for status in sorted(job_status_counts):
        lines.append(f'memory_runtime_job_status{{status="{status}"}} {job_status_counts[status]}')

    lines.append("# HELP memory_runtime_job_status_by_type Current job count by type and status.")
    lines.append("# TYPE memory_runtime_job_status_by_type gauge")
    for job_type, status in sorted(job_type_status_counts):
        value = job_type_status_counts[(job_type, status)]
        lines.append(
            f'memory_runtime_job_status_by_type{{job_type="{job_type}",status="{status}"}} {value}'
        )

    lines.append("# HELP memory_runtime_mcp_request_by_method_total MCP requests grouped by JSON-RPC method and outcome.")
    lines.append("# TYPE memory_runtime_mcp_request_by_method_total counter")
    for method, statuses in sorted((mcp_metrics.get("requests_by_method") or {}).items()):
        for status, value in sorted(statuses.items()):
            lines.append(
                f'memory_runtime_mcp_request_by_method_total{{method="{method}",status="{status}"}} {value}'
            )

    lines.append("# HELP memory_runtime_mcp_tool_call_by_name_total MCP tool calls grouped by tool and outcome.")
    lines.append("# TYPE memory_runtime_mcp_tool_call_by_name_total counter")
    for tool_name, statuses in sorted((mcp_metrics.get("tool_calls_by_name") or {}).items()):
        for status, value in sorted(statuses.items()):
            lines.append(
                f'memory_runtime_mcp_tool_call_by_name_total{{tool_name="{tool_name}",status="{status}"}} {value}'
            )

    lines.append("# HELP memory_runtime_mcp_resource_read_by_name_total MCP resource reads grouped by resource and outcome.")
    lines.append("# TYPE memory_runtime_mcp_resource_read_by_name_total counter")
    for resource_name, statuses in sorted((mcp_metrics.get("resource_reads_by_name") or {}).items()):
        for status, value in sorted(statuses.items()):
            lines.append(
                f'memory_runtime_mcp_resource_read_by_name_total{{resource_name="{resource_name}",status="{status}"}} {value}'
            )

    lines.append("# HELP memory_runtime_mcp_prompt_request_by_name_total MCP prompt requests grouped by prompt and outcome.")
    lines.append("# TYPE memory_runtime_mcp_prompt_request_by_name_total counter")
    for prompt_name, statuses in sorted((mcp_metrics.get("prompt_requests_by_name") or {}).items()):
        for status, value in sorted(statuses.items()):
            lines.append(
                f'memory_runtime_mcp_prompt_request_by_name_total{{prompt_name="{prompt_name}",status="{status}"}} {value}'
            )

    lines.append("# HELP memory_runtime_mcp_request_by_client_total MCP requests grouped by client name.")
    lines.append("# TYPE memory_runtime_mcp_request_by_client_total counter")
    for client_name, value in sorted((mcp_metrics.get("requests_by_client") or {}).items()):
        lines.append(f'memory_runtime_mcp_request_by_client_total{{client_name="{client_name}"}} {value}')

    lines.append("# HELP memory_runtime_mcp_request_latency_bucket_total MCP request latency bucket counts in milliseconds.")
    lines.append("# TYPE memory_runtime_mcp_request_latency_bucket_total counter")
    for bucket, value in sorted((mcp_metrics.get("request_latency_buckets_ms") or {}).items()):
        lines.append(f'memory_runtime_mcp_request_latency_bucket_total{{bucket_ms="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_mcp_tool_latency_bucket_total MCP tool latency bucket counts in milliseconds.")
    lines.append("# TYPE memory_runtime_mcp_tool_latency_bucket_total counter")
    for bucket, value in sorted((mcp_metrics.get("tool_latency_buckets_ms") or {}).items()):
        lines.append(f'memory_runtime_mcp_tool_latency_bucket_total{{bucket_ms="{bucket}"}} {value}')

    return "\n".join(lines) + "\n"


def _latency_bucket(latency_ms: int) -> str:
    for upper_bound in _LATENCY_BUCKETS_MS:
        if latency_ms <= upper_bound:
            return f"le_{upper_bound}"
    return "gt_10000"


def _pair_counter_snapshot(counter: Counter[tuple[str, str]]) -> dict[str, dict[str, int]]:
    snapshot: dict[str, dict[str, int]] = {}
    for (name, status), value in sorted(counter.items()):
        snapshot.setdefault(name, {})[status] = value
    return snapshot
