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
TS_PREFIX_RE = re.compile(r"^\s*(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—|]?\s*(?P<text>.+)$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


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


def norm_spaces(s: str) -> str:
    return " ".join(s.strip().split())


def words_count(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", s))


def similarity(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9']+", a.lower()))
    tb = set(re.findall(r"[a-z0-9']+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def split_sentences(raw: str) -> list[str]:
    chunks = [norm_spaces(x) for x in raw.splitlines() if norm_spaces(x)]
    merged: list[str] = []
    cur = ""
    for c in chunks:
        cur = f"{cur} {c}".strip() if cur else c
        if re.search(r"[.!?]$", c) or words_count(cur) >= 18:
            merged.append(cur)
            cur = ""
    if cur:
        merged.append(cur)

    parts: list[str] = []
    for m in merged:
        parts.extend([norm_spaces(p) for p in SENTENCE_SPLIT_RE.split(m) if norm_spaces(p)])

    out: list[str] = []
    bad_endings = {"if", "and", "or", "to", "on", "in", "with", "for", "that", "which", "based", "most"}
    for p in parts:
        if words_count(p) < 6:
            continue
        if not re.search(r"[.!?]$", p):
            p = p + "."
        last_word = re.findall(r"[a-zA-Z]+", p.lower())[-1] if re.findall(r"[a-zA-Z]+", p.lower()) else ""
        if last_word in bad_endings:
            continue
        if any(similarity(p, x) >= 0.85 for x in out):
            continue
        out.append(p[:500])
    return out


def extract_creator_notes(raw: str, max_items: int = 12) -> list[dict]:
    notes: list[dict] = []
    sentences = split_sentences(raw)
    for s in sentences:
        ts = None
        text = s
        m = TS_PREFIX_RE.match(s)
        if m:
            text = norm_spaces(m.group("text"))
            ts_raw = m.group("ts")
            if len(ts_raw.split(":")) == 2:
                ts = f"00:{ts_raw}"
            else:
                ts = ts_raw
        if words_count(text) < 6:
            continue
        if any(similarity(text, n["quote"]) >= 0.9 for n in notes):
            continue
        quote = text[:200]
        note = f"Creator explains: {text}"[:160]
        notes.append({"timestamp": ts, "quote": quote, "note": note})
        if len(notes) >= max_items:
            break
    return notes


def extract_rules(sentences: list[str], limit: int = 20) -> list[str]:
    rule_markers = ("rule", "wait", "enter", "exit", "avoid", "use", "search", "click")
    rules: list[str] = []
    for s in sentences:
        l = s.lower()
        if any(m in l for m in rule_markers):
            if not any(similarity(s, r) >= 0.88 for r in rules):
                rules.append(s[:500])
        if len(rules) >= limit:
            break
    if not rules:
        return ["Not specified in content."]
    return rules[:limit]


def extract_indicator_hints(raw: str) -> tuple[list[str], list[dict]]:
    names: list[str] = []
    hints: list[dict] = []

    author_global = None
    m_auth = re.search(r"\bwritten\s+by\s+([A-Za-z][A-Za-z0-9\- ]{2,60})", raw, re.I)
    if m_auth:
        author_global = norm_spaces(m_auth.group(1).strip(" .,:;"))

    candidates: list[tuple[str, float]] = []
    for m in re.finditer(r"\bsearch\s+([A-Za-z][A-Za-z0-9\- ]{3,80})", raw, re.I):
        n = norm_spaces(re.split(r"[.,;:!?]", m.group(1))[0])
        if words_count(n) >= 3:
            candidates.append((n, 0.93))

    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9\- ]{3,80}\s+pressure\s+index)\b", raw, re.I):
        n = norm_spaces(m.group(1))
        if words_count(n) >= 3:
            candidates.append((n, 0.88))

    for n, conf in candidates:
        if any(similarity(n, x) >= 0.75 for x in names):
            continue
        names.append(n)
        hint = {
            "name": n,
            "keywords": re.findall(r"[a-z0-9]+", n.lower())[:5],
            "confidence": conf,
        }
        if author_global:
            hint["author_hint"] = author_global
        hints.append(hint)
        if len(names) >= 20 or len(hints) >= 10:
            break

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

    sentences = split_sentences(raw_trunc)
    bullets = sentences[:10]
    rules = extract_rules(sentences, 20)
    creator_notes = extract_creator_notes(raw_trunc, 12)
    indicators, hints = extract_indicator_hints(raw_trunc)

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
        "creator_notes": creator_notes if creator_notes else None,
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
