#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-card-path", required=True)
    ap.add_argument("--indicator-record-paths", default="[]")
    ap.add_argument("--output-root", default="artifacts/links")
    args = ap.parse_args()

    rc_path = Path(args.research_card_path)
    card = json.loads(rc_path.read_text(encoding="utf-8-sig"))
    hints = card.get("tv_search_hints", [])
    indicator_paths = json.loads(args.indicator_record_paths)

    day = datetime.now().strftime("%Y%m%d")
    out_dir = Path(args.output_root) / day
    out_dir.mkdir(parents=True, exist_ok=True)

    link_id = card.get("id", rc_path.stem)
    out = {
        "research_card_path": str(rc_path).replace('\\', '/'),
        "indicator_record_paths": indicator_paths,
        "grabber_queue": [
            {
                "hint": h.get("name"),
                "author_hint": h.get("author_hint"),
                "keywords": h.get("keywords", []),
                "confidence": h.get("confidence"),
            }
            for h in hints
        ],
    }
    out_path = out_dir / f"{link_id}.linkmap.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"linkmap_path": str(out_path).replace('\\', '/')}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
