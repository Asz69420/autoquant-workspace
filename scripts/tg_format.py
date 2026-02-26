#!/usr/bin/env python3
"""Convert ActionEvent JSON to Telegram message (strict fixed mono layout)."""
import json
import sys
from typing import Any

# Force UTF-8 IO on Windows
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


def to_model_label(model_id: str) -> str:
    known = {
        "openai-codex/gpt-5.3-codex": "codex 5.3",
        "opencode/claude-opus-4-6": "opus 4.6",
        "anthropic/claude-sonnet-4-6": "sonnet 4.6",
        "anthropic/claude-haiku-4-5-20251001": "haiku 4.5",
    }
    if model_id in known:
        return known[model_id]
    if model_id in {"system", "build1-mock"}:
        return model_id
    short = model_id.split("/")[-1]
    short = short.replace("gpt-", "").replace("claude-", "")
    short = short.replace("-", " ").strip()
    return short if short else model_id


def _normalize_status_emoji(status_emoji: str, status_word: str) -> str:
    se = _as_str(status_emoji, "").strip()
    sw = _as_str(status_word, "").upper()
    fallback = STATUS_EMOJI_FALLBACK.get(sw, "ℹ️")

    if (not se) or (se.upper() == sw) or (se == "️"):
        return fallback
    if se in STATUS_EMOJI_FALLBACK.values():
        return se
    return fallback


def _normalize_timestamp(ts_local: str, ts_iso: str) -> str:
    t = (ts_local or "").strip()
    if t:
        return t.replace(" AEST", "")
    return (ts_iso or "").strip() or "(timestamp unavailable)"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("event_path", nargs="?", default=None, help="Path to event.json file")
    args = parser.parse_args()

    try:
        if args.event_path:
            with open(args.event_path, "r", encoding="utf-8") as f:
                event = json.load(f)
        else:
            raw = sys.stdin.read()
            event = json.loads(raw)

        agent = _as_str(event["agent"])
        model_id = _as_str(event["model_id"])
        model_label = to_model_label(model_id)
        status_word = _as_str(event["status_word"])
        status_emoji = _normalize_status_emoji(event.get("status_emoji"), status_word)
        reason_code = _as_str(event.get("reason_code"), "")
        summary = _as_str(event["summary"])
        ts_local = _as_str(event.get("ts_local"), "")
        ts_iso = _as_str(event.get("ts_iso"), "")

        display_agent = 'Lab' if _as_str(reason_code) == 'AUTOPILOT_SUMMARY' else agent
        agent_display = f"{AGENT_EMOJI.get(display_agent, AGENT_EMOJI.get(agent, ''))} {display_agent}".strip()

        show_reason = bool(reason_code) and reason_code.upper() != "EXPERIMENT"
        status_text = f"{status_emoji} {status_word}"

        header = f"{agent_display} | {status_text}"
        if show_reason:
            detail = f"({reason_code}) — {summary}"
        else:
            detail = summary

        # Strict fixed layout (2 lines): header, reason+summary (reason on line 2)
        body = "\n".join([header, detail])
        telegram_msg = f"```\n{body}\n```"

        print(telegram_msg)
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
