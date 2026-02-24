#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 40 * 1024
MAX_RAW_BYTES = 200 * 1024
MAX_INDEX = 200

TF_RE = re.compile(r"\b(1m|3m|5m|15m|30m|45m|1h|2h|4h|1d|1w|1mo|daily|weekly|monthly)\b", re.I)
ASSET_RE = re.compile(r"\b(BTC|ETH|SOL|XRP|EURUSD|GBPUSD|SPX|NASDAQ|AAPL|TSLA|GOLD|XAUUSD)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_id(source_ref: str, raw: str) -> str:
    digest = hashlib.sha256(f"{source_ref}|{raw[:4000]}".encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"research-{datetime.now().strftime('%Y%m%d')}-{digest}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def truncate_text(text: str, max_bytes: int) -> tuple[str, bool]:
    data = text.encode("utf-8", errors="ignore")
    if len(data) <= max_bytes:
        return text, False
    trimmed = data[:max_bytes]
    while True:
        try:
            return trimmed.decode("utf-8"), True
        except UnicodeDecodeError:
            trimmed = trimmed[:-1]


def pick_lines(raw: str, limit: int, max_len: int) -> list[str]:
    out = []
    for line in [l.strip(" -\t") for l in raw.splitlines() if l.strip()]:
        if line not in out:
            out.append(line[:max_len])
        if len(out) >= limit:
            break
    return out


def extract_indicator_hints(raw: str) -> tuple[list[str], list[dict]]:
    names: list[str] = []
    hints: list[dict] = []
    patterns = [
        r"\b(?:indicator|using|use|called|named)\s+([A-Z][A-Za-z0-9\- ]{2,60})",
        r"\b([A-Z][A-Za-z0-9\- ]{2,60})\s+(?:indicator|oscillator|strategy)\b",
    ]
    for p in patterns:
        for m in re.finditer(p, raw):
            n = " ".join(m.group(1).split())
            if n.lower() in {"the", "this", "that"}:
                continue
            if n not in names:
                names.append(n)
                hints.append({
                    "name": n,
                    "keywords": n.lower().split()[:4],
                    "confidence": 0.75,
                })
            if len(names) >= 20 or len(hints) >= 10:
                return names[:20], hints[:10]
    return names[:20], hints[:10]


def update_index(index_path: Path, pointer: str) -> None:
    index = []
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = []
    if pointer in index:
        index.remove(pointer)
    index.insert(0, pointer)
    index = index[:MAX_INDEX]
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-ref", required=True)
    ap.add_argument("--source-type", default="text")
    ap.add_argument("--raw-text", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--tags", default="[]")
    ap.add_argument("--output-root", default="artifacts/research")
    args = ap.parse_args()

    raw_trunc, raw_truncated = truncate_text(args.raw_text, MAX_RAW_BYTES)
    rid = make_id(args.source_ref, raw_trunc)
    day = datetime.now().strftime("%Y%m%d")
    out_dir = Path(args.output_root) / day
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / f"{rid}.raw.txt"
    raw_path.write_text(raw_trunc, encoding="utf-8")

    indicators, hints = extract_indicator_hints(raw_trunc)
    rules = pick_lines(raw_trunc, 20, 500)
    bullets = pick_lines(raw_trunc, 10, 500)

    timeframes = list(dict.fromkeys([m.group(1).lower() for m in TF_RE.finditer(raw_trunc)]))[:20]
    assets = list(dict.fromkeys([m.group(1).upper() for m in ASSET_RE.finditer(raw_trunc)]))[:20]
    tags = json.loads(args.tags)

    card = {
        "schema_version": "1.0",
        "id": rid,
        "created_at": now_iso(),
        "source_type": args.source_type,
        "source_ref": args.source_ref,
        "title": args.title or None,
        "author": args.author or None,
        "summary_bullets": bullets,
        "extracted_rules": rules,
        "indicators_mentioned": indicators,
        "tv_search_hints": hints,
        "timeframes_mentioned": timeframes,
        "assets_mentioned": assets,
        "tags": tags[:20],
        "raw_pointer": str(raw_path).replace('\\', '/'),
        "sha256": sha256_text(raw_trunc),
        "truncated": raw_truncated,
    }
    card = {k: v for k, v in card.items() if v is not None}

    payload = json.dumps(card, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        raise SystemExit("ResearchCard exceeds 40KB")

    card_path = out_dir / f"{rid}.research_card.json"
    card_path.write_text(payload, encoding="utf-8")

    update_index(Path(args.output_root) / "INDEX.json", str(card_path).replace('\\', '/'))

    print(json.dumps({"research_card_path": str(card_path).replace('\\', '/'), "raw_path": str(raw_path).replace('\\', '/')}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
