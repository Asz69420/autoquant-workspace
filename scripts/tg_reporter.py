#!/usr/bin/env python3
"""Report ActionEvents → Telegram + NDJSON (actions.ndjson, errors.ndjson only)."""
import json
import os
import sys
import subprocess
import time
import atexit
from pathlib import Path
from datetime import datetime, timedelta

OUTBOX_DIR = Path("data/logs/outbox")
SPOOL_DIR = Path("data/logs/spool")  # Legacy; read-only for backward compat
ACTIONS_LOG = Path("data/logs/actions.ndjson")
ERRORS_LOG = Path("data/logs/errors.ndjson")
LOCK_FILE = Path("data/logs/tg_reporter.lock")

# Anti-spam dedup: (run_id, status_word, ts_iso) → last send time (in-memory only per cycle)
last_sent = {}
DEDUP_WINDOW_SECONDS = 60

KEEPER_ALWAYS_REASON_CODES = {
    "BASELINE_MANIFEST_VIOLATION",
    "BASELINE_OVER_CAP",
    "MEMORY_INDEX_TOO_LARGE",
    "STATUS_SECTION_MARKERS_MISSING",
    "KEEPER_BUDGET_EXCEEDED",
    "CONTEXT_DRIFT",
}

KEEPER_REASON_HINTS = {
    "BASELINE_MANIFEST_VIOLATION": "check baseline manifest + pinned files",
    "BASELINE_OVER_CAP": "reduce baseline scope/token load",
    "MEMORY_INDEX_TOO_LARGE": "trim MEMORY-INDEX summary bullets",
    "STATUS_SECTION_MARKERS_MISSING": "restore STATUS section markers",
    "KEEPER_BUDGET_EXCEEDED": "reduce writes/time and rerun keeper",
    "CONTEXT_DRIFT": "re-scope or rerun with pinned context",
}

INFO_TELEGRAM_ALLOWLIST = {
    "YT_WATCH_SUMMARY",
    "TV_CATALOG_SUMMARY",
    "GRABBER_SUMMARY",
    "PROMOTION_SUMMARY",
    "BATCH_BACKTEST_SUMMARY",
    "REFINEMENT_SUMMARY",
    "LIBRARIAN_SUMMARY",
    "AUTOPILOT_SUMMARY",
}

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

def is_duplicate(run_id, status_word, ts_iso):
    """Check if (run_id, status_word, ts_iso) sent in last 60s (in-memory only)."""
    key = f"{run_id}_{status_word}_{ts_iso}"
    if key in last_sent:
        elapsed = time.time() - last_sent[key]
        if elapsed < DEDUP_WINDOW_SECONDS:
            return True
    return False

def mark_sent(run_id, status_word, ts_iso):
    """Mark (run_id, status_word, ts_iso) as sent (in-memory only)."""
    key = f"{run_id}_{status_word}_{ts_iso}"
    last_sent[key] = time.time()


