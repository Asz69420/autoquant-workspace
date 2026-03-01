#!/usr/bin/env python3
"""Evaluate adaptive promotion gate against a batch_backtest artifact.

Returns JSON:
{
  "status": "OK|BLOCKED",
  "reason_code": "...",
  "summary": "...",
  "metrics": {...}
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-artifact", required=True)
    ap.add_argument("--policy", required=True)
    args = ap.parse_args()

    batch_path = Path(args.batch_artifact)
    policy_path = Path(args.policy)

    if not batch_path.exists():
        print(json.dumps({
            "status": "BLOCKED",
            "reason_code": "BATCH_ARTIFACT_MISSING",
            "summary": f"adaptive gate: batch artifact missing: {batch_path}",
            "metrics": {},
        }))
        return 0

    policy = _load_json(policy_path) if policy_path.exists() else {}
    pg = (policy.get("promotion_gate") or {})

    enabled = bool(policy.get("enabled", True)) and bool(pg.get("enabled", True))
    if not enabled:
        print(json.dumps({
            "status": "OK",
            "reason_code": "ADAPTIVE_GATE_DISABLED",
            "summary": "adaptive gate disabled; pass-through",
            "metrics": {},
        }))
        return 0

    batch = _load_json(batch_path)
    summary = batch.get("summary") or {}

    total_runs = int(summary.get("total_runs") or 0)
    failed_runs = int(summary.get("failed_runs") or 0)
    executed_runs = max(0, total_runs - failed_runs)
    net_profit = float(summary.get("net_profit") or 0.0)
    profit_factor = float(summary.get("profit_factor") or 0.0)
    max_drawdown = float(summary.get("max_drawdown") or 0.0)

    min_pf = float(pg.get("min_profit_factor", 1.0))
    max_dd = float(pg.get("max_drawdown", 1e18))
    require_pos = bool(pg.get("require_positive_net", False))
    min_exec = int(pg.get("min_executed_runs", 1))

    reasons: list[str] = []
    if executed_runs < min_exec:
        reasons.append(f"EXECUTED_RUNS_LT_MIN({executed_runs}<{min_exec})")
    if profit_factor < min_pf:
        reasons.append(f"PF_LT_MIN({profit_factor:.4f}<{min_pf:.4f})")
    if max_drawdown > max_dd:
        reasons.append(f"DD_GT_MAX({max_drawdown:.2f}>{max_dd:.2f})")
    if require_pos and net_profit <= 0:
        reasons.append(f"NET_NOT_POSITIVE({net_profit:.2f})")

    metrics = {
        "total_runs": total_runs,
        "executed_runs": executed_runs,
        "failed_runs": failed_runs,
        "net_profit": net_profit,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "thresholds": {
            "min_profit_factor": min_pf,
            "max_drawdown": max_dd,
            "require_positive_net": require_pos,
            "min_executed_runs": min_exec,
        },
    }

    if reasons:
        print(json.dumps({
            "status": "BLOCKED",
            "reason_code": "ADAPTIVE_PROMOTION_GATE",
            "summary": "adaptive gate blocked: " + "; ".join(reasons),
            "metrics": metrics,
        }))
        return 0

    print(json.dumps({
        "status": "OK",
        "reason_code": "ADAPTIVE_PROMOTION_GATE",
        "summary": "adaptive gate pass",
        "metrics": metrics,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
