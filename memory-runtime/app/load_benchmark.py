from __future__ import annotations

import argparse
import asyncio
import json
import time
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from statistics import mean
from time import perf_counter

import httpx
from fastapi.testclient import TestClient

from app.http_client import create_local_runtime_client
from app.main import create_app
from app.performance_benchmark import _summary, run_performance_benchmark


def _flatten_brief(brief: dict[str, list[str]]) -> str:
    return "\n".join(item for items in brief.values() for item in items)


async def _issue_recall(
    client: httpx.AsyncClient,
    *,
    namespace_id: str,
    agent_id: str,
    session_id: str,
    query: str,
    context_budget_tokens: int,
) -> dict[str, object]:
    started_at = perf_counter()
    response = await client.post(
        "/v1/adapters/openclaw/recall",
        json={
            "namespace_id": namespace_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "query": query,
            "context_budget_tokens": context_budget_tokens,
        },
    )
    latency_ms = max(0, int((perf_counter() - started_at) * 1000))
    if response.status_code != 200:
        return {
            "ok": False,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "selected_count": 0,
            "brief_chars": 0,
        }

    payload = response.json()
    return {
        "ok": True,
        "status_code": 200,
        "latency_ms": latency_ms,
        "selected_count": int(payload["trace"]["selected_count"]),
        "brief_chars": len(_flatten_brief(payload["brief"])),
    }


async def _run_concurrent_recalls(
    *,
    client_factory,
    namespace_id: str,
    agent_id: str,
    concurrency: int,
    rounds: int,
    query: str,
    context_budget_tokens: int,
) -> dict[str, object]:
    async with client_factory() as client:
        all_results: list[dict[str, object]] = []
        started_at = time.perf_counter()
        for round_index in range(rounds):
            tasks = [
                _issue_recall(
                    client,
                    namespace_id=namespace_id,
                    agent_id=agent_id,
                    session_id=f"load:round:{round_index}:worker:{worker_index}",
                    query=query,
                    context_budget_tokens=context_budget_tokens,
                )
                for worker_index in range(concurrency)
            ]
            all_results.extend(await asyncio.gather(*tasks))
        total_elapsed_seconds = max(time.perf_counter() - started_at, 0.0001)

    latencies = [int(item["latency_ms"]) for item in all_results]
    selected_counts = [int(item["selected_count"]) for item in all_results if item["ok"]]
    brief_chars = [int(item["brief_chars"]) for item in all_results if item["ok"]]
    failures = sum(1 for item in all_results if not item["ok"])
    total_requests = len(all_results)

    return {
        "total_requests": total_requests,
        "failures": failures,
        "failure_rate": round((failures / total_requests) if total_requests else 0.0, 4),
        "throughput_rps": round((total_requests / total_elapsed_seconds) if total_elapsed_seconds else 0.0, 4),
        "latency_ms": _summary(latencies),
        "selected_count": _summary(selected_counts),
        "brief_chars": _summary(brief_chars),
        "selected_count_mean": round(mean(selected_counts), 4) if selected_counts else 0.0,
        "brief_chars_mean": round(mean(brief_chars), 4) if brief_chars else 0.0,
    }


def _in_process_clients() -> tuple[AbstractContextManager, callable]:
    app = create_app()

    def sync_factory() -> TestClient:
        return TestClient(app)

    def async_factory() -> AbstractAsyncContextManager:
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://benchmark")

    return sync_factory, async_factory


def _remote_clients(base_url: str, timeout: float) -> tuple[AbstractContextManager, callable]:
    def sync_factory():
        return create_local_runtime_client(base_url=base_url, timeout=timeout)

    def async_factory() -> AbstractAsyncContextManager:
        return httpx.AsyncClient(base_url=base_url, timeout=timeout, trust_env=False)

    return sync_factory, async_factory


def run_load_benchmark(
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 500,
    concurrency: int = 8,
    rounds: int = 5,
    scenario: str = "balanced_runtime",
    context_budget_tokens: int = 900,
    base_url: str | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    sync_factory, async_factory = (
        _remote_clients(base_url, timeout) if base_url else _in_process_clients()
    )

    with sync_factory() as client:
        warmup = run_performance_benchmark(
            client,
            namespace_suffix=namespace_suffix,
            memory_count=memory_count,
            query_count=1,
            scenario=scenario,
        )

    namespace_id = warmup["namespace_id"]
    agent_id = warmup["agent_id"]
    query = "What runtime architecture and rollout guidance matter right now?"
    load_result = asyncio.run(
        _run_concurrent_recalls(
            client_factory=async_factory,
            namespace_id=namespace_id,
            agent_id=agent_id,
            concurrency=concurrency,
            rounds=rounds,
            query=query,
            context_budget_tokens=context_budget_tokens,
        )
    )

    return {
        "mode": "remote" if base_url else "in_process",
        "base_url": base_url,
        "scenario": scenario,
        "memory_count": memory_count,
        "concurrency": concurrency,
        "rounds": rounds,
        "query": query,
        **load_result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a concurrent recall load benchmark against memory-runtime.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--memory-count", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--scenario",
        default="balanced_runtime",
        choices=["balanced_runtime", "procedure_heavy", "session_pressure", "integration_mix"],
    )
    parser.add_argument("--context-budget-tokens", type=int, default=900)
    args = parser.parse_args(argv)

    report = run_load_benchmark(
        namespace_suffix=args.namespace_suffix,
        memory_count=args.memory_count,
        concurrency=args.concurrency,
        rounds=args.rounds,
        scenario=args.scenario,
        context_budget_tokens=args.context_budget_tokens,
        base_url=args.base_url,
        timeout=args.timeout,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
