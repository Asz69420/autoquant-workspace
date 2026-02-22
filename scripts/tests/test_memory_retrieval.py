#!/usr/bin/env python3
"""Lightweight memory retrieval smoke checks (stdlib only)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> int:
    memory_md = ROOT / "MEMORY.md"
    daily_dir = ROOT / "memory"
    standard_doc = ROOT / "docs" / "CONTRACTS" / "memory-retrieval-standard.md"

    if not memory_md.exists():
        return fail("MEMORY.md missing")
    ok("MEMORY.md exists")

    if not standard_doc.exists():
        return fail("memory-retrieval-standard.md missing")
    ok("memory-retrieval-standard.md exists")

    text = memory_md.read_text(encoding="utf-8", errors="ignore")
    required_tokens = ["Mission:", "North Star", "Architecture"]
    missing = [t for t in required_tokens if t not in text]
    if missing:
        return fail(f"MEMORY.md missing expected anchors: {', '.join(missing)}")
    ok("MEMORY.md contains expected anchor sections")

    if not daily_dir.exists() or not daily_dir.is_dir():
        return fail("memory/ directory missing")

    daily_files = sorted(daily_dir.glob("*.md"))
    if not daily_files:
        return fail("No daily memory markdown files found in memory/")
    ok(f"daily memory files present ({len(daily_files)})")

    print("PASS: memory retrieval smoke checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
