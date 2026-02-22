#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "keeper" / "runner.py"


class KeeperFlowTests(unittest.TestCase):
    def test_runner_returns_json(self):
        env = {**os.environ}
        proc = subprocess.run([sys.executable, str(RUNNER)], cwd=str(ROOT), capture_output=True, text=True, env=env)
        self.assertTrue(proc.stdout.strip())
        payload = json.loads(proc.stdout.strip())
        self.assertIn(payload.get("status"), {"ok", "fail"})

    def test_idempotent_marker_behavior(self):
        from scripts.keeper.runner import append_promotions_idempotent

        base = "# M\n"
        name = "handoff-20260222-1234.md"
        bullets = ["A", "B"]
        first, added1 = append_promotions_idempotent(base, name, bullets)
        second, added2 = append_promotions_idempotent(first, name, bullets)
        self.assertGreaterEqual(added1, 1)
        self.assertEqual(added2, 0)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
