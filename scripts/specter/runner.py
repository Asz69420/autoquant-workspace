#!/usr/bin/env python3
"""Specter Build 1.1 runner: hard gating + preset validation + mock responses."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_EVENT = ROOT / "scripts" / "log_event.py"
CONFIG_PATH = ROOT / "scripts" / "specter" / "config.example.json"

ALLOWED_PROVIDER_TARGETS = {"claude_web", "generic_browser_ai"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def emit_event(
    run_id: str,
    action: str,
    status_word: str,
    status_emoji: str,
    summary: str,
    reason_code: str | None = None,
    outputs: list[str] | None = None,
):
    if os.getenv("SPECTER_TEST_MODE") == "1":
        return

    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id",
        run_id,
        "--agent",
        "Specter",
        "--action",
        action,
        "--status-word",
        status_word,
        "--status-emoji",
        status_emoji,
        "--model-id",
        "build1-mock",
        "--summary",
        summary,
    ]
    if reason_code:
        cmd.extend(["--reason-code", reason_code])
    if outputs:
        cmd.extend(["--outputs", *outputs])
    subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)


def validate_request(req: dict, config: dict) -> tuple[bool, str | None]:
    required = ["version", "trace_id", "request_id", "provider_target", "prompt", "intent"]
    for field in required:
        if field not in req:
            return False, f"missing required field: {field}"

    if not isinstance(req["prompt"], str) or not req["prompt"].strip():
        return False, "prompt must be a non-empty string"

    if req["provider_target"] not in ALLOWED_PROVIDER_TARGETS:
        return False, "provider_target must be one of: claude_web, generic_browser_ai"

    if req["intent"] not in {"mock", "execute"}:
        return False, "intent must be one of: mock, execute"

    timeout_ms = req.get("timeout_ms", 30000)
    if not isinstance(timeout_ms, int) or timeout_ms < 1000 or timeout_ms > 180000:
        return False, "timeout_ms must be an integer between 1000 and 180000"

    preset = req.get("mode", config.get("defaults", {}).get("operator_preset", "default"))
    presets = set(config.get("operator_presets", {}).keys())
    if preset not in presets:
        return False, f"mode must be one of: {', '.join(sorted(presets))}"

    return True, None


def is_mock_safe(req: dict, config: dict) -> bool:
    # Build 1.1 hard gate: only explicit mock intent is allowed
    if req.get("intent") != "mock":
        return False

    # Guard optional execute-like flags
    if req.get("external_action") is True:
        return False

    preset = req.get("mode", config.get("defaults", {}).get("operator_preset", "default"))
    return preset in set(config.get("operator_presets", {}).keys())


def blocked_response(req: dict, timing_ms: int) -> dict:
    return {
        "version": req["version"],
        "trace_id": req["trace_id"],
        "request_id": req["request_id"],
        "status": "blocked",
        "provider": req["provider_target"],
        "model_label": None,
        "response_text": None,
        "timing_ms": timing_ms,
        "cache": {"hit": False, "key": None},
        "error": {
            "code": "NEEDS_APPROVAL",
            "message": "Build 1.1 hard gate blocked non-mock-safe request.",
            "retryable": False,
        },
        "ts_iso": now_iso(),
    }


def ok_mock_response(req: dict, timing_ms: int) -> dict:
    return {
        "version": req["version"],
        "trace_id": req["trace_id"],
        "request_id": req["request_id"],
        "status": "ok",
        "provider": req["provider_target"],
        "model_label": "build1-mock",
        "response_text": "[MOCK] Specter Build 1.1 response. No external action performed.",
        "timing_ms": timing_ms,
        "cache": {"hit": False, "key": None},
        "error": None,
        "ts_iso": now_iso(),
    }


def fail_response(req: dict | None, code: str, message: str, timing_ms: int) -> dict:
    return {
        "version": req.get("version", "v1") if isinstance(req, dict) else "v1",
        "trace_id": req.get("trace_id", "unknown") if isinstance(req, dict) else "unknown",
        "request_id": req.get("request_id", "unknown") if isinstance(req, dict) else "unknown",
        "status": "error",
        "provider": req.get("provider_target", "unknown") if isinstance(req, dict) else "unknown",
        "model_label": "build1-mock",
        "response_text": None,
        "timing_ms": timing_ms,
        "cache": {"hit": False, "key": None},
        "error": {"code": code, "message": message, "retryable": False},
        "ts_iso": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, help="Path to request JSON")
    args = parser.parse_args()

    start = time.time()
    run_id = f"specter-build1_1-{int(start)}"
    emit_event(run_id, "specter_run", "START", "▶️", "Specter Build 1.1 run started")

    req_obj = None

    try:
        config = load_config()
        req_path = Path(args.request)
        with req_path.open("r", encoding="utf-8-sig") as f:
            req_obj = json.load(f)

        ok, err = validate_request(req_obj, config)
        if not ok:
            timing = int((time.time() - start) * 1000)
            resp = fail_response(req_obj, "VALIDATION_ERROR", err or "invalid request", timing)
            print(json.dumps(resp))
            emit_event(
                run_id,
                "specter_run",
                "FAIL",
                "❌",
                f"Validation failed: {err}",
                reason_code="VALIDATION_ERROR",
            )
            return 2

        timing = int((time.time() - start) * 1000)

        if not is_mock_safe(req_obj, config):
            resp = blocked_response(req_obj, timing)
            print(json.dumps(resp))
            emit_event(
                run_id,
                "specter_run",
                "BLOCKED",
                "⛔",
                "Build 1.1 blocked non-mock-safe request",
                reason_code="NEEDS_APPROVAL",
            )
            return 0

        resp = ok_mock_response(req_obj, timing)
        print(json.dumps(resp))
        emit_event(run_id, "specter_run", "OK", "✅", "Build 1.1 mock response emitted")
        return 0

    except json.JSONDecodeError as e:
        timing = int((time.time() - start) * 1000)
        resp = fail_response(req_obj, "VALIDATION_ERROR", str(e), timing)
        print(json.dumps(resp))
        emit_event(
            run_id,
            "specter_run",
            "FAIL",
            "❌",
            "Request JSON parse failed",
            reason_code="VALIDATION_ERROR",
        )
        return 3
    except Exception as e:  # noqa: BLE001
        timing = int((time.time() - start) * 1000)
        resp = fail_response(req_obj, "RUNTIME_ERROR", str(e), timing)
        print(json.dumps(resp))
        emit_event(run_id, "specter_run", "FAIL", "❌", "Specter runtime error")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
