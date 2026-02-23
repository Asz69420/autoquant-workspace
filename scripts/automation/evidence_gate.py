#!/usr/bin/env python3
"""Evidence gate checker for outbound status claims.

Validates task_ledger latest row for a task against requested claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LEDGER = Path("task_ledger.jsonl")


def load_latest(task_id: str):
    if not LEDGER.exists():
        raise SystemExit("BLOCKED: task_ledger.jsonl not found")
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    for r in reversed(rows):
        if r.get("task_id") == task_id:
            return r
    raise SystemExit(f"BLOCKED: task_id not found: {task_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--claim", required=True, choices=["NOT_STARTED", "EXECUTING", "BLOCKED", "COMPLETE"])
    ns = ap.parse_args()

    row = load_latest(ns.task_id)

    if ns.claim == "NOT_STARTED":
        if row.get("state") != "NOT_STARTED":
            raise SystemExit("NOT_STARTED")

    if ns.claim == "EXECUTING":
        if row.get("state") != "EXECUTING" or not row.get("pid_or_session"):
            raise SystemExit("NOT_STARTED")

    if ns.claim == "COMPLETE":
        if row.get("state") != "COMPLETE" or not row.get("artifacts"):
            raise SystemExit("NOT_STARTED")

    if ns.claim == "BLOCKED":
        if row.get("state") != "BLOCKED" or not row.get("blocker_trace"):
            raise SystemExit("NOT_STARTED")

    print(json.dumps({"ok": True, "task_id": ns.task_id, "claim": ns.claim, "row": row}, ensure_ascii=False))


if __name__ == "__main__":
    main()
