#!/usr/bin/env python3
"""Keeper Build 1 runner: automated maintenance + compatibility checks."""

from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "MEMORY.md"
HANDOFF_GLOB = str(ROOT / "docs" / "HANDOFFS" / "handoff-*.md")
LOG_EVENT = ROOT / "scripts" / "log_event.py"
RETRIEVAL_TEST = ROOT / "scripts" / "tests" / "test_memory_retrieval.py"
COMPAT_CHECK = ROOT / "scripts" / "keeper" / "check_compatibility.py"


def emit(run_id: str, status_word: str, emoji: str, summary: str, reason_code: str | None = None) -> None:
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id", run_id,
        "--agent", "Keeper",
        "--action", "maintenance",
        "--status-word", status_word,
        "--status-emoji", emoji,
        "--model-id", "system",
        "--summary", summary,
    ]
    if reason_code:
        cmd.extend(["--reason-code", reason_code])
    subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_promotions(handoff_path: Path) -> list[str]:
    text = handoff_path.read_text(encoding="utf-8", errors="ignore")
    bullets = []
    for line in text.splitlines():
        if line.strip().startswith("- "):
            item = line.strip()[2:].strip()
            if item:
                bullets.append(item)
    return bullets[:5]


def append_promotions_idempotent(memory_text: str, handoff_name: str, bullets: list[str]) -> tuple[str, int]:
    marker = f"[keeper:handoff:{handoff_name}]"
    if marker in memory_text:
        return memory_text, 0

    additions = [f"- {b} ({marker})" for b in bullets]
    if not additions:
        return memory_text, 0

    block = "\n## Keeper Promotions\n" + "\n".join(additions) + "\n"
    if "## Keeper Promotions" in memory_text:
        # append under existing section tail
        new_text = memory_text.rstrip() + "\n" + "\n".join(additions) + "\n"
    else:
        new_text = memory_text.rstrip() + block
    return new_text, len(additions)


def run_subprocess_json(path: Path) -> tuple[int, dict | None, str]:
    proc = subprocess.run([sys.executable, str(path)], cwd=str(ROOT), capture_output=True, text=True)
    payload = None
    raw = proc.stdout.strip()
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
    return proc.returncode, payload, raw


def main() -> int:
    run_id = f"keeper-build1-{int(time.time())}"
    emit(run_id, "START", "▶️", "Keeper Build 1 maintenance started")

    handoffs = sorted(Path(p) for p in glob.glob(HANDOFF_GLOB))

    # retrieval health
    retrieval_proc = subprocess.run([sys.executable, str(RETRIEVAL_TEST)], cwd=str(ROOT), capture_output=True, text=True)
    if retrieval_proc.returncode != 0:
        emit(run_id, "FAIL", "❌", "Retrieval smoke test failed", reason_code="RETRIEVAL_FAIL")
        print(json.dumps({"status": "fail", "reason_code": "RETRIEVAL_FAIL", "summary": retrieval_proc.stdout + retrieval_proc.stderr, "ts_iso": now_iso()}))
        return 2

    # compatibility check
    c_rc, compat, compat_raw = run_subprocess_json(COMPAT_CHECK)
    if c_rc != 0:
        emit(run_id, "FAIL", "❌", "Compatibility checker failed", reason_code="COMPAT_FAIL")
        print(json.dumps({"status": "fail", "reason_code": "COMPAT_FAIL", "summary": compat_raw, "ts_iso": now_iso()}))
        return 3

    if not MEMORY.exists():
        emit(run_id, "FAIL", "❌", "MEMORY.md missing", reason_code="MISSING_MEMORY")
        print(json.dumps({"status": "fail", "reason_code": "MISSING_MEMORY", "ts_iso": now_iso()}))
        return 4

    memory_text = MEMORY.read_text(encoding="utf-8", errors="ignore")
    promoted = 0

    if not handoffs:
        emit(run_id, "WARN", "⚠️", "No handoff notes found; skipped promotion", reason_code="NO_NOTES")
    else:
        latest = handoffs[-1]
        bullets = extract_promotions(latest)
        new_text, added = append_promotions_idempotent(memory_text, latest.name, bullets)
        promoted += added
        if added > 0:
            MEMORY.write_text(new_text, encoding="utf-8")

    # emit based on compatibility findings severity
    compat_status = (compat or {}).get("status", "ok")
    if compat_status == "warn":
        emit(run_id, "WARN", "⚠️", f"Keeper completed with {len((compat or {}).get('findings', []))} compatibility warnings", reason_code="COMPAT_WARN")
    elif compat_status == "ok" and promoted == 0 and handoffs:
        emit(run_id, "WARN", "⚠️", "Keeper completed; no new promotions (idempotent)", reason_code="NO_CHANGES")
    else:
        emit(run_id, "OK", "✅", f"Keeper completed; promoted {promoted} items")

    print(json.dumps({
        "status": "ok",
        "promoted": promoted,
        "handoffs_seen": len(handoffs),
        "compat_status": compat_status,
        "ts_iso": now_iso(),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
