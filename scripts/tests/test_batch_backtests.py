#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def _build_fixture_dataset(day_dir: Path) -> Path:
    meta_path = day_dir / 'fixture_2y_1h.meta.json'
    csv_path = day_dir / 'fixture_2y_1h.csv'

    meta = {
        'symbol': 'BTC',
        'timeframe': '1h',
        'start': '2024-01-01T00:00:00Z',
        'end': '2026-01-01T00:00:00Z',
    }
    meta_path.write_text(json.dumps(meta), encoding='utf-8')

    rows = ['time,open,high,low,close']
    price = 100.0
    for i in range(600):
        price += 0.02
        low = price - 0.5
        high = price + 0.5
        rows.append(f'2024-01-01T00:{i%60:02d}:00Z,{price:.4f},{high:.4f},{low:.4f},{price:.4f}')
    csv_path.write_text('\n'.join(rows), encoding='utf-8')
    return meta_path


def main() -> int:
    day_dir = ROOT / 'artifacts' / 'datasets' / '20260226'
    day_dir.mkdir(parents=True, exist_ok=True)
    dataset_meta = _build_fixture_dataset(day_dir)

    spec = ROOT / 'scripts/tests/fixtures/strategy_specs/trendpullback_v1.json'

    out = run([
        PY,
        'scripts/pipeline/run_batch_backtests.py',
        '--strategy-spec',
        str(spec),
        '--variant',
        'TrendPullback_v1',
        '--datasets',
        str(dataset_meta),
    ])
    info = json.loads(out)

    assert 'batch_artifact_path' in info
    batch_path = Path(info['batch_artifact_path'])
    assert batch_path.exists()

    batch = json.loads(batch_path.read_text(encoding='utf-8'))
    assert batch['summary']['total_runs'] == 1
    assert batch['summary']['failed_runs'] >= 1

    if batch['summary']['failed_runs'] > 0:
        assert info['experiment_plan_path']
        exp_path = Path(info['experiment_plan_path'])
        assert exp_path.exists()

    print(json.dumps(info))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
