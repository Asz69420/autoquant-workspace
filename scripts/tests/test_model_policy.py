#!/usr/bin/env python3
"""Drift guard for model/reasoning policy.

Checks:
- required buckets exist
- all mappings point to valid buckets
- explicit required task keys exist (prevents accidental deletions)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "model_reasoning_policy.json"

REQUIRED_BUCKETS = {"system", "low", "medium", "high"}
REQUIRED_TASK_KEYS = {
    "grabber_dedup_check",
    "simple_text_summary",
    "claude_bridge_chat",
    "claude_deep_iterator",
    "claude_strategy_researcher",
    "claude_strategy_generator",
    "claude_doctrine_synthesizer",
    "claude_backtest_auditor",
}


def fail(msg: str) -> int:
    print(json.dumps({"status": "FAIL", "reason": msg}, ensure_ascii=False))
    return 1


def main() -> int:
    if not POLICY_PATH.exists():
        return fail(f"missing policy file: {POLICY_PATH}")

    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return fail(f"invalid json: {e}")

    buckets = policy.get("buckets")
    if not isinstance(buckets, dict):
        return fail("policy.buckets must be an object")

    bucket_keys = set(buckets.keys())
    if not REQUIRED_BUCKETS.issubset(bucket_keys):
        return fail(f"missing required buckets: {sorted(REQUIRED_BUCKETS - bucket_keys)}")

    mappings = policy.get("task_mappings")
    if not isinstance(mappings, dict) or not mappings:
        return fail("policy.task_mappings must be a non-empty object")

    bad = {k: v for k, v in mappings.items() if v not in buckets}
    if bad:
        return fail(f"invalid bucket references in mappings: {bad}")

    missing_required = sorted(k for k in REQUIRED_TASK_KEYS if k not in mappings)
    if missing_required:
        return fail(f"missing required task mappings: {missing_required}")

    if str(policy.get("unknown_task_policy", "")).lower() not in {"error", "fallback"}:
        return fail("unknown_task_policy must be 'error' or 'fallback'")

    print(
        json.dumps(
            {
                "status": "PASS",
                "policy_path": str(POLICY_PATH.relative_to(ROOT)).replace('\\', '/'),
                "bucket_count": len(buckets),
                "mapping_count": len(mappings),
                "required_keys_checked": len(REQUIRED_TASK_KEYS),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
