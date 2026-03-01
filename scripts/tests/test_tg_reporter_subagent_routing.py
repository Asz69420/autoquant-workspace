#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.tg_reporter as tg_reporter


class TgReporterSubagentRoutingTests(unittest.TestCase):
    def test_subagent_finish_routes_to_log_chat_sender(self):
        event = {
            "run_id": "subagent-route-proof-1",
            "agent": "Oragorn",
            "action": "SUBAGENT_FINISH",
            "status_word": "OK",
            "reason_code": "PROOF",
            "summary": "proof terminal",
            "ts_iso": "2026-03-01T12:00:00Z",
            "model_id": "openai-codex/gpt-5.3-codex",
        }

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            r = R()
            if kwargs.get("text"):
                r.stdout = "ok"
                r.stderr = ""
            else:
                r.stdout = b"subagent routed"
                r.stderr = b""
            return r

        with patch.dict(os.environ, {"TELEGRAM_LOG_CHAT_ID": "-10042"}, clear=False):
            with patch("scripts.tg_reporter.subprocess.run", side_effect=fake_run):
                ok = tg_reporter.send_event_to_telegram(event)

        self.assertTrue(ok)
        notify_calls = [c for c in calls if any("tg_notify.py" in str(x) for x in c[0])]
        self.assertEqual(len(notify_calls), 1)
        notify_cmd, notify_kwargs = notify_calls[0]
        self.assertIn("--chat-id", notify_cmd)
        self.assertIn("-10042", notify_cmd)
        self.assertEqual(str(notify_kwargs.get("env", {}).get("TG_LOG_TEXT_ENABLED")), "1")

    def test_drain_once_sends_subagent_spawn_start_via_sender_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outbox = root / "outbox"
            outbox.mkdir(parents=True, exist_ok=True)
            actions = root / "actions.ndjson"
            errors = root / "errors.ndjson"

            event = {
                "run_id": "subagent-route-proof-2",
                "agent": "Oragorn",
                "action": "SUBAGENT_SPAWN",
                "status_word": "START",
                "status_emoji": "▶️",
                "reason_code": "SPAWN_START",
                "summary": "spawn proof",
                "ts_iso": "2026-03-01T12:01:00Z",
                "model_id": "openai-codex/gpt-5.3-codex",
                "inputs": [],
                "outputs": [],
                "attempt": None,
                "error": None,
            }
            fp = outbox / "20260301T120100Z___subagent-route-proof-2___Oragorn___START.json"
            fp.write_text(json.dumps(event), encoding="utf-8")

            sent_events = []

            def fake_send(ev):
                sent_events.append(ev)
                return True

            with patch.object(tg_reporter, "OUTBOX_DIR", outbox), \
                 patch.object(tg_reporter, "SPOOL_DIR", root / "spool"), \
                 patch.object(tg_reporter, "ACTIONS_LOG", actions), \
                 patch.object(tg_reporter, "ERRORS_LOG", errors), \
                 patch("scripts.tg_reporter.send_event_to_telegram", side_effect=fake_send):
                sent, skipped, failures = tg_reporter.drain_once(max_messages=20)

            self.assertEqual((sent, skipped, failures), (1, 0, 0))
            self.assertEqual(len(sent_events), 1)
            self.assertEqual(sent_events[0].get("action"), "SUBAGENT_SPAWN")
            self.assertFalse(fp.exists())
            lines = [ln for ln in actions.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]).get("action"), "SUBAGENT_SPAWN")


if __name__ == "__main__":
    unittest.main()
