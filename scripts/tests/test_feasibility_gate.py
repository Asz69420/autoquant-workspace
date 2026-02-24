#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _run(cmd: list[str]) -> dict:
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    return json.loads(out)


def _make_specs(tmp_dir: Path) -> tuple[Path, Path]:
    base_variant = {
        'name': 'v_pass',
        'description': 'pass variant',
        'entry_long': ['ema up'],
        'entry_short': ['ema down'],
        'filters': [],
        'exit_rules': [],
        'risk_rules': ['stop_atr_mult=1.5', 'take_profit_atr_mult=2.0'],
        'risk_policy': {'stop_type': 'atr', 'stop_atr_mult': 1.5, 'tp_type': 'atr', 'tp_atr_mult': 2.0, 'risk_per_trade_pct': 1.0},
        'execution_policy': {'entry_fill': 'bar_close', 'tie_break': 'worst_case', 'allow_reverse': True},
        'parameters': [],
        'constraints': [],
    }
    pass_spec = {
        'schema_version': '1.1',
        'id': 'pass_spec',
        'created_at': '2026-02-25T00:00:00Z',
        'source_thesis_path': 'fixture://pass',
        'variants': [base_variant],
    }
    fail_variant = dict(base_variant)
    fail_variant['name'] = 'v_fail'
    fail_variant.pop('risk_policy', None)
    fail_variant.pop('execution_policy', None)
    fail_variant['risk_rules'] = ['ema_trend=200', 'ema_slope=50', 'rsi_long_max=10', 'rsi_short_min=90']
    fail_spec = dict(pass_spec)
    fail_spec['id'] = 'fail_spec'
    fail_spec['variants'] = [fail_variant]

    pass_path = tmp_dir / 'pass.strategy_spec.json'
    fail_path = tmp_dir / 'fail.strategy_spec.json'
    pass_path.write_text(json.dumps(pass_spec), encoding='utf-8')
    fail_path.write_text(json.dumps(fail_spec), encoding='utf-8')
    return pass_path, fail_path


def main() -> int:
    tmp_dir = ROOT / 'artifacts' / 'tmp' / 'feasibility_test'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pass_spec, fail_spec = _make_specs(tmp_dir)

    dataset_meta = ROOT / 'artifacts' / 'data' / 'hyperliquid' / 'BTC' / '4h' / '20240225T120000Z-20260224T120000Z.meta.json'

    fail = _run([
        PY, 'scripts/pipeline/check_feasibility.py',
        '--strategy-spec', str(fail_spec),
        '--variant', 'v_fail',
        '--dataset-meta', str(dataset_meta),
    ])
    assert fail['verdict'] == 'FAIL'

    passed = _run([
        PY, 'scripts/pipeline/check_feasibility.py',
        '--strategy-spec', str(pass_spec),
        '--variant', 'v_pass',
        '--dataset-meta', str(dataset_meta),
    ])
    assert passed['verdict'] == 'PASS'

    batch = _run([
        PY, 'scripts/pipeline/run_batch_backtests.py',
        '--strategy-spec', str(fail_spec),
        '--variant', 'v_fail',
        '--datasets', str(dataset_meta),
    ])
    b = json.loads(Path(batch['batch_artifact_path']).read_text(encoding='utf-8'))
    assert b['runs'][0]['status'] == 'SKIPPED'
    assert b['runs'][0]['skip_reason'] == 'FEASIBILITY_FAIL'

    print(json.dumps({'fail': fail['feasibility_report_path'], 'pass': passed['feasibility_report_path'], 'batch': batch['batch_artifact_path']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
