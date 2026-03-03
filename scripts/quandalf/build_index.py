#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text == "":
        return ""
    if text.startswith("[") and text.endswith("]"):
        try:
            return json.loads(text)
        except Exception:
            pass
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


def parse_simple_yaml(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_list_key:
            data.setdefault(current_list_key, [])
            data[current_list_key].append(parse_scalar(stripped[2:]))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = parse_scalar(value)
    return data


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8", errors="ignore").lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, text
    fm = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).strip()
    return parse_simple_yaml(fm), body


def write_if_changed(path: Path, content: str) -> str:
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing == content:
            return "UNCHANGED"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "WROTE"


def sort_key_ts(entry: dict[str, Any]) -> tuple[str, str]:
    ts = str(entry.get("ts") or entry.get("updated_at") or "")
    return (ts, str(entry.get("id", "")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--journal-tail", type=int, default=50)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    brain = root / "brain"

    object_files: list[tuple[str, Path]] = []
    for obj_type in ("fact", "rule", "constraint", "failure"):
        dir_path = brain / f"{obj_type}s"
        if not dir_path.exists():
            continue
        for p in sorted(dir_path.glob("*.md")):
            object_files.append((obj_type, p))

    rows: list[dict[str, Any]] = []
    for obj_type, path in sorted(object_files, key=lambda t: t[1].name.lower()):
        fm, _body = parse_frontmatter(path)
        if not fm:
            continue
        row = {
            "id": fm.get("id"),
            "type": fm.get("type", obj_type),
            "title": fm.get("title", ""),
            "status": fm.get("status", ""),
            "confidence": fm.get("confidence"),
            "tags": sorted(fm.get("tags", [])) if isinstance(fm.get("tags"), list) else [],
            "evidence_paths": fm.get("evidence_paths", []) if isinstance(fm.get("evidence_paths"), list) else [],
            "supporting_ids": fm.get("supporting_ids", []) if isinstance(fm.get("supporting_ids"), list) else [],
            "contradictory_ids": fm.get("contradictory_ids", []) if isinstance(fm.get("contradictory_ids"), list) else [],
            "supersedes": fm.get("supersedes", []) if isinstance(fm.get("supersedes"), list) else [],
            "superseded_by": fm.get("superseded_by", []) if isinstance(fm.get("superseded_by"), list) else [],
            "updated_at": fm.get("updated_at", ""),
            "validated_at": fm.get("validated_at", ""),
            "source_path": str(path.relative_to(root)).replace("\\", "/"),
        }
        rows.append(row)

    rows = sorted(rows, key=lambda r: (str(r.get("id", "")), str(r.get("source_path", ""))))

    objects_jsonl = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)
    if objects_jsonl:
        objects_jsonl += "\n"

    index_dir = brain / "index"
    objects_path = index_dir / "objects.jsonl"
    objects_state = write_if_changed(objects_path, objects_jsonl)

    journals: list[dict[str, Any]] = []
    journal_dir = brain / "journal"
    if journal_dir.exists():
        for p in sorted(journal_dir.glob("*.md")):
            fm, body = parse_frontmatter(p)
            journals.append(
                {
                    "id": fm.get("id", p.stem),
                    "ts": fm.get("ts", fm.get("updated_at", "")),
                    "pointers": fm.get("pointers", []) if isinstance(fm.get("pointers"), list) else [],
                    "source_path": str(p.relative_to(root)).replace("\\", "/"),
                    "summary": body[:240],
                }
            )

    journals = sorted(journals, key=sort_key_ts)
    if args.journal_tail > 0:
        journals = journals[-args.journal_tail :]

    deterministic_ts = ""
    if journals:
        deterministic_ts = str(journals[-1].get("ts", ""))
    elif rows:
        deterministic_ts = str(sorted([str(r.get("updated_at", "")) for r in rows])[-1])

    journal_tail_payload = {
        "generated_at": deterministic_ts,
        "count": len(journals),
        "entries": journals,
    }
    journal_path = index_dir / "journal_tail.json"
    journal_state = write_if_changed(journal_path, json.dumps(journal_tail_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "objects": len(rows),
                "journal_entries": len(journals),
                "objects_jsonl": objects_state,
                "journal_tail_json": journal_state,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


