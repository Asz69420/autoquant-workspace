#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _notify(msg: str) -> None:
    ps = ROOT / "scripts" / "claude-tasks" / "notify-asz.ps1"
    subprocess.run([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps), "-Message", msg
    ], cwd=ROOT, check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="data/forward/FORWARD_LOG.ndjson")
    ap.add_argument("--missed-cycles", type=int, default=2)
    ap.add_argument("--hours-per-cycle", type=int, default=4)
    args = ap.parse_args()

    p = ROOT / args.log
    if not p.exists():
        _notify("⚠️ Forward runner health: no log file found yet.")
        return 0

    lines = [ln for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    if not lines:
        _notify("⚠️ Forward runner health: log file empty.")
        return 0

    last = json.loads(lines[-1])
    ts = str(last.get("ts_iso") or "")
    if not ts:
        _notify("⚠️ Forward runner health: latest log missing ts_iso.")
        return 0

    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    max_gap = timedelta(hours=args.hours_per_cycle * max(1, args.missed_cycles))
    if (now - dt) > max_gap:
        _notify(f"⚠️ Forward runner missed {args.missed_cycles}+ cycles. Last log: {ts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
