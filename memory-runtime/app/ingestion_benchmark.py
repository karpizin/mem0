from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from statistics import mean
from time import perf_counter

from fastapi.testclient import TestClient

from app.http_client import create_local_runtime_client
from app.main import create_app
from app.performance_benchmark import _scenario_catalog, _summary
from app.workers.runner import WorkerRunner


def _snapshot_jobs(client) -> dict[str, object]:
    response = client.get("/v1/observability/stats")
    response.raise_for_status()
    payload = response.json()
    return {
        "metrics": payload["metrics"],
        "jobs": payload["jobs"],
    }


def _in_process_client() -> tuple[AbstractContextManager, Callable[[], int] | None]:
    app = create_app()
    return TestClient(app), WorkerRunner.run_pending_jobs


def _remote_client(base_url: str, timeout: float) -> tuple[AbstractContextManager, Callable[[], int] | None]:
    return create_local_runtime_client(base_url=base_url, timeout=timeout), None


def _job_status_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(before) | set(after))
    return {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in keys}


def _job_type_delta(
    before: dict[str, dict[str, int]],
    after: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    keys = sorted(set(before) | set(after))
    delta: dict[str, dict[str, int]] = {}
    for key in keys:
        delta[key] = _job_status_delta(before.get(key, {}), after.get(key, {}))
    return delta


def run_ingestion_benchmark(
    *,
    namespace_suffix: str | None = None,
    memory_count: int = 1000,
    scenario: str = "balanced_runtime",
    sample_every: int = 100,
    poll_seconds: float = 0.1,
    max_wait_seconds: float = 60.0,
    base_url: str | None = None,
    timeout: float = 30.0,
) -> dict[str, object]:
    client_ctx, job_drainer = (
        _remote_client(base_url, timeout) if base_url else _in_process_client()
    )

    with client_ctx as client:
        scenario_payload = _scenario_catalog(memory_count=memory_count, query_count=1)[scenario]
        seeds = scenario_payload["seeds"]

        before = _snapshot_jobs(client)
        bootstrap = client.post(
            "/v1/adapters/openclaw/bootstrap",
            json={
                "namespace_name": f"ingestion-benchmark:{namespace_suffix or scenario}:{memory_count}",
                "agent_name": "planner",
                "external_ref": f"ingestion-benchmark:{namespace_suffix or scenario}:{memory_count}",
            },
        )
        bootstrap.raise_for_status()
        scope = bootstrap.json()
        namespace_id = scope["namespace_id"]
        agent_id = scope["agent_id"]

        ingest_latencies: list[int] = []
        sampled_pending: list[int] = []
        sampled_completed: list[int] = []
        sampled_oldest_age: list[float] = []
        peak_pending_jobs = 0
        started_at = perf_counter()

        for index, seed in enumerate(seeds):
            event_started_at = perf_counter()
            response = client.post(
                "/v1/adapters/openclaw/events",
                json={
                    "namespace_id": namespace_id,
                    "agent_id": agent_id,
                    "session_id": f"ingestion-benchmark:{namespace_suffix or scenario}:{index}",
                    "event_type": seed["event_type"],
                    "space_hint": seed["space_hint"],
                    "event_origin": seed.get("event_origin", "agent_output"),
                    "messages": [
                        {
                            "role": seed.get("role", "assistant"),
                            "content": seed["content"],
                        }
                    ],
                },
            )
            response.raise_for_status()
            ingest_latencies.append(max(0, int((perf_counter() - event_started_at) * 1000)))

            if (index + 1) % max(sample_every, 1) == 0 or index == len(seeds) - 1:
                stats = _snapshot_jobs(client)
                pending = int(stats["jobs"]["by_status"].get("pending", 0))
                peak_pending_jobs = max(peak_pending_jobs, pending)
                sampled_pending.append(pending)
                sampled_completed.append(int(stats["jobs"]["by_status"].get("completed", 0)))
                sampled_oldest_age.append(float(stats["jobs"].get("oldest_pending_age_seconds") or 0.0))

        ingest_elapsed_seconds = max(perf_counter() - started_at, 0.0001)
        after_ingest = _snapshot_jobs(client)
        pending_after_ingest = int(after_ingest["jobs"]["by_status"].get("pending", 0))
        peak_pending_jobs = max(peak_pending_jobs, pending_after_ingest)

        drain_started_at = perf_counter()
        drained = False
        while True:
            if job_drainer is not None:
                job_drainer()
            stats = _snapshot_jobs(client)
            pending = int(stats["jobs"]["by_status"].get("pending", 0))
            peak_pending_jobs = max(peak_pending_jobs, pending)
            if pending == 0:
                drained = True
                final = stats
                break
            if perf_counter() - drain_started_at >= max_wait_seconds:
                final = stats
                break
            time.sleep(poll_seconds)

    ingest_status_delta = _job_status_delta(before["jobs"]["by_status"], after_ingest["jobs"]["by_status"])
    final_status_delta = _job_status_delta(before["jobs"]["by_status"], final["jobs"]["by_status"])
    ingest_type_delta = _job_type_delta(before["jobs"]["by_type"], after_ingest["jobs"]["by_type"])
    final_type_delta = _job_type_delta(before["jobs"]["by_type"], final["jobs"]["by_type"])
    drain_elapsed_seconds = max(perf_counter() - drain_started_at, 0.0)

    return {
        "mode": "remote" if base_url else "in_process",
        "base_url": base_url,
        "scenario": scenario,
        "memory_count": memory_count,
        "total_events": len(seeds),
        "namespace_id": namespace_id,
        "agent_id": agent_id,
        "ingest_throughput_eps": round((len(seeds) / ingest_elapsed_seconds) if ingest_elapsed_seconds else 0.0, 4),
        "ingest_latency_ms": _summary(ingest_latencies),
        "ingest_latency_mean_ms": round(mean(ingest_latencies), 4) if ingest_latencies else 0.0,
        "peak_pending_jobs": peak_pending_jobs,
        "pending_after_ingest": pending_after_ingest,
        "drain_seconds": round(drain_elapsed_seconds, 4),
        "drained": drained,
        "sampled_pending_jobs": sampled_pending,
        "sampled_completed_jobs": sampled_completed,
        "sampled_oldest_pending_age_seconds": [round(value, 4) for value in sampled_oldest_age],
        "job_status_delta_after_ingest": ingest_status_delta,
        "job_status_delta_after_drain": final_status_delta,
        "job_type_delta_after_ingest": ingest_type_delta,
        "job_type_delta_after_drain": final_type_delta,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an ingestion/backlog benchmark against memory-runtime.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--namespace-suffix", default=None)
    parser.add_argument("--memory-count", type=int, default=1000)
    parser.add_argument("--sample-every", type=int, default=100)
    parser.add_argument("--poll-seconds", type=float, default=0.1)
    parser.add_argument("--max-wait-seconds", type=float, default=60.0)
    parser.add_argument(
        "--scenario",
        default="balanced_runtime",
        choices=["balanced_runtime", "procedure_heavy", "session_pressure", "integration_mix"],
    )
    args = parser.parse_args(argv)

    report = run_ingestion_benchmark(
        namespace_suffix=args.namespace_suffix,
        memory_count=args.memory_count,
        scenario=args.scenario,
        sample_every=args.sample_every,
        poll_seconds=args.poll_seconds,
        max_wait_seconds=args.max_wait_seconds,
        base_url=args.base_url,
        timeout=args.timeout,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
