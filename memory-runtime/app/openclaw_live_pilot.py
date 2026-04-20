from __future__ import annotations

import argparse
import json
import subprocess
import time
from json import JSONDecoder
from pathlib import Path
from typing import Any

from app.http_client import create_local_runtime_client
from app.pilot_artifacts import default_artifact_run_name, export_trace_bundle


DEFAULT_TURN_TIMEOUT_SECONDS = 180
DEFAULT_CONTINUITY_TIMEOUT_SECONDS = 240
DEFAULT_THINKING_LEVEL = "off"
DEFAULT_CONTINUITY_THINKING_LEVEL = "off"


def load_openclaw_mem0_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else (Path.home() / ".openclaw" / "openclaw.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["plugins"]["entries"]["openclaw-mem0"]["config"]


def extract_json_object(raw_output: str) -> dict[str, Any]:
    decoder = JSONDecoder()
    for index, char in enumerate(raw_output):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw_output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("No JSON object found in OpenClaw output")


def _flatten_brief(brief: dict[str, list[str]]) -> str:
    return "\n".join(item for items in brief.values() for item in items)


def _safe_session_id(*parts: str) -> str:
    raw = "-".join(parts)
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in raw)


def _run_openclaw_turn(
    *,
    session_id: str,
    message: str,
    timeout_seconds: int,
    thinking_level: str,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "openclaw",
                "agent",
                "--local",
                "--session-id",
                session_id,
                "--message",
                message,
                "--json",
                "--thinking",
                thinking_level,
                "--timeout",
                str(timeout_seconds),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds + 20,
        )
    except subprocess.TimeoutExpired as exc:
        combined = "\n".join(
            part
            for part in (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout,
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr,
            )
            if part
        ).strip()
        raise RuntimeError(
            "OpenClaw agent turn exceeded process timeout "
            f"(session_id={session_id}, cli_timeout={timeout_seconds}s): {combined[-1000:]}"
        ) from exc
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "OpenClaw agent turn failed "
            f"(exit={completed.returncode}, session_id={session_id}): {combined[-1000:]}"
        )
    payload = extract_json_object(combined)
    return {
        "payload": payload,
        "raw_output": combined,
        "capture_confirmed": "auto-captured" in combined,
        "recall_timeout_observed": "recall timed out" in combined,
        "registered_count": combined.count("openclaw-mem0: registered"),
        "timeout_seconds": timeout_seconds,
        "thinking_level": thinking_level,
    }


