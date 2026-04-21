from __future__ import annotations

import argparse
import json
from typing import Any

from app.load_benchmark import run_load_benchmark


def _trend_summary(reports: list[dict[str, Any]]) -> list[dict[str, float | int]]:
    summary: list[dict[str, float | int]] = []
    for report in reports:
        summary.append(
            {
                "memory_count": int(report["memory_count"]),
                "avg_latency_ms": float(report["latency_ms"]["avg"]),
                "p95_latency_ms": float(report["latency_ms"]["p95"]),
                "throughput_rps": float(report["throughput_rps"]),
                "failure_rate": float(report["failure_rate"]),
                "candidate_fetch_ms": float(report["phase_avg_latency_ms"].get("candidate_fetch", 0.0)),
                "feedback_lookup_ms": float(report["phase_avg_latency_ms"].get("feedback_lookup", 0.0)),
                "audit_record_ms": float(report["phase_avg_latency_ms"].get("audit_record", 0.0)),
            }
        )
    return summary


def run_scale_benchmark(
    *,
    memory_counts: list[int],
    namespace_prefix: str | None = None,
    concurrency: int = 8,
    rounds: int = 5,
    scenario: str = "balanced_runtime",
    context_budget_tokens: int = 900,
    base_url: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for index, memory_count in enumerate(memory_counts):
        suffix = f"{namespace_prefix or 'scale'}:{scenario}:{memory_count}:{index}"
        report = run_load_benchmark(
            namespace_suffix=suffix,
            memory_count=memory_count,
            concurrency=concurrency,
            rounds=rounds,
            scenario=scenario,
            context_budget_tokens=context_budget_tokens,
            base_url=base_url,
            timeout=timeout,
        )
        reports.append(report)

    return {
        "mode": "remote" if base_url else "in_process",
        "base_url": base_url,
        "scenario": scenario,
        "memory_counts": memory_counts,
        "concurrency": concurrency,
        "rounds": rounds,
        "reports": reports,
        "trend_summary": _trend_summary(reports),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a scale benchmark over multiple memory counts.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--namespace-prefix", default=None)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--scenario",
        default="balanced_runtime",
        choices=["balanced_runtime", "procedure_heavy", "session_pressure", "integration_mix"],
    )
    parser.add_argument("--context-budget-tokens", type=int, default=900)
    parser.add_argument("--memory-counts", type=int, nargs="+", required=True)
    args = parser.parse_args(argv)

    report = run_scale_benchmark(
        memory_counts=args.memory_counts,
        namespace_prefix=args.namespace_prefix,
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
