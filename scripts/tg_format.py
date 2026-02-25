#!/usr/bin/env python3
"""Convert ActionEvent JSON to single-line Telegram message."""
import json
import re
import sys
from typing import Any

try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

STATUS_EMOJI_FALLBACK = {
    "OK": "✅",
    "WARN": "⚠️",
    "FAIL": "❌",
}

AGENT_EMOJI = {
    "òQ": "🤖",
    "oQ": "🤖",
    "oq": "🤖",
    "Logger": "🧾",
    "Reader": "🔗",
    "Grabber": "🧲",
    "TV Catalog": "📤",
    "Promotion": "🧠",
    "Backtester": "📈",
    "Refinement": "🔁",
    "Librarian": "📚",
    "Strategist": "🧠",
    "Keeper": "🗃️",
    "Firewall": "🛡️",
    "Scheduler": "⏱️",
    "Specter": "🎭",
}


def _as_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v)


def _normalize_status_word(status_word: str) -> str:
    sw = _as_str(status_word, "").upper().strip()
    if sw not in {"OK", "WARN", "FAIL"}:
        return "OK"
    return sw


def _normalize_status_emoji(status_emoji: str, status_word: str) -> str:
    sw = _normalize_status_word(status_word)
    se = _as_str(status_emoji, "").strip()
    if se in STATUS_EMOJI_FALLBACK.values():
        return se
    return STATUS_EMOJI_FALLBACK.get(sw, "✅")


def _clean_one_line(text: str) -> str:
    t = _as_str(text, "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def render_one_line(event: dict) -> str:
    agent = _clean_one_line(event.get("agent", "Unknown")) or "Unknown"
    agent_emoji = AGENT_EMOJI.get(agent, "🤖")

    status_word = _normalize_status_word(event.get("status_word", "OK"))
    status_emoji = _normalize_status_emoji(event.get("status_emoji", ""), status_word)

    reason_code = _clean_one_line(event.get("reason_code", "")) or "NO_REASON"
    summary = _clean_one_line(event.get("summary", "")) or "Completed"

    return f"{agent_emoji} {agent} | {status_emoji} {status_word} ({reason_code}) — {summary}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("event_path", nargs="?", default=None)
    args = parser.parse_args()

    try:
        if args.event_path:
            with open(args.event_path, "r", encoding="utf-8") as f:
                event = json.load(f)
        else:
            event = json.loads(sys.stdin.read())

        print(render_one_line(event))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
