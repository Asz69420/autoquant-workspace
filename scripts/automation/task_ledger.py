#!/usr/bin/env python3
"""Persistent task ledger for execution integrity.

Usage examples:
  python scripts/automation/task_ledger.py create --task-id t1 --description "patch x"
  python scripts/automation/task_ledger.py update --task-id t1 --state EXECUTING --pid-or-session 1234
  python scripts/automation/task_ledger.py update --task-id t1 --state COMPLETE --artifact scripts/foo.py --verifier-artifact docs/verification/v1.md
  python scripts/automation/task_ledger.py show --task-id t1
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("task_ledger.jsonl")
VALID_STATES = {"NOT_STARTED", "EXECUTING", "BLOCKED", "COMPLETE"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_all(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def latest_for_task(rows: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    for r in reversed(rows):
        if r.get("task_id") == task_id:
            return r
    return None


def validate_transition(row: dict[str, Any]) -> None:
    state = row["state"]
    if state not in VALID_STATES:
        raise SystemExit(f"Invalid state: {state}")

    if state == "EXECUTING" and not row.get("pid_or_session"):
        raise SystemExit("EXECUTING requires pid_or_session")
    if state == "COMPLETE" and not row.get("artifacts"):
        raise SystemExit("COMPLETE requires at least one artifact")
    if state == "BLOCKED" and not row.get("blocker_trace"):
        raise SystemExit("BLOCKED requires blocker_trace")


def cmd_create(args: argparse.Namespace) -> None:
    rows = read_all(LEDGER_PATH)
    if latest_for_task(rows, args.task_id):
        raise SystemExit(f"task_id already exists: {args.task_id}")

    ts = now_iso()
    row = {
        "task_id": args.task_id,
        "created_at": ts,
        "description": args.description,
        "state": "NOT_STARTED",
        "pid_or_session": None,
        "artifacts": [],
        "verifier_or_audit_artifact": None,
        "blocker_trace": None,
        "last_update_at": ts,
    }
    append(LEDGER_PATH, row)
    print(json.dumps(row, ensure_ascii=False))


def cmd_update(args: argparse.Namespace) -> None:
    rows = read_all(LEDGER_PATH)
    base = latest_for_task(rows, args.task_id)
    if not base:
        raise SystemExit(f"task_id not found: {args.task_id}")

    row = dict(base)
    row["state"] = args.state
    row["last_update_at"] = now_iso()

    if args.pid_or_session is not None:
        row["pid_or_session"] = args.pid_or_session
    if args.artifact:
        artifacts = list(row.get("artifacts") or [])
        artifacts.extend(args.artifact)
        row["artifacts"] = artifacts
    if args.verifier_or_audit_artifact is not None:
        row["verifier_or_audit_artifact"] = args.verifier_or_audit_artifact
    if args.blocker_trace is not None:
        row["blocker_trace"] = args.blocker_trace

    validate_transition(row)
    append(LEDGER_PATH, row)
    print(json.dumps(row, ensure_ascii=False))


def cmd_show(args: argparse.Namespace) -> None:
    rows = read_all(LEDGER_PATH)
    if args.task_id:
        row = latest_for_task(rows, args.task_id)
        if not row:
            raise SystemExit(f"task_id not found: {args.task_id}")
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return
    print(json.dumps(rows[-args.limit :], ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("--task-id", required=True)
    c.add_argument("--description", required=True)
    c.set_defaults(func=cmd_create)

    u = sub.add_parser("update")
    u.add_argument("--task-id", required=True)
    u.add_argument("--state", required=True, choices=sorted(VALID_STATES))
    u.add_argument("--pid-or-session")
    u.add_argument("--artifact", action="append")
    u.add_argument("--verifier-or-audit-artifact")
    u.add_argument("--blocker-trace")
    u.set_defaults(func=cmd_update)

    s = sub.add_parser("show")
    s.add_argument("--task-id")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_show)
    return p


if __name__ == "__main__":
    parser = build_parser()
    ns = parser.parse_args()
    ns.func(ns)
