#!/usr/bin/env python3
"""Auto-refresh Oragorn context docs from live system state.

Updates:
- agents/oragorn/agent/CONTEXT.md
- docs/claude-context/SESSION_CONTEXT.md (mirrored copy)

Behavior:
- Inject/refresh a live pipeline snapshot section
- Refresh Known Issues section from recent deterministic signals
- Add/refresh Roadmap Progress section
- Emit ActionEvent via scripts/log_event.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ACTIONS_PATH = ROOT / "data" / "logs" / "actions.ndjson"
LESSONS_PATH = ROOT / "data" / "logs" / "lessons.ndjson"
DOCTRINE_PATH = ROOT / "docs" / "DOCTRINE" / "analyser-doctrine.md"
ADVISORY_PATH = ROOT / "docs" / "claude-reports" / "STRATEGY_ADVISORY.md"
CONTEXT_PATH = ROOT / "agents" / "oragorn" / "agent" / "CONTEXT.md"
SESSION_CONTEXT_PATH = ROOT / "docs" / "claude-context" / "SESSION_CONTEXT.md"
LOG_EVENT = ROOT / "scripts" / "log_event.py"


def _read_ndjson_tail(path: Path, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: list[dict[str, Any]] = []
    for ln in lines[-max_lines:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def _extract_int(summary: str, pattern: str) -> int:
    m = re.search(pattern, summary or "")
    return int(m.group(1)) if m else 0


def _replace_section(md: str, heading_regex: str, new_block: str) -> str:
    # Replace from matching heading to next level-2 heading or EOF.
    pat = re.compile(rf"(?ms)^{heading_regex}.*?(?=^##\s|\Z)")
    if pat.search(md):
        return pat.sub(new_block.strip() + "\n\n", md, count=1)
    # If absent, append.
    return md.rstrip() + "\n\n" + new_block.strip() + "\n"


def _insert_before_heading(md: str, heading: str, block: str) -> str:
    idx = md.find(heading)
    if idx == -1:
        return md.rstrip() + "\n\n" + block.strip() + "\n"
    return md[:idx].rstrip() + "\n\n" + block.strip() + "\n\n" + md[idx:]


def _emit(status_word: str, reason_code: str, summary: str, outputs: list[str]) -> None:
    run_id = f"oragorn-context-sync-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    emoji = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status_word, "ℹ️")
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id",
        run_id,
        "--agent",
        "Oragorn",
        "--action",
        "CONTEXT_REFRESH",
        "--status-word",
        status_word,
        "--status-emoji",
        emoji,
        "--model-id",
        "gpt-5.3-codex",
        "--summary",
        summary,
        "--reason-code",
        reason_code,
        "--inputs",
        "data/logs/actions.ndjson",
        "data/logs/lessons.ndjson",
        "docs/DOCTRINE/analyser-doctrine.md",
        "docs/claude-reports/STRATEGY_ADVISORY.md",
        "--outputs",
        *outputs,
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=False)


def main() -> int:
    try:
        if not CONTEXT_PATH.exists():
            _emit("FAIL", "CONTEXT_MISSING", "Oragorn CONTEXT.md missing; sync skipped.", [])
            print("Missing CONTEXT.md", file=sys.stderr)
            return 2

        base_md = CONTEXT_PATH.read_text(encoding="utf-8", errors="ignore")
        actions = _read_ndjson_tail(ACTIONS_PATH, 400)
        lessons = _read_ndjson_tail(LESSONS_PATH, 200)

        recent = actions[-50:]
        fetched = executed = promoted = dvars = stall = starvation = errors = 0
        error_events = 0
        for e in recent:
            action = str(e.get("action", ""))
            summary = str(e.get("summary", ""))
            status = str(e.get("status_word", "")).upper()
            if action == "GRABBER_SUMMARY":
                fetched = max(fetched, _extract_int(summary, r"fetched=(\d+)"))
            elif action == "BATCH_BACKTEST_SUMMARY":
                executed = max(executed, _extract_int(summary, r"executed=(\d+)"))
            elif action == "PROMOTION_SUMMARY":
                promoted = max(promoted, _extract_int(summary, r"variants=(\d+)"))
            elif action == "DIRECTIVE_LOOP_SUMMARY":
                dvars = max(dvars, _extract_int(summary, r"directive_variants=(\d+)"))
            elif action == "DIRECTIVE_LOOP_STALL_WARN":
                stall = max(stall, _extract_int(summary, r"(\d+)\s*cycle"))
            elif action == "LAB_STARVATION_WARN":
                starvation = max(starvation, _extract_int(summary, r"(\d+)"))

            if status in {"FAIL", "BLOCKED"}:
                error_events += 1
            if action == "LAB_SUMMARY":
                errors = max(errors, _extract_int(summary, r"errors=(\d+)"))

        # Artifacts quick counts
        strategy_specs = len(list((ROOT / "artifacts" / "strategy_specs").glob("*.json"))) if (ROOT / "artifacts" / "strategy_specs").exists() else 0
        backtests = len(list((ROOT / "artifacts" / "backtests").glob("*.json"))) if (ROOT / "artifacts" / "backtests").exists() else 0
        bundles = len(list((ROOT / "artifacts" / "bundles").glob("*.json"))) if (ROOT / "artifacts" / "bundles").exists() else 0
        claude_specs = len(list((ROOT / "artifacts" / "claude-specs").glob("*.json"))) if (ROOT / "artifacts" / "claude-specs").exists() else 0

        # Lesson signals
        lesson_recent = lessons[-20:]
        reason_counter = Counter(str(x.get("reason_code", "")).strip() for x in lesson_recent if str(x.get("reason_code", "")).strip())
        top_reasons = [k for k, _ in reason_counter.most_common(3)]

        doctrine_lines = len(DOCTRINE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()) if DOCTRINE_PATH.exists() else 0
        advisory_lines = len(ADVISORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()) if ADVISORY_PATH.exists() else 0

        now_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        snapshot_block = f"""## Live Pipeline Snapshot (auto-updated)
