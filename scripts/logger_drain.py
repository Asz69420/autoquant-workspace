#!/usr/bin/env python3
"""
Drain spool directory: send Telegram + append NDJSON + delete spool files.

This is the main Logger component. It runs continuously or via cron and:
1. Scans data/logs/spool/ in timestamp order
2. For each ActionEvent JSON file:
   - Parses the JSON
   - Formats a Telegram message via tg_format.py
   - Sends to Telegram via tg_notify.py
   - Appends to data/logs/actions.ndjson
   - Deletes the spool file
3. If Telegram send fails: appends FAIL event to errors.ndjson, keeps spool file, continues

Usage:
    # Drain spool once (one iteration)
    python scripts/logger_drain.py
    
    # Continuous daemon mode
    python scripts/logger_drain.py --daemon
    
    # Manual drain with specific directory
    python scripts/logger_drain.py --manual --spool-dir data/logs/spool/
    
    # With custom interval (daemon mode)
    python scripts/logger_drain.py --daemon --interval 30

Options:
    --daemon              Run continuously (loop with interval)
    --manual              Single-pass drain (default)
    --spool-dir PATH      Custom spool directory (default: data/logs/spool/)
    --interval SECONDS    Loop interval in daemon mode (default: 60)
    --verbose             Print debug info

Environment Variables:
    TELEGRAM_BOT_TOKEN  Required (checked on startup)
    TELEGRAM_CHAT_ID    Required (checked on startup)

Spool File Format:
    data/logs/spool/{ts_file}___{run_id}___{agent}___{status_word}.json
    where ts_file = YYYYMMDDTHHMMSSZ

Output Files:
    data/logs/actions.ndjson  - All ActionEvents (append-only)
    data/logs/errors.ndjson   - Only FAIL events with full error details
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


def drain_spool_once(spool_dir: str = "data/logs/spool", verbose: bool = False) -> dict:
    """
    Drain spool directory one time.
    
    TODO: Implement:
    1. Check that TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set
    2. List all JSON files in spool_dir, sorted by filename (timestamp order)
    3. For each file:
       a. Parse JSON (ActionEvent)
       b. Run tg_format.py to create Telegram message
       c. Run tg_notify.py to send message
       d. Append original event JSON to data/logs/actions.ndjson
       e. Delete spool file
    4. If tg_notify.py fails:
       - Write FAIL ActionEvent to data/logs/errors.ndjson
       - Keep spool file for next cycle
       - Continue (don't crash)
    5. Return stats: {"processed": N, "failed": N, "errors": [...]}
    
    Args:
        spool_dir: Path to spool directory
        verbose: Print debug info
    
    Returns:
        Stats dict: {"processed": int, "failed": int, "errors": list}
    """
    print("logger_drain.py: stub implementation (not yet functional)")
    print(f"Spool directory: {spool_dir}")
    print("TODO: Implement spool draining (scan → format → send → log → delete)")
    return {"processed": 0, "failed": 0, "errors": []}


def run_daemon(spool_dir: str = "data/logs/spool", interval: int = 60, verbose: bool = False):
    """
    Run Logger in daemon mode (continuous loop).
    
    Args:
        spool_dir: Path to spool directory
        interval: Seconds between drain cycles
        verbose: Print debug info
    """
    print("logger_drain.py daemon mode: stub implementation")
    print(f"Interval: {interval}s")
    print("TODO: Implement continuous drain loop (with error handling, graceful shutdown)")


def main():
    parser = argparse.ArgumentParser(
        description="Drain spool directory and post to Telegram.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--manual", action="store_true", help="Single-pass drain (default)")
    parser.add_argument("--spool-dir", default="data/logs/spool", help="Spool directory path")
    parser.add_argument("--interval", type=int, default=60, help="Daemon loop interval (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print debug info")
    
    args = parser.parse_args()
    
    # Check env vars early
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID not set", file=sys.stderr)
        sys.exit(1)
    
    print("✓ Telegram env vars present")
    
    # Create output directories if missing
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    
    if args.daemon:
        run_daemon(args.spool_dir, args.interval, args.verbose)
    else:
        # Single-pass drain
        stats = drain_spool_once(args.spool_dir, args.verbose)
        print(f"\nStats: processed={stats['processed']}, failed={stats['failed']}")
        if stats["errors"]:
            print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
