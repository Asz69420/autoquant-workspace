#!/usr/bin/env python3
"""Send a message to Telegram using Bot API with proper formatting."""
import os
import sys
import argparse
from pathlib import Path
import requests
import json
from datetime import datetime, timezone


def load_env_fallback() -> None:
    """Load TELEGRAM_* vars from .env when process env is missing (e.g., SYSTEM task)."""
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_LOG_CHAT_ID"):
        return

    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    try:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_LOG_CHAT_ID", "TELEGRAM_CMD_CHAT_ID"} and not os.getenv(k):
                os.environ[k] = v
    except Exception:
        # Silent fallback: caller handles missing vars explicitly.
        return


def _append_action_event(reason_code: str, parse_mode: str, text_value: str, used_pre_entities: bool = False) -> None:
    """Append lightweight debug event to actions.ndjson (never user-visible)."""
    try:
        logs_dir = Path.cwd() / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        actions_path = logs_dir / "actions.ndjson"
        ts = datetime.now(timezone.utc)
        prefix = (text_value or "")[:30]
        event = {
            "ts_iso": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": f"tg-notify-{int(ts.timestamp())}",
            "agent": "Logger",
            "model_id": "system",
            "action": "TG_NOTIFY_PAYLOAD_DEBUG",
            "status_word": "INFO",
            "status_emoji": "ℹ️",
            "reason_code": reason_code,
            "summary": "Telegram payload debug (leaderboard)",
            "inputs": [],
            "outputs": [f"parse_mode={parse_mode}", f"text_prefix={prefix}", f"entities_pre={str(used_pre_entities).lower()}"],
            "attempt": None,
            "error": None,
        }
        with actions_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def send_telegram_message(
    message: str,
    chat_id: str = None,
    parse_mode: str = "MarkdownV2",
    reason_code: str | None = None,
    command: str | None = None,
) -> bool:
    """Send a message to Telegram Bot API with configurable formatting."""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN env var not set")
    if not log_chat_id:
        raise ValueError("TELEGRAM_LOG_CHAT_ID env var not set")

    target_chat_id = chat_id if chat_id else log_chat_id

    reason = (reason_code or "").strip().upper()
    cmd = (command or "").strip().lower()
    final_mode = parse_mode
    final_text = message

    looks_like_leaderboard = ("TF  P&L" in message) and any(
        token in message for token in ("BTC ", "ETH ", "SOL ")
    )
    is_leaderboard = reason == "LEADERBOARD" or cmd == "leaderboard" or looks_like_leaderboard

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    if is_leaderboard:
        payload = {
            "chat_id": target_chat_id,
            "text": final_text,
            "entities": [{"type": "pre", "offset": 0, "length": len(final_text)}],
        }
        _append_action_event("LEADERBOARD_PAYLOAD_DEBUG", "NONE", final_text, used_pre_entities=True)
    else:
        payload = {
            "chat_id": target_chat_id,
            "text": final_text,
            "parse_mode": final_mode,
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        raise Exception(f"Telegram API error: {e}")


def main():
    load_env_fallback()

    parser = argparse.ArgumentParser(
        description="Send a message to Telegram (default: log group)."
    )
    parser.add_argument("message", help="Message to send")
    parser.add_argument(
        "--chat-id",
        help="Override target chat ID (default: TELEGRAM_LOG_CHAT_ID). Use for Commander/testing only."
    )
    parser.add_argument(
        "--parse-mode",
        default="MarkdownV2",
        help="Telegram parse mode override (default: MarkdownV2)."
    )
    parser.add_argument(
        "--reason-code",
        help="Optional reason code for message-specific formatting rules (e.g. LEADERBOARD)."
    )
    parser.add_argument(
        "--command",
        help="Optional command name for message-specific formatting rules (e.g. leaderboard)."
    )

    args = parser.parse_args()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
    
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)
    
    if not log_chat_id:
        print("Error: TELEGRAM_LOG_CHAT_ID env var not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        send_telegram_message(
            args.message,
            args.chat_id,
            parse_mode=args.parse_mode,
            reason_code=args.reason_code,
            command=args.command,
        )
        print("✓ Message sent to Telegram", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
