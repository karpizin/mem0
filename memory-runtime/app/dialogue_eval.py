from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import Engine, select

from app.database import get_session_factory
from app.models.audit_log import AuditLog
from app.models.memory_unit import MemoryUnit


def load_scenarios(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _flatten_brief(brief: dict[str, list[str]]) -> str:
    return "\n".join(item for items in brief.values() for item in items)


def _wait_for_jobs(
    client,
    *,
    job_drainer: Callable[[], int] | None,
    poll_seconds: float,
    max_wait_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + max_wait_seconds
    stats_payload: dict[str, Any] = {}
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


def _create_namespace(client, *, name: str, mode: str) -> str:
    response = client.post(
        "/v1/namespaces",
        json={
            "name": name,
            "mode": mode,
            "source_systems": ["openclaw"],
        },
    )
    response.raise_for_status()
    return response.json()["id"]


def _create_agent(client, *, namespace_id: str, name: str) -> str:
    response = client.post(
        f"/v1/namespaces/{namespace_id}/agents",
        json={"name": name, "source_system": "openclaw"},
    )
    response.raise_for_status()
    return response.json()["id"]


def _create_event(
    client,
    *,
    namespace_id: str,
    agent_id: str,
    turn: dict[str, Any],
    default_session_id: str,
) -> dict[str, Any]:
    messages = turn.get("messages")
    if messages is None:
        messages = [{"role": turn["role"], "content": turn["content"]}]
    response = client.post(
        "/v1/events",
        json={
            "namespace_id": namespace_id,
            "agent_id": agent_id,
            "session_id": turn.get("session_id", default_session_id),
            "source_system": "openclaw",
            "event_type": turn.get("event_type", "conversation_turn"),
            "event_origin": turn.get("event_origin"),
            "space_hint": turn.get("space_hint"),
            "messages": messages,
            "metadata": turn.get("metadata", {}),
        },
    )
    response.raise_for_status()
    return response.json()


def _record_feedback(
    client,
    *,
    namespace_id: str,
    agent_id: str,
    episode_ids: list[str],
    helpful: bool,
    query: str,
    notes: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/v1/recall/feedback",
        json={
            "namespace_id": namespace_id,
            "agent_id": agent_id,
            "episode_ids": episode_ids,
            "helpful": helpful,
            "query": query,
            "notes": notes,
        },
    )
    response.raise_for_status()
    return response.json()


def _list_memory_units(
    engine: Engine,
    *,
    namespace_id: str,
    scope: str | None = None,
) -> list[MemoryUnit]:
    del engine
    with get_session_factory()() as session:
        stmt = (
            select(MemoryUnit)
            .where(MemoryUnit.namespace_id == namespace_id)
            .where(MemoryUnit.status == "active")
            .order_by(MemoryUnit.created_at.asc())
        )
        if scope is not None:
            stmt = stmt.where(MemoryUnit.scope == scope)
        return list(session.execute(stmt).scalars().all())


def _list_audit_rows(engine: Engine, *, namespace_id: str) -> list[AuditLog]:
    del engine
    with get_session_factory()() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.namespace_id == namespace_id)
            .order_by(AuditLog.created_at.asc())
        )
        return list(session.execute(stmt).scalars().all())


def _recall(
    client,
    *,
    namespace_id: str,
    agent_id: str,
    session_id: str,
    query: str,
    context_budget_tokens: int,
) -> dict[str, Any]:
    response = client.post(
        "/v1/recall",
        json={
            "namespace_id": namespace_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "query": query,
            "context_budget_tokens": context_budget_tokens,
        },
    )
    response.raise_for_status()
    return response.json()


def _evaluate_text_expectations(
    *,
    haystack: str,
    must_contain: list[str],
    must_not_contain: list[str],
) -> dict[str, Any]:
    missing = [item for item in must_contain if item not in haystack]
    unexpected = [item for item in must_not_contain if item in haystack]
    return {
        "passed": not missing and not unexpected,
        "missing": missing,
        "unexpected": unexpected,
    }


