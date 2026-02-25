#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_INDEX = 200
ALLOWED_ROLES = {"trend", "entry", "exit", "confirmation", "regime_gate", "risk"}
SCHEMA_PATH = Path("docs/SCHEMAS/insight_card.schema.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def make_id(title: str, concept: str) -> str:
    digest = hashlib.sha256((title + concept).encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"insight-{digest}"


def validate_lightweight(card: dict) -> None:
    if card.get("schema_version") != "1.0":
        raise SystemExit("schema_version must be 1.0")
    if card.get("source") != "manual":
        raise SystemExit("source must be manual")
    title = str(card.get("title", ""))
    concept = str(card.get("concept", ""))
    if not (1 <= len(title) <= 120):
        raise SystemExit("title length out of bounds")
    if not (1 <= len(concept) <= 2000):
        raise SystemExit("concept length out of bounds")
    tags = card.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 10:
        raise SystemExit("tags must be array <= 10")
    roles = card.get("suggested_roles", [])
    if not isinstance(roles, list) or len(roles) > 6:
        raise SystemExit("suggested_roles must be array <= 6")
    for r in roles:
        if r not in ALLOWED_ROLES:
            raise SystemExit(f"invalid role: {r}")
    conf = card.get("confidence")
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        raise SystemExit("confidence must be number 0..1")
    if card.get("status") not in {"NEW", "PROCESSED"}:
        raise SystemExit("status must be NEW|PROCESSED")
    lra = card.get("last_reviewed_at")
    if lra is not None and not isinstance(lra, str):
        raise SystemExit("last_reviewed_at must be null|string")
    tu = card.get("times_used")
    if not isinstance(tu, int) or tu < 0:
        raise SystemExit("times_used must be integer >= 0")


def validate_with_schema(card: dict) -> None:
    try:
        import jsonschema  # type: ignore
    except Exception:
        validate_lightweight(card)
        return

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(card, schema)


def update_index(index_path: Path, pointer: str) -> int:
    items: list[str] = []
    if index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                items = [str(x) for x in raw]
        except Exception:
            items = []
    if pointer in items:
        items.remove(pointer)
    items.insert(0, pointer)
    items = items[:MAX_INDEX]
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return len(items)


def dedup_cap(values: list[str], max_items: int) -> list[str]:
    out: list[str] = []
    for v in values:
        s = v.strip()
        if s and s not in out:
            out.append(s[:64])
        if len(out) >= max_items:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--roles", default="")
    ap.add_argument("--confidence", type=float, default=0.5)
    ap.add_argument("--output-root", default="artifacts/insights")
    args = ap.parse_args()

    title = args.title.strip()
    concept = args.concept.strip()
    tags = dedup_cap(parse_csv(args.tags), 10)
    roles = dedup_cap(parse_csv(args.roles), 6)

    for r in roles:
        if r not in ALLOWED_ROLES:
            raise SystemExit(f"Invalid role '{r}'. Allowed: {sorted(ALLOWED_ROLES)}")

    cid = make_id(title, concept)
    day = datetime.now().strftime("%Y%m%d")
    out_dir = Path(args.output_root) / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{cid}.insight_card.json"

    card = {
        "schema_version": "1.0",
        "id": cid,
        "created_at": now_iso(),
        "source": "manual",
        "title": title,
        "concept": concept,
        "tags": tags,
        "suggested_roles": roles,
        "confidence": float(args.confidence),
        "status": "NEW",
        "last_reviewed_at": None,
        "times_used": 0,
    }

    validate_with_schema(card)
    out_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    index_path = Path(args.output_root) / "INDEX.json"
    index_len = update_index(index_path, str(out_path).replace("\\", "/"))

    print(json.dumps({"insight_card_path": str(out_path).replace("\\", "/"), "index_len": index_len, "id": cid}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
