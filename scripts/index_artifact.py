#!/usr/bin/env python3
"""Index an artifact metadata record into artifacts.db with hash dedup/upsert."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_id(kind: str, full_hash: str) -> str:
    return f"{kind}--{full_hash[:12]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    p = argparse.ArgumentParser(description="Index artifact metadata")
    p.add_argument("--db", default="artifacts.db")
    p.add_argument("--file", required=True, help="Artifact file path")
    p.add_argument("--type", required=True, help="Artifact type (e.g., backtest, research)")
    p.add_argument("--path", help="Logical artifact path (default: parent dir of --file)")
    p.add_argument("--title", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--tags", default="[]", help="JSON array string")
    p.add_argument("--source-url", default="")
    p.add_argument("--rights", default="unknown")
    p.add_argument("--attribution-required", action="store_true")
    p.add_argument("--license", default="")
    p.add_argument("--lineage", default="{}", help="JSON object string")
    p.add_argument("--metadata", default="{}", help="JSON object string")
    args = p.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"ERROR: file not found: {file_path}")

    tags = json.dumps(json.loads(args.tags), ensure_ascii=False)
    lineage_json = json.dumps(json.loads(args.lineage), ensure_ascii=False)
    metadata_json = json.dumps(json.loads(args.metadata), ensure_ascii=False)

    full_hash = sha256_file(file_path)
    artifact_id = make_id(args.type, full_hash)
    logical_path = args.path or str(file_path.parent).replace('\\', '/')

    sql = """
    INSERT INTO artifacts (
      id, type, source_url, created_at, hash, path, title, summary,
      tags, rights, attribution_required, license, lineage_json, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(hash) DO UPDATE SET
      id=excluded.id,
      type=excluded.type,
      source_url=excluded.source_url,
      path=excluded.path,
      title=excluded.title,
      summary=excluded.summary,
      tags=excluded.tags,
      rights=excluded.rights,
      attribution_required=excluded.attribution_required,
      license=excluded.license,
      lineage_json=excluded.lineage_json,
      metadata_json=excluded.metadata_json
    """

    with sqlite3.connect(args.db) as conn:
        conn.execute(
            sql,
            (
                artifact_id,
                args.type,
                args.source_url,
                now_iso(),
                full_hash,
                logical_path,
                args.title,
                args.summary,
                tags,
                args.rights,
                1 if args.attribution_required else 0,
                args.license,
                lineage_json,
                metadata_json,
            ),
        )
        conn.commit()

    print(json.dumps({"id": artifact_id, "hash": full_hash, "db": args.db}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
