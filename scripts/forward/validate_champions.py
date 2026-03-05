#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def fail(msg: str) -> int:
    print(msg)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="docs/shared/CHAMPIONS.json")
    ap.add_argument("--schema", default="docs/shared/CHAMPIONS.schema.json")
    args = ap.parse_args()

    fp = Path(args.file)
    if not fp.exists():
        return fail(f"CHAMPIONS_MISSING: {fp}")

    try:
        payload = json.loads(fp.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return fail(f"CHAMPIONS_PARSE_FAIL: {e}")

    required_top = ["schema_version", "timezone", "runner", "champions"]
    for k in required_top:
        if k not in payload:
            return fail(f"CHAMPIONS_MISSING_FIELD: {k}")

    champions = payload.get("champions")
    if not isinstance(champions, list) or not champions:
        return fail("CHAMPIONS_EMPTY")

    ids: set[str] = set()
    active = 0
    per_bucket_active: dict[tuple[str, str], list[str]] = {}
    max_active_per_bucket = 3
    for c in champions:
        if not isinstance(c, dict):
            return fail("CHAMPIONS_INVALID_ITEM")
        for k in ["id", "status", "strategy_name", "template_name", "asset", "timeframe", "entry_long", "entry_short", "risk_policy", "execution_policy", "canonical_backtest"]:
            if k not in c:
                return fail(f"CHAMPION_MISSING_FIELD: {k}")
        cid = str(c.get("id"))
        if cid in ids:
            return fail(f"CHAMPION_DUPLICATE_ID: {cid}")
        ids.add(cid)

        status = str(c.get("status"))
        if status in {"active", "watch"}:
            active += 1
            asset = str(c.get("asset") or "").upper()
            timeframe = str(c.get("timeframe") or "").lower()
            bucket = (asset, timeframe)
            if bucket not in per_bucket_active:
                per_bucket_active[bucket] = []
            per_bucket_active[bucket].append(cid)

        rp = c.get("risk_policy") or {}
        for rk in ["stop_type", "stop_atr_mult", "tp_type", "tp_atr_mult", "risk_per_trade_pct"]:
            if rk not in rp:
                return fail(f"CHAMPION_RISK_MISSING: {cid}:{rk}")

        ep = c.get("execution_policy") or {}
        for ek in ["entry_fill", "tie_break", "allow_reverse"]:
            if ek not in ep:
                return fail(f"CHAMPION_EXEC_MISSING: {cid}:{ek}")

    for (asset, timeframe), ids_in_bucket in per_bucket_active.items():
        if len(ids_in_bucket) > max_active_per_bucket:
            return fail(
                f"CHAMPION_BUCKET_CAP_EXCEEDED: {asset}/{timeframe} count={len(ids_in_bucket)} cap={max_active_per_bucket} ids={','.join(ids_in_bucket)}"
            )

    if active < 1:
        return fail("CHAMPIONS_NO_ACTIVE")

    print(json.dumps({"ok": True, "champions": len(champions), "active_or_watch": active, "max_active_per_asset_tf": max_active_per_bucket}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
