#!/usr/bin/env python3
"""
Convert an ActionEvent to a Telegram code-block message.

This script takes an ActionEvent (as dict or JSON) and formats it as a
Telegram message in a code block with strict template:

    ```
    [<timestamp 12h AM/PM AEST>] <AgentName> | <model-id> | <status_emoji> <STATUS_WORD> (<reason_code_if_any>)
    <Line 2: summary (max 50 chars)>
    <Line 3: optional detail (max 50 chars)>
    Run: <run_id>
    ```

Usage:
    python scripts/tg_format.py --event '{"ts_local": "22 Feb 10:01 AM AEST", ...}'
    
    # Or read from file
    python scripts/tg_format.py --event-file data/logs/spool/20260222T150100Z___backtest--a1b2c3d4e5f6___BacktestRunner___OK.json

Output:
    Formatted Telegram message string (ready to send via tg_notify.py)

Status Emoji Mapping:
    START → ▶️, OK → ✅, WARN → ⚠️, FAIL → ❌
    BLOCKED → ⛔, SKIP → ⏭️, PAUSE → ⏸️, QUEUED → ⏳
    RETRY → 🔁, THROTTLED → 🐢, CANCELLED → 🛑, ARCHIVED → 🧊
    TESTING → 🧪, PROMOTED → 🏆, REJECTED → 🗑️, INFO → ℹ️
"""

import argparse
import json
import sys


STATUS_EMOJI_MAP = {
    "START": "▶️",
    "OK": "✅",
    "WARN": "⚠️",
    "FAIL": "❌",
    "BLOCKED": "⛔",
    "SKIP": "⏭️",
    "PAUSE": "⏸️",
    "QUEUED": "⏳",
    "RETRY": "🔁",
    "THROTTLED": "🐢",
    "CANCELLED": "🛑",
    "ARCHIVED": "🧊",
    "TESTING": "🧪",
    "PROMOTED": "🏆",
    "REJECTED": "🗑️",
    "INFO": "ℹ️",
}


def format_action_event(event: dict) -> str:
    """
    Convert ActionEvent dict to Telegram code-block message.
    
    TODO: Implement:
    1. Extract required fields: ts_local, agent, model_id, status_word, reason_code, summary, run_id
    2. Look up emoji from STATUS_EMOJI_MAP
    3. Build header: [ts_local] agent | model_id | emoji STATUS_WORD (reason_code if present)
    4. Add summary (line 2, max 50 chars)
    5. Add optional detail from inputs/outputs (line 3, max 50 chars)
    6. Add "Run: {run_id}"
    7. Wrap in triple backticks
    8. Return formatted string
    
    Args:
        event: ActionEvent dict with ts_local, agent, model_id, status_word, etc.
    
    Returns:
        Formatted Telegram message string
    """
    print("tg_format.py: stub implementation (not yet functional)")
    print(f"Input event type: {type(event)}")
    if isinstance(event, dict):
        print(f"Fields: {list(event.keys())}")
    print()
    print("TODO: Implement ActionEvent → Telegram message formatting")
    return "```\n[ERROR] Formatting not yet implemented\n```"


def main():
    parser = argparse.ArgumentParser(
        description="Convert ActionEvent to Telegram code-block message.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--event", help="ActionEvent as JSON string")
    group.add_argument("--event-file", help="Path to ActionEvent JSON file")
    
    args = parser.parse_args()
    
    if args.event:
        try:
            event = json.loads(args.event)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --event: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            with open(args.event_file, "r") as f:
                event = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not read/parse {args.event_file}: {e}", file=sys.stderr)
            sys.exit(1)
    
    message = format_action_event(event)
    print(message)


if __name__ == "__main__":
    main()
