#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
