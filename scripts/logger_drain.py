#!/usr/bin/env python3
"""Drain spool → Telegram + NDJSON (actions.ndjson, errors.ndjson only)."""
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta

SPOOL_DIR = Path("data/logs/spool")
ACTIONS_LOG = Path("data/logs/actions.ndjson")
ERRORS_LOG = Path("data/logs/errors.ndjson")

# Anti-spam dedup: (run_id, status_word) → last send time (in-memory only per cycle)
last_sent = {}
DEDUP_WINDOW_SECONDS = 60

def compute_ts_local_aest(ts_iso_str):
    """Convert ISO UTC timestamp to ts_local (12-hour AEST)."""
    dt_utc = datetime.fromisoformat(ts_iso_str.replace("Z", "+00:00"))
    dt_aest = dt_utc + timedelta(hours=10)
    
    day = dt_aest.strftime("%d").lstrip("0")
    month = dt_aest.strftime("%b")
    hour_12 = dt_aest.strftime("%I").lstrip("0")
    minute = dt_aest.strftime("%M")
    ampm = dt_aest.strftime("%p")
    
    return f"{day} {month} {hour_12}:{minute} {ampm} AEST"

def is_duplicate(run_id, status_word):
    """Check if (run_id, status_word) sent in last 60s (in-memory only)."""
    key = f"{run_id}_{status_word}"
    if key in last_sent:
        elapsed = time.time() - last_sent[key]
        if elapsed < DEDUP_WINDOW_SECONDS:
            return True
    return False

def mark_sent(run_id, status_word):
    """Mark (run_id, status_word) as sent (in-memory only)."""
    key = f"{run_id}_{status_word}"
    last_sent[key] = time.time()

def send_event_to_telegram(event):
    """Format and send an ActionEvent to Telegram. Returns True on success."""
    try:
        # Format event via stdin (bytes-based for Windows robustness)
        event_json = json.dumps(event)
        env = {**os.environ, "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, "scripts/tg_format.py"],
            input=event_json.encode("utf-8"),
            text=False,
            capture_output=True,
            check=True,
            env=env
        )
        formatted_msg = result.stdout.decode("utf-8", errors="replace").strip()
        
        # Send to Telegram
        send_result = subprocess.run(
            [sys.executable, "scripts/tg_notify.py", formatted_msg],
            capture_output=True,
            text=True
        )
        
        return send_result.returncode == 0
    except subprocess.CalledProcessError as e:
        # tg_format.py failed; print diagnostics
        exit_code = e.returncode
        stderr_text = e.stderr.decode("utf-8", errors="replace") if e.stderr else "(no stderr)"
        stdout_preview = e.stdout.decode("utf-8", errors="replace")[:200] if e.stdout else "(no stdout)"
        print(f"tg_format.py exited {exit_code}", file=sys.stderr)
        print(f"stderr: {stderr_text}", file=sys.stderr)
        if stdout_preview:
            print(f"stdout (first 200): {stdout_preview}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error formatting/sending event: {e}", file=sys.stderr)
        return False

def drain_once(max_messages=20):
    """
    Drain spool files (at most max_messages Telegram sends).
    Returns (sent, skipped, consecutive_failures).
    """
    if not SPOOL_DIR.exists():
        return 0, 0, 0
    
    spool_files = sorted(SPOOL_DIR.glob("*.json"))
    if not spool_files:
        return 0, 0, 0
    
    sent = 0
    skipped = 0
    consecutive_failures = 0
    
    # Ensure log dirs
    ACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ERRORS_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    for idx, spool_file in enumerate(spool_files):
        # Check if we hit max_messages
        if sent >= max_messages:
            remaining = len(spool_files) - idx
            if remaining > 0:
                # Create INFO ActionEvent for rollup (no file writing)
                ts_iso = datetime.utcnow().isoformat() + "Z"
                ts_local = compute_ts_local_aest(ts_iso)
                
                rollup_event = {
                    "ts_iso": ts_iso,
                    "ts_local": ts_local,
                    "ts_file": datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                    "run_id": "logger-rollup",
                    "agent": "Logger",
                    "model_id": "system",
                    "action": "rollup",
                    "status_word": "INFO",
                    "status_emoji": "ℹ️",
                    "reason_code": None,
                    "summary": f"{remaining} more events queued",
                    "inputs": [],
                    "outputs": [],
                    "attempt": None,
                    "error": None
                }
                
                send_event_to_telegram(rollup_event)
            break
        
        try:
            with open(spool_file) as f:
                event = json.load(f)
            
            run_id = event["run_id"]
            status_word = event["status_word"]
            
            # Check dedup (in-memory only)
            if is_duplicate(run_id, status_word):
                skipped += 1
                print(f"Skipped (dedup): {spool_file.name}", file=sys.stderr)
                continue
            
            # Send to Telegram
            if send_event_to_telegram(event):
                # Success: append to NDJSON, delete spool
                event_line = json.dumps(event)
                with open(ACTIONS_LOG, "a") as f:
                    f.write(event_line + "\n")
                
                if status_word == "FAIL":
                    with open(ERRORS_LOG, "a") as f:
                        f.write(event_line + "\n")
                
                spool_file.unlink()
                mark_sent(run_id, status_word)
                sent += 1
                consecutive_failures = 0
                print(f"Sent: {spool_file.name}", file=sys.stderr)
            else:
                consecutive_failures += 1
                print(f"Send failed: {spool_file.name} (attempt {consecutive_failures}/5)", file=sys.stderr)
                
                if consecutive_failures >= 5:
                    print(f"Max consecutive failures (5) reached. Exiting.", file=sys.stderr)
                    return sent, skipped, consecutive_failures
        
        except Exception as e:
            consecutive_failures += 1
            print(f"Error processing {spool_file.name}: {e}", file=sys.stderr)
            if consecutive_failures >= 5:
                print(f"Max consecutive failures (5) reached. Exiting.", file=sys.stderr)
                return sent, skipped, consecutive_failures
    
    return sent, skipped, consecutive_failures

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", action="store_true", help="Drain once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run in loop")
    parser.add_argument("--interval", type=int, default=10, help="Loop interval (seconds)")
    args = parser.parse_args()
    
    if args.manual:
        sent, skipped, failures = drain_once()
        print(f"Drained: {sent} sent, {skipped} skipped, {failures} failures", file=sys.stderr)
        sys.exit(0 if failures == 0 else 1)
    elif args.daemon:
        print(f"Daemon mode: interval={args.interval}s", file=sys.stderr)
        try:
            while True:
                sent, skipped, failures = drain_once()
                if sent > 0 or skipped > 0:
                    print(f"Cycle: {sent} sent, {skipped} skipped", file=sys.stderr)
                if failures >= 5:
                    print("Too many failures. Exiting daemon.", file=sys.stderr)
                    sys.exit(1)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Daemon stopped", file=sys.stderr)
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
