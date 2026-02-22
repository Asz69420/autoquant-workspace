#!/usr/bin/env python3
"""Specter vNext runner: provider router plumbing + operator profiles (gated)."""

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

ALLOWED_PROVIDER_TARGETS = {"claude_cli", "claude_web", "generic_browser_ai"}
ALLOWED_EXECUTION_MODES = {"mock", "cli_live", "browser_live"}
ALLOWED_ROUTING_INTENTS = {"auto", "forced"}
MODEL_ALIASES = {
    "opus 4.6": "opencode/claude-opus-4-6",
    "sonnet 4.6": "anthropic/claude-sonnet-4-6",
    "haiku 4.5": "anthropic/claude-haiku-4-5-20251001",
    "codex 5.3": "openai-codex/gpt-5.3-codex",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def emit_event(run_id: str, status_word: str, status_emoji: str, summary: str, reason_code: str | None = None):
    if os.getenv("SPECTER_TEST_MODE") == "1":
        return
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id", run_id,
        "--agent", "Specter",
        "--action", "specter_run",
        "--status-word", status_word,
        "--status-emoji", status_emoji,
        "--model-id", "build1-mock",
        "--summary", summary,
    ]
    if reason_code:
        cmd.extend(["--reason-code", reason_code])
    subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)


def normalize_request(req: dict, cfg: dict) -> dict:
    # backward compatibility from Build 1.1
    if "execution_mode" not in req:
        req["execution_mode"] = "mock" if req.get("intent", "mock") == "mock" else "cli_live"
    if "operator_profile" not in req:
        req["operator_profile"] = req.get("mode", cfg["defaults"].get("operator_profile", "default"))
    if "routing_intent" not in req:
        req["routing_intent"] = cfg["defaults"].get("routing_intent", "auto")
    if "model_request" not in req:
        req["model_request"] = "build1-mock"
    return req


def resolve_model(model_request: str) -> str:
    return MODEL_ALIASES.get(model_request.lower(), model_request)


def validate_request(req: dict, cfg: dict) -> tuple[bool, str | None]:
    required = ["version", "trace_id", "request_id", "provider_target", "prompt", "execution_mode", "routing_intent", "operator_profile", "model_request"]
    for f in required:
        if f not in req:
            return False, f"missing required field: {f}"

    if req["provider_target"] not in ALLOWED_PROVIDER_TARGETS:
        return False, "provider_target must be one of: claude_cli, claude_web, generic_browser_ai"
    if req["execution_mode"] not in ALLOWED_EXECUTION_MODES:
        return False, "execution_mode must be one of: mock, cli_live, browser_live"
    if req["routing_intent"] not in ALLOWED_ROUTING_INTENTS:
        return False, "routing_intent must be one of: auto, forced"
    if req["operator_profile"] not in set(cfg.get("operator_presets", {}).keys()):
        return False, f"operator_profile must be one of: {', '.join(sorted(cfg.get('operator_presets', {}).keys()))}"
    if not isinstance(req.get("prompt"), str) or not req["prompt"].strip():
        return False, "prompt must be a non-empty string"
    return True, None


