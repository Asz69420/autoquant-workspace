#!/usr/bin/env python3
"""Send a message to Telegram using Bot API with proper formatting."""
import os
import sys
import argparse
from pathlib import Path
import requests


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


def send_telegram_message(message: str, chat_id: str = None) -> bool:
    """Send a message to Telegram Bot API with MarkdownV2 formatting."""
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN env var not set")
    if not log_chat_id:
        raise ValueError("TELEGRAM_LOG_CHAT_ID env var not set")
    
    target_chat_id = chat_id if chat_id else log_chat_id
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": message,
        "parse_mode": "MarkdownV2"
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
        send_telegram_message(args.message, args.chat_id)
        print("✓ Message sent to Telegram", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
