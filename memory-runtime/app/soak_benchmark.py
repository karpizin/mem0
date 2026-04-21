from __future__ import annotations

import argparse
import json
from statistics import mean
from time import perf_counter

from app.http_client import create_local_runtime_client
from app.performance_benchmark import _summary, run_performance_benchmark


def run_soak_benchmark(
    client,
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 500,
    iterations: int = 50,
    scenario: str = "balanced_runtime",
) -> dict[str, object]:
    warmup = run_performance_benchmark(
        client,
        namespace_suffix=namespace_suffix,
        memory_count=memory_count,
        query_count=1,
        scenario=scenario,
    )
    namespace_id = warmup["namespace_id"]
    agent_id = warmup["agent_id"]

    latencies_ms: list[int] = []
    selected_counts: list[int] = []
    brief_chars: list[int] = []
    failures = 0

    query = "What runtime architecture and rollout guidance matter right now?"
    for index in range(iterations):
        started_at = perf_counter()
        response = client.post(
            "/v1/adapters/openclaw/recall",
            json={
                "namespace_id": namespace_id,
                "agent_id": agent_id,
                "session_id": f"{namespace_suffix or 'soak'}:soak:{index}",
                "query": query,
                "context_budget_tokens": 900,
            },
        )
        latency_ms = max(0, int((perf_counter() - started_at) * 1000))
        latencies_ms.append(latency_ms)

        if response.status_code != 200:
            failures += 1
            continue

        payload = response.json()
        selected_counts.append(int(payload["trace"]["selected_count"]))
        flattened = "\n".join(item for items in payload["brief"].values() for item in items)
        brief_chars.append(len(flattened))

    return {
        "scenario": scenario,
        "memory_count": memory_count,
        "iterations": iterations,
        "failures": failures,
        "failure_rate": round((failures / iterations) if iterations else 0.0, 4),
        "latency_ms": _summary(latencies_ms),
        "selected_count": _summary(selected_counts),
        "brief_chars": _summary(brief_chars),
        "selected_count_mean": round(mean(selected_counts), 4) if selected_counts else 0.0,
        "brief_chars_mean": round(mean(brief_chars), 4) if brief_chars else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a repeated-recall soak benchmark against memory-runtime.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--memory-count", type=int, default=500)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument(
        "--scenario",
        default="balanced_runtime",
        choices=["balanced_runtime", "procedure_heavy", "session_pressure", "integration_mix"],
    )
    args = parser.parse_args(argv)

    with create_local_runtime_client(base_url=args.base_url, timeout=30.0) as client:
        report = run_soak_benchmark(
            client,
            namespace_suffix=args.namespace_suffix,
            memory_count=args.memory_count,
            iterations=args.iterations,
            scenario=args.scenario,
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
