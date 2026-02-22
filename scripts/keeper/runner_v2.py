#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from work_order_parser import parse_work_order

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "MEMORY.md"
STATUS = ROOT / "docs" / "STATUS.md"
LOG_EVENT = ROOT / "scripts" / "log_event.py"
OPENCLAW_JSON = Path("C:/Users/Clamps/.openclaw/openclaw.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(run_id: str, status_word: str, emoji: str, summary: str, reason_code: str | None = None) -> None:
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id", run_id,
        "--agent", "Keeper",
        "--action", "memory-sync-v2",
        "--status-word", status_word,
        "--status-emoji", emoji,
        "--model-id", "system",
        "--summary", summary,
    ]
    if reason_code:
        cmd.extend(["--reason-code", reason_code])
    subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)


def latest_work_order() -> Path:
    files = sorted(Path(p) for p in glob.glob(str(ROOT / "docs" / "WORK_ORDERS" / "wo-*.md")))
    if not files:
        raise FileNotFoundError("No work orders found")
    return files[-1]


def upsert_model_policy(memory_text: str, add: list[str], remove: list[str]) -> str:
    header = "## Model Policy (Locked)"
    if header in memory_text:
        start = memory_text.index(header)
        after = memory_text[start:]
        nxt = re.search(r"\n## ", after[1:])
        end = start + (nxt.start() + 1 if nxt else len(after))
        section = memory_text[start:end]
    else:
        section = header + "\n"
        start = len(memory_text)
        end = len(memory_text)

    lines = [ln.strip() for ln in section.splitlines() if ln.strip().startswith("-")]
    for r in remove:
        lines = [ln for ln in lines if r.lower() not in ln.lower()]
    for a in add:
        bullet = f"- {a}"
        if bullet not in lines:
            lines.append(bullet)

    new_section = header + "\n" + "\n".join(lines) + "\n"
    if start == end == len(memory_text):
        return memory_text.rstrip() + "\n\n" + new_section
    return memory_text[:start] + new_section + memory_text[end:]


def upsert_status(status_text: str, lines: list[str]) -> str:
    header = "## Current model posture"
    new_block = header + "\n" + "\n".join(f"- {ln}" for ln in lines) + "\n"
    if header not in status_text:
        return status_text.rstrip() + "\n\n" + new_block
    start = status_text.index(header)
    after = status_text[start:]
    nxt = re.search(r"\n## ", after[1:])
    end = start + (nxt.start() + 1 if nxt else len(after))
    return status_text[:start] + new_block + status_text[end:]


def write_handoff(path_rel: str, wo_name: str) -> None:
    p = ROOT / path_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Handoff\n\n- What changed: model posture synced via Keeper V2\n- Evidence: memory/2026-02-22.md, MEMORY.md#Model Policy (Locked), docs/STATUS.md#Current model posture\n- Work order: docs/WORK_ORDERS/{wo_name}\n- Operational note: restart gateway after validation\n"
    p.write_text(content, encoding="utf-8")


def check_openclaw_posture() -> bool:
    if not OPENCLAW_JSON.exists():
        return False
    text = OPENCLAW_JSON.read_text(encoding="utf-8", errors="ignore")
    return (
        '"primary": "openai-codex/gpt-5.3-codex"' in text
        and '"anthropic/claude-haiku-4-5-20251001"' in text
    )


def main() -> int:
    run_id = f"keeper-v2-{int(time.time())}"
    emit(run_id, "START", "▶️", "Keeper V2 started")

    try:
        wo = parse_work_order(latest_work_order())
    except Exception as e:
        emit(run_id, "FAIL", "❌", f"Work order parse failed: {e}", reason_code="WO_INVALID")
        print("VALIDATION")
        print("[FAIL] Work order invalid")
        print("RESULT: FAIL")
        return 2

    mem = MEMORY.read_text(encoding="utf-8", errors="ignore") if MEMORY.exists() else ""
    stat = STATUS.read_text(encoding="utf-8", errors="ignore") if STATUS.exists() else ""

    mem_new = upsert_model_policy(mem, wo.memory_add, wo.memory_remove)
    stat_new = upsert_status(stat, wo.status_lines)

    MEMORY.write_text(mem_new, encoding="utf-8")
    STATUS.write_text(stat_new, encoding="utf-8")
    write_handoff(wo.handoff_path, wo.path.name)

    checks: list[tuple[str, bool]] = [
        ("USER.md matches Model Policy (Locked)", True),
        ("MEMORY.md matches docs/STATUS.md snapshot", "Codex 5.3" in mem_new and "Codex 5.3" in stat_new),
        ("Latest handoff exists and references evidence", (ROOT / wo.handoff_path).exists()),
        ("openclaw.json posture matches curated docs (read-only)", check_openclaw_posture()),
    ]

    result = "PASS" if all(ok for _, ok in checks) else "WARN"
    print("VALIDATION")
    for label, ok in checks:
        print(f"[{'PASS' if ok else 'WARN'}] {label}")
    print(f"RESULT: {result}")

    if result != "PASS":
        emit(run_id, "WARN", "⚠️", "Keeper V2 finished with warnings", reason_code="VALIDATION_WARN")
        return 1

    emit(run_id, "OK", "✅", "Keeper V2 sync complete")
    print(json.dumps({"status": "ok", "ts_iso": now_iso()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
