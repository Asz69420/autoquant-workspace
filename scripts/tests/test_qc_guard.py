#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "qc_guard.py"


class QcGuardTests(unittest.TestCase):
    def run_guard(self, *args: str):
        return subprocess.run(
            [sys.executable, str(GUARD), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_missing_evidence_fails_closed(self):
        proc = self.run_guard("--stage", "proposal", "--require-evidence", "--run-id", "test-missing")
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload.get("gate_status"), "NOT_VERIFIED")

    def test_malformed_evidence_fails(self):
        proc = self.run_guard(
            "--stage",
            "proposal",
            "--require-evidence",
            "--evidence-json",
            "{bad json",
            "--run-id",
            "test-malformed",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload.get("gate_status"), "NOT_VERIFIED")

    def test_valid_evidence_passes(self):
        evidence = {
            "verifier_run_id": "vr-123",
            "verdict": "PASS",
            "summary": "clean pass",
        }
        proc = self.run_guard(
            "--stage",
            "proposal",
            "--require-evidence",
            "--evidence-json",
            json.dumps(evidence),
            "--run-id",
            "test-pass",
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload.get("gate_status"), "VERIFIED")

    def test_partials_require_blockers_or_fixes(self):
        evidence = {
            "verifier_run_id": "vr-124",
            "verdict": "PARTIAL",
            "summary": "has issues",
        }
        proc = self.run_guard(
            "--stage",
            "proposal",
            "--require-evidence",
            "--evidence-json",
            json.dumps(evidence),
            "--run-id",
            "test-partial",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload.get("gate_status"), "NOT_VERIFIED")

    def test_no_direct_telegram_or_ndjson_writes(self):
        source = GUARD.read_text(encoding="utf-8")
        banned_markers = ["tg_reporter", "tg_notify", "message send", "actions.ndjson", "errors.ndjson"]
        for marker in banned_markers:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
