#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _dedupe_keep_order(items: list[str], limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
        if len(out) >= limit:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-artifact', required=True)
    args = ap.parse_args()

    batch = _load_json(args.batch_artifact)
    runs = batch.get('runs', [])
    failing = [r for r in runs if not bool(r.get('gate_pass', True))][:10]

    if not failing:
        print(json.dumps({'experiment_plan_path': None, 'created': False}))
        return 0

    suggestions_raw: list[str] = []
    failing_runs: list[dict] = []
    for r in failing:
        rp = r.get('relax_suggestion_path')
        if rp and Path(rp).exists():
            s = _load_json(rp)
            suggestions_raw.extend(s.get('suggested_relaxations', []))
            suggestions_raw.extend(s.get('suspected_blockers', []))
        failing_runs.append({
            'symbol': r.get('symbol'),
            'timeframe': r.get('timeframe'),
            'dataset_meta_path': r.get('dataset_meta_path'),
            'backtest_result_path': r.get('backtest_result_path'),
        })

    suggestions = _dedupe_keep_order(suggestions_raw, limit=20)
    recommended_next_actions = _dedupe_keep_order(suggestions[:10], limit=10)

    payload = {
        'schema_version': '1.0',
        'id': f"exp_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'strategy_spec_path': batch.get('strategy_spec_path'),
        'variant': batch.get('variant'),
        'failing_runs': failing_runs,
        'suggestions': suggestions,
        'recommended_next_actions': recommended_next_actions,
    }

    out_dir = Path('artifacts/experiments') / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{payload['id']}.experiment_plan.json"
    out_path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')

    print(json.dumps({'experiment_plan_path': str(out_path), 'created': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
