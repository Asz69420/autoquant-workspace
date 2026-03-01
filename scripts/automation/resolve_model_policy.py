#!/usr/bin/env python3
"""Resolve model/reasoning policy for a task key.

Usage examples:
  python scripts/automation/resolve_model_policy.py --task strategy_generate
  python scripts/automation/resolve_model_policy.py --agent claude --action strategy_research
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = ROOT / "config" / "model_reasoning_policy.json"


def _norm(value: str | None) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(policy: dict[str, Any], task: str | None, agent: str | None, action: str | None, allow_fallback: bool) -> dict[str, Any]:
    buckets = policy.get("buckets") or {}
    mappings = policy.get("task_mappings") or {}

    candidates: list[str] = []
    task_n = _norm(task)
    agent_n = _norm(agent)
    action_n = _norm(action)

    if task_n:
        candidates.append(task_n)
    if agent_n and action_n:
        candidates.append(f"{agent_n}_{action_n}")
    if action_n:
        candidates.append(action_n)

    matched_key = None
    bucket = None
    for c in candidates:
        if c in mappings:
            matched_key = c
            bucket = mappings[c]
            break

    if bucket is None:
        unknown_mode = str(policy.get("unknown_task_policy") or "error").lower()
        if unknown_mode == "fallback" and allow_fallback:
            bucket = str(policy.get("fallback_bucket") or "medium")
            matched_key = "<fallback>"
        else:
            raise KeyError(
                f"No policy mapping for task/agent/action candidates: {candidates or ['<none>']}"
            )

    if bucket not in buckets:
        raise KeyError(f"Mapped bucket '{bucket}' not defined in policy.buckets")

    b = buckets[bucket]
    return {
        "task": task_n or None,
        "agent": agent_n or None,
        "action": action_n or None,
        "resolved_key": matched_key,
        "bucket": bucket,
        "llm_required": bool(b.get("llm_required", False)),
        "model": b.get("model"),
        "reasoning": b.get("reasoning"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve task -> model/reasoning policy")
    ap.add_argument("--task", default="", help="Task key (preferred explicit mapping key)")
    ap.add_argument("--agent", default="", help="Agent name (optional)")
    ap.add_argument("--action", default="", help="Action name (optional)")
    ap.add_argument("--policy", default=str(DEFAULT_POLICY_PATH), help="Path to policy json")
    ap.add_argument("--allow-fallback", action="store_true", help="Allow fallback bucket when task is unmapped")
    args = ap.parse_args()

    try:
        policy = _load_policy(Path(args.policy))
        out = resolve(policy, args.task, args.agent, args.action, args.allow_fallback)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as e:
        err = {
            "status": "error",
            "error": str(e),
            "task": _norm(args.task),
            "agent": _norm(args.agent),
            "action": _norm(args.action),
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
