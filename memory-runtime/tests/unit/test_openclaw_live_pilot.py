from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.openclaw_live_pilot import (
    _safe_session_id,
    _run_openclaw_turn,
    extract_json_object,
    load_openclaw_mem0_config,
    run_live_openclaw_pilot,
)


def test_extract_json_object_skips_plugin_logs() -> None:
    raw = """
[plugins] openclaw-mem0: registered (mode: runtime, user: pilot-user)
{
  "payloads": [{"text": "Noted."}],
  "meta": {"stopReason": "stop"}
}
[plugins] openclaw-mem0: auto-captured 1 memories
"""

    parsed = extract_json_object(raw)

    assert parsed["payloads"][0]["text"] == "Noted."
    assert parsed["meta"]["stopReason"] == "stop"


def test_load_openclaw_mem0_config_reads_plugin_section(tmp_path: Path) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "plugins": {
                    "entries": {
                        "openclaw-mem0": {
                            "enabled": True,
                            "config": {
                                "mode": "runtime",
                                "userId": "pilot-user",
                                "runtime": {"baseUrl": "http://127.0.0.1:8080", "agentName": "primary"},
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    payload = load_openclaw_mem0_config(config_path)

    assert payload["userId"] == "pilot-user"
    assert payload["runtime"]["agentName"] == "primary"


def test_safe_session_id_strips_disallowed_symbols() -> None:
    assert _safe_session_id("pilot:user", "carryover") == "pilot-user-carryover"


def test_run_openclaw_turn_raises_if_cli_process_hangs(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        exc = subprocess.TimeoutExpired(
            cmd=["openclaw", "agent"],
            timeout=140,
        )
        exc.stdout = "[plugins] openclaw-mem0: registered"
        exc.stderr = "still waiting"
        raise exc

    monkeypatch.setattr("app.openclaw_live_pilot.subprocess.run", fake_run)

    try:
        _run_openclaw_turn(
            session_id="pilot-user-timeout",
            message="Ping",
            timeout_seconds=120,
            thinking_level="off",
        )
    except RuntimeError as exc:
        assert "exceeded process timeout" in str(exc)
        assert "pilot-user-timeout" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for hung OpenClaw CLI process")


def test_run_openclaw_turn_passes_thinking_level(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Completed:
        returncode = 0
        stdout = '{"payloads":[{"text":"Noted."}],"meta":{"stopReason":"stop"}}'
        stderr = ""

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _Completed()

    monkeypatch.setattr("app.openclaw_live_pilot.subprocess.run", fake_run)

    payload = _run_openclaw_turn(
        session_id="pilot-user-thinking",
        message="Ping",
        timeout_seconds=150,
        thinking_level="minimal",
    )

    assert "--thinking" in captured["args"]
    thinking_index = captured["args"].index("--thinking")
    assert captured["args"][thinking_index + 1] == "minimal"
    assert payload["thinking_level"] == "minimal"
    assert payload["timeout_seconds"] == 150


def test_run_live_openclaw_pilot_aggregates_scenario_results(monkeypatch, tmp_path: Path) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"jobs": {"by_status": {"pending": 0, "running": 0, "completed": 0, "failed": 0}}}

    class _Client:
        def get(self, _path: str):
            return _Response()

    monkeypatch.setattr("app.openclaw_live_pilot.create_local_runtime_client", lambda *_args, **_kwargs: _Client())
    monkeypatch.setattr(
        "app.openclaw_live_pilot._bootstrap_scope",
        lambda *_args, **_kwargs: {"namespace_id": "ns-1", "agent_id": "ag-1"},
    )
    monkeypatch.setattr(
        "app.openclaw_live_pilot._wait_for_jobs",
        lambda *_args, **_kwargs: {"jobs": {"by_status": {"pending": 0, "running": 0, "completed": 2, "failed": 0}}},
    )

    turns = [
        {
            "payload": {"payloads": [{"text": "Noted."}]},
            "capture_confirmed": True,
            "recall_timeout_observed": False,
            "registered_count": 1,
            "raw_output": "{}",
        }
        for _ in range(5)
    ]

    turn_calls: list[dict[str, object]] = []

    def fake_turn(**kwargs):
        turn_calls.append(kwargs)
        return turns.pop(0)

    recalls = [
        {"brief": {"critical_facts": ["standalone memory-runtime with Postgres, Redis, and a dedicated worker"]}, "trace": {}},
        {"brief": {"standing_procedures": ["concise summary before implementation details"]}, "trace": {}},
        {"brief": {"recent_session_carryover": ["live pilot acceptance checklist"]}, "trace": {}},
        {"brief": {"prior_decisions": ["validating live OpenClaw capture on pilot-user-2"]}, "trace": {}},
        {"brief": {"critical_facts": ["standalone memory-runtime with Postgres, Redis, and a dedicated worker"]}, "trace": {}},
    ]

    memories = [
        {"results": [{"memory": "standalone memory-runtime with Postgres, Redis, and a dedicated worker"}]},
        {"results": [{"memory": "concise summary before implementation details"}]},
        {"results": [{"memory": "live pilot acceptance checklist"}]},
        {"results": [{"memory": "validating live OpenClaw capture on pilot-user-2"}]},
        {"results": [{"memory": "standalone memory-runtime with Postgres, Redis, and a dedicated worker"}]},
    ]

    monkeypatch.setattr("app.openclaw_live_pilot._run_openclaw_turn", fake_turn)
    monkeypatch.setattr("app.openclaw_live_pilot._run_recall", lambda *_args, **_kwargs: recalls.pop(0))
    monkeypatch.setattr("app.openclaw_live_pilot._list_memories", lambda *_args, **_kwargs: memories.pop(0))
    monkeypatch.setattr("app.pilot_artifacts.ARTIFACT_ROOT", tmp_path / "artifacts")

    report = run_live_openclaw_pilot(
        runtime_base_url="http://127.0.0.1:8080",
        user_id="pilot-user-2",
        artifact_run_name="pytest-live",
        timeout_seconds=150,
        continuity_timeout_seconds=240,
        thinking_level="off",
        continuity_thinking_level="minimal",
    )

    assert report["total"] == 5
    assert report["passed"] == 5
    assert report["failed"] == 0
    assert Path(report["artifact_dir"]).exists()
    assert report["execution_profile"] == {
        "timeout_seconds": 150,
        "continuity_timeout_seconds": 240,
        "thinking_level": "off",
        "continuity_thinking_level": "minimal",
    }
    assert [call["timeout_seconds"] for call in turn_calls] == [150, 150, 150, 240, 150]
    assert [call["thinking_level"] for call in turn_calls] == ["off", "off", "off", "minimal", "off"]
