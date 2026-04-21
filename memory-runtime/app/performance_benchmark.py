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


def _make_noise(
    *,
    prefix: str,
    count: int,
    space_hint: str = "project-space",
    event_origin: str = "agent_output",
    role: str = "assistant",
) -> list[dict[str, str]]:
    return [
        {
            "event_type": "conversation_turn",
            "space_hint": space_hint,
            "event_origin": event_origin,
            "role": role,
            "content": (
                f"{prefix} {index}: bakery ideas, postponed errands, scratch rename notes, "
                "deprecated side experiments, and low-value chatter that should not matter for runtime recall."
            ),
        }
        for index in range(count)
    ]


def _scenario_catalog(memory_count: int, query_count: int) -> dict[str, dict[str, object]]:
    noise_count = max(0, memory_count)
    return {
        "balanced_runtime": {
            "description": "Balanced durable runtime facts mixed with heavy low-value project chatter.",
            "seeds": [
                {
                    "event_type": "architecture_decision",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "We decided to keep Postgres, Redis, and a dedicated worker as the runtime baseline.",
                },
                {
                    "event_type": "policy_update",
                    "space_hint": "agent-core",
                    "event_origin": "user_input",
                    "role": "user",
                    "content": "For pilot summaries, always start with the verdict before details.",
                },
                {
                    "event_type": "conversation_turn",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "The live pilot still needs the acceptance checklist and rollback notes before launch.",
                },
            ]
            + _make_noise(prefix="Balanced runtime chatter", count=max(0, noise_count - 3)),
            "queries": [
                "What runtime architecture has already been decided?",
                "How should pilot updates be presented?",
                "What project context still matters before the live pilot?",
                "Summarize the durable runtime stack and rollout guidance.",
                "What matters for the memory runtime pilot right now?",
            ][: max(1, query_count)],
        },
        "procedure_heavy": {
            "description": "Many procedural/agent-core memories competing with noisy project chatter.",
            "seeds": [
                {
                    "event_type": "policy_update",
                    "space_hint": "agent-core",
                    "event_origin": "user_input",
                    "role": "user",
                    "content": "Always lead with the verdict, then the evidence, then the backlog.",
                },
                {
                    "event_type": "policy_update",
                    "space_hint": "agent-core",
                    "event_origin": "user_input",
                    "role": "user",
                    "content": "Include owner and deadline whenever you summarize follow-up actions.",
                },
                {
                    "event_type": "architecture_decision",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "The runtime stack stays on Postgres and Redis for the pilot period.",
                },
            ]
            + _make_noise(prefix="Procedure-heavy chatter", count=max(0, noise_count - 3)),
            "queries": [
                "How should pilot reports be structured?",
                "What standing procedures should the planner follow?",
                "What durable runtime stack is still in effect?",
                "Summarize the reporting rules and rollout context.",
                "What should the agent remember before posting an update?",
            ][: max(1, query_count)],
        },
        "session_pressure": {
            "description": "Large active-session carryover competing with durable background context.",
            "seeds": [
                {
                    "event_type": "architecture_decision",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "We decided to keep the dedicated worker and Postgres-backed runtime for the pilot.",
                },
                {
                    "event_type": "conversation_turn",
                    "space_hint": "session-space",
                    "event_origin": "user_input",
                    "role": "user",
                    "content": "In the current session we still need the acceptance checklist and the rollback owner before launch.",
                    "session_scope": "active",
                },
                {
                    "event_type": "conversation_turn",
                    "space_hint": "session-space",
                    "event_origin": "user_input",
                    "role": "user",
                    "content": "In this session the final blocker is confirming the worker heartbeat and retry policy.",
                    "session_scope": "active",
                },
            ]
            + _make_noise(prefix="Session carryover chatter", count=max(0, noise_count - 3)),
            "queries": [
                "What still matters in the current session before launch?",
                "What active-session carryover should I keep in mind right now?",
                "Summarize the current-session blockers and durable runtime context.",
                "What still needs action before the pilot launch in this session?",
                "What is the current session waiting on?",
            ][: max(1, query_count)],
        },
        "integration_mix": {
            "description": "Integration-heavy memory pool with OpenClaw, MCP, and adapter facts mixed with noise.",
            "seeds": [
                {
                    "event_type": "architecture_decision",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "OpenClaw uses runtime mode against the standalone memory-runtime service on localhost.",
                },
                {
                    "event_type": "conversation_turn",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "The MCP facade already supports memory.recall, memory.ingest_event, and memory.record_feedback.",
                },
                {
                    "event_type": "conversation_turn",
                    "space_hint": "project-space",
                    "event_origin": "agent_output",
                    "role": "assistant",
                    "content": "BunkerAI shares durable integration context through the same adapter surface.",
                },
            ]
            + _make_noise(prefix="Integration chatter", count=max(0, noise_count - 3)),
            "queries": [
                "What integration surfaces already exist for the memory runtime?",
                "What should I remember about OpenClaw and MCP integration?",
                "Summarize the adapter and MCP capabilities.",
                "What cross-system context exists for OpenClaw and BunkerAI?",
                "What integration facts matter right now?",
            ][: max(1, query_count)],
        },
    }


