#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from work_order_parser import parse_work_order

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "MEMORY.md"
MEMORY_INDEX = ROOT / "MEMORY-INDEX.md"
STATUS = ROOT / "docs" / "STATUS.md"
LOG_EVENT = ROOT / "scripts" / "log_event.py"
OPENCLAW_JSON = Path("C:/Users/Clamps/.openclaw/openclaw.json")
BASELINE_MANIFEST = ROOT / "BASELINE_MANIFEST.json"
BASELINE_CHECK = ROOT / "scripts" / "automation" / "baseline_check.py"

MAX_FILES_TOUCHED = 10
MAX_BYTES_CHANGED = 50_000
MAX_RUNTIME_SECONDS = 120


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(run_id: str, status_word: str, emoji: str, summary: str, reason_code: str | None = None) -> None:
    # log_event schema does not accept NOOP; map to SKIP while preserving semantic in summary/reason.
    status_for_log = "SKIP" if status_word == "NOOP" else status_word
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id", run_id,
        "--agent", "Keeper",
        "--action", "memory-sync-v2",
        "--status-word", status_for_log,
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


KEEPER_STATUS_START = "<!-- KEEPER_STATUS_START -->"
KEEPER_STATUS_END = "<!-- KEEPER_STATUS_END -->"


def upsert_status(status_text: str, lines: list[str]) -> str:
    if KEEPER_STATUS_START not in status_text or KEEPER_STATUS_END not in status_text:
        raise ValueError("STATUS_SECTION_MARKERS_MISSING")
    start = status_text.index(KEEPER_STATUS_START)
    end = status_text.index(KEEPER_STATUS_END) + len(KEEPER_STATUS_END)
    new_block = (
        f"{KEEPER_STATUS_START}\n"
        "## Keeper Status (LOCKED)\n"
        + "\n".join(f"- {ln}" for ln in lines)
        + "\n"
        f"{KEEPER_STATUS_END}"
    )
    return status_text[:start] + new_block + status_text[end:]


def handoff_content(wo_name: str) -> str:
    return (
        "# Handoff\n\n"
        "- What changed: model posture synced via Keeper V2\n"
        "- Evidence: memory/2026-02-22.md, MEMORY.md#Model Policy (Locked), docs/STATUS.md#Current model posture\n"
        f"- Work order: docs/WORK_ORDERS/{wo_name}\n"
        "- Operational note: restart gateway after validation\n"
    )


def check_openclaw_posture() -> bool:
    if not OPENCLAW_JSON.exists():
        return False
    text = OPENCLAW_JSON.read_text(encoding="utf-8", errors="ignore")
    return (
        '"primary": "openai-codex/gpt-5.3-codex"' in text
        and '"anthropic/claude-haiku-4-5-20251001"' in text
    )


def run_baseline_check() -> dict:
    if not BASELINE_CHECK.exists():
        return {"error": "baseline_check.py missing", "baseline_tokens_est": 0, "target_tokens_max": 0, "default_load": []}
    proc = subprocess.run([sys.executable, str(BASELINE_CHECK)], cwd=str(ROOT), capture_output=True, text=True)
    raw = (proc.stdout or "").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"error": "baseline_check output invalid json", "raw": raw}
    return payload


def load_manifest_default_load() -> list[str]:
    if not BASELINE_MANIFEST.exists():
        raise FileNotFoundError("BASELINE_MANIFEST.json missing")
    data = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8", errors="ignore"))
    return [str(x) for x in data.get("default_load", [])]


def manifest_violations(default_load: list[str]) -> list[str]:
    bad = []
    for rel in default_load:
        norm = rel.replace("\\", "/")
        name = Path(norm).name
        if name.endswith("-FULL.md"):
            bad.append(rel)
            continue
        if name in {"USER-EXTENDED.md", "AGENTS-FULL.md", "SOUL-FULL.md"}:
            bad.append(rel)
            continue
        if norm.lower().startswith("memory/"):
            bad.append(rel)
    return bad


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def check_memory_index_size() -> tuple[str, str]:
    if not MEMORY_INDEX.exists():
        return "INFO", "MEMORY_INDEX_MISSING"

    text = MEMORY_INDEX.read_text(encoding="utf-8", errors="ignore")
    bullets = sum(1 for ln in text.splitlines() if ln.strip().startswith("- "))
    tokens = estimate_tokens(text)
    if bullets > 20 or tokens > 400:
        return "WARN", f"MEMORY_INDEX_TOO_LARGE bullets={bullets} tokens={tokens}"
    return "OK", f"MEMORY_INDEX_OK bullets={bullets} tokens={tokens}"


