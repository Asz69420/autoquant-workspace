#!/usr/bin/env python3
"""Spawn lifecycle helper: enforce canonical sub-agent lifecycle ActionEvents.

Usage:
  python scripts/spawn_lifecycle.py start --run-id <id> --summary "..." [--emit-start]
  python scripts/spawn_lifecycle.py end --run-id <id> --result OK|WARN|FAIL --summary "..." [--reason-code X]
  python scripts/spawn_lifecycle.py validate --run-id <id> [--actions-log data/logs/actions.ndjson]

Note: --emit-start is accepted for compatibility; start now always emits SUBAGENT_SPAWN.

State files:
  data/logs/spawn_state/<run_id>.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path("data/logs/spawn_state")
LOG_EVENT = Path("scripts/log_event.py")
ACTIONS_LOG = Path("data/logs/actions.ndjson")

SPAWN_ACTION = "SUBAGENT_SPAWN"
FINISH_ACTION = "SUBAGENT_FINISH"
FAIL_ACTION = "SUBAGENT_FAIL"


def ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "-", value).strip("-")


def resolve_run_id(run_id: str | None, child_session_key: str | None) -> str:
    if run_id and run_id.strip():
        return run_id.strip()
    if child_session_key and child_session_key.strip():
        return f"subagent::{_slug(child_session_key.strip())}"
    raise ValueError("Provide --run-id or --child-session-key")


def state_path(run_id: str) -> Path:
    safe = run_id.replace("/", "_")
    return STATE_DIR / f"{safe}.json"


def load_state(run_id: str) -> dict:
    p = state_path(run_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(run_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = state_path(run_id)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_event(
    *,
    run_id: str,
    action: str,
    status_word: str,
    summary: str,
    reason_code: str | None,
    model_id: str,
    agent: str,
    outputs: list[str] | None = None,
) -> None:
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id",
        run_id,
        "--agent",
        agent,
        "--action",
        action,
        "--status-word",
        status_word,
        "--status-emoji",
        {
            "START": "▶️",
            "OK": "✅",
            "WARN": "⚠️",
            "FAIL": "❌",
        }[status_word],
        "--model-id",
        model_id,
        "--summary",
        summary,
    ]
    if reason_code:
        cmd += ["--reason-code", reason_code]
    cmd += ["--inputs", "sessions_spawn"]
    if outputs:
        cmd += ["--outputs", *outputs]
    subprocess.run(cmd, check=True)


def cmd_start(args: argparse.Namespace) -> int:
    try:
        run_id = resolve_run_id(args.run_id, args.child_session_key)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    st = load_state(run_id)
    if st.get("terminal_emitted"):
        print("Terminal already emitted for this run_id; start ignored.", file=sys.stderr)
        return 1

    outputs: list[str] = []
    if args.child_session_key:
        outputs.append(f"child_session:{args.child_session_key}")

    emit_event(
        run_id=run_id,
        action=SPAWN_ACTION,
        status_word="START",
        summary=args.summary,
        reason_code="SPAWN_START",
        model_id=args.model_id,
        agent=args.agent,
        outputs=outputs,
    )

    new_state = {
        "run_id": run_id,
        "child_session_key": args.child_session_key,
        "started_at": ts_iso(),
        "spawn_emitted": True,
        "terminal_emitted": False,
        "agent": args.agent,
        "model_id": args.model_id,
    }
    save_state(run_id, new_state)
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    if args.result not in {"OK", "WARN", "FAIL"}:
        print("result must be OK/WARN/FAIL", file=sys.stderr)
        return 2

    try:
        run_id = resolve_run_id(args.run_id, args.child_session_key)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    st = load_state(run_id)
    if st.get("terminal_emitted") and not args.force:
        print("Terminal already emitted for this run_id. Use --force to override.", file=sys.stderr)
        return 1

    state_child = st.get("child_session_key")
    if state_child and args.child_session_key and state_child != args.child_session_key:
        print(
            "child_session_key mismatch for run_id; refusing terminal emit.",
            file=sys.stderr,
        )
        return 2

    action = FAIL_ACTION if args.result == "FAIL" else FINISH_ACTION
    outputs = list(args.outputs)
    child_session_key = args.child_session_key or state_child
    if child_session_key:
        child_ref = f"child_session:{child_session_key}"
        if child_ref not in outputs:
            outputs.append(child_ref)

    emit_event(
        run_id=run_id,
        action=action,
        status_word=args.result,
        summary=args.summary,
        reason_code=args.reason_code,
        model_id=args.model_id,
        agent=args.agent,
        outputs=outputs,
    )

    st.update(
        {
            "run_id": run_id,
            "child_session_key": child_session_key,
            "terminal_emitted": True,
            "terminal_action": action,
            "terminal_status": args.result,
            "terminal_reason_code": args.reason_code,
            "terminal_at": ts_iso(),
            "agent": args.agent,
            "model_id": args.model_id,
        }
    )
    save_state(run_id, st)
    return 0


def _action_matches(ev: dict, run_id: str, child_session_key: str | None) -> bool:
    if ev.get("run_id") != run_id:
        return False
    if not child_session_key:
        return True
    outputs = ev.get("outputs") or []
    if not isinstance(outputs, list):
        return False
    return f"child_session:{child_session_key}" in [str(x) for x in outputs]


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        run_id = resolve_run_id(args.run_id, args.child_session_key)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    actions_log = Path(args.actions_log)
    if not actions_log.exists():
        print(f"actions log missing: {actions_log}", file=sys.stderr)
        return 2

    saw_spawn = False
    saw_terminal = False
    with actions_log.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except Exception:
                continue
            if not _action_matches(ev, run_id, args.child_session_key):
                continue
            action = str(ev.get("action") or "")
            if action == SPAWN_ACTION:
                saw_spawn = True
            elif action in {FINISH_ACTION, FAIL_ACTION}:
                saw_terminal = True

    if not saw_spawn or not saw_terminal:
        print(
            f"missing lifecycle entries run_id={run_id} spawn={saw_spawn} terminal={saw_terminal}",
            file=sys.stderr,
        )
        return 1

    print(f"OK run_id={run_id} spawn+terminal present")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start")
    ps.add_argument("--run-id", required=False)
    ps.add_argument("--child-session-key", default=None)
    ps.add_argument("--summary", required=True)
    ps.add_argument(
        "--emit-start",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    ps.add_argument("--agent", default="oQ")
    ps.add_argument("--model-id", default="openai-codex/gpt-5.3-codex")

    pe = sub.add_parser("end")
    pe.add_argument("--run-id", required=False)
    pe.add_argument("--child-session-key", default=None)
    pe.add_argument("--result", required=True, choices=["OK", "WARN", "FAIL"])
    pe.add_argument("--summary", required=True)
    pe.add_argument("--reason-code", default=None)
    pe.add_argument("--outputs", nargs="*", default=[])
    pe.add_argument("--force", action="store_true")
    pe.add_argument("--agent", default="oQ")
    pe.add_argument("--model-id", default="openai-codex/gpt-5.3-codex")

    pv = sub.add_parser("validate")
    pv.add_argument("--run-id", required=False)
    pv.add_argument("--child-session-key", default=None)
    pv.add_argument("--actions-log", default=str(ACTIONS_LOG))
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "start":
        return cmd_start(args)
    if args.cmd == "end":
        return cmd_end(args)
    if args.cmd == "validate":
        return cmd_validate(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
