from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from statistics import mean
from time import perf_counter
from uuid import uuid4

from app.http_client import create_local_runtime_client


def _wait_for_jobs(
    client,
    *,
    job_drainer: Callable[[], int] | None,
    poll_seconds: float,
    max_wait_seconds: float,
) -> dict[str, object]:
    deadline = time.time() + max_wait_seconds
    stats_payload: dict[str, object] = {}
    while True:
        if job_drainer is not None:
            job_drainer()
        stats_response = client.get("/v1/observability/stats")
        stats_response.raise_for_status()
        stats_payload = stats_response.json()
        pending = stats_payload["jobs"]["by_status"].get("pending", 0)
        if pending == 0 or time.time() >= deadline:
            return stats_payload
        time.sleep(poll_seconds)


def _percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return float(ordered[index])


def _summary(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "min": float(min(values)),
        "avg": round(mean(values), 4),
        "p50": _percentile(values, 0.5),
        "p95": _percentile(values, 0.95),
        "max": float(max(values)),
    }


def run_performance_benchmark(
    client,
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 200,
    query_count: int = 5,
    job_drainer: Callable[[], int] | None = None,
    poll_seconds: float = 0.25,
    max_wait_seconds: float = 20.0,
) -> dict[str, object]:
    suffix = namespace_suffix or str(uuid4())
    bootstrap = client.post(
        "/v1/adapters/openclaw/bootstrap",
        json={
            "namespace_name": f"benchmark:{suffix}:performance",
            "agent_name": "planner",
            "external_ref": f"{suffix}:performance",
        },
    )
    bootstrap.raise_for_status()
    scope = bootstrap.json()
    namespace_id = scope["namespace_id"]
    agent_id = scope["agent_id"]

    seed_memories = [
        (
            "architecture_decision",
            "project-space",
            "assistant",
            "We decided to keep Postgres, Redis, and a dedicated worker as the runtime baseline.",
        ),
        (
            "policy_update",
            "agent-core",
            "user",
            "For pilot summaries, always start with the verdict before details.",
        ),
        (
            "conversation_turn",
            "project-space",
            "assistant",
            "The live pilot still needs the acceptance checklist and rollback notes before launch.",
        ),
    ]
    noise_count = max(0, memory_count - len(seed_memories))

    for index, (event_type, space_hint, role, content) in enumerate(seed_memories):
        response = client.post(
            "/v1/adapters/openclaw/events",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": f"{suffix}:seed:{index}",
                "event_type": event_type,
                "space_hint": space_hint,
                "event_origin": "agent_output" if role == "assistant" else "user_input",
                "messages": [{"role": role, "content": content}],
            },
        )
        response.raise_for_status()

    for index in range(noise_count):
        response = client.post(
            "/v1/adapters/openclaw/events",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": f"{suffix}:noise:{index}",
                "event_type": "conversation_turn",
                "space_hint": "project-space",
                "event_origin": "agent_output",
                "messages": [
                    {
                        "role": "assistant",
                        "content": (
                            f"Low-value chatter {index}: bakery ideas, postponed errands, scratch rename notes, "
                            "and deprecated side experiments that should not matter for runtime recall."
                        ),
                    }
                ],
            },
        )
        response.raise_for_status()

    stats_payload = _wait_for_jobs(
        client,
        job_drainer=job_drainer,
        poll_seconds=poll_seconds,
        max_wait_seconds=max_wait_seconds,
    )

    queries = [
        "What runtime architecture has already been decided?",
        "How should pilot updates be presented?",
        "What project context still matters before the live pilot?",
        "Summarize the durable runtime stack and rollout guidance.",
        "What matters for the memory runtime pilot right now?",
    ][: max(1, query_count)]

    results: list[dict[str, object]] = []
    latencies_ms: list[int] = []
    candidate_counts: list[int] = []
    selected_counts: list[int] = []
    brief_chars: list[int] = []

    for index, query in enumerate(queries):
        started_at = perf_counter()
        recall = client.post(
            "/v1/adapters/openclaw/recall",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": f"{suffix}:recall:{index}",
                "query": query,
                "context_budget_tokens": 900,
            },
        )
        recall.raise_for_status()
        latency_ms = max(0, int((perf_counter() - started_at) * 1000))
        payload = recall.json()
        flattened = "\n".join(item for items in payload["brief"].values() for item in items)
        latencies_ms.append(latency_ms)
        candidate_counts.append(int(payload["trace"]["candidate_count"]))
        selected_counts.append(int(payload["trace"]["selected_count"]))
        brief_chars.append(len(flattened))
        results.append(
            {
                "query": query,
                "latency_ms": latency_ms,
                "candidate_count": payload["trace"]["candidate_count"],
                "selected_count": payload["trace"]["selected_count"],
                "brief_chars": len(flattened),
                "selected_space_types": payload["trace"]["selected_space_types"],
            }
        )

    return {
        "namespace_id": namespace_id,
        "agent_id": agent_id,
        "memory_count": memory_count,
        "query_count": len(results),
        "jobs_by_status": stats_payload["jobs"]["by_status"],
        "metrics": {
            "latency_ms": _summary(latencies_ms),
            "candidate_count": _summary(candidate_counts),
            "selected_count": _summary(selected_counts),
            "brief_chars": _summary(brief_chars),
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a high-density performance benchmark against memory-runtime.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--memory-count", type=int, default=200)
    parser.add_argument("--query-count", type=int, default=5)
    parser.add_argument("--poll-seconds", type=float, default=0.25)
    parser.add_argument("--max-wait-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)

    with create_local_runtime_client(base_url=args.base_url, timeout=30.0) as client:
        report = run_performance_benchmark(
            client,
            namespace_suffix=args.namespace_suffix,
            memory_count=args.memory_count,
            query_count=args.query_count,
            poll_seconds=args.poll_seconds,
            max_wait_seconds=args.max_wait_seconds,
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
