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
_RECALL_LATENCY_BUCKETS: Counter[str] = Counter()
_RECALL_CANDIDATE_BUCKETS: Counter[str] = Counter()
_RECALL_SELECTED_BUCKETS: Counter[str] = Counter()
_RECALL_EXTERNAL_CANDIDATE_BUCKETS: Counter[str] = Counter()
_RECALL_BRIEF_ITEM_BUCKETS: Counter[str] = Counter()
_RECALL_PHASE_TOTALS: Counter[str] = Counter()
_RECALL_PHASE_MAX: Counter[str] = Counter()
_RECALL_PHASE_BUCKETS: Counter[tuple[str, str]] = Counter()
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


def record_recall_observation(
    *,
    latency_ms: int,
    candidate_count: int,
    selected_count: int,
    external_candidate_count: int,
    brief_item_count: int,
    phase_latencies_ms: dict[str, int] | None = None,
) -> None:
    with _LOCK:
        _RECALL_LATENCY_BUCKETS[_latency_bucket(latency_ms)] += 1
        _RECALL_CANDIDATE_BUCKETS[_count_bucket(candidate_count)] += 1
        _RECALL_SELECTED_BUCKETS[_count_bucket(selected_count)] += 1
        _RECALL_EXTERNAL_CANDIDATE_BUCKETS[_count_bucket(external_candidate_count)] += 1
        _RECALL_BRIEF_ITEM_BUCKETS[_count_bucket(brief_item_count)] += 1
        _COUNTERS["recall_latency_ms_total"] += latency_ms
        _COUNTERS["recall_candidate_count_total"] += candidate_count
        _COUNTERS["recall_selected_count_total"] += selected_count
        _COUNTERS["recall_external_candidate_count_total"] += external_candidate_count
        _COUNTERS["recall_brief_item_count_total"] += brief_item_count
        _COUNTERS["recall_latency_ms_max"] = max(_COUNTERS["recall_latency_ms_max"], latency_ms)
        for phase, value in sorted((phase_latencies_ms or {}).items()):
            _RECALL_PHASE_TOTALS[phase] += value
            _RECALL_PHASE_MAX[phase] = max(_RECALL_PHASE_MAX[phase], value)
            _RECALL_PHASE_BUCKETS[(phase, _latency_bucket(value))] += 1


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


