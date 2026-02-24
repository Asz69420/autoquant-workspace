#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MAX_RC_JSON = 40 * 1024
MAX_IR_JSON = 60 * 1024
MAX_RAW = 200 * 1024
MAX_PINE = 200 * 1024
MAX_INDEX = 200


def must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def check_size(path: Path, cap: int, label: str) -> None:
    must(path.exists(), f"Missing {label}: {path}")
    must(path.stat().st_size <= cap, f"{label} too large: {path}")


def words_count(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", s))


def similarity(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9']+", a.lower()))
    tb = set(re.findall(r"[a-z0-9']+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-card")
    ap.add_argument("--indicator-record")
    ap.add_argument("--linkmap")
    ap.add_argument("--research-index", default="artifacts/research/INDEX.json")
    ap.add_argument("--indicator-index", default="artifacts/indicators/INDEX.json")
    args = ap.parse_args()

    if args.research_card:
        rc_path = Path(args.research_card)
        check_size(rc_path, MAX_RC_JSON, "ResearchCard JSON")
        rc = json.loads(rc_path.read_text(encoding="utf-8"))
        must(rc.get("sha256"), "ResearchCard sha256 missing")
        rp = rc.get("raw_pointer")
        if rp:
            check_size(Path(rp), MAX_RAW, "Research raw")

        bullets = rc.get("summary_bullets", [])
        for b in bullets:
            must(words_count(str(b)) >= 6, "summary_bullets contains fragment (<6 words)")
        for i in range(len(bullets)):
            for j in range(i + 1, len(bullets)):
                must(similarity(str(bullets[i]), str(bullets[j])) < 0.85, "summary_bullets contains repeated/near-identical fragments")

        raw_text = ""
        if rp:
            raw_path = Path(rp)
            if raw_path.exists():
                raw_text = raw_path.read_text(encoding="utf-8", errors="ignore")

        if rp and not rc.get("creator_notes"):
            print("WARN: creator_notes missing while transcript/raw exists")

        comps = rc.get("strategy_components") or []
        if words_count(raw_text) > 300 and not comps:
            must(False, "strategy_components missing for transcript >300 words")

        if words_count(raw_text) > 300 and comps:
            ui_terms = ["click", "indicators", "settings", "style tab", "search"]
            ui_count = sum(1 for c in comps if any(t in str(c.get("description", "")).lower() for t in ui_terms))
            if ui_count / max(len(comps), 1) > 0.5:
                must(False, "more than 50% of strategy_components are UI/navigation language")

        if re.search(r"\bset\s+it\s+at\b", raw_text, re.I) and not rc.get("parameters_set"):
            print("WARN: parameters_set missing despite transcript containing 'set it at'")

        structured = [x for x in (rc.get("explicit_conditions") or []) if any(k in str(x).lower() for k in ["require", "confirm", "entry:", "stop:", "target:", "above 30", "center line"])]
        if len(structured) < 2:
            print("WARN: fewer than 2 structured entry/confirmation conditions detected")

    if args.indicator_record:
        ir_path = Path(args.indicator_record)
        check_size(ir_path, MAX_IR_JSON, "IndicatorRecord JSON")
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
        must(ir.get("sha256"), "IndicatorRecord sha256 missing")
        sp = ir.get("source_pointer")
        if sp:
            check_size(Path(sp), MAX_PINE, "Indicator pine")

    for idx in [Path(args.research_index), Path(args.indicator_index)]:
        if idx.exists():
            entries = json.loads(idx.read_text(encoding="utf-8"))
            must(isinstance(entries, list), f"Index not a list: {idx}")
            must(len(entries) <= MAX_INDEX, f"Index exceeds {MAX_INDEX}: {idx}")

    if args.linkmap:
        lm_path = Path(args.linkmap)
        lm = json.loads(lm_path.read_text(encoding="utf-8"))
        must(Path(lm["research_card_path"]).exists(), "linkmap research_card_path missing")
        for p in lm.get("indicator_record_paths", []):
            must(Path(p).exists(), f"linkmap indicator missing: {p}")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
