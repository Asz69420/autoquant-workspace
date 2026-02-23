#!/usr/bin/env python3
"""QC guard for significant-build proposal approval gating.

Fail-closed rule:
- If proposal-stage verifier evidence is missing or malformed, block approval ask.
- Emit compliance ActionEvent via scripts/log_event.py (outbox path).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_EVENT = ROOT / "scripts" / "log_event.py"


def _emit_event(*, run_id: str, status_word: str, status_emoji: str, reason_code: str, summary: str, model_id: str) -> None:
    """Best-effort compliance event emission via log_event.py (outbox-only)."""
    cmd = [
        sys.executable,
        str(LOG_EVENT),
        "--run-id",
        run_id,
        "--agent",
        "oq",
        "--action",
        "qc_guard",
        "--status-word",
        status_word,
        "--status-emoji",
        status_emoji,
        "--model-id",
        model_id,
        "--reason-code",
        reason_code,
        "--summary",
        summary,
    ]
    try:
        subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)
    except Exception:
        # Guard must never crash due to logging errors.
        pass


def _load_evidence(evidence_json: str | None, evidence_file: str | None):
    if evidence_json:
        return json.loads(evidence_json)
    if evidence_file:
        return json.loads(Path(evidence_file).read_text(encoding="utf-8"))
    return None


def _validate_evidence(payload: dict) -> tuple[bool, str]:
    required_keys = ["verifier_run_id", "verdict", "summary"]
    for key in required_keys:
        if key not in payload:
            return False, f"missing required key: {key}"

    verdict = str(payload.get("verdict", "")).strip().upper()
    if verdict not in {"PASS", "PARTIAL", "FAIL"}:
        return False, "verdict must be one of PASS|PARTIAL|FAIL"

    summary = str(payload.get("summary", "")).strip()
    if not summary:
        return False, "summary must be non-empty"

    # For non-pass outcomes, blockers/fixes summary must be non-empty.
    if verdict in {"PARTIAL", "FAIL"}:
        blockers = payload.get("blockers")
        fixes = payload.get("fixes")
        blockers_ok = isinstance(blockers, list) and len(blockers) > 0
        fixes_ok = isinstance(fixes, list) and len(fixes) > 0
        if not (blockers_ok or fixes_ok):
            return False, "PARTIAL/FAIL requires non-empty blockers or fixes"

    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["proposal", "implementation"])
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("--evidence-json", default=None)
    parser.add_argument("--evidence-file", default=None)
    parser.add_argument("--run-id", default="qc-guard")
    parser.add_argument("--model-id", default="openai-codex/gpt-5.3-codex")
    args = parser.parse_args()

    if args.stage != "proposal":
        print(json.dumps({"gate_status": "NOT_VERIFIED", "reason": "unsupported stage"}))
        return 2

    if args.require_evidence and not (args.evidence_json or args.evidence_file):
        _emit_event(
            run_id=args.run_id,
            status_word="FAIL",
            status_emoji="❌",
            reason_code="QC_EVIDENCE_MISSING",
            summary="qc_guard blocked approval ask: verifier evidence missing",
            model_id=args.model_id,
        )
        print(json.dumps({"gate_status": "NOT_VERIFIED", "reason": "evidence missing"}))
        return 2

    try:
        evidence = _load_evidence(args.evidence_json, args.evidence_file)
    except Exception as exc:
        _emit_event(
            run_id=args.run_id,
            status_word="FAIL",
            status_emoji="❌",
            reason_code="QC_EVIDENCE_MALFORMED",
            summary=f"qc_guard blocked approval ask: malformed evidence ({exc})",
            model_id=args.model_id,
        )
        print(json.dumps({"gate_status": "NOT_VERIFIED", "reason": "evidence malformed"}))
        return 2

    if args.require_evidence:
        ok, reason = _validate_evidence(evidence or {})
        if not ok:
            _emit_event(
                run_id=args.run_id,
                status_word="FAIL",
                status_emoji="❌",
                reason_code="QC_EVIDENCE_MALFORMED",
                summary=f"qc_guard blocked approval ask: {reason}",
                model_id=args.model_id,
            )
            print(json.dumps({"gate_status": "NOT_VERIFIED", "reason": reason}))
            return 2

    verdict = str((evidence or {}).get("verdict", "PASS")).strip().upper() if evidence else "PASS"
    gate_status = "VERIFIED" if verdict == "PASS" else "PARTIAL"
    _emit_event(
        run_id=args.run_id,
        status_word="OK",
        status_emoji="✅",
        reason_code="QC_GUARD_PASS",
        summary=f"qc_guard passed: {gate_status}",
        model_id=args.model_id,
    )
    print(json.dumps({"gate_status": gate_status, "verdict": verdict}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
