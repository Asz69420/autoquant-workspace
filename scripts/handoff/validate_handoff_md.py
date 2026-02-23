#!/usr/bin/env python3
"""Validate markdown handoff files against lightweight template constraints."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_HEADINGS = [
    "## Status",
    "## What\u2019s Running",
    "## Next 3 Actions",
    "## Authoritative Pointers",
    "## Key Decisions",
    "## Blockers",
]


def main() -> int:
    p = argparse.ArgumentParser(description="Validate markdown handoff format")
    p.add_argument("file", help="Path to handoff markdown file")
    p.add_argument("--max-lines", type=int, default=60)
    args = p.parse_args()

    fp = Path(args.file)
    if not fp.exists():
        raise SystemExit(f"ERROR: file not found: {fp}")

    text = fp.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > args.max_lines:
        raise SystemExit(f"ERROR: line limit exceeded ({len(lines)} > {args.max_lines})")

    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    if missing:
        raise SystemExit("ERROR: missing required headings: " + ", ".join(missing))

    # basic timestamp-in-filename check: handoff-YYYYMMDD-HHMM.md
    if not re.search(r"handoff-\d{8}-\d{4}\.md$", fp.name):
        raise SystemExit("ERROR: filename does not match handoff-YYYYMMDD-HHMM.md")

    print(f"OK: {fp} valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