def already_logged(run_id, status_word, ts_iso):
    """Persistent dedup: skip if already appended in actions.ndjson."""
    if not ACTIONS_LOG.exists():
        return False
    try:
        with open(ACTIONS_LOG, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if (
                    e.get("run_id") == run_id
                    and e.get("status_word") == status_word
                    and e.get("ts_iso") == ts_iso
                ):
                    return True
    except Exception:
        return False
    return False

def acquire_lock_or_exit():
    """Best-effort single-instance lock (prevents duplicate sends from parallel daemons)."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        def _cleanup_lock():
            try:
                if LOCK_FILE.exists():
                    LOCK_FILE.unlink()
            except Exception:
                pass

        atexit.register(_cleanup_lock)
        return True
    except FileExistsError:
        try:
            existing_pid_txt = LOCK_FILE.read_text(encoding="utf-8", errors="ignore").strip()
            existing_pid = int(existing_pid_txt)
            alive = True
            try:
                os.kill(existing_pid, 0)
            except Exception:
                alive = False

            if not alive:
                try:
                    LOCK_FILE.unlink()
                except Exception:
                    pass
                return acquire_lock_or_exit()
        except Exception:
            existing_pid_txt = "unknown"

        print(f"Another tg_reporter instance is active (pid={existing_pid_txt}). Exiting.", file=sys.stderr)
        return False


def _event_sort_key(path_obj):
    """Deterministic ordering: ts_iso, run_id, status rank (START before terminal)."""
    status_rank = {
        "START": 0,
        "QUEUED": 1,
        "RETRY": 2,
        "INFO": 3,
        "OK": 4,
        "WARN": 5,
        "BLOCKED": 6,
        "FAIL": 7,
    }
    try:
        with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
            e = json.load(f)
        ts = e.get("ts_iso") or ""
        run_id = e.get("run_id") or ""
        sw = e.get("status_word") or ""
        return (ts, run_id, status_rank.get(sw, 99), path_obj.name)
    except Exception:
        return ("", "", 99, path_obj.name)


def _parse_keeper_summary(summary: str) -> dict:
    parsed = {}
    for part in (summary or "").split(";"):
        s = part.strip()
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        parsed[k.strip().lower()] = v.strip()
    return parsed


def _to_int(val, default=0):
    try:
        return int(str(val).strip())
    except Exception:
        return default


def _escape_md_v2(text: str) -> str:
    text = str(text)
    for ch in r"_[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _keeper_should_post(event: dict) -> bool:
    status_word = str(event.get("status_word") or "").upper()
    reason_code = str(event.get("reason_code") or "").upper()

    if status_word in {"WARN", "FAIL"}:
        return True
    if reason_code in KEEPER_ALWAYS_REASON_CODES:
        return True

    if reason_code == "KEEPER_SUMMARY":
        kv = _parse_keeper_summary(event.get("summary") or "")
        status = (kv.get("status") or status_word).upper()
        files_written = _to_int(kv.get("files_written"), 0)
        bytes_changed = _to_int(kv.get("bytes_changed"), 0)
        warnings_count = _to_int(kv.get("warnings_count"), 0)

        if status == "NOOP" and warnings_count == 0:
            return False
        if status == "OK" and (files_written > 0 or bytes_changed > 0):
            return True
        if status == "NOOP":
            return False

    if reason_code == "BASELINE_OK":
        kv = _parse_keeper_summary(event.get("summary") or "")
        if (kv.get("simulation", "").lower() == "false"):
            return False

    return False


def _keeper_telegram_message(event: dict) -> str:
    status_word = str(event.get("status_word") or "").upper()
    reason_code = str(event.get("reason_code") or "").upper()

    if reason_code == "KEEPER_SUMMARY":
        kv = _parse_keeper_summary(event.get("summary") or "")
        status = (kv.get("status") or status_word).upper()
        files_written = _to_int(kv.get("files_written"), 0)
        bytes_changed = _to_int(kv.get("bytes_changed"), 0)
        if status == "OK":
            return _escape_md_v2(f"Keeper: OK (wrote {files_written} file{'s' if files_written != 1 else ''}, bytes {bytes_changed})")
        if status == "NOOP":
            return _escape_md_v2("Keeper: NOOP")
        return _escape_md_v2(f"Keeper: {status}")

    if status_word in {"WARN", "FAIL"} or reason_code in KEEPER_ALWAYS_REASON_CODES:
        hint = KEEPER_REASON_HINTS.get(reason_code, "check keeper summary")
        return _escape_md_v2(f"Keeper: {status_word} ({reason_code}) - {hint}")

    return _escape_md_v2(f"Keeper: {status_word}")


def send_event_to_telegram(event):
    """Format and send an ActionEvent to Telegram. Returns True on success."""
    try:
        if str(event.get("agent") or "").lower() == "keeper":
            if not _keeper_should_post(event):
                return None
            formatted_msg = _keeper_telegram_message(event)
        else:
            status_word = str(event.get("status_word") or "").upper()
            reason_code = str(event.get("reason_code") or "").upper()
            if reason_code.startswith("AUTOPILOT_STAGE_"):
                return None
            if status_word == "INFO" and reason_code not in INFO_TELEGRAM_ALLOWLIST:
                return None
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

        send_result = subprocess.run(
            [sys.executable, "scripts/tg_notify.py", formatted_msg],
            capture_output=True,
            text=True
        )

        return send_result.returncode == 0
    except subprocess.CalledProcessError as e:
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
    Drain outbox and spool (legacy compat) files.
    Returns (sent, skipped, consecutive_failures).
    Processes outbox first, then spool (backward compatibility).
    """
    # Collect files from both directories
    event_files = []
    
    if OUTBOX_DIR.exists():
        event_files.extend(OUTBOX_DIR.glob("*.json"))
    
    if SPOOL_DIR.exists():
        event_files.extend(SPOOL_DIR.glob("*.json"))
    
    event_files = sorted(event_files, key=_event_sort_key)
    
    if not event_files:
        return 0, 0, 0
    
    sent = 0
    skipped = 0
    consecutive_failures = 0
    
    # Ensure log dirs
    ACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ERRORS_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    for idx, event_file in enumerate(event_files):
        # Check if we hit max_messages
        if sent >= max_messages:
            remaining = len(event_files) - idx
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
            with open(event_file) as f:
                event = json.load(f)
            
            run_id = event["run_id"]
            status_word = event["status_word"]
            ts_iso = event.get("ts_iso", "")
            agent = event.get("agent")

            # Persistent dedup across process restarts
            if already_logged(run_id, status_word, ts_iso):
                event_file.unlink()
                skipped += 1
                print(f"Skipped (already-logged): {event_file.name}", file=sys.stderr)
                continue

            # Result-first policy: suppress START notifications in Telegram.
            # Final statuses (OK/WARN/FAIL/BLOCKED/etc.) are what matter in chat.
            # Keep START in actions.ndjson for lifecycle auditability.
            if status_word == "START":
                event_line = json.dumps(event)
                with open(ACTIONS_LOG, "a") as f:
                    f.write(event_line + "\n")
                event_file.unlink()
                mark_sent(run_id, status_word, ts_iso)
                skipped += 1
                print(f"Skipped (start-suppressed, logged): {event_file.name}", file=sys.stderr)
                continue
            
            # Check dedup (in-memory only)
            if is_duplicate(run_id, status_word, ts_iso):
                skipped += 1
                print(f"Skipped (dedup): {event_file.name}", file=sys.stderr)
                continue
            
            # Send to Telegram (or suppress per reporter policy)
            send_result = send_event_to_telegram(event)
            if send_result is None:
                # Suppressed from Telegram; still append to NDJSON and clear outbox
                event_line = json.dumps(event)
                with open(ACTIONS_LOG, "a") as f:
                    f.write(event_line + "\n")
                if status_word == "FAIL":
                    with open(ERRORS_LOG, "a") as f:
                        f.write(event_line + "\n")
                event_file.unlink()
                mark_sent(run_id, status_word, ts_iso)
                skipped += 1
                consecutive_failures = 0
                print(f"Skipped (telegram-policy, logged): {event_file.name}", file=sys.stderr)
            elif send_result:
                # Success: append to NDJSON, delete event file
                event_line = json.dumps(event)
                with open(ACTIONS_LOG, "a") as f:
                    f.write(event_line + "\n")
                
                if status_word == "FAIL":
                    with open(ERRORS_LOG, "a") as f:
                        f.write(event_line + "\n")
                
                event_file.unlink()
                mark_sent(run_id, status_word, ts_iso)
                sent += 1
                consecutive_failures = 0
                print(f"Sent: {event_file.name}", file=sys.stderr)
            else:
                consecutive_failures += 1
                print(f"Send failed: {event_file.name} (attempt {consecutive_failures}/5)", file=sys.stderr)
                
                if consecutive_failures >= 5:
                    print(f"Max consecutive failures (5) reached. Exiting.", file=sys.stderr)
                    return sent, skipped, consecutive_failures
        
        except Exception as e:
            consecutive_failures += 1
            print(f"Error processing {event_file.name}: {e}", file=sys.stderr)
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
    
    if not acquire_lock_or_exit():
        sys.exit(1)

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