def _wait_for_jobs(
    client,
    *,
    poll_seconds: float,
    max_wait_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + max_wait_seconds
    stats_payload: dict[str, Any] = {}
    while True:
        response = client.get("/v1/observability/stats")
        response.raise_for_status()
        stats_payload = response.json()
        pending = int(stats_payload["jobs"]["by_status"].get("pending", 0))
        running = int(stats_payload["jobs"]["by_status"].get("running", 0))
        if (pending == 0 and running == 0) or time.time() >= deadline:
            return stats_payload
        time.sleep(poll_seconds)


def _wait_for_runtime_ready(
    client,
    *,
    poll_seconds: float,
    max_wait_seconds: float,
) -> None:
    deadline = time.time() + max_wait_seconds
    while True:
        try:
            response = client.get("/healthz")
            response.raise_for_status()
            return
        except Exception:
            if time.time() >= deadline:
                raise
            time.sleep(poll_seconds)


def _bootstrap_scope(client, *, user_id: str, agent_name: str) -> dict[str, str]:
    response = client.post(
        "/v1/adapters/openclaw/bootstrap",
        json={
            "namespace_name": user_id,
            "agent_name": agent_name,
            "external_ref": user_id,
        },
    )
    response.raise_for_status()
    return response.json()


def _run_recall(
    client,
    *,
    namespace_id: str,
    agent_id: str,
    session_id: str,
    query: str,
) -> dict[str, Any]:
    response = client.post(
        "/v1/adapters/openclaw/recall",
        json={
            "namespace_id": namespace_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "query": query,
            "context_budget_tokens": 1000,
        },
    )
    response.raise_for_status()
    return response.json()


def _list_memories(
    client,
    *,
    namespace_id: str,
    agent_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    response = client.get(
        "/v1/adapters/openclaw/memories",
        params={"namespace_id": namespace_id, "agent_id": agent_id, "limit": limit},
    )
    response.raise_for_status()
    return response.json()


def _evaluate_presence(text: str, required: tuple[str, ...]) -> list[str]:
    return [snippet for snippet in required if snippet not in text]


def _scenario_result(
    *,
    scenario_id: str,
    turn_result: dict[str, Any],
    recall_payload: dict[str, Any],
    memory_list_payload: dict[str, Any],
    stats_payload: dict[str, Any],
    required_snippets: tuple[str, ...],
    forbidden_snippets: tuple[str, ...] = (),
) -> dict[str, Any]:
    flattened = _flatten_brief(recall_payload["brief"])
    list_text = "\n".join(item["memory"] for item in memory_list_payload["results"])
    combined = "\n".join(filter(None, (flattened, list_text)))
    missing = _evaluate_presence(combined, required_snippets)
    leaked = [snippet for snippet in forbidden_snippets if snippet in combined]
    return {
        "id": scenario_id,
        "passed": (not missing) and (not leaked),
        "missing": missing,
        "leaked": leaked,
        "capture_confirmed": turn_result["capture_confirmed"],
        "recall_timeout_observed": turn_result["recall_timeout_observed"],
        "recall_trace": recall_payload["trace"],
        "memory_count": len(memory_list_payload["results"]),
        "jobs_by_status": stats_payload["jobs"]["by_status"],
        "agent_output": turn_result["payload"]["payloads"][0]["text"],
    }


def run_live_openclaw_pilot(
    *,
    runtime_base_url: str,
    user_id: str,
    agent_name: str = "primary",
    artifact_run_name: str | None = None,
    poll_seconds: float = 0.5,
    max_wait_seconds: float = 15.0,
    timeout_seconds: int = DEFAULT_TURN_TIMEOUT_SECONDS,
    continuity_timeout_seconds: int = DEFAULT_CONTINUITY_TIMEOUT_SECONDS,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    continuity_thinking_level: str = DEFAULT_CONTINUITY_THINKING_LEVEL,
) -> dict[str, Any]:
    client = create_local_runtime_client(base_url=runtime_base_url, timeout=30.0)
    _wait_for_runtime_ready(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    scope = _bootstrap_scope(client, user_id=user_id, agent_name=agent_name)

    suffix = default_artifact_run_name(user_id.replace(":", "-"))
    shared_artifacts: dict[str, Any] = {
        "scope": scope,
        "initial_observability": client.get("/v1/observability/stats").json(),
        "execution_profile": {
            "timeout_seconds": timeout_seconds,
            "continuity_timeout_seconds": continuity_timeout_seconds,
            "thinking_level": thinking_level,
            "continuity_thinking_level": continuity_thinking_level,
        },
    }

    scenario_results: list[dict[str, Any]] = []
    artifact_payloads: dict[str, Any] = dict(shared_artifacts)

    # 1. Durable architecture decision
    architecture_session = _safe_session_id(suffix, "architecture")
    architecture_turn = _run_openclaw_turn(
        session_id=architecture_session,
        message=(
            "For future reference: our OpenClaw memory pilot uses a standalone memory-runtime "
            "with Postgres, Redis, and a dedicated worker. Please acknowledge briefly."
        ),
        timeout_seconds=timeout_seconds,
        thinking_level=thinking_level,
    )
    architecture_stats = _wait_for_jobs(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    architecture_recall = _run_recall(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
        session_id=_safe_session_id(suffix, "architecture-recall"),
        query="What architecture decisions already exist for the OpenClaw memory pilot?",
    )
    architecture_memories = _list_memories(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
    )
    architecture_result = _scenario_result(
        scenario_id="durable-architecture-decision",
        turn_result=architecture_turn,
        recall_payload=architecture_recall,
        memory_list_payload=architecture_memories,
        stats_payload=architecture_stats,
        # OpenClaw adapter previews may ellipsize the tail of long durable memories,
        # so we intentionally check a stable prefix for the worker fragment here.
        required_snippets=("standalone memory-runtime", "Postgres", "Redis", "dedicated w"),
    )
    scenario_results.append(architecture_result)
    artifact_payloads["01-durable-architecture-turn"] = architecture_turn
    artifact_payloads["01-durable-architecture-recall"] = architecture_recall
    artifact_payloads["01-durable-architecture-memories"] = architecture_memories

    # 2. Standing procedure recall
    procedure_session = _safe_session_id(suffix, "procedure")
    procedure_turn = _run_openclaw_turn(
        session_id=procedure_session,
        message=(
            "For future reference: always start architecture updates with a concise summary "
            "before implementation details."
        ),
        timeout_seconds=timeout_seconds,
        thinking_level=thinking_level,
    )
    procedure_stats = _wait_for_jobs(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    procedure_recall = _run_recall(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
        session_id=_safe_session_id(suffix, "procedure-recall"),
        query="How should architecture updates be presented?",
    )
    procedure_memories = _list_memories(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
    )
    procedure_result = _scenario_result(
        scenario_id="standing-procedure-recall",
        turn_result=procedure_turn,
        recall_payload=procedure_recall,
        memory_list_payload=procedure_memories,
        stats_payload=procedure_stats,
        required_snippets=("concise summary", "implementation details"),
    )
    scenario_results.append(procedure_result)
    artifact_payloads["02-standing-procedure-turn"] = procedure_turn
    artifact_payloads["02-standing-procedure-recall"] = procedure_recall
    artifact_payloads["02-standing-procedure-memories"] = procedure_memories

    # 3. Active session carryover
    carry_session = _safe_session_id(suffix, "carryover")
    carry_turn = _run_openclaw_turn(
        session_id=carry_session,
        message="Right now I am preparing the OpenClaw live pilot acceptance checklist.",
        timeout_seconds=timeout_seconds,
        thinking_level=thinking_level,
    )
    carry_stats = _wait_for_jobs(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    carry_recall = _run_recall(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
        session_id=carry_session,
        query="What am I doing in this session right now?",
    )
    carry_memories = _list_memories(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
    )
    carry_result = _scenario_result(
        scenario_id="active-session-carryover",
        turn_result=carry_turn,
        recall_payload=carry_recall,
        memory_list_payload=carry_memories,
        stats_payload=carry_stats,
        required_snippets=("live pilot acceptance checklist",),
    )
    scenario_results.append(carry_result)
    artifact_payloads["03-session-carryover-turn"] = carry_turn
    artifact_payloads["03-session-carryover-recall"] = carry_recall
    artifact_payloads["03-session-carryover-memories"] = carry_memories

    # 4. Cross-session continuity
    continuity_turn = _run_openclaw_turn(
        session_id=_safe_session_id(suffix, "continuity-source"),
        message="For future reference: we paused after validating live OpenClaw capture on pilot-user-2.",
        timeout_seconds=continuity_timeout_seconds,
        thinking_level=continuity_thinking_level,
    )
    continuity_stats = _wait_for_jobs(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    continuity_recall = _run_recall(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
        session_id=_safe_session_id(suffix, "continuity-target"),
        query="Where did we stop on the OpenClaw memory pilot?",
    )
    continuity_memories = _list_memories(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
    )
    continuity_result = _scenario_result(
        scenario_id="cross-session-continuity",
        turn_result=continuity_turn,
        recall_payload=continuity_recall,
        memory_list_payload=continuity_memories,
        stats_payload=continuity_stats,
        required_snippets=("validating live OpenClaw capture", "pilot-user-2"),
    )
    scenario_results.append(continuity_result)
    artifact_payloads["04-cross-session-turn"] = continuity_turn
    artifact_payloads["04-cross-session-recall"] = continuity_recall
    artifact_payloads["04-cross-session-memories"] = continuity_memories

    # 5. Noise resistance
    noise_turn = _run_openclaw_turn(
        session_id=_safe_session_id(suffix, "noise-source"),
        message="Temporary scratch note: maybe rename env vars next quarter.",
        timeout_seconds=timeout_seconds,
        thinking_level=thinking_level,
    )
    noise_stats = _wait_for_jobs(client, poll_seconds=poll_seconds, max_wait_seconds=max_wait_seconds)
    noise_recall = _run_recall(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
        session_id=_safe_session_id(suffix, "noise-target"),
        query="What durable architecture context exists for the OpenClaw memory pilot?",
    )
    noise_memories = _list_memories(
        client,
        namespace_id=scope["namespace_id"],
        agent_id=scope["agent_id"],
    )
    noise_result = _scenario_result(
        scenario_id="noise-resistance",
        turn_result=noise_turn,
        recall_payload=noise_recall,
        memory_list_payload=noise_memories,
        stats_payload=noise_stats,
        required_snippets=("standalone memory-runtime",),
        forbidden_snippets=("rename env vars next quarter",),
    )
    scenario_results.append(noise_result)
    artifact_payloads["05-noise-resistance-turn"] = noise_turn
    artifact_payloads["05-noise-resistance-recall"] = noise_recall
    artifact_payloads["05-noise-resistance-memories"] = noise_memories

    artifact_dir = export_trace_bundle(
        category="openclaw-live-pilot",
        run_name=artifact_run_name or default_artifact_run_name("openclaw-live-pilot"),
        payloads=artifact_payloads,
    )
    passed = sum(1 for result in scenario_results if result["passed"])
    failed = len(scenario_results) - passed
    return {
        "user_id": user_id,
        "agent_name": agent_name,
        "namespace_id": scope["namespace_id"],
        "agent_id": scope["agent_id"],
        "execution_profile": shared_artifacts["execution_profile"],
        "total": len(scenario_results),
        "passed": passed,
        "failed": failed,
        "artifact_dir": str(artifact_dir),
        "results": scenario_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run live OpenClaw pilot scenarios against the memory runtime.")
    parser.add_argument("--runtime-base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--config-path", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--user-id")
    parser.add_argument("--agent-name")
    parser.add_argument("--artifact-run-name")
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--max-wait-seconds", type=float, default=15.0)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TURN_TIMEOUT_SECONDS)
    parser.add_argument("--continuity-timeout-seconds", type=int, default=DEFAULT_CONTINUITY_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", default=DEFAULT_THINKING_LEVEL)
    parser.add_argument("--continuity-thinking", default=DEFAULT_CONTINUITY_THINKING_LEVEL)
    args = parser.parse_args(argv)

    plugin_config = load_openclaw_mem0_config(args.config_path)
    user_id = args.user_id or plugin_config["userId"]
    agent_name = args.agent_name or plugin_config.get("runtime", {}).get("agentName", "primary")
    report = run_live_openclaw_pilot(
        runtime_base_url=args.runtime_base_url,
        user_id=user_id,
        agent_name=agent_name,
        artifact_run_name=args.artifact_run_name,
        poll_seconds=args.poll_seconds,
        max_wait_seconds=args.max_wait_seconds,
        timeout_seconds=args.timeout_seconds,
        continuity_timeout_seconds=args.continuity_timeout_seconds,
        thinking_level=args.thinking,
        continuity_thinking_level=args.continuity_thinking,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
