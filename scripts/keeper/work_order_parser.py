#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REQUIRED_HEADINGS = [
    "## Intent",
    "## Evidence (read-only pointers)",
    "## Allowlist (Keeper may edit ONLY these)",
    "## Curated changes (exact bullets to apply)",
    "## Safety",
    "## Validation checklist (must PASS before commit)",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]"),
    re.compile(r"(?i)token\s*[:=]"),
    re.compile(r"(?i)authorization:\s*bearer"),
]


@dataclass
class WorkOrder:
    path: Path
    text: str
    allowlist: dict[str, str]  # file -> section lock
    memory_add: list[str]
    memory_remove: list[str]
    status_lines: list[str]
    handoff_path: str


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^{re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    start = m.end()
    tail = text[start:]
    n = re.search(r"^##\s+", tail, re.M)
    return tail[: n.start()] if n else tail


def _parse_allowlist(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = re.match(r'-\s+(.+?)\s+\(ONLY section:\s+"(.+?)"\)', line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
            continue
        m2 = re.match(r"-\s+(.+?)\s+\(new file only\)", line)
        if m2:
            out[m2.group(1).strip()] = "__NEW_FILE_ONLY__"
    return out


def _parse_bullets(block: str, marker: str) -> list[str]:
    m = re.search(rf"{re.escape(marker)}\s*(.*?)\n(?:[A-Z][A-Za-z ]+:|Reason|$)", block, re.S)
    if not m:
        return []
    lines = []
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if ln.startswith("-"):
            lines.append(ln[1:].strip())
    return lines


def parse_work_order(path: Path) -> WorkOrder:
    text = path.read_text(encoding="utf-8", errors="ignore")

    for h in REQUIRED_HEADINGS:
        if h not in text:
            raise ValueError(f"Missing required heading: {h}")

    for pat in SECRET_PATTERNS:
        if pat.search(text):
            raise ValueError("Potential secret pattern in work order")

    allowlist_block = _section(text, "## Allowlist (Keeper may edit ONLY these)")
    allowlist = _parse_allowlist(allowlist_block)
    if not allowlist:
        raise ValueError("Allowlist missing or malformed")

    curated = _section(text, "## Curated changes (exact bullets to apply)")
    mem_block = _section(curated, "### MEMORY.md → Model Policy (Locked)") if "### MEMORY.md" in curated else ""
    if not mem_block:
        m = re.search(r"### MEMORY\.md\s*→\s*Model Policy \(Locked\)(.*?)(?:\n### |\Z)", curated, re.S)
        mem_block = m.group(1) if m else ""

    status_block = ""
    m = re.search(r"### docs/STATUS\.md\s*→\s*Current model posture(.*?)(?:\n### |\Z)", curated, re.S)
    if m:
        status_block = m.group(1)

    handoff_path = ""
    m = re.search(r"###\s+(docs/HANDOFFS/handoff-[^\s]+)", curated)
    if m:
        handoff_path = m.group(1)

    memory_add = _parse_bullets(mem_block, "ADD bullets:")
    memory_remove = _parse_bullets(mem_block, "REMOVE bullets:")

    status_lines = []
    m = re.search(r"Replace snapshot lines with:(.*?)(?:\n### |\Z)", status_block, re.S)
    if m:
        for ln in m.group(1).splitlines():
            ln = ln.strip()
            if ln.startswith("-"):
                status_lines.append(ln[1:].strip())

    if not memory_add:
        raise ValueError("No explicit MEMORY add bullets found")
    if not status_lines:
        raise ValueError("No explicit STATUS replacement lines found")
    if not handoff_path:
        raise ValueError("No handoff target found")

    return WorkOrder(
        path=path,
        text=text,
        allowlist=allowlist,
        memory_add=memory_add,
        memory_remove=memory_remove,
        status_lines=status_lines,
        handoff_path=handoff_path,
    )
