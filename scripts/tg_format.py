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
        status_emoji = _as_str(event["status_emoji"])
        status_word = _as_str(event["status_word"])
        reason_code = _as_str(event.get("reason_code"), "")
        summary = _as_str(event["summary"])
        run_id = _as_str(event["run_id"])

        header_emoji = "⚙️" if _is_spawned_subagent_event(event) else status_emoji

        if reason_code:
            header = f"{header_emoji} {status_word} | {agent} | {model_label} ({reason_code})"
        else:
            header = f"{header_emoji} {status_word} | {agent} | {model_label}"

        summary_truncated = (summary[:47] + "...") if len(summary) > 50 else summary
        lines = [header, summary_truncated, f"Run: {run_id}"]
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
