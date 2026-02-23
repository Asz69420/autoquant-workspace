#!/usr/bin/env python3
"""Query artifacts.db for artifact pointers by id/type/tag/date."""

from __future__ import annotations

import argparse
import json
import sqlite3


def main() -> int:
    p = argparse.ArgumentParser(description="Query artifacts index")
    p.add_argument("--db", default="artifacts.db")
    p.add_argument("--id")
    p.add_argument("--type")
    p.add_argument("--tag")
    p.add_argument("--from-date", help="ISO date/time lower bound")
    p.add_argument("--to-date", help="ISO date/time upper bound")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    where = []
    vals: list[object] = []
    if args.id:
        where.append("id = ?")
        vals.append(args.id)
    if args.type:
        where.append("type = ?")
        vals.append(args.type)
    if args.tag:
        where.append("tags LIKE ?")
        vals.append(f"%{args.tag}%")
    if args.from_date:
        where.append("created_at >= ?")
        vals.append(args.from_date)
    if args.to_date:
        where.append("created_at <= ?")
        vals.append(args.to_date)

    sql = "SELECT id, type, created_at, path, title, summary, tags, hash FROM artifacts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    vals.append(args.limit)

    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(sql, vals).fetchall()]

    print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
