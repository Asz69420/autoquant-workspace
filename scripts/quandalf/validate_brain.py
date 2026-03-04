#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRAIN_ROOT = ROOT / "brain"
OBJECT_DIRS = {
    "fact": BRAIN_ROOT / "facts",
    "rule": BRAIN_ROOT / "rules",
    "constraint": BRAIN_ROOT / "constraints",
    "failure": BRAIN_ROOT / "failures",
}
SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


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
        try:
            return int(text)
        except Exception:
            return text
    if re.fullmatch(r"-?\d+\.\d+", text):
        try:
            return float(text)
        except Exception:
            return text
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


def _validate_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def validate_with_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        import jsonschema  # type: ignore

        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: str(e.path))
        return [f"schema:{'/'.join([str(p) for p in err.path]) or '<root>'}:{err.message}" for err in errors]
    except Exception:
        issues: list[str] = []
        for key in schema.get("required", []):
            if key not in data:
                issues.append(f"schema:{key}:is required")
        properties = schema.get("properties", {})
        for key, rules in properties.items():
            if key not in data:
                continue
            value = data[key]
            typ = rules.get("type")
            if typ and not _validate_type(value, typ):
                issues.append(f"schema:{key}:expected {typ}")
                continue
            if "const" in rules and value != rules["const"]:
                issues.append(f"schema:{key}:must equal {rules['const']}")
            enum = rules.get("enum")
            if enum and value not in enum:
                issues.append(f"schema:{key}:must be one of {enum}")
            if isinstance(value, (int, float)):
                if "minimum" in rules and value < rules["minimum"]:
                    issues.append(f"schema:{key}:must be >= {rules['minimum']}")
                if "maximum" in rules and value > rules["maximum"]:
                    issues.append(f"schema:{key}:must be <= {rules['maximum']}")
            if isinstance(value, str):
                if "minLength" in rules and len(value) < rules["minLength"]:
                    issues.append(f"schema:{key}:minLength {rules['minLength']}")
            if isinstance(value, list):
                if "minItems" in rules and len(value) < rules["minItems"]:
                    issues.append(f"schema:{key}:minItems {rules['minItems']}")
                item_rules = rules.get("items", {})
                item_type = item_rules.get("type")
                item_enum = item_rules.get("enum")
                for idx, item in enumerate(value):
                    if item_type and not _validate_type(item, item_type):
                        issues.append(f"schema:{key}[{idx}]:expected {item_type}")
                    if item_enum and item not in item_enum:
                        issues.append(f"schema:{key}[{idx}]:must be one of {item_enum}")
        return issues


def validate_journal_pointer_policy(journal_dir: Path, root: Path) -> list[str]:
    warns: list[str] = []
    for entry in sorted(journal_dir.glob("*.md")):
        fm, body = parse_frontmatter(entry)
        pointers = fm.get("pointers")
        if not isinstance(pointers, list) or len(pointers) == 0:
            warns.append(f"journal:{entry.relative_to(root)} missing pointers[]")
        if len(body) > 600:
            warns.append(f"journal:{entry.relative_to(root)} body too long for pointer-only phase")
    return warns


def load_action_run_ids(actions_path: Path) -> set[str]:
    run_ids: set[str] = set()
    if not actions_path.exists():
        return run_ids
    for line in actions_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except Exception:
            continue
        rid = str(obj.get("run_id", "")).strip()
        if rid:
            run_ids.add(rid)
    return run_ids


def evidence_path_satisfied(root: Path, evidence_path: str, action_run_ids: set[str]) -> tuple[bool, bool]:
    p = (root / str(evidence_path)).resolve()
    if p.exists():
        return True, False

    norm = str(evidence_path).replace('\\', '/').lstrip('./')
    if norm.startswith("data/logs/outbox/") and norm.endswith(".json"):
        parts = Path(norm).name.split("___")
        if len(parts) >= 2:
            run_id = parts[1].strip()
            if run_id and run_id in action_run_ids:
                return True, True

    return False, False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()

    root = Path(args.root).resolve()
    brain_root = root / "brain"

    errors: list[str] = []
    warns: list[str] = []
    object_records: list[tuple[Path, dict[str, Any], str]] = []
    action_run_ids = load_action_run_ids(root / "data" / "logs" / "actions.ndjson")

    for obj_type, directory in OBJECT_DIRS.items():
        dir_path = root / directory.relative_to(ROOT)
        schema_path = SCHEMA_DIR / f"{obj_type}.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        if not dir_path.exists():
            continue

        for md_file in sorted(dir_path.glob("*.md")):
            fm, _body = parse_frontmatter(md_file)
            rel = md_file.relative_to(root)
            if not fm:
                errors.append(f"{rel}: missing/invalid frontmatter")
                continue

            schema_issues = validate_with_schema(fm, schema)
            for issue in schema_issues:
                errors.append(f"{rel}: {issue}")

            if fm.get("type") != obj_type:
                errors.append(f"{rel}: type mismatch expected={obj_type} got={fm.get('type')}")

            evidence_paths = fm.get("evidence_paths", [])
            if isinstance(evidence_paths, list):
                for ep in evidence_paths:
                    ok, via_actions = evidence_path_satisfied(root, str(ep), action_run_ids)
                    if not ok:
                        errors.append(f"{rel}: missing evidence path {ep}")
                    elif via_actions:
                        warns.append(f"{rel}: evidence path drained from outbox but run_id exists in actions.ndjson ({ep})")
            object_records.append((md_file, fm, obj_type))

    ids: dict[str, Path] = {}
    for path, fm, _ in object_records:
        oid = str(fm.get("id", "")).strip()
        if not oid:
            continue
        if oid in ids:
            errors.append(f"{path.relative_to(root)}: duplicate id {oid}")
        ids[oid] = path

    for path, fm, _ in object_records:
        rel = path.relative_to(root)
        for field in ("supersedes", "superseded_by"):
            refs = fm.get(field, [])
            if isinstance(refs, list):
                for rid in refs:
                    if rid not in ids:
                        errors.append(f"{rel}: unresolved {field} ref {rid}")
        for field in ("supporting_ids", "contradictory_ids"):
            refs = fm.get(field, [])
            if isinstance(refs, list):
                for rid in refs:
                    if rid not in ids:
                        warns.append(f"{rel}: unresolved optional {field} ref {rid}")
        if "validated_at" not in fm:
            warns.append(f"{rel}: missing validated_at")

    journal_dir = brain_root / "journal"
    if journal_dir.exists():
        warns.extend(validate_journal_pointer_policy(journal_dir, root))

    status = "OK"
    if errors:
        status = "FAIL"
    elif warns:
        status = "WARN"

    summary = f"BRAIN_VALIDATE [{status}] counts=objects:{len(object_records)},fail:{len(errors)},warn:{len(warns)}"
    print(summary)

    for issue in errors:
        print(f"[FAIL] {issue}")
    for issue in warns:
        print(f"[WARN] {issue}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())



