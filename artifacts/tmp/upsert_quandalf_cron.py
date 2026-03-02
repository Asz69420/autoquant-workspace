import json
import time
import uuid
from pathlib import Path

p = Path(r"C:\Users\Clamps\.openclaw\cron\jobs.json")
j = json.loads(p.read_text(encoding="utf-8"))
jobs = j.get("jobs", [])
name = "quandalf-auto-execute"
msg = (
    "Run scripts/quandalf-auto-execute.sh. If orders are pending, execute them, "
    "write docs/shared/LAST_CYCLE_RESULTS.md, set docs/shared/QUANDALF_ORDERS.md "
    "status COMPLETE, commit docs updates, and reply with a concise summary. "
    "If no pending order, reply: no pending order."
)
now = int(time.time() * 1000)

existing = next((job for job in jobs if job.get("name") == name), None)
if existing is None:
    jobs.append(
        {
            "id": str(uuid.uuid4()),
            "agentId": "main",
            "name": name,
            "description": "Execute pending Quandalf orders and publish cycle results",
            "enabled": True,
            "createdAtMs": now,
            "updatedAtMs": now,
            "schedule": {"kind": "cron", "expr": "*/30 * * * *", "tz": "Australia/Brisbane"},
            "sessionTarget": "isolated",
            "wakeMode": "now",
            "payload": {"kind": "agentTurn", "message": msg},
            "delivery": {"mode": "announce", "channel": "last"},
        }
    )
else:
    existing["enabled"] = True
    existing["updatedAtMs"] = now
    existing["schedule"] = {"kind": "cron", "expr": "*/30 * * * *", "tz": "Australia/Brisbane"}
    existing["sessionTarget"] = "isolated"
    existing["wakeMode"] = "now"
    existing["payload"] = {"kind": "agentTurn", "message": msg}
    existing["delivery"] = {"mode": "announce", "channel": "last"}

p.write_text(json.dumps(j, indent=2), encoding="utf-8")
print("OK")
