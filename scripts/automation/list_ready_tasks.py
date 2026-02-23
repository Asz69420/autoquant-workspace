#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("task_ledger.jsonl")
if not p.exists():
    print("[]")
    raise SystemExit(0)

rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
latest = {}
for r in rows:
    latest[r["task_id"]] = r

ready = [r for r in latest.values() if r.get("state") == "READY_FOR_USER_APPROVAL"]
ready.sort(key=lambda x: x.get("last_update_at", ""), reverse=True)
out = [
    {
        "task_id": r.get("task_id"),
        "description": r.get("description", "")[:120],
        "last_update_at": r.get("last_update_at"),
    }
    for r in ready[:5]
]
print(json.dumps(out, ensure_ascii=False, indent=2))
