#!/usr/bin/env python3
"""Emit an ActionEvent to data/logs/spool/."""
import json
import os
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

ALLOWED_STATUS_WORDS = {
    "OK", "WARN", "FAIL", "BLOCKED", "START", "QUEUED", "RETRY",
    "THROTTLED", "CANCELLED", "ARCHIVED", "TESTING", "PROMOTED",
    "REJECTED", "PAUSE", "INFO", "SKIP"
}

def compute_ts_local_aest(ts_iso_str):
    """Convert ISO UTC timestamp to ts_local (12-hour AEST)."""
    dt_utc = datetime.fromisoformat(ts_iso_str.replace("Z", "+00:00"))
    # AEST is UTC+10 (fixed year-round per USER.md)
    dt_aest = dt_utc + timedelta(hours=10)
    
    day = dt_aest.strftime("%d").lstrip("0")
    month = dt_aest.strftime("%b")
    hour_12 = dt_aest.strftime("%I").lstrip("0")
    minute = dt_aest.strftime("%M")
    ampm = dt_aest.strftime("%p")
    
    return f"{day} {month} {hour_12}:{minute} {ampm} AEST"

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--ts-iso", default=None, help="ISO 8601 UTC timestamp")
    parser.add_argument("--ts-local", default=None, help="Pre-computed ts_local (Brisbane AEST)")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--status-word", required=True, 
                        choices=sorted(ALLOWED_STATUS_WORDS),
                        help="Must be one of: " + ", ".join(sorted(ALLOWED_STATUS_WORDS)))
    parser.add_argument("--status-emoji", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--reason-code", default=None)
    parser.add_argument("--inputs", nargs="*", default=[])
    parser.add_argument("--outputs", nargs="*", default=[])
    parser.add_argument("--attempt", type=int, default=None)
    parser.add_argument("--error-message", default=None, help="Error message (requires --error-type)")
    parser.add_argument("--error-type", default=None, help="Error type (e.g., NetworkError)")
    parser.add_argument("--error-stack", default=None, help="Short stack trace")
    args = parser.parse_args()
    
    # Validate error object
    error = None
    if args.error_message or args.error_type or args.error_stack:
        if not args.error_type:
            parser.error("--error-type required if providing error details")
        error = {
            "message": args.error_message or "",
            "type": args.error_type,
            "stack_short": args.error_stack or ""
        }
    
    # Compute ts_iso if not provided
    if args.ts_iso:
        ts_iso = args.ts_iso
    else:
        ts_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    
    # Compute ts_local if not provided
    if args.ts_local:
        ts_local = args.ts_local
    else:
        ts_local = compute_ts_local_aest(ts_iso)
    
    # ts_file from ts_iso
    dt_utc = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    ts_file = dt_utc.strftime("%Y%m%dT%H%M%SZ")
    
    # Construct ActionEvent
    event = {
        "ts_iso": ts_iso,
        "ts_local": ts_local,
        "ts_file": ts_file,
        "run_id": args.run_id,
        "agent": args.agent,
        "model_id": args.model_id,
        "action": args.action,
        "status_word": args.status_word,
        "status_emoji": args.status_emoji,
        "reason_code": args.reason_code,
        "summary": args.summary,
        "inputs": args.inputs,
        "outputs": args.outputs,
        "attempt": args.attempt,
        "error": error,
    }
    
    # Filename: ts_file___run_id___agent___status_word.json
    filename = f"{ts_file}___{args.run_id}___{args.agent}___{args.status_word}.json"
    
    # Atomic write to outbox (primary) or spool (legacy fallback)
    outbox_dir = Path("data/logs/outbox")
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    final_path = outbox_dir / filename
    tmp_path = outbox_dir / f"{filename}.{os.getpid()}.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(event, f)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, final_path)
    print(f"Emitted: {final_path.name}", file=sys.stderr)
    sys.exit(0)

if __name__ == "__main__":
    main()
