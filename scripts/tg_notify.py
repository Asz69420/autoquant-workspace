#!/usr/bin/env python3
"""Send a message to Telegram using Bot API."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


TG_API = "https://api.telegram.org"


def load_env_fallback() -> None:
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
        return


def _append_action_event(reason_code: str, parse_mode: str, text_value: str) -> None:
    """Append debug/audit event to actions.ndjson only (never user-visible)."""
    try:
        logs_dir = Path.cwd() / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        actions_path = logs_dir / "actions.ndjson"
        ts = datetime.now(timezone.utc)
        event = {
            "ts_iso": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": f"tg-notify-{int(ts.timestamp())}",
            "agent": "Logger",
            "model_id": "system",
            "action": "TG_NOTIFY_PAYLOAD_DEBUG",
            "type": "LEADERBOARD_PAYLOAD_DEBUG",
            "debug": True,
            "status_word": "INFO",
            "status_emoji": "ℹ️",
            "reason_code": reason_code,
            "summary": "Telegram payload debug (leaderboard)",
            "inputs": [],
            "outputs": [f"parse_mode={parse_mode}", f"text_prefix={(text_value or '')[:30]}"],
            "attempt": None,
            "error": None,
        }
        with actions_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def send_message(chat_id: str, text: str, **kwargs) -> dict:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN env var not set")

    payload = {"chat_id": chat_id, "text": text}
    payload.update({k: v for k, v in kwargs.items() if v is not None})

    if "parse_mode" in payload and "entities" in payload:
        del payload["entities"]

    resp = requests.post(f"{TG_API}/bot{bot_token}/sendMessage", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _escape_html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unwrap_triple_backticks(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```") and t.endswith("```"):
        inner = t[3:-3]
        # Handle both LF and CRLF without altering internal formatting.
        if inner.startswith("\r\n"):
            inner = inner[2:]
        elif inner.startswith("\n"):
            inner = inner[1:]

        if inner.endswith("\r\n"):
            inner = inner[:-2]
        elif inner.endswith("\n"):
            inner = inner[:-1]
        return inner
    return t


def _append_send_audit(parse_mode: str, text_value: str) -> None:
    try:
        logs_dir = Path.cwd() / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        actions_path = logs_dir / "actions.ndjson"
        ts = datetime.now(timezone.utc)
        event = {
            "ts_iso": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": f"tg-audit-{int(ts.timestamp())}",
            "agent": "Logger",
            "model_id": "system",
            "action": "TG_SEND_AUDIT_LOG",
            "type": "TG_SEND_AUDIT_LOG",
            "debug": True,
            "status_word": "INFO",
            "status_emoji": "ℹ️",
            "reason_code": "TG_SEND_AUDIT_LOG",
            "summary": "Telegram send payload audit (log channel)",
            "inputs": [],
            "outputs": [f"parse_mode={parse_mode}", f"text_prefix={(text_value or '')[:10]}"],
            "attempt": None,
            "error": None,
        }
        with actions_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def send_telegram_message(
    message: str,
    chat_id: str | None = None,
    parse_mode: str | None = None,
    reason_code: str | None = None,
    command: str | None = None,
) -> bool:
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
    if not log_chat_id:
        raise ValueError("TELEGRAM_LOG_CHAT_ID env var not set")

    target_chat_id = chat_id if chat_id else log_chat_id

    if (reason_code or '').strip().upper().endswith('_DEBUG'):
        _append_action_event(str(reason_code or 'DEBUG'), str(parse_mode or 'NONE'), message)

    effective_parse_mode = parse_mode
    outbound_message = message
    msg_trim = (message or '').strip()
    if not effective_parse_mode and msg_trim.startswith('<pre>') and msg_trim.endswith('</pre>'):
        effective_parse_mode = 'HTML'

    # Log channel: keep existing content, but render monospace via HTML <pre> wrapper only.
    if str(target_chat_id) == str(log_chat_id):
        body = _unwrap_triple_backticks(outbound_message)
        outbound_message = f"<pre>{_escape_html(body)}</pre>"
        effective_parse_mode = 'HTML'
        _append_send_audit('HTML', outbound_message)

    try:
        send_message(target_chat_id, outbound_message, parse_mode=effective_parse_mode)
        return True
    except requests.exceptions.RequestException as e:
        raise Exception(f"Telegram API error: {e}")


def main():
    load_env_fallback()

    parser = argparse.ArgumentParser(description="Send a message to Telegram (default: log group).")
    parser.add_argument("message", help="Message to send")
    parser.add_argument("--chat-id", help="Override target chat ID (default: TELEGRAM_LOG_CHAT_ID).")
    parser.add_argument("--parse-mode", default=None, help="Telegram parse mode override.")
    parser.add_argument("--reason-code", help="Optional reason code for message-specific formatting.")
    parser.add_argument("--command", help="Optional command name for message-specific formatting.")
    args = parser.parse_args()

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("Error: TELEGRAM_BOT_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)
    if not os.getenv("TELEGRAM_LOG_CHAT_ID"):
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