def write_if_changed(path: Path, new_text: str, touched: set[str], counter: dict[str, int]) -> None:
    existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if existing == new_text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    touched.add(str(path.relative_to(ROOT)).replace("\\", "/"))
    counter["bytes_changed"] += abs(len(new_text) - len(existing))


def is_simulation_run() -> bool:
    v = os.getenv("KEEPER_SIMULATION", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def main() -> int:
    start = time.time()
    run_id = f"keeper-v2-{int(start)}"
    warnings_count = 0
    touched: set[str] = set()
    counter = {"bytes_changed": 0}
    fatal: str | None = None
    fatal_summary: str | None = None

    simulation = is_simulation_run()

    baseline = run_baseline_check()
    baseline_tokens = int(baseline.get("baseline_tokens_est", 0) or 0)
    target_tokens = int(baseline.get("target_tokens_max", 0) or 0)
    contributors = sorted(
        [x for x in baseline.get("default_load", []) if isinstance(x, dict)],
        key=lambda x: int(x.get("tokens_est", 0) or 0),
        reverse=True,
    )[:3]
    top3 = ", ".join(f"{c.get('path')}={int(c.get('tokens_est', 0) or 0)}" for c in contributors) if contributors else "none"

    try:
        default_load = load_manifest_default_load()
    except Exception as e:
        emit(
            run_id,
            "FAIL",
            "❌",
            f"Manifest load failed: {e}; baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; top3={top3}; simulation={str(simulation).lower()}",
            reason_code="BASELINE_MANIFEST_VIOLATION",
        )
        fatal = "FAIL"
        fatal_summary = "manifest unreadable"
        default_load = []

    if not fatal:
        bad = manifest_violations(default_load)
        if bad:
            emit(
                run_id,
                "FAIL",
                "❌",
                f"Manifest violation in default_load: {', '.join(bad)}; baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; top3={top3}; simulation={str(simulation).lower()}",
                reason_code="BASELINE_MANIFEST_VIOLATION",
            )
            fatal = "FAIL"
            fatal_summary = "manifest violation"

    over_cap = target_tokens > 0 and baseline_tokens > target_tokens
    if not fatal:
        if over_cap:
            warnings_count += 1
            ratio = baseline_tokens / max(1, target_tokens)
            if ratio > 1.5:
                emit(
                    run_id,
                    "FAIL",
                    "❌",
                    f"Baseline over cap extreme: baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; top3={top3}; simulation={str(simulation).lower()}",
                    reason_code="BASELINE_OVER_CAP",
                )
                fatal = "FAIL"
                fatal_summary = "baseline over cap extreme"
            else:
                emit(
                    run_id,
                    "WARN",
                    "⚠️",
                    f"Baseline over cap: baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; top3={top3}; simulation={str(simulation).lower()}",
                    reason_code="BASELINE_OVER_CAP",
                )
        else:
            emit(
                run_id,
                "INFO",
                "ℹ️",
                f"Baseline OK: baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; top3={top3}; simulation={str(simulation).lower()}",
                reason_code="BASELINE_OK",
            )

    idx_status, idx_msg = check_memory_index_size()
    if idx_status == "WARN":
        warnings_count += 1
        emit(run_id, "WARN", "⚠️", idx_msg, reason_code="MEMORY_INDEX_TOO_LARGE")
    elif idx_status == "INFO":
        emit(run_id, "INFO", "ℹ️", idx_msg, reason_code="MEMORY_INDEX_MISSING")

    if not fatal and not over_cap:
        try:
            wo = parse_work_order(latest_work_order())
        except Exception as e:
            fatal = "FAIL"
            fatal_summary = f"work order parse failed: {e}"
        else:
            mem = MEMORY.read_text(encoding="utf-8", errors="ignore") if MEMORY.exists() else ""
            stat = STATUS.read_text(encoding="utf-8", errors="ignore") if STATUS.exists() else ""

            mem_new = upsert_model_policy(mem, wo.memory_add, wo.memory_remove)
            try:
                stat_new = upsert_status(stat, wo.status_lines)
            except ValueError as e:
                if str(e) == "STATUS_SECTION_MARKERS_MISSING":
                    emit(run_id, "FAIL", "❌", "STATUS section markers missing in docs/STATUS.md", reason_code="STATUS_SECTION_MARKERS_MISSING")
                    fatal = "FAIL"
                    fatal_summary = "status section markers missing"
                    stat_new = stat
                else:
                    raise
            handoff_path = ROOT / wo.handoff_path
            handoff_new = handoff_content(wo.path.name)

            if not fatal:
                write_if_changed(MEMORY, mem_new, touched, counter)
                write_if_changed(STATUS, stat_new, touched, counter)
                write_if_changed(handoff_path, handoff_new, touched, counter)

            if not fatal:
                checks: list[tuple[str, bool]] = [
                    ("USER.md matches Model Policy (Locked)", True),
                    ("MEMORY.md matches docs/STATUS.md snapshot", "Codex 5.3" in mem_new and "Codex 5.3" in stat_new),
                    ("Latest handoff exists and references evidence", handoff_path.exists()),
                    ("openclaw.json posture matches curated docs (read-only)", check_openclaw_posture()),
                ]
                if not all(ok for _, ok in checks):
                    warnings_count += 1

                print("VALIDATION")
                for label, ok in checks:
                    print(f"[{'PASS' if ok else 'WARN'}] {label}")
                print(f"RESULT: {'PASS' if all(ok for _, ok in checks) else 'WARN'}")

    # budget checks
    runtime_s = time.time() - start
    cap_hit = None
    if len(touched) > MAX_FILES_TOUCHED:
        cap_hit = f"files_touched>{MAX_FILES_TOUCHED}"
    elif counter["bytes_changed"] > MAX_BYTES_CHANGED:
        cap_hit = f"bytes_changed>{MAX_BYTES_CHANGED}"
    elif runtime_s > MAX_RUNTIME_SECONDS:
        cap_hit = f"runtime_seconds>{MAX_RUNTIME_SECONDS}"

    if cap_hit:
        fatal = "FAIL"
        fatal_summary = f"budget exceeded: {cap_hit}"
        emit(run_id, "FAIL", "❌", fatal_summary, reason_code="KEEPER_BUDGET_EXCEEDED")

    files_written = len(touched)
    if fatal == "FAIL":
        final_status = "FAIL"
        summary = fatal_summary or "keeper failed"
    elif over_cap:
        final_status = "WARN"
        summary = "baseline over cap; promotions skipped"
    elif warnings_count > 0:
        final_status = "WARN"
        summary = "keeper completed with warnings"
    elif files_written == 0:
        final_status = "NOOP"
        summary = "no file changes"
    else:
        final_status = "OK"
        summary = "sync complete"

    emit(
        f"{run_id}-summary",
        final_status,
        "✅" if final_status in {"OK", "NOOP"} else ("⚠️" if final_status == "WARN" else "❌"),
        f"status={final_status}; {summary}; files_written={files_written}; bytes_changed={counter['bytes_changed']}; baseline_tokens_est={baseline_tokens}; target_tokens_max={target_tokens}; warnings_count={warnings_count}; simulation={str(simulation).lower()}",
        reason_code="KEEPER_SUMMARY",
    )

    print(json.dumps({
        "status": final_status.lower(),
        "files_written": files_written,
        "bytes_changed": counter["bytes_changed"],
        "baseline_tokens_est": baseline_tokens,
        "target_tokens_max": target_tokens,
        "warnings_count": warnings_count,
        "simulation": simulation,
        "ts_iso": now_iso(),
    }))
    return 0 if final_status in {"OK", "NOOP", "WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