def _run_single_scenario(
    client,
    *,
    scenario_name: str,
    scenario: dict[str, object],
    namespace_suffix: str,
    job_drainer: Callable[[], int] | None,
    poll_seconds: float,
    max_wait_seconds: float,
) -> dict[str, object]:
    bootstrap = client.post(
        "/v1/adapters/openclaw/bootstrap",
        json={
            "namespace_name": f"benchmark:{namespace_suffix}:{scenario_name}",
            "agent_name": "planner",
            "external_ref": f"{namespace_suffix}:{scenario_name}",
        },
    )
    bootstrap.raise_for_status()
    scope = bootstrap.json()
    namespace_id = scope["namespace_id"]
    agent_id = scope["agent_id"]
    active_session_id = f"{namespace_suffix}:{scenario_name}:active-session"

    seeds = scenario["seeds"]
    for index, seed in enumerate(seeds):
        session_id = (
            active_session_id
            if seed.get("session_scope") == "active"
            else f"{namespace_suffix}:{scenario_name}:seed:{index}"
        )
        response = client.post(
            "/v1/adapters/openclaw/events",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "event_type": seed["event_type"],
                "space_hint": seed["space_hint"],
                "event_origin": seed["event_origin"],
                "messages": [{"role": seed["role"], "content": seed["content"]}],
            },
        )
        response.raise_for_status()

    stats_payload = _wait_for_jobs(
        client,
        job_drainer=job_drainer,
        poll_seconds=poll_seconds,
        max_wait_seconds=max_wait_seconds,
    )

    results: list[dict[str, object]] = []
    latencies_ms: list[int] = []
    candidate_counts: list[int] = []
    selected_counts: list[int] = []
    brief_chars: list[int] = []

    for index, query in enumerate(scenario["queries"]):
        started_at = perf_counter()
        recall = client.post(
            "/v1/adapters/openclaw/recall",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": active_session_id if scenario_name == "session_pressure" else f"{namespace_suffix}:{scenario_name}:recall:{index}",
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
        "scenario": scenario_name,
        "description": scenario["description"],
        "namespace_id": namespace_id,
        "agent_id": agent_id,
        "memory_count": len(seeds),
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


def run_performance_benchmark(
    client,
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 200,
    query_count: int = 5,
    scenario: str = "balanced_runtime",
    job_drainer: Callable[[], int] | None = None,
    poll_seconds: float = 0.25,
    max_wait_seconds: float = 20.0,
) -> dict[str, object]:
    suffix = namespace_suffix or str(uuid4())
    catalog = _scenario_catalog(memory_count=memory_count, query_count=query_count)
    if scenario not in catalog:
        raise ValueError(f"Unknown scenario '{scenario}'")
    return _run_single_scenario(
        client,
        scenario_name=scenario,
        scenario=catalog[scenario],
        namespace_suffix=suffix,
        job_drainer=job_drainer,
        poll_seconds=poll_seconds,
        max_wait_seconds=max_wait_seconds,
    )


def run_performance_benchmark_pool(
    client,
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 200,
    query_count: int = 5,
    scenarios: list[str] | None = None,
    job_drainer: Callable[[], int] | None = None,
    poll_seconds: float = 0.25,
    max_wait_seconds: float = 20.0,
) -> dict[str, object]:
    suffix = namespace_suffix or str(uuid4())
    catalog = _scenario_catalog(memory_count=memory_count, query_count=query_count)
    scenario_names = scenarios or list(catalog.keys())

    reports = [
        _run_single_scenario(
            client,
            scenario_name=name,
            scenario=catalog[name],
            namespace_suffix=suffix,
            job_drainer=job_drainer,
            poll_seconds=poll_seconds,
            max_wait_seconds=max_wait_seconds,
        )
        for name in scenario_names
    ]

    latency_values = [int(report["metrics"]["latency_ms"]["avg"]) for report in reports]
    candidate_values = [int(report["metrics"]["candidate_count"]["avg"]) for report in reports]
    selected_values = [int(report["metrics"]["selected_count"]["avg"]) for report in reports]
    brief_char_values = [int(report["metrics"]["brief_chars"]["avg"]) for report in reports]

    return {
        "scenario_count": len(reports),
        "memory_count_per_scenario": memory_count,
        "query_count_per_scenario": query_count,
        "scenarios": reports,
        "overall": {
            "latency_ms": _summary(latency_values),
            "candidate_count": _summary(candidate_values),
            "selected_count": _summary(selected_values),
            "brief_chars": _summary(brief_char_values),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run performance benchmarks against memory-runtime.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--memory-count", type=int, default=200)
    parser.add_argument("--query-count", type=int, default=5)
    parser.add_argument(
        "--scenario",
        default="all",
        choices=["all", "balanced_runtime", "procedure_heavy", "session_pressure", "integration_mix"],
    )
    parser.add_argument("--poll-seconds", type=float, default=0.25)
    parser.add_argument("--max-wait-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)

    with create_local_runtime_client(base_url=args.base_url, timeout=30.0) as client:
        if args.scenario == "all":
            report = run_performance_benchmark_pool(
                client,
                namespace_suffix=args.namespace_suffix,
                memory_count=args.memory_count,
                query_count=args.query_count,
                poll_seconds=args.poll_seconds,
                max_wait_seconds=args.max_wait_seconds,
            )
        else:
            report = run_performance_benchmark(
                client,
                namespace_suffix=args.namespace_suffix,
                memory_count=args.memory_count,
                query_count=args.query_count,
                scenario=args.scenario,
                poll_seconds=args.poll_seconds,
                max_wait_seconds=args.max_wait_seconds,
            )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
