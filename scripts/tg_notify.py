#!/usr/bin/env python3
"""
Send a message to Telegram using environment variables.

This script sends a message to Telegram using credentials from env vars only.
No secrets are hardcoded or stored in files.

Environment Variables (Required):
    TELEGRAM_BOT_TOKEN  - Bot token from BotFather (e.g., "123:ABC...")
    TELEGRAM_CHAT_ID    - Chat/channel ID (e.g., "987654321")

Usage:
    export TELEGRAM_BOT_TOKEN="123:ABC..."
    export TELEGRAM_CHAT_ID="987654321"
    
    python scripts/tg_notify.py "Your message here"
    
    # Or via stdin
    echo "Message" | python scripts/tg_notify.py

Exit Codes:
    0 = Success
    1 = Missing env vars
    2 = API error (connection, timeout, etc.)

Error Behavior:
    - Raises exception on HTTP error (caller decides retry logic)
    - Prints error details to stderr
    - Does NOT suppress exceptions; let caller handle retry
"""

import os
import sys


def send_telegram_message(message: str) -> bool:
    """
    Send a message to Telegram.
    
    TODO: Implement:
    1. Get TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from env
    2. Raise ValueError if either is missing
    3. Use requests.post() to send to Telegram Bot API
    4. Handle HTTP errors (raise exception)
    5. Return True on success
    6. Let exceptions bubble up (caller handles retry)
    
    Args:
        message: Text message (can include code blocks)
    
    Returns:
        True if sent successfully
    
    Raises:
        ValueError: Missing env vars
        requests.RequestException: Network error (timeout, connection refused, etc.)
    """
    print("tg_notify.py: stub implementation (not yet functional)")
    print(f"Message length: {len(message)} chars")
    print("TODO: Implement Telegram API send (requests.post with env var credentials)")
    return False


def main():
    # Get message from stdin or args
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = sys.stdin.read()
    
    if not message.strip():
        print("Error: No message provided", file=sys.stderr)
        sys.exit(2)
    
    # Check env vars
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)
    
    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID env var not set", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ Env vars found (token length: {len(bot_token)}, chat_id: {chat_id})")
    print(f"✓ Message ready (length: {len(message)})")
    print()
    print("TODO: Send via requests.post() to Telegram Bot API")
    
    # TODO: Uncomment after implementation
    # try:
    #     success = send_telegram_message(message)
    #     if success:
    #         print("✓ Message sent to Telegram", file=sys.stderr)
    #         sys.exit(0)
    # except ValueError as e:
    #     print(f"Error: {e}", file=sys.stderr)
    #     sys.exit(1)
    # except Exception as e:
    #     print(f"Error: Failed to send: {e}", file=sys.stderr)
    #     sys.exit(2)


if __name__ == "__main__":
    main()