Generated: {now_utc}

- Recent events window: last 50 ActionEvents
- Grabber fetched: {fetched}
- Backtests executed: {executed}
- Promoted variants: {promoted}
- Directive variants: {dvars}
- Stall cycles: {stall}
- Starvation cycles: {starvation}
- Error events: {max(errors, error_events)}

Artifact state:
- strategy_specs: {strategy_specs}
- backtests: {backtests}
- bundles: {bundles}
- claude-specs (staging): {claude_specs}
"""

        issues: list[str] = []
        if stall > 5:
            issues.append(f"Pipeline stall warning active ({stall} cycles).")
        if starvation > 10:
            issues.append(f"Pipeline starvation warning active ({starvation} cycles).")
        if max(errors, error_events) > 0:
            issues.append(f"Recent error signal detected ({max(errors, error_events)} event(s)).")
        if dvars == 0 and executed == 0:
            issues.append("No directive variants/backtests observed in the recent window.")
        for r in top_reasons:
            issues.append(f"Lesson pattern observed: {r}")
        if not issues:
            issues.append("No critical issues detected in the recent deterministic window.")

        issues_block = "## Known Issues (auto-updated)\n" + "\n".join(f"- {x}" for x in issues)

        phase1_ok = (ROOT / "config" / "model_reasoning_policy.json").exists() and (ROOT / "scripts" / "automation" / "resolve_model_policy.py").exists()
        phase2_refs = 0
        for py in (ROOT / "scripts").rglob("*.py"):
            try:
                txt = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "resolve_model_policy.py" in txt:
                phase2_refs += 1
        roadmap_block = f"""## Roadmap Progress (auto-updated)
- Model policy Phase 1 (policy + resolver + drift guard): {'✅ active' if phase1_ok else '⚠️ missing components'}
- Model policy Phase 2 (script wiring references): {phase2_refs} script(s) currently reference the resolver
- Oragorn context auto-sync: ✅ enabled (daily target 03:00)
- Doctrine source size: {doctrine_lines} lines
- Strategy advisory source size: {advisory_lines} lines
"""

        out_md = base_md

        # Snapshot near operational sections (before known issues)
        if re.search(r"(?m)^## Live Pipeline Snapshot \(auto-updated\)", out_md):
            out_md = _replace_section(out_md, r"## Live Pipeline Snapshot \(auto-updated\)", snapshot_block)
        else:
            out_md = _insert_before_heading(out_md, "## Known Issues", snapshot_block)

        out_md = _replace_section(out_md, r"## Known Issues(?: \(.*?\))?", issues_block)

        if re.search(r"(?m)^## Roadmap Progress \(auto-updated\)", out_md):
            out_md = _replace_section(out_md, r"## Roadmap Progress \(auto-updated\)", roadmap_block)
        else:
            out_md = _insert_before_heading(out_md, "## Roadmap", roadmap_block)

        # Basic validation
        required_headers = [
            "## Live Pipeline Snapshot (auto-updated)",
            "## Known Issues (auto-updated)",
            "## Roadmap Progress (auto-updated)",
        ]
        for h in required_headers:
            if h not in out_md:
                _emit("FAIL", "CONTEXT_VALIDATE_FAIL", f"Generated context missing required heading: {h}", [])
                print(f"Validation failed: {h}", file=sys.stderr)
                return 3

        changed = out_md != base_md
        if changed:
            backup = CONTEXT_PATH.with_suffix(f".bak-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.md")
            backup.write_text(base_md, encoding="utf-8")
            CONTEXT_PATH.write_text(out_md, encoding="utf-8")
            SESSION_CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
            SESSION_CONTEXT_PATH.write_text(out_md, encoding="utf-8")
            summary = (
                f"Context refreshed: fetched={fetched}, executed={executed}, promoted={promoted}, "
                f"stall={stall}, starvation={starvation}, errors={max(errors,error_events)}"
            )
            _emit(
                "OK",
                "CONTEXT_REFRESHED",
                summary,
                [
                    "agents/oragorn/agent/CONTEXT.md",
                    "docs/claude-context/SESSION_CONTEXT.md",
                ],
            )
        else:
            _emit("OK", "NOOP_CONTEXT_CURRENT", "Context refresh noop: no meaningful changes detected.", [])

        print("OK")
        return 0

    except Exception as e:  # pragma: no cover
        _emit("FAIL", "CONTEXT_SYNC_EXCEPTION", f"Context sync failed: {e}", [])
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