def snapshot_recall_metrics() -> dict[str, object]:
    with _LOCK:
        observed = int(_COUNTERS.get("recall_requests_total", 0))
        latency_total = int(_COUNTERS.get("recall_latency_ms_total", 0))
        candidate_total = int(_COUNTERS.get("recall_candidate_count_total", 0))
        selected_total = int(_COUNTERS.get("recall_selected_count_total", 0))
        external_total = int(_COUNTERS.get("recall_external_candidate_count_total", 0))
        brief_total = int(_COUNTERS.get("recall_brief_item_count_total", 0))
        phase_totals = dict(sorted(_RECALL_PHASE_TOTALS.items()))
        phase_max = dict(sorted(_RECALL_PHASE_MAX.items()))
        phase_buckets: dict[str, dict[str, int]] = {}
        for (phase, bucket), value in sorted(_RECALL_PHASE_BUCKETS.items()):
            phase_buckets.setdefault(phase, {})[bucket] = value
        return {
            "requests_observed_total": observed,
            "latency_buckets_ms": dict(sorted(_RECALL_LATENCY_BUCKETS.items())),
            "candidate_buckets": dict(sorted(_RECALL_CANDIDATE_BUCKETS.items())),
            "selected_buckets": dict(sorted(_RECALL_SELECTED_BUCKETS.items())),
            "external_candidate_buckets": dict(sorted(_RECALL_EXTERNAL_CANDIDATE_BUCKETS.items())),
            "brief_item_buckets": dict(sorted(_RECALL_BRIEF_ITEM_BUCKETS.items())),
            "latency_ms_total": latency_total,
            "latency_ms_max": int(_COUNTERS.get("recall_latency_ms_max", 0)),
            "phase_latency_ms_total": phase_totals,
            "phase_latency_ms_max": phase_max,
            "phase_latency_buckets_ms": phase_buckets,
            "phase_avg_latency_ms": {
                phase: round((total / observed) if observed else 0.0, 4)
                for phase, total in phase_totals.items()
            },
            "avg_candidate_count": round((candidate_total / observed) if observed else 0.0, 4),
            "avg_selected_count": round((selected_total / observed) if observed else 0.0, 4),
            "avg_external_candidate_count": round((external_total / observed) if observed else 0.0, 4),
            "avg_brief_item_count": round((brief_total / observed) if observed else 0.0, 4),
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
        _RECALL_LATENCY_BUCKETS.clear()
        _RECALL_CANDIDATE_BUCKETS.clear()
        _RECALL_SELECTED_BUCKETS.clear()
        _RECALL_EXTERNAL_CANDIDATE_BUCKETS.clear()
        _RECALL_BRIEF_ITEM_BUCKETS.clear()
        _RECALL_PHASE_TOTALS.clear()
        _RECALL_PHASE_MAX.clear()
        _RECALL_PHASE_BUCKETS.clear()


def render_prometheus_metrics(
    *,
    counters: dict[str, int] | None = None,
    job_status_counts: dict[str, int] | None = None,
    job_type_status_counts: dict[tuple[str, str], int] | None = None,
    mcp_metrics: dict[str, dict] | None = None,
    quality_metrics: dict[str, dict] | None = None,
) -> str:
    metric_values = counters or snapshot_metrics()
    job_status_counts = job_status_counts or {}
    job_type_status_counts = job_type_status_counts or {}
    mcp_metrics = mcp_metrics or snapshot_mcp_metrics()
    quality_metrics = quality_metrics or {}

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

    recall_metrics = quality_metrics.get("__recall_performance__") or {}
    lines.append("# HELP memory_runtime_recall_latency_bucket_total Recall latency bucket counts in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_latency_bucket_total counter")
    for bucket, value in sorted((recall_metrics.get("latency_buckets_ms") or {}).items()):
        lines.append(f'memory_runtime_recall_latency_bucket_total{{bucket_ms="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_recall_candidate_bucket_total Recall candidate-count bucket totals.")
    lines.append("# TYPE memory_runtime_recall_candidate_bucket_total counter")
    for bucket, value in sorted((recall_metrics.get("candidate_buckets") or {}).items()):
        lines.append(f'memory_runtime_recall_candidate_bucket_total{{bucket="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_recall_selected_bucket_total Recall selected-count bucket totals.")
    lines.append("# TYPE memory_runtime_recall_selected_bucket_total counter")
    for bucket, value in sorted((recall_metrics.get("selected_buckets") or {}).items()):
        lines.append(f'memory_runtime_recall_selected_bucket_total{{bucket="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_recall_external_candidate_bucket_total External recall candidate-count bucket totals.")
    lines.append("# TYPE memory_runtime_recall_external_candidate_bucket_total counter")
    for bucket, value in sorted((recall_metrics.get("external_candidate_buckets") or {}).items()):
        lines.append(f'memory_runtime_recall_external_candidate_bucket_total{{bucket="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_recall_brief_item_bucket_total Recall brief-item-count bucket totals.")
    lines.append("# TYPE memory_runtime_recall_brief_item_bucket_total counter")
    for bucket, value in sorted((recall_metrics.get("brief_item_buckets") or {}).items()):
        lines.append(f'memory_runtime_recall_brief_item_bucket_total{{bucket="{bucket}"}} {value}')

    lines.append("# HELP memory_runtime_recall_latency_ms_total Total recall latency in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_latency_ms_total counter")
    lines.append(f'memory_runtime_recall_latency_ms_total {int(recall_metrics.get("latency_ms_total", 0))}')

    lines.append("# HELP memory_runtime_recall_latency_ms_max Maximum observed recall latency in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_latency_ms_max gauge")
    lines.append(f'memory_runtime_recall_latency_ms_max {int(recall_metrics.get("latency_ms_max", 0))}')

    lines.append("# HELP memory_runtime_recall_phase_latency_ms_total Total recall latency by internal phase in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_phase_latency_ms_total counter")
    for phase, value in sorted((recall_metrics.get("phase_latency_ms_total") or {}).items()):
        lines.append(f'memory_runtime_recall_phase_latency_ms_total{{phase="{phase}"}} {int(value)}')

    lines.append("# HELP memory_runtime_recall_phase_latency_ms_max Maximum observed recall latency by internal phase in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_phase_latency_ms_max gauge")
    for phase, value in sorted((recall_metrics.get("phase_latency_ms_max") or {}).items()):
        lines.append(f'memory_runtime_recall_phase_latency_ms_max{{phase="{phase}"}} {int(value)}')

    lines.append("# HELP memory_runtime_recall_phase_latency_bucket_total Recall phase latency bucket counts in milliseconds.")
    lines.append("# TYPE memory_runtime_recall_phase_latency_bucket_total counter")
    for phase, buckets in sorted((recall_metrics.get("phase_latency_buckets_ms") or {}).items()):
        for bucket, value in sorted(buckets.items()):
            lines.append(
                f'memory_runtime_recall_phase_latency_bucket_total{{phase="{phase}",bucket_ms="{bucket}"}} {value}'
            )

    lines.append("# HELP memory_runtime_promotion_decision_total Promotion decisions grouped by outcome and reason.")
    lines.append("# TYPE memory_runtime_promotion_decision_total counter")
    for reason_name, reason_counts in (
        ("promote", quality_metrics.get("promote_reasons") or {}),
        ("session_only", quality_metrics.get("session_only_reasons") or {}),
        ("reject", quality_metrics.get("reject_reasons") or {}),
    ):
        for reason, value in sorted(reason_counts.items()):
            lines.append(
                f'memory_runtime_promotion_decision_total{{outcome="{reason_name}",reason="{reason}"}} {value}'
            )

    lines.append("# HELP memory_runtime_promotion_signal_total Promotion-decision signal flags set to true.")
    lines.append("# TYPE memory_runtime_promotion_signal_total counter")
    for signal_name, value in sorted((quality_metrics.get("signal_flags") or {}).items()):
        lines.append(f'memory_runtime_promotion_signal_total{{signal="{signal_name}"}} {value}')

    lines.append("# HELP memory_runtime_promotion_novelty_state_total Promotion decisions grouped by novelty state.")
    lines.append("# TYPE memory_runtime_promotion_novelty_state_total counter")
    for state, value in sorted((quality_metrics.get("novelty_states") or {}).items()):
        lines.append(f'memory_runtime_promotion_novelty_state_total{{state="{state}"}} {value}')

    rescue = quality_metrics.get("rescue") or {}
    lines.append("# HELP memory_runtime_rescue_event_total Rescue outcomes grouped by status and key.")
    lines.append("# TYPE memory_runtime_rescue_event_total counter")
    for trigger, value in sorted((rescue.get("applied_by_trigger") or {}).items()):
        lines.append(f'memory_runtime_rescue_event_total{{status="applied",key="{trigger}"}} {value}')
    for reason, value in sorted((rescue.get("blocked_by_reason") or {}).items()):
        lines.append(f'memory_runtime_rescue_event_total{{status="blocked",key="{reason}"}} {value}')

    return "\n".join(lines) + "\n"


def _latency_bucket(latency_ms: int) -> str:
    for upper_bound in _LATENCY_BUCKETS_MS:
        if latency_ms <= upper_bound:
            return f"le_{upper_bound}"
    return "gt_10000"


def _count_bucket(value: int) -> str:
    thresholds = (1, 3, 5, 10, 25, 50, 100, 250, 500)
    for upper_bound in thresholds:
        if value <= upper_bound:
            return f"le_{upper_bound}"
    return "gt_500"


def _pair_counter_snapshot(counter: Counter[tuple[str, str]]) -> dict[str, dict[str, int]]:
    snapshot: dict[str, dict[str, int]] = {}
    for (name, status), value in sorted(counter.items()):
        snapshot.setdefault(name, {})[status] = value
    return snapshot
