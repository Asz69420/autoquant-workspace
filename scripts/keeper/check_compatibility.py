#!/usr/bin/env python3
"""Rule-based compatibility checks for Keeper Build 1."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check_text(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8", errors="ignore")


def run_checks() -> dict:
    findings: list[dict] = []

    agents_index = ROOT / "agents" / "index.md"
    telegram_runbook = ROOT / "docs" / "RUNBOOKS" / "telegram-logging.md"
    keeper_agent = ROOT / "agents" / "keeper.md"

    if not agents_index.exists():
        findings.append({"level": "FAIL", "reason_code": "MISSING_FILE", "message": "agents/index.md missing", "path": "agents/index.md"})
    else:
        idx_text = agents_index.read_text(encoding="utf-8", errors="ignore")
        if "data/logs/outbox/" not in idx_text:
            findings.append({"level": "WARN", "reason_code": "DRIFT_OUTBOX", "message": "agents/index.md missing outbox reference", "path": "agents/index.md"})

    if not check_text(telegram_runbook, "data/logs/outbox/"):
        findings.append({"level": "WARN", "reason_code": "DRIFT_OUTBOX", "message": "telegram runbook missing outbox reference", "path": "docs/RUNBOOKS/telegram-logging.md"})

    if keeper_agent.exists():
        kt = keeper_agent.read_text(encoding="utf-8", errors="ignore")
        if "sole authority" not in kt.lower() and "SOLE authority" not in kt:
            findings.append({"level": "WARN", "reason_code": "ROLE_DRIFT", "message": "Keeper authority wording unclear", "path": "agents/keeper.md"})
    else:
        findings.append({"level": "FAIL", "reason_code": "MISSING_FILE", "message": "agents/keeper.md missing", "path": "agents/keeper.md"})

    status = "ok"
    if any(f["level"] == "FAIL" for f in findings):
        status = "fail"
    elif findings:
        status = "warn"

    return {"status": status, "findings": findings}


def main() -> int:
    result = run_checks()
    print(json.dumps(result))
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
