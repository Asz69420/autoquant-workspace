#!/usr/bin/env python3
"""Reconcile spawn lifecycle state and surface missing terminal events.

- Scans data/logs/spawn_state/*.json
- For stale runs with no terminal event, emits SUBAGENT_FAIL (reason_code=MISSING_TERMINAL_EVENT)
- --strict exits nonzero if unresolved stale runs exist
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

TERMINAL_ACTIONS = {"SUBAGENT_FINISH", "SUBAGENT_FAIL"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def emit_terminal_fail(run_id: str, summary: str, model_id: str, agent: str) -> None:
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id",
        run_id,
        "--agent",
        agent,
        "--action",
        "SUBAGENT_FAIL",
        "--status-word",
        "FAIL",
        "--status-emoji",
        "❌",
        "--model-id",
        model_id,
        "--reason-code",
        "MISSING_TERMINAL_EVENT",
        "--summary",
        summary,
        "--inputs",
        "sessions_spawn",
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grace-seconds", type=int, default=120)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument(
        "--require-actions-log",
        action="store_true",
        help="Require terminal run_ids to be present in actions.ndjson",
    )
    ap.add_argument(
        "--max-age-minutes",
        type=int,
        default=180,
        help="Lookback window for actions.ndjson delivery proof",
    )
    args = ap.parse_args()

    if not STATE_DIR.exists():
        print("No spawn state directory; nothing to reconcile.")
        return 0

    unresolved = 0
    checked = 0

    delivered_run_ids: set[str] = set()
    pending_run_ids: set[str] = set()
    if args.require_actions_log:
        actions = Path("data/logs/actions.ndjson")
        if actions.exists():
            cutoff = now_utc().timestamp() - (args.max_age_minutes * 60)
            for line in actions.read_text(encoding="utf-8", errors="ignore").splitlines()[-5000:]:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("action") not in TERMINAL_ACTIONS:
                    continue
                if obj.get("status_word") not in {"OK", "WARN", "FAIL"}:
                    continue
                ts = parse_iso(obj.get("ts_iso"))
                if ts and ts.timestamp() >= cutoff:
                    rid = obj.get("run_id")
                    if rid:
                        delivered_run_ids.add(str(rid))

        outbox = Path("data/logs/outbox")
        if outbox.exists():
            for fp in outbox.glob("*.json"):
                parts = fp.name.split("___")
                if len(parts) >= 2:
                    pending_run_ids.add(parts[1])

    for p in sorted(STATE_DIR.glob("*.json")):
        checked += 1
        try:
            st = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        run_id = st.get("run_id") or p.stem

        if st.get("terminal_emitted"):
            if (
                args.require_actions_log
                and str(run_id) not in delivered_run_ids
                and str(run_id) not in pending_run_ids
            ):
                unresolved += 1
                agent = st.get("agent") or "oQ"
                model_id = st.get("model_id") or "openai-codex/gpt-5.3-codex"
                summary = "Sub-agent terminal event missing from actions.ndjson delivery proof"
                emit_terminal_fail(
                    run_id=str(run_id), summary=summary, model_id=model_id, agent=agent
                )
                st["terminal_emitted"] = True
                p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        started = parse_iso(st.get("started_at"))
        if not started:
            continue

        age = (now_utc() - started).total_seconds()
        if age < args.grace_seconds:
            continue

        unresolved += 1
        agent = st.get("agent") or "oQ"
        model_id = st.get("model_id") or "openai-codex/gpt-5.3-codex"
        summary = f"Sub-agent lifecycle missing terminal event (age={int(age)}s)"
        emit_terminal_fail(run_id=run_id, summary=summary, model_id=model_id, agent=agent)
        st["terminal_emitted"] = True
        st["terminal_action"] = "SUBAGENT_FAIL"
        st["terminal_status"] = "FAIL"
        st["terminal_reason_code"] = "MISSING_TERMINAL_EVENT"
        st["terminal_at"] = now_utc().isoformat().replace("+00:00", "Z")
        p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Checked={checked} unresolved={unresolved}")
    if args.strict and unresolved > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
