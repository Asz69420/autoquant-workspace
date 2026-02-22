import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts" / "specter" / "runner.py"
FIX = ROOT / "scripts" / "specter" / "tests" / "fixtures"


class TestSpecterRunnerVNext(unittest.TestCase):
    def run_request_obj(self, obj: dict, extra_env: dict | None = None):
        env = {**os.environ, "SPECTER_TEST_MODE": "1"}
        if extra_env:
            env.update(extra_env)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(obj, tf)
            p = tf.name
        try:
            proc = subprocess.run(
                [sys.executable, str(RUNNER), "--request", p],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                env=env,
            )
            self.assertTrue(proc.stdout.strip(), "runner should output JSON")
            payload = json.loads(proc.stdout.strip())
            return proc.returncode, payload
        finally:
            Path(p).unlink(missing_ok=True)

    def run_case(self, fixture_name: str, extra_env: dict | None = None):
        env = {**os.environ, "SPECTER_TEST_MODE": "1"}
        if extra_env:
            env.update(extra_env)
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
        self.assertEqual(payload["cache"]["key"], "mock")

    def test_cli_live_blocked_when_not_enabled(self):
        req = {
            "version": "v1",
            "trace_id": "t-cli",
            "request_id": "r-cli",
            "provider_target": "claude_cli",
            "model_request": "opencode/claude-opus-4-6",
            "prompt": "build it",
            "execution_mode": "cli_live",
            "routing_intent": "auto",
            "operator_profile": "default",
        }
        rc, payload = self.run_request_obj(req)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["error"]["code"], "NEEDS_APPROVAL")
        self.assertEqual(payload["cache"]["key"], "cli_live")

    def test_browser_live_blocked_when_not_enabled(self):
        req = {
            "version": "v1",
            "trace_id": "t-web",
            "request_id": "r-web",
            "provider_target": "claude_web",
            "model_request": "opus 4.6",
            "prompt": "do thing",
            "execution_mode": "browser_live",
            "routing_intent": "forced",
            "operator_profile": "safe",
        }
        rc, payload = self.run_request_obj(req)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["model_label"], "opencode/claude-opus-4-6")

    def test_invalid_profile_fail(self):
        req = {
            "version": "v1",
            "trace_id": "t-bad",
            "request_id": "r-bad",
            "provider_target": "claude_web",
            "model_request": "opencode/claude-opus-4-6",
            "prompt": "x",
            "execution_mode": "mock",
            "routing_intent": "auto",
            "operator_profile": "turbo",
        }
        rc, payload = self.run_request_obj(req)
        self.assertEqual(rc, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_invalid_fail_legacy_fixture(self):
        rc, payload = self.run_case("invalid.json")
        self.assertEqual(rc, 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
