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

FLUFF_PATTERNS = [
    r"\bsubscrib\w*\b",
    r"\blike (the )?video\b",
    r"\bwatch (this )?video until the end\b",
    r"\bwatch\b.*\bend\b",
    r"\bproud to announce\b",
    r"\bpublished a book\b",
    r"\blink is in the description\b",
    r"\bthank you for watching\b",
    r"\bgood luck with your trading\b",
]

COND_PATTERNS = [
    r"\bwhen\b.+",
    r"\bif\b.+",
    r"\bwe enter\b.+",
    r"\bwe could enter\b.+",
    r"\bstop loss\b.+",
    r"\bprofit target\b.+",
    r"\brisk\b.+",
]

NUM_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "fifteen": "15",
    "thirty": "30", "fifty": "50", "hundred": "100", "two hundred": "200",
}


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


def is_fluff(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in FLUFF_PATTERNS)


def to_sentences(raw: str) -> list[str]:
    text = norm_spaces(raw.replace("\n", " "))
    parts = [norm_spaces(p) for p in re.split(r"(?<=[.!?])\s+", text) if norm_spaces(p)]
    out: list[str] = []
    for p in parts:
        if words_count(p) < 6:
            continue
        if not p.endswith((".", "!", "?")):
            p += "."
        if is_fluff(p):
            continue
        if any(similarity(p, x) >= 0.88 for x in out):
            continue
        out.append(p[:500])
    return out


def extract_creator_notes(raw: str, max_items: int = 12) -> list[dict]:
    notes: list[dict] = []
    for s in to_sentences(raw):
        ts = None
        m = TS_PREFIX_RE.match(s)
        text = norm_spaces(m.group("text")) if m else s
        if m:
            ts_raw = m.group("ts")
            ts = f"00:{ts_raw}" if len(ts_raw.split(":")) == 2 else ts_raw
        if is_fluff(text):
            continue
        quote = text[:200]
        note = f"Meaning: {text}"[:160]
        if any(similarity(quote, n["quote"]) >= 0.9 for n in notes):
            continue
        notes.append({"timestamp": ts, "quote": quote, "note": note})
        if len(notes) >= max_items:
            break
    return notes


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


def extract_rules(sentences: list[str], limit: int = 20) -> list[str]:
    rules: list[str] = []
    for s in sentences:
        l = s.lower()
        if any(re.search(p, l) for p in COND_PATTERNS) or "rule" in l:
            if not any(similarity(s, r) >= 0.88 for r in rules):
                rules.append(s[:500])
        if len(rules) >= limit:
            break
    return rules if rules else ["Not specified in content."]


def normalize_num_word(v: str) -> str:
    x = v.strip().lower()
    return NUM_WORDS.get(x, v.strip())


def extract_parameters(raw: str, max_items: int = 20) -> list[dict]:
    params: list[dict] = []
    text = raw.replace("\n", " ")
    pat = re.compile(
        r"for\s+(?:the\s+)?(?P<name>[a-zA-Z][a-zA-Z0-9\- ]{2,40}?)\s+we\s+set\s+it\s+at\s+(?P<value>[a-zA-Z0-9.%-]{1,20})",
        re.I,
    )
    for m in pat.finditer(text):
        name = norm_spaces(m.group("name")).lower()
        if name.startswith("the "):
            name = name[4:]
        value = normalize_num_word(m.group("value").strip().strip(".,;:"))
        context = norm_spaces(text[max(0, m.start()-30):m.end()+40])
        item = {"name": name[:80], "value": value[:40], "context": context[:120]}
        if any(item["name"] == x["name"] and item["value"] == x["value"] for x in params):
            continue
        params.append(item)
        if len(params) >= max_items:
            break
    return params


def normalize_statement(s: str) -> str:
    x = norm_spaces(s)
    repl = [
        (r"\bwe should have\b", "Require"),
        (r"\bwe could enter\b", "Entry:"),
        (r"\bwe enter\b", "Entry:"),
        (r"\bstop loss below\b", "Stop: below"),
        (r"\bprofit target at risk[- ]to[- ]reward ratio of two\b", "Target: 2R"),
    ]
    for pat, rep in repl:
        x = re.sub(pat, rep, x, flags=re.I)
    x = re.sub(r"\s+", " ", x).strip()
    if not x.endswith((".", "!", "?")):
        x += "."
    return x[:500]


