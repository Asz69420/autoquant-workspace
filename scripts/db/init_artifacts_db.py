#!/usr/bin/env python3
"""Initialize artifacts.db with core retrieval tables and indexes (idempotent)."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  source_url TEXT,
  created_at TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  path TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  tags TEXT,
  rights TEXT,
  attribution_required INTEGER,
  license TEXT,
  lineage_json TEXT,
  metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(hash);
CREATE INDEX IF NOT EXISTS idx_artifacts_rights ON artifacts(rights);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize artifacts.db schema")
    parser.add_argument("--db", default="artifacts.db", help="Path to sqlite database")
    args = parser.parse_args()

    db_path = Path(args.db)
    init_db(db_path)
    print(f"OK: initialized {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
