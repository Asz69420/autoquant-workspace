#!/usr/bin/env python3
"""
Send a message to Telegram using environment variables.

This is a generic sender. By default, sends to TELEGRAM_LOG_CHAT_ID (log group).
Allow explicit override via --chat-id for Commander/testing.

Environment Variables (Required):
    TELEGRAM_BOT_TOKEN  - Bot token from BotFather
    TELEGRAM_LOG_CHAT_ID - Log group chat ID
    TELEGRAM_CMD_CHAT_ID - Command chat ID (for Commander/testing only)

Usage:
    python scripts/tg_notify.py "Your message here"
    
    # Override to send to DM (Commander/testing only)
    python scripts/tg_notify.py --chat-id <TELEGRAM_CMD_CHAT_ID> "Your message here"

Exit Codes:
    0 = Success
    1 = Missing env vars
    2 = API error (connection, timeout, etc.)
"""

import os
import sys
import argparse


def send_telegram_message(message: str, chat_id: str = None) -> bool:
    """
    Send a message to Telegram.
    
    Default chat_id = TELEGRAM_LOG_CHAT_ID (log group).
    Can override with --chat-id for Commander/DM replies.
    
    Args:
        message: Text message to send
        chat_id: Optional override; if None, uses TELEGRAM_LOG_CHAT_ID
    
    Returns:
        True if sent successfully
    
    Raises:
        ValueError: Missing env vars
        Exception: Network/API error (caller handles retry)
    """
    
    # Load env vars
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN env var not set")
    if not log_chat_id:
        raise ValueError("TELEGRAM_LOG_CHAT_ID env var not set")
    
    # Use provided chat_id, or default to log group
    target_chat_id = chat_id if chat_id else log_chat_id
    
    # TODO: Implement Telegram API send
    # Use requests.post() with bot token + target_chat_id
    # Raise exception on HTTP error (don't suppress)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Send a message to Telegram (default: log group).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("message", help="Message to send")
    parser.add_argument(
        "--chat-id",
        help="Override target chat ID (default: TELEGRAM_LOG_CHAT_ID). Use for Commander/testing only."
    )
    
    args = parser.parse_args()
    
    # Check env vars early
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_chat_id = os.getenv("TELEGRAM_LOG_CHAT_ID")
    
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)
    
    if not log_chat_id:
        print("Error: TELEGRAM_LOG_CHAT_ID env var not set", file=sys.stderr)
        sys.exit(1)
    
    print("✓ Telegram env vars configured")
    if args.chat_id:
        print("✓ Using override chat ID (Commander/testing mode)")
    else:
        print("✓ Sending to log group (default)")
    
    # TODO: Send via requests.post() to Telegram Bot API
    # print("✓ Message sent")


if __name__ == "__main__":
    main()
