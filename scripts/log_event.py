#!/usr/bin/env python3
"""
Write an ActionEvent to the spool directory.

This script validates and writes a single ActionEvent JSON file to data/logs/spool/.
All agents use this to emit structured log events; only Logger reads and processes spool files.

Usage:
    python scripts/log_event.py \\
        --ts_iso "2026-02-22T15:01:00Z" \\
        --ts_local "22 Feb 10:01 AM AEST" \\
        --run_id "backtest--a1b2c3d4e5f6" \\
        --agent "BacktestRunner" \\
        --model_id "n/a" \\
        --action "run_backtest" \\
        --status_word "OK" \\
        --summary "Backtest completed" \\
        --inputs "strategies/specs/strategy-mean-revert-btc-v1.json" \\
        --outputs "backtest--a1b2c3d4e5f6"

    # With optional fields:
    python scripts/log_event.py \\
        ... \\
        --reason_code "TIMEOUT" \\
        --error_message "Execution exceeded limit" \\
        --error_type "TimeoutError" \\
        --tags "timeout,critical"

File Path Format:
    data/logs/spool/{ts_file}___{run_id}___{agent}___{status_word}.json
    where ts_file = YYYYMMDDTHHMMSSZ (no colons)

Example Output:
    data/logs/spool/20260222T150100Z___backtest--a1b2c3d4e5f6___BacktestRunner___OK.json

Note:
    - Creates data/logs/spool/ directory if it doesn't exist
    - No secrets in event (ever)
    - Windows-safe filename (no colons)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def main():
    """
    Parse arguments, validate ActionEvent, write to spool.
    
    TODO: Implement full logic:
    1. Parse CLI arguments
    2. Build ActionEvent dict with all required fields
    3. Validate against schema (all required fields present, status_word in allowed set)
    4. Extract filename-safe timestamp from ts_iso
    5. Create spool directory if missing
    6. Write JSON file atomically
    7. Print confirmation or error
    """
    parser = argparse.ArgumentParser(
        description="Write an ActionEvent to the spool directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Required fields
    parser.add_argument("--ts_iso", required=True, help="UTC ISO timestamp: 2026-02-22T15:01:00Z")
    parser.add_argument("--ts_local", required=True, help="Brisbane AEST timestamp: 22 Feb 10:01 AM AEST")
    parser.add_argument("--run_id", required=True, help="Unique run identifier")
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--model_id", required=True, help="Model ID (e.g., haiku, sonnet, n/a)")
    parser.add_argument("--action", required=True, help="Action name")
    parser.add_argument("--status_word", required=True, help="Status: START, OK, WARN, FAIL, BLOCKED, SKIP, PAUSE, QUEUED, RETRY, THROTTLED, CANCELLED, ARCHIVED, TESTING, PROMOTED, REJECTED, INFO")
    parser.add_argument("--summary", required=True, help="One-liner summary")
    parser.add_argument("--inputs", nargs="*", default=[], help="Input paths/URLs")
    parser.add_argument("--outputs", nargs="*", default=[], help="Output paths/artifact IDs")
    
    # Optional fields
    parser.add_argument("--reason_code", help="Reason code if status is WARN/FAIL/BLOCKED/SKIP/REJECTED")
    parser.add_argument("--attempt", help="Retry attempt count (e.g., 2/5)")
    parser.add_argument("--error_message", help="Error message (if FAIL status)")
    parser.add_argument("--error_type", help="Error type (e.g., TimeoutError)")
    parser.add_argument("--tags", help="Comma-separated tags")
    
    args = parser.parse_args()
    
    print("log_event.py: stub implementation (not yet functional)")
    print("Accepted arguments:")
    print(f"  run_id: {args.run_id}")
    print(f"  agent: {args.agent}")
    print(f"  status_word: {args.status_word}")
    print(f"  summary: {args.summary}")
    print()
    print("TODO: Implement full ActionEvent validation and spool file write")


if __name__ == "__main__":
    main()
