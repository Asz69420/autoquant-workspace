#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_objects(index_path: Path) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if not index_path.exists():
        return objects
    for line in index_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        objects.append(json.loads(line))
    return objects


def intersects(values: list[str], target: set[str]) -> bool:
    return bool(set(values).intersection(target))


def sort_key_object(obj: dict[str, Any]) -> tuple[str, str]:
    return (str(obj.get("updated_at", "")), str(obj.get("id", "")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--scope-id", default="")
    ap.add_argument("--asset", default="")
    ap.add_argument("--timeframe", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--max-objects", type=int, default=12)
    ap.add_argument("--supporting-n", type=int, default=3)
    ap.add_argument("--contradictory-n", type=int, default=2)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    index_dir = root / "brain" / "index"

    objects = load_objects(index_dir / "objects.jsonl")
    by_id = {str(o.get("id")): o for o in objects if o.get("id")}

    query_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.asset:
        query_tags.append(args.asset)
    if args.timeframe:
        query_tags.append(args.timeframe)
    qset = set(query_tags)

    primary: list[dict[str, Any]] = []
    if args.scope_id and args.scope_id in by_id:
        primary.append(by_id[args.scope_id])
    else:
        candidates = [o for o in objects if o.get("type") in {"fact", "rule"}]
        if qset:
            candidates = [o for o in candidates if intersects(o.get("tags", []), qset)]
        candidates = sorted(candidates, key=sort_key_object, reverse=True)
        primary = candidates[:1]

    supporting_ids: list[str] = []
    contradictory_ids: list[str] = []
    for p in primary:
        supporting_ids.extend([str(x) for x in p.get("supporting_ids", [])])
        contradictory_ids.extend([str(x) for x in p.get("contradictory_ids", [])])

    supporting = [by_id[sid] for sid in sorted(set(supporting_ids)) if sid in by_id][: max(args.supporting_n, 0)]
    contradictory = [by_id[cid] for cid in sorted(set(contradictory_ids)) if cid in by_id][: max(args.contradictory_n, 0)]

    selector_tags = set(qset)
    for p in primary:
        selector_tags.update([str(t) for t in p.get("tags", [])])

    constraints = [o for o in objects if o.get("type") == "constraint"]
    failures = [o for o in objects if o.get("type") == "failure"]

    if selector_tags:
        constraints = [o for o in constraints if intersects(o.get("tags", []), selector_tags)]
        failures = [o for o in failures if intersects(o.get("tags", []), selector_tags)]

    constraints = sorted(constraints, key=sort_key_object, reverse=True)
    failures = sorted(failures, key=sort_key_object, reverse=True)

    journal_tail = load_json(index_dir / "journal_tail.json", {"entries": []})
    journal_entries = journal_tail.get("entries", [])
    journal_last2 = sorted(journal_entries, key=lambda j: (str(j.get("ts", "")), str(j.get("id", ""))))[-2:]

    ordered: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for bucket in (primary, supporting, contradictory, constraints, failures):
        for obj in bucket:
            oid = str(obj.get("id", ""))
            if not oid or oid in seen_ids:
                continue
            seen_ids.add(oid)
            ordered.append(obj)

    max_objects = max(args.max_objects, 1)
    ordered = ordered[:max_objects]

    validation_timestamps = {
        str(obj.get("id")): obj.get("validated_at", "")
        for obj in ordered
        if obj.get("id")
    }

    missing_contradictions = len(contradictory) == 0
    warn = missing_contradictions

    generated_candidates: list[str] = []
    generated_candidates.extend([str(j.get("ts", "")) for j in journal_last2 if j.get("ts")])
    generated_candidates.extend([str(o.get("validated_at", "")) for o in ordered if o.get("validated_at")])
    generated_candidates.extend([str(o.get("updated_at", "")) for o in ordered if o.get("updated_at")])
    generated_at = sorted(generated_candidates)[-1] if generated_candidates else ""

    payload = {
        "schema_version": "quandalf-working-set/v1",
        "generated_at": generated_at,
        "scope": {
            "scope_id": args.scope_id,
            "asset": args.asset,
            "timeframe": args.timeframe,
            "tags": sorted(set(query_tags)),
        },
        "counts": {
            "primary": len(primary),
            "supporting": len(supporting),
            "contradictory": len(contradictory),
            "constraints": len(constraints),
            "failures": len(failures),
            "objects_included": len(ordered),
        },
        "primary": primary,
        "supporting": supporting,
        "contradictory": contradictory,
        "constraints": constraints,
        "failures": failures,
        "journal_last2": journal_last2,
        "objects": ordered,
        "validation_timestamps": validation_timestamps,
        "missing_contradictions": missing_contradictions,
        "warn": warn,
        "warn_reasons": ["missing_contradictions"] if missing_contradictions else [],
    }

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = root / out_path
    else:
        key = args.scope_id or "default"
        out_path = root / "brain" / "working_sets" / f"{key}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if out_path.exists() and out_path.read_text(encoding="utf-8", errors="ignore") == content:
        state = "UNCHANGED"
    else:
        out_path.write_text(content, encoding="utf-8")
        state = "WROTE"

    print(json.dumps({"ok": True, "output": str(out_path.relative_to(root)).replace('\\', '/'), "state": state, "warn": warn}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