def _evaluate_dialogue_scenario(
    client,
    *,
    engine: Engine,
    scenario: dict[str, Any],
    job_drainer: Callable[[], int] | None,
    poll_seconds: float,
    max_wait_seconds: float,
) -> dict[str, Any]:
    suffix = uuid4().hex[:8]
    namespace_name = f"dialogue-eval:{scenario['id']}:{suffix}"
    namespace_id = _create_namespace(
        client,
        name=namespace_name,
        mode=scenario.get("namespace_mode", "isolated"),
    )
    agent_id = _create_agent(client, namespace_id=namespace_id, name=scenario.get("agent_name", "planner"))
    default_session_id = scenario.get("session_id", f"{scenario['id']}:{suffix}")

    ingested_events: list[dict[str, Any]] = []
    operation_results: list[dict[str, Any]] = []
    stats_payload: dict[str, Any] = {}
    operations = scenario.get("script")
    if operations is None:
        operations = [{"type": "ingest", "turn": turn} for turn in scenario["dialogue"]]

    for operation in operations:
        op_type = operation["type"]
        if op_type == "ingest":
            event = _create_event(
                client,
                namespace_id=namespace_id,
                agent_id=agent_id,
                turn=operation["turn"],
                default_session_id=default_session_id,
            )
            ingested_events.append(event)
            operation_results.append({"type": "ingest", "event": event})
            stats_payload = _wait_for_jobs(
                client,
                job_drainer=job_drainer,
                poll_seconds=poll_seconds,
                max_wait_seconds=max_wait_seconds,
            )
            continue

        if op_type == "feedback":
            target_indices = operation.get("target_turn_indexes", [])
            episode_ids = [ingested_events[index]["episode_id"] for index in target_indices]
            feedback_result = _record_feedback(
                client,
                namespace_id=namespace_id,
                agent_id=agent_id,
                episode_ids=episode_ids,
                helpful=operation["helpful"],
                query=operation["query"],
                notes=operation.get("notes"),
            )
            operation_results.append(
                {
                    "type": "feedback",
                    "helpful": operation["helpful"],
                    "episode_ids": episode_ids,
                    "feedback": feedback_result,
                }
            )
            continue

        raise ValueError(f"Unsupported dialogue eval script step type '{op_type}'")

    long_term_units = _list_memory_units(engine, namespace_id=namespace_id, scope="long-term")
    short_term_units = _list_memory_units(engine, namespace_id=namespace_id, scope="short-term")
    audit_rows = _list_audit_rows(engine, namespace_id=namespace_id)
    long_term_text = "\n".join(unit.content for unit in long_term_units)
    short_term_text = "\n".join(unit.content for unit in short_term_units)
    audit_actions = [row.action for row in audit_rows]
    audit_reasons = [
        (row.details_json or {}).get("reason")
        for row in audit_rows
        if (row.details_json or {}).get("reason")
    ]
    audit_signal_values = [
        str(value)
        for row in audit_rows
        for value in ((row.details_json or {}).get("signals") or {}).values()
        if value is not None
    ]

    expectations = scenario.get("expectations", {})
    storage = expectations.get("long_term", {})
    short_term = expectations.get("short_term", {})
    audit = expectations.get("audit", {})

    long_term_result = _evaluate_text_expectations(
        haystack=long_term_text,
        must_contain=storage.get("must_contain", []),
        must_not_contain=storage.get("must_not_contain", []),
    )
    short_term_result = _evaluate_text_expectations(
        haystack=short_term_text,
        must_contain=short_term.get("must_contain", []),
        must_not_contain=short_term.get("must_not_contain", []),
    )
    missing_actions = [item for item in audit.get("must_include_actions", []) if item not in audit_actions]
    missing_reasons = [item for item in audit.get("must_include_reasons", []) if item not in audit_reasons]
    missing_signal_values = [
        item for item in audit.get("must_include_signal_values", []) if item not in audit_signal_values
    ]
    forbidden_actions = [item for item in audit.get("must_not_include_actions", []) if item in audit_actions]
    forbidden_reasons = [item for item in audit.get("must_not_include_reasons", []) if item in audit_reasons]
    forbidden_signal_values = [
        item for item in audit.get("must_not_include_signal_values", []) if item in audit_signal_values
    ]
    audit_result = {
        "passed": not missing_actions
        and not missing_reasons
        and not missing_signal_values
        and not forbidden_actions
        and not forbidden_reasons
        and not forbidden_signal_values,
        "missing_actions": missing_actions,
        "missing_reasons": missing_reasons,
        "missing_signal_values": missing_signal_values,
        "forbidden_actions": forbidden_actions,
        "forbidden_reasons": forbidden_reasons,
        "forbidden_signal_values": forbidden_signal_values,
    }

    recall_results: list[dict[str, Any]] = []
    recall_passed = True
    for check in expectations.get("recall_checks", []):
        recall_payload = _recall(
            client,
            namespace_id=namespace_id,
            agent_id=agent_id,
            session_id=check.get("session_id", default_session_id),
            query=check["query"],
            context_budget_tokens=check.get("context_budget_tokens", 1000),
        )
        flattened = _flatten_brief(recall_payload["brief"])
        text_result = _evaluate_text_expectations(
            haystack=flattened,
            must_contain=check.get("must_contain", []),
            must_not_contain=check.get("must_not_contain", []),
        )
        recall_results.append(
            {
                "query": check["query"],
                "passed": text_result["passed"],
                "missing": text_result["missing"],
                "unexpected": text_result["unexpected"],
                "selected_count": recall_payload["trace"]["selected_count"],
                "trace": recall_payload["trace"],
            }
        )
        if not text_result["passed"]:
            recall_passed = False

    passed = long_term_result["passed"] and short_term_result["passed"] and audit_result["passed"] and recall_passed
    return {
        "id": scenario["id"],
        "description": scenario["description"],
        "annotation_notes": scenario.get("annotation_notes"),
        "passed": passed,
        "namespace_id": namespace_id,
        "agent_id": agent_id,
        "ingested_event_ids": [event["id"] for event in ingested_events],
        "operations": operation_results,
        "jobs_by_status": stats_payload.get("jobs", {}).get("by_status", {}),
        "storage": {
            "long_term": {
                **long_term_result,
                "memory_texts": [unit.content for unit in long_term_units],
            },
            "short_term": {
                **short_term_result,
                "memory_texts": [unit.content for unit in short_term_units],
            },
        },
        "audit": {
            **audit_result,
            "actions": audit_actions,
            "reasons": audit_reasons,
            "signal_values": audit_signal_values,
        },
        "recall_checks": recall_results,
    }


