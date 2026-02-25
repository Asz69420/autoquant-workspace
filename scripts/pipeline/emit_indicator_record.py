#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 60 * 1024
MAX_SRC_BYTES = 200 * 1024
MAX_INDEX = 200


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def make_id(tv_ref: str, source_code: str) -> str:
    digest = hashlib.sha256(f"{tv_ref}|{source_code[:4000]}".encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"indicator-{datetime.now().strftime('%Y%m%d')}-{digest}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


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


def parse_list(s: str) -> list[str]:
    return [str(x) for x in json.loads(s)]


def minify_pine(source: str) -> str:
    out: list[str] = []
    i = 0
    n = len(source)
    in_block = False
    in_line = False
    in_str = False
    str_q = ""

    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""

        if in_line:
            if ch == "\n":
                in_line = False
                out.append(ch)
            i += 1
            continue

        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
            else:
                i += 1
            continue

        if in_str:
            out.append(ch)
            if ch == str_q and (i == 0 or source[i - 1] != "\\"):
                in_str = False
                str_q = ""
            i += 1
            continue

        if ch in {'"', "'"}:
            in_str = True
            str_q = ch
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block = True
            i += 2
            continue

        out.append(ch)
        i += 1

    text = "".join(out)
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() != ""]
    return "\n".join(lines)


def component_type(source: str) -> str:
    s = source.lower()
    needles = ["strategy(", "strategy.entry", "strategy.exit", "strategy.order"]
    return "STRATEGY" if any(x in s for x in needles) else "INDICATOR"


def size_class_bytes(min_bytes: int) -> str:
    if min_bytes < 20 * 1024:
        return "small"
    if min_bytes < 80 * 1024:
        return "medium"
    return "large"


def size_class_lines(min_lines: int) -> str:
    if min_lines < 200:
        return "small"
    if min_lines < 600:
        return "medium"
    return "large"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tv-ref", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--name", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--version", default="")
    ap.add_argument("--source-code", default="")
    ap.add_argument("--key-inputs", default="[]")
    ap.add_argument("--signals", default="[]")
    ap.add_argument("--notes", default="[]")
    ap.add_argument("--output-root", default="artifacts/indicators")
    args = ap.parse_args()

    src_trunc, src_truncated = truncate_text(args.source_code, MAX_SRC_BYTES)
    src_min = minify_pine(src_trunc)

    raw_bytes = len(src_trunc.encode("utf-8", errors="ignore"))
    raw_lines = len(src_trunc.splitlines()) if src_trunc else 0
    min_bytes = len(src_min.encode("utf-8", errors="ignore"))
    min_lines = len(src_min.splitlines()) if src_min else 0

    p_size_class_bytes = size_class_bytes(min_bytes)
    p_size_class_lines = size_class_lines(min_lines)
    too_large = min_lines > 600 or min_bytes >= 80 * 1024
    too_large_reason = None
    if too_large:
        too_large_reason = "bytes" if min_bytes >= 80 * 1024 else "lines"
    ctype = component_type(src_trunc)

    iid = make_id(args.tv_ref, src_trunc)
    day = datetime.now().strftime("%Y%m%d")
    out_dir = Path(args.output_root) / day
    out_dir.mkdir(parents=True, exist_ok=True)

    source_pointer = None
    source_min_pointer = None
    if src_trunc:
        pine_path = out_dir / f"{iid}.pine.txt"
        pine_path.write_text(src_trunc, encoding="utf-8")
        source_pointer = str(pine_path).replace('\\', '/')

        pine_min_path = out_dir / f"{iid}.pine.min.txt"
        pine_min_path.write_text(src_min, encoding="utf-8")
        source_min_pointer = str(pine_min_path).replace('\\', '/')

    record = {
        "schema_version": "1.0",
        "id": iid,
        "created_at": now_iso(),
        "tv_ref": args.tv_ref,
        "url": args.url or None,
        "name": args.name,
        "author": args.author or None,
        "version": args.version or None,
        "key_inputs": parse_list(args.key_inputs)[:30],
        "signals_described": parse_list(args.signals)[:20],
        "notes": parse_list(args.notes)[:10],
        "source_pointer": source_pointer,
        "source_min_pointer": source_min_pointer,
        "component_type": ctype,
        "pine_raw_bytes": raw_bytes,
        "pine_raw_lines": raw_lines,
        "pine_min_bytes": min_bytes,
        "pine_min_lines": min_lines,
        "pine_size_class": p_size_class_bytes,
        "pine_size_class_bytes": p_size_class_bytes,
        "pine_size_class_lines": p_size_class_lines,
        "pine_too_large": too_large,
        "pine_too_large_reason": too_large_reason,
        "sha256": sha256_text(src_trunc if src_trunc else args.name),
        "truncated": src_truncated,
    }
    record = {k: v for k, v in record.items() if v is not None}

    payload = json.dumps(record, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        raise SystemExit("IndicatorRecord exceeds 60KB")

    rec_path = out_dir / f"{iid}.indicator_record.json"
    rec_path.write_text(payload, encoding="utf-8")

    update_index(Path(args.output_root) / "INDEX.json", str(rec_path).replace('\\', '/'))
    print(json.dumps({"indicator_record_path": str(rec_path).replace('\\', '/'), "pine_path": source_pointer, "pine_min_path": source_min_pointer}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