def build_response(req: dict, status: str, timing_ms: int, *, error: dict | None, route_selected: str, provider_resolved: str, model_resolved: str, response_text: str | None):
    return {
        "version": req["version"],
        "trace_id": req["trace_id"],
        "request_id": req["request_id"],
        "status": status,
        "provider": provider_resolved,
        "model_label": model_resolved,
        "response_text": response_text,
        "timing_ms": timing_ms,
        "cache": {"hit": False, "key": route_selected},
        "error": error,
        "ts_iso": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()

    start = time.time()
    run_id = f"specter-vnext-{int(start)}"
    emit_event(run_id, "START", "▶️", "Specter vNext run started")

    req = None
    try:
        cfg = load_config()
        with Path(args.request).open("r", encoding="utf-8-sig") as f:
            req = normalize_request(json.load(f), cfg)

        ok, err = validate_request(req, cfg)
        if not ok:
            timing = int((time.time() - start) * 1000)
            req_safe = {
                "version": req.get("version", "v1") if isinstance(req, dict) else "v1",
                "trace_id": req.get("trace_id", "unknown") if isinstance(req, dict) else "unknown",
                "request_id": req.get("request_id", "unknown") if isinstance(req, dict) else "unknown",
                "provider_target": req.get("provider_target", "unknown") if isinstance(req, dict) else "unknown",
                "model_request": req.get("model_request", "unknown") if isinstance(req, dict) else "unknown",
            }
            out = build_response(req_safe, "error", timing,
                                 error={"code":"VALIDATION_ERROR","message":err or "invalid request","retryable":False},
                                 route_selected="mock", provider_resolved=req_safe.get("provider_target","unknown"),
                                 model_resolved=req_safe.get("model_request","unknown"), response_text=None)
            print(json.dumps(out))
            emit_event(run_id, "FAIL", "❌", f"Validation failed: {err}", reason_code="VALIDATION_ERROR")
            return 2

        timing = int((time.time() - start) * 1000)
        route_selected = req["execution_mode"]
        provider_resolved = req["provider_target"]
        model_resolved = resolve_model(req["model_request"])

        if req["execution_mode"] != "mock" and os.getenv("SPECTER_ENABLE_LIVE") != "1":
            out = build_response(req, "blocked", timing,
                                 error={"code":"NEEDS_APPROVAL","message":"Live execution disabled. Set SPECTER_ENABLE_LIVE=1 to enable.","retryable":False},
                                 route_selected=route_selected, provider_resolved=provider_resolved, model_resolved=model_resolved,
                                 response_text=f"[BLOCKED] route={route_selected} provider={provider_resolved} model={model_resolved} profile={req['operator_profile']} intent={req['routing_intent']}")
            print(json.dumps(out))
            emit_event(run_id, "BLOCKED", "⛔", f"Blocked route={route_selected} reason=NEEDS_APPROVAL", reason_code="NEEDS_APPROVAL")
            return 0

        out = build_response(req, "ok", timing, error=None,
                             route_selected=route_selected, provider_resolved=provider_resolved, model_resolved=model_resolved,
                             response_text=f"[MOCK] route={route_selected} provider={provider_resolved} model={model_resolved} profile={req['operator_profile']} intent={req['routing_intent']}")
        print(json.dumps(out))
        emit_event(run_id, "OK", "✅", f"Mock OK route={route_selected}")
        return 0

    except json.JSONDecodeError as e:
        timing = int((time.time() - start) * 1000)
        req_fallback = req if isinstance(req, dict) else {"version":"v1","trace_id":"unknown","request_id":"unknown","provider_target":"unknown","model_request":"unknown"}
        out = build_response(req_fallback, "error", timing,
                             error={"code":"VALIDATION_ERROR","message":str(e),"retryable":False},
                             route_selected="mock", provider_resolved=req_fallback.get("provider_target","unknown"),
                             model_resolved=req_fallback.get("model_request","unknown"), response_text=None)
        print(json.dumps(out))
        emit_event(run_id, "FAIL", "❌", "Request JSON parse failed", reason_code="VALIDATION_ERROR")
        return 3
    except Exception as e:
        timing = int((time.time() - start) * 1000)
        req_fallback = req if isinstance(req, dict) else {"version":"v1","trace_id":"unknown","request_id":"unknown","provider_target":"unknown","model_request":"unknown"}
        out = build_response(req_fallback, "error", timing,
                             error={"code":"VALIDATION_ERROR","message":str(e),"retryable":False},
                             route_selected="mock", provider_resolved=req_fallback.get("provider_target","unknown"),
                             model_resolved=req_fallback.get("model_request","unknown"), response_text=None)
        print(json.dumps(out))
        emit_event(run_id, "FAIL", "❌", "Specter runtime error", reason_code="VALIDATION_ERROR")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
