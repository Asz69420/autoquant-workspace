#!/usr/bin/env python3
"""Convert ActionEvent JSON to Telegram message (triple backticks)."""
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


NAMED_AGENTS = {
    "òQ", "oQ", "oq",
    "Keeper", "Specter", "Reader", "Grabber", "Strategist",
    "Backtester", "Firewall", "Scheduler", "Logger",
}

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


def _maybe_fix_mojibake(text: str) -> str:
    """Best-effort fix for UTF-8 text accidentally decoded as cp1252/latin1."""
    if not isinstance(text, str):
        return text
    if any(ch in text for ch in ("Ã", "â", "œ", "�")):
        try:
            return text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore") or text
        except Exception:
            return text
    return text


def _as_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return _maybe_fix_mojibake(str(v))


def to_model_label(model_id: str) -> str:
    """Return short human-friendly model label for Telegram logs."""
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
    """Return a sane emoji; repair malformed values like status_emoji='START'."""
    se = _as_str(status_emoji, "").strip()
    sw = _as_str(status_word, "").upper()

    fallback = STATUS_EMOJI_FALLBACK.get(sw, "ℹ️")

    # If missing, textual token, lone variation selector, or clearly mojibake -> fallback.
    if (not se) or (se.upper() == sw) or (se == "️") or any(ch in se for ch in ("Ã", "â", "�")):
        return fallback

    # If the provided emoji is one of our known status emojis, keep it; otherwise normalize.
    if se in STATUS_EMOJI_FALLBACK.values():
        return se

    return fallback


def _is_spawned_subagent_event(event: dict) -> bool:
    """Cogwheel is ONLY for spawned task sub-agents, never named system agents."""
    agent = _as_str(event.get("agent", ""))
    if agent in NAMED_AGENTS:
        return False

    tags = event.get("tags") or []
    tags_l = {str(t).lower() for t in tags if t is not None}
    if "subagent" in tags_l or "work-order" in tags_l or "delegated" in tags_l:
        return True

    run_id = _as_str(event.get("run_id", "")).lower()
    return run_id.startswith("subagent-")


def _fit_summary_mobile(summary: str, max_lines: int = 3, max_line_len: int = 72) -> str:
    """Keep summary readable on mobile: up to max_lines, wrap long lines, no ellipsis."""
    if not summary:
        return ""

    words = summary.replace("\r", "").replace("\t", " ").split()
    if not words:
        return ""

    lines = []
    current = ""
    for w in words:
        candidate = (current + " " + w).strip()
        if len(candidate) <= max_line_len:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    return "\n".join(lines[:max_lines])


def _normalize_timestamp(ts_local: str, ts_iso: str) -> str:
    """Prefer ts_local but remove timezone suffix text like ' AEST'."""
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

        is_subagent = _is_spawned_subagent_event(event)

        agent_display = f"{AGENT_EMOJI.get(agent, '')} {agent}".strip()
        if is_subagent:
            agent_display = f"⚙️ {agent_display}".strip()

        show_reason = bool(reason_code) and reason_code.upper() != "EXPERIMENT"
        status_text = f"{status_emoji} {status_word}"
        if show_reason:
            status_text = f"{status_text} ({reason_code})"

        header = f"{agent_display} | {model_label} | {status_text}"

        summary_mobile = _fit_summary_mobile(summary, max_lines=3, max_line_len=72)
        timestamp_line = _normalize_timestamp(ts_local, ts_iso)
        lines = [header, summary_mobile, timestamp_line]
        body = "\n".join(lines)
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
