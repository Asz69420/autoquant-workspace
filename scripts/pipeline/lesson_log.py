#!/usr/bin/env python3
"""Lightweight structured lesson logger. Append-only, non-blocking.
Usage: python lesson_log.py --agent quandalf --type insight --detail "message here"
"""
import json, argparse, os
from datetime import datetime, timezone
from pathlib import Path


def log_lesson(agent: str, lesson_type: str, detail: str, action: str = ""):
    root = Path(__file__).resolve().parents[2]
    log_path = root / "data" / "logs" / "lessons.ndjson"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "type": lesson_type,
        "detail": detail,
    }
    if action:
        entry["action_taken"] = action

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


if name == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--agent", required=True)
    p.add_argument("--type", required=True, choices=["insight", "error", "violation", "pattern", "success"])
    p.add_argument("--detail", required=True)
    p.add_argument("--action", default="")
    args = p.parse_args()
    log_lesson(args.agent, args.type, args.detail, args.action)
