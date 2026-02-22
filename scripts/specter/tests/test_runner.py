import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts" / "specter" / "runner.py"
FIX = ROOT / "scripts" / "specter" / "tests" / "fixtures"


class TestSpecterRunnerBuild11(unittest.TestCase):
    def run_case(self, fixture_name: str):
        env = {**os.environ, "SPECTER_TEST_MODE": "1"}
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--request", str(FIX / fixture_name)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )
        self.assertTrue(proc.stdout.strip(), "runner should output JSON")
        payload = json.loads(proc.stdout.strip())
        return proc.returncode, payload

    def test_mock_ok(self):
        rc, payload = self.run_case("mock_ok.json")
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertIsNone(payload["error"])

    def test_needs_approval_blocked(self):
        rc, payload = self.run_case("needs_approval.json")
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["error"]["code"], "NEEDS_APPROVAL")

    def test_invalid_fail(self):
        rc, payload = self.run_case("invalid.json")
        self.assertEqual(rc, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