def run_dialogue_memory_eval(
    client,
    *,
    engine: Engine,
    scenarios: list[dict[str, Any]],
    job_drainer: Callable[[], int] | None = None,
    poll_seconds: float = 0.05,
    max_wait_seconds: float = 3.0,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    storage_passed = 0
    audit_passed = 0
    recall_passed = 0

    for scenario in scenarios:
        result = _evaluate_dialogue_scenario(
            client,
            engine=engine,
            scenario=scenario,
            job_drainer=job_drainer,
            poll_seconds=poll_seconds,
            max_wait_seconds=max_wait_seconds,
        )
        results.append(result)
        if result["storage"]["long_term"]["passed"] and result["storage"]["short_term"]["passed"]:
            storage_passed += 1
        if result["audit"]["passed"]:
            audit_passed += 1
        if all(item["passed"] for item in result["recall_checks"]):
            recall_passed += 1

    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round((passed / total) if total else 1.0, 4),
        "metrics": {
            "storage_pass_rate": round((storage_passed / total) if total else 1.0, 4),
            "audit_pass_rate": round((audit_passed / total) if total else 1.0, 4),
            "recall_pass_rate": round((recall_passed / total) if total else 1.0, 4),
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    from app.http_client import create_local_runtime_client
    from app.database import get_engine

    parser = argparse.ArgumentParser(description="Run dialogue-based memory evaluation scenarios.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--scenarios",
        default="tests/fixtures/evals/dialogue_memory_scenarios.json",
    )
    parser.add_argument("--poll-seconds", type=float, default=0.25)
    parser.add_argument("--max-wait-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    with create_local_runtime_client(base_url=args.base_url, timeout=10.0) as client:
        report = run_dialogue_memory_eval(
            client,
            engine=get_engine(),
            scenarios=scenarios,
            job_drainer=None,
            poll_seconds=args.poll_seconds,
            max_wait_seconds=args.max_wait_seconds,
        )

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