def classify_component(s: str) -> str:
    l = s.lower()
    if any(k in l for k in ["risk", "stop:", "stop loss", "target:", "profit target", "risk-to-reward", "1%"]):
        return "risk"
    if any(k in l for k in ["trend", "longer macd", "downtrend", "uptrend"]):
        return "trend"
    if any(k in l for k in ["shorter macd", "momentum", "histogram"]):
        return "momentum"
    if any(k in l for k in ["confirmed", "require", "above 30", "control level"]):
        return "confirmation"
    if any(k in l for k in ["rejected", "avoid", "doesn't show", "filter"]):
        return "filter"
    return "other"


def extract_conditions_and_components(sentences: list[str]) -> tuple[list[str], list[dict], list[str]]:
    conditions: list[str] = []
    components: list[dict] = []
    risk_notes: list[str] = []

    ui_noise = ["click on", "indicators", "style tab", "settings", "search "]
    action_keywords = ["center line", "above 30", "confirmed", "entry", "stop", "target", "risk", "long position", "short position", "goes above", "goes below"]

    for s in sentences:
        if is_fluff(s):
            continue
        ns = normalize_statement(s)
        l = ns.lower()

        if any(n in l for n in ui_noise) and not any(k in l for k in ["enter", "stop", "target", "risk", "confirmed", "above 30"]):
            continue

        cond = any(re.search(p, l) for p in COND_PATTERNS) and any(k in l for k in action_keywords)
        if cond and not any(similarity(ns, c) >= 0.88 for c in conditions):
            conditions.append(ns)

        ctype = classify_component(ns)
        if ctype in {"trend", "momentum", "confirmation", "filter", "risk"}:
            desc = ns
            if "above 30" in l and "bull" in l:
                desc = "Bullish pressure must exceed 30 to confirm long setup."
            elif "above 30" in l and "red" in l:
                desc = "Bearish pressure must exceed 30 to confirm short setup."
            elif "entry:" in l:
                desc = ns.replace("Entry:", "Entry:").strip()
            elif "stop:" in l:
                desc = "Stop: below previous swing low."
            elif "target: 2r" in l or "risk-to-reward ratio of two" in l:
                desc = "Target: 2R."
            entry = {"type": ctype, "description": desc[:220]}
            if not any(similarity(entry["description"], x["description"]) >= 0.88 for x in components):
                components.append(entry)

        if ctype == "risk":
            rn = None
            if "stop" in l:
                rn = "Stop below previous swing low."
            elif "target" in l or "2r" in l or "risk-to-reward ratio of two" in l:
                rn = "Target at 2R."
            elif "1%" in l or "1% roll" in l:
                rn = "Apply 1% risk rule."
            elif "manage your risk" in l:
                rn = "Use explicit risk management on every trade."
            if rn and not any(similarity(rn, r) >= 0.9 for r in risk_notes):
                risk_notes.append(rn[:220])

        if len(conditions) >= 20 and len(components) >= 20 and len(risk_notes) >= 10:
            break

    return conditions[:20], components[:20], risk_notes[:10]


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

    sentences = to_sentences(raw_trunc)
    bullets = sentences[:10]
    creator_notes = extract_creator_notes(raw_trunc, 12)
    rules = extract_rules(sentences, 20)
    indicators, hints = extract_indicator_hints(raw_trunc)

    parameters_set = extract_parameters(raw_trunc, 20)
    explicit_conditions, strategy_components, risk_management_notes = extract_conditions_and_components(sentences)

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
        "parameters_set": parameters_set if parameters_set else None,
        "strategy_components": strategy_components if strategy_components else None,
        "explicit_conditions": explicit_conditions if explicit_conditions else None,
        "risk_management_notes": risk_management_notes if risk_management_notes else None,
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
