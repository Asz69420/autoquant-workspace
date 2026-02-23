#!/usr/bin/env python3
"""Dry verifier operational path checks (no live spawn side effects)."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT.parent / "openclaw.json"
OPENCLAW_BIN = shutil.which("openclaw") or shutil.which("openclaw.cmd") or "openclaw"


class VerifierAgentPathTests(unittest.TestCase):
    def test_config_has_verifier_agent(self):
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        agents = cfg.get("agents", {}).get("list", [])
        ids = {str(a.get("id", "")).strip() for a in agents}
        self.assertIn("verifier", ids)

    def test_main_allowlist_includes_verifier(self):
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        agents = cfg.get("agents", {}).get("list", [])
        main = next((a for a in agents if a.get("id") == "main"), {})
        allow = main.get("subagents", {}).get("allowAgents", [])
        self.assertIn("verifier", allow)

    def test_agents_list_tool_exposes_verifier(self):
        proc = subprocess.run(
            [OPENCLAW_BIN, "config", "get", "agents.list"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        ids = {str(a.get("id", "")).strip() for a in payload}
        self.assertIn("verifier", ids)


if __name__ == "__main__":
    unittest.main()
