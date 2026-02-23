#!/usr/bin/env python3
"""Spawn lifecycle helper: enforce terminal ActionEvent emission for sessions_spawn runs.

Usage:
  python scripts/spawn_lifecycle.py start --run-id <id> --summary "..." [--emit-start]
  python scripts/spawn_lifecycle.py end --run-id <id> --result OK|WARN|FAIL --summary "..." [--reason-code X]

State files:
  data/logs/spawn_state/<run_id>.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path("data/logs/spawn_state")
LOG_EVENT = Path("scripts/log_event.py")


def ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def emit_event(*, run_id: str, status_word: str, summary: str, reason_code: str | None, model_id: str, agent: str, outputs: list[str] | None = None) -> None:
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id", run_id,
        "--agent", agent,
        "--action", "sessions_spawn",
        "--status-word", status_word,
        "--status-emoji", {"START": "▶️", "OK": "✅", "WARN": "⚠️", "FAIL": "❌"}[status_word],
        "--model-id", model_id,
        "--summary", summary,
    ]
    if reason_code:
        cmd += ["--reason-code", reason_code]
    cmd += ["--inputs", "sessions_spawn"]
    if outputs:
        cmd += ["--outputs", *outputs]
    subprocess.run(cmd, check=True)


def cmd_start(args: argparse.Namespace) -> int:
    st = load_state(args.run_id)
    if st.get("terminal_emitted"):
        print("Terminal already emitted for this run_id; start ignored.", file=sys.stderr)
        return 1

    new_state = {
        "run_id": args.run_id,
        "started_at": ts_iso(),
        "emit_start": bool(args.emit_start),
        "terminal_emitted": False,
        "agent": args.agent,
        "model_id": args.model_id,
    }
    save_state(args.run_id, new_state)

    if args.emit_start:
        emit_event(
            run_id=args.run_id,
            status_word="START",
            summary=args.summary,
            reason_code="SPAWN_START",
            model_id=args.model_id,
            agent=args.agent,
        )
    return 0


def cmd_end(args: argparse.Namespace) -> int:
    if args.result not in {"OK", "WARN", "FAIL"}:
        print("result must be OK/WARN/FAIL", file=sys.stderr)
        return 2

    st = load_state(args.run_id)
    if st.get("terminal_emitted") and not args.force:
        print("Terminal already emitted for this run_id. Use --force to override.", file=sys.stderr)
        return 1

    emit_event(
        run_id=args.run_id,
        status_word=args.result,
        summary=args.summary,
        reason_code=args.reason_code,
        model_id=args.model_id,
        agent=args.agent,
        outputs=args.outputs,
    )

    st.update(
        {
            "run_id": args.run_id,
            "terminal_emitted": True,
            "terminal_status": args.result,
            "terminal_reason_code": args.reason_code,
            "terminal_at": ts_iso(),
            "agent": args.agent,
            "model_id": args.model_id,
        }
    )
    save_state(args.run_id, st)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start")
    ps.add_argument("--run-id", required=True)
    ps.add_argument("--summary", required=True)
    ps.add_argument("--emit-start", action="store_true", help="Emit START event (use only for long/multi-step runs)")
    ps.add_argument("--agent", default="oQ")
    ps.add_argument("--model-id", default="openai-codex/gpt-5.3-codex")

    pe = sub.add_parser("end")
    pe.add_argument("--run-id", required=True)
    pe.add_argument("--result", required=True, choices=["OK", "WARN", "FAIL"])
    pe.add_argument("--summary", required=True)
    pe.add_argument("--reason-code", default=None)
    pe.add_argument("--outputs", nargs="*", default=[])
    pe.add_argument("--force", action="store_true")
    pe.add_argument("--agent", default="oQ")
    pe.add_argument("--model-id", default="openai-codex/gpt-5.3-codex")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "start":
        return cmd_start(args)
    if args.cmd == "end":
        return cmd_end(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
