#!/usr/bin/env python3
"""
Research Digest Worker — scans research cards, extracts trading concepts,
writes a rolling digest that Quandalf reads each cycle.

Keeps docs/shared/RESEARCH_DIGEST.md under a size cap by replacing oldest
entries when new ones arrive. Preserves trading nuance — specific indicators,
entry/exit logic, risk frameworks, market structure concepts.

Run manually or via cron to keep digest fresh.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DIR = ROOT / "artifacts" / "research"
DIGEST_PATH = ROOT / "docs" / "shared" / "RESEARCH_DIGEST.md"
DIGEST_INDEX_PATH = ROOT / "docs" / "shared" / ".digest_seen.json"

MAX_ENTRIES = 25
MIN_RAW_LENGTH = 500


def _load_seen() -> set[str]:
    if DIGEST_INDEX_PATH.exists():
        try:
            rows = json.loads(DIGEST_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(rows, list):
                return {str(x) for x in rows}
        except Exception:
            return set()
    return set()


def _save_seen(seen: set[str]) -> None:
    DIGEST_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_INDEX_PATH.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def _safe_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _raw_len(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8-sig", errors="ignore"))
    except Exception:
        return 0


def _extract_entry(card_path: Path) -> dict | None:
    card = _safe_json(card_path)
    if not card:
        return None

    card_id = str(card.get("id") or "")
    if not card_id:
        return None

    title = str(card.get("title") or "Unknown")
    author = str(card.get("author") or "Unknown")
    source_ref = str(card.get("source_ref") or "")
    source_type = str(card.get("source_type") or "")
    created_full = str(card.get("created_at") or "")
    created = created_full[:10] if created_full else "unknown"

    raw_ptr = str(card.get("raw_pointer") or "")
    raw_path = ROOT / raw_ptr if raw_ptr else Path()
    if not raw_path.exists():
        return None

    raw_text = raw_path.read_text(encoding="utf-8-sig", errors="ignore")
    if len(raw_text) < MIN_RAW_LENGTH:
        return None

    sections: list[str] = []

    bullets = card.get("summary_bullets") if isinstance(card.get("summary_bullets"), list) else []
    real_bullets = [
        str(b).strip()
        for b in bullets
        if isinstance(b, str)
        and len(b.strip()) > 20
        and not b.startswith("source_ref=")
        and "TRANSCRIPT_UNAVAILABLE" not in b
    ]
    if real_bullets:
        sections.append("**Summary:** " + " ".join(real_bullets[:5]))

    rules = card.get("extracted_rules") if isinstance(card.get("extracted_rules"), list) else []
    real_rules = [str(r).strip() for r in rules if isinstance(r, str) and r.strip() and r.strip() != "Not specified in content."]
    if real_rules:
        sections.append("**Trading Rules:**")
        for r in real_rules[:8]:
            sections.append(f"- {r[:200]}")

    components = card.get("strategy_components") if isinstance(card.get("strategy_components"), list) else []
    comp_types: dict[str, list[str]] = {}
    for c in components:
        if not isinstance(c, dict):
            continue
        t = str(c.get("type") or "other")
        d = str(c.get("description") or "").strip()
        if d and len(d) > 15:
            comp_types.setdefault(t, []).append(d[:200])
    if comp_types:
        sections.append("**Strategy Components:**")
        for t, descs in comp_types.items():
            for d in descs[:3]:
                sections.append(f"- [{t}] {d}")

    risk_notes = card.get("risk_management_notes") if isinstance(card.get("risk_management_notes"), list) else []
    real_risk = [str(r).strip() for r in risk_notes if isinstance(r, str) and len(str(r).strip()) > 10]
    if real_risk:
        sections.append("**Risk Management:**")
        for r in real_risk[:4]:
            sections.append(f"- {r[:200]}")

    conditions = card.get("explicit_conditions") if isinstance(card.get("explicit_conditions"), list) else []
    real_conditions = [str(c).strip() for c in conditions if isinstance(c, str) and len(str(c).strip()) > 15]
    if real_conditions:
        sections.append("**Entry/Exit Conditions:**")
        for c in real_conditions[:6]:
            sections.append(f"- {c[:200]}")

    indicators = card.get("indicators_mentioned") if isinstance(card.get("indicators_mentioned"), list) else []
    ind = [str(i).strip() for i in indicators if str(i).strip()]
    if ind:
        sections.append(f"**Indicators:** {', '.join(ind[:10])}")

    params = card.get("parameters_set") if isinstance(card.get("parameters_set"), list) else []
    param_strs = []
    for p in params[:5]:
        if isinstance(p, dict):
            name = str(p.get("name") or "?")
            val = str(p.get("value") or "?")
            param_strs.append(f"{name}={val}")
    if param_strs:
        sections.append(f"**Parameters:** {', '.join(param_strs)}")

    tfs = card.get("timeframes_mentioned") if isinstance(card.get("timeframes_mentioned"), list) else []
    assets = card.get("assets_mentioned") if isinstance(card.get("assets_mentioned"), list) else []
    meta = []
    if tfs:
        meta.append(f"Timeframes: {', '.join(str(x) for x in tfs[:5])}")
    if assets:
        meta.append(f"Assets: {', '.join(str(x) for x in assets[:5])}")
    if meta:
        sections.append(f"**Context:** {' | '.join(meta)}")

    if len(sections) < 2:
        snippet = raw_text[:800].strip()
        if len(snippet) > 100:
            sections.append(f"**Raw Concepts:** {snippet}...")

    if not sections:
        return None

    return {
        "id": card_id,
        "title": title,
        "author": author,
        "source_ref": source_ref,
        "source_type": source_type,
        "created": created,
        "created_at": created_full,
        "content": "\n".join(sections),
    }


def _build_digest(entries: list[dict]) -> str:
    lines = [
        "# Research Digest",
        "",
        "> Trading concepts extracted from YouTube videos and TradingView research.",
        "> Updated automatically. Quandalf reads this each cycle for strategy inspiration.",
        "> This is a rolling digest — oldest entries drop off as new ones arrive.",
        "",
        f"**Last updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Entries:** {len(entries)}",
        "",
        "---",
        "",
    ]

    for i, entry in enumerate(entries, 1):
        lines.append(f"## {i}. {entry['title']}")
        lines.append(f"*{entry['author']} | {entry['source_type']} | {entry['created']}*")
        if entry.get("source_ref"):
            lines.append(f"Source: {entry['source_ref']}")
        lines.append("")
        lines.append(entry["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def run() -> None:
    seen_before = _load_seen()

    all_cards: list[Path] = []
    if RESEARCH_DIR.exists():
        for date_dir in sorted(RESEARCH_DIR.iterdir()):
            if not date_dir.is_dir():
                continue
            all_cards.extend(sorted(date_dir.glob("*.research_card.json")))

    entries: list[dict] = []
    seen_now: set[str] = set()

    for card_path in all_cards:
        entry = _extract_entry(card_path)
        if not entry:
            continue
        entries.append(entry)
        seen_now.add(entry["id"])

    if not entries:
        print(json.dumps({"ok": True, "entries": 0, "message": "No cards with sufficient content"}))
        _save_seen(seen_now)
        return

    def _sort_key(e: dict):
        return str(e.get("created_at") or "")

    entries.sort(key=_sort_key)
    entries = entries[-MAX_ENTRIES:]

    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(_build_digest(entries), encoding="utf-8")
    _save_seen(seen_now)

    print(
        json.dumps(
            {
                "ok": True,
                "total_cards_scanned": len(all_cards),
                "entries_in_digest": len(entries),
                "new_entries": len(seen_now - seen_before),
                "digest_path": str(DIGEST_PATH),
            }
        )
    )


if __name__ == "__main__":
    run()
