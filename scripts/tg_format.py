#!/usr/bin/env python3
"""Convert ActionEvent JSON to legacy single-line Telegram message."""
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
    "START": "▶️",
    "OK": "✅",
    "WARN": "⚠️",
    "FAIL": "❌",
    "BLOCKED": "⛔",
    "INFO": "ℹ️",
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


def _clean_one_line(text: str) -> str:
    return re.sub(r"\s+", " ", _as_str(text, "")).strip()


def to_model_label(model_id: str) -> str:
    known = {
        "openai-codex/gpt-5.3-codex": "codex 5.3",
        "opencode/claude-opus-4-6": "opus 4.6",
        "anthropic/claude-sonnet-4-6": "sonnet 4.6",
        "anthropic/claude-haiku-4-5-20251001": "haiku 4.5",
    }
    if model_id in known:
        return known[model_id]
    short = model_id.split("/")[-1].replace("-", " ").replace("gpt", "gpt").replace("claude", "").strip()
    return _clean_one_line(short) or _clean_one_line(model_id)


def render_one_line(event: dict) -> str:
    agent = _clean_one_line(event.get("agent", "Unknown")) or "Unknown"
    agent_emoji = AGENT_EMOJI.get(agent, "🤖")

    status_word = _clean_one_line(event.get("status_word", "INFO")).upper()
    status_emoji = _clean_one_line(event.get("status_emoji", ""))
    if not status_emoji or status_emoji.upper() == status_word:
        status_emoji = STATUS_EMOJI_FALLBACK.get(status_word, "ℹ️")

    reason_code = _clean_one_line(event.get("reason_code", ""))
    reason_suffix = f" ({reason_code})" if reason_code else ""

    summary = _clean_one_line(event.get("summary", ""))
    model_label = to_model_label(_clean_one_line(event.get("model_id", "")))

    ts_local = _clean_one_line(event.get("ts_local", ""))
    if ts_local.endswith(" AEST"):
        ts_local = ts_local[:-5]

    parts = [
        f"{agent_emoji} {agent}",
        model_label,
        f"{status_emoji} {status_word}{reason_suffix}",
    ]
    if summary:
        parts.append(summary)
    if ts_local:
        parts.append(ts_local)

    return " | ".join(parts[:3]) + (" " + " ".join(parts[3:]) if len(parts) > 3 else "")


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
