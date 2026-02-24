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


def _build_dataset(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    meta = base / 'cluster_4h.meta.json'
    csvp = base / 'cluster_4h.csv'
    meta.write_text(json.dumps({'symbol': 'BTC', 'timeframe': '4h', 'start': '2024-01-01T00:00:00Z', 'end': '2026-01-01T00:00:00Z'}), encoding='utf-8')
    rows = ['time,open,high,low,close']
    price = 100.0
    for i in range(4200):
        price = 100.0 if i % 2 == 0 else 102.0
        rows.append(f'2024-01-01T00:00:00Z,{price},{price+0.5},{price-0.5},{price}')
    csvp.write_text('\n'.join(rows), encoding='utf-8')
    return meta


def _write_spec(path: Path, variant: dict, sid: str):
    payload = {'schema_version': '1.1', 'id': sid, 'created_at': '2026-02-25T00:00:00Z', 'source_thesis_path': 'fixture://t', 'variants': [variant]}
    path.write_text(json.dumps(payload), encoding='utf-8')


def _base_variant(name: str) -> dict:
    return {
        'name': name,
        'description': 'fixture',
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


def main() -> int:
    td = ROOT / 'artifacts' / 'tmp' / 'feasibility_v2'
    td.mkdir(parents=True, exist_ok=True)
    meta = _build_dataset(td)

    # FIRE_COUNT_TOO_LOW fail
    v_fail = _base_variant('v_fire_low')
    v_fail['parameters'] = [{'name': 'signal_sparsity', 'min': 1, 'max': 1000, 'step': 1, 'default': 500}]
    fail_spec = td / 'fire_low.strategy_spec.json'
    _write_spec(fail_spec, v_fail, 'fire_low')
    fail = _run([PY, 'scripts/pipeline/check_feasibility.py', '--strategy-spec', str(fail_spec), '--variant', 'v_fire_low', '--dataset-meta', str(meta)])

    # SIGNAL_CLUSTERED pass
    v_cluster = _base_variant('v_cluster')
    cluster_spec = td / 'cluster.strategy_spec.json'
    _write_spec(cluster_spec, v_cluster, 'cluster')
    clustered = _run([PY, 'scripts/pipeline/check_feasibility.py', '--strategy-spec', str(cluster_spec), '--variant', 'v_cluster', '--dataset-meta', str(meta)])

    # PARAM_CLIFF flag/fail
    v_cliff = _base_variant('v_cliff')
    v_cliff['parameters'] = [{'name': 'signal_sparsity', 'min': 1, 'max': 10, 'step': 5, 'default': 1}]
    cliff_spec = td / 'cliff.strategy_spec.json'
    _write_spec(cliff_spec, v_cliff, 'cliff')
    cliff = _run([PY, 'scripts/pipeline/check_feasibility.py', '--strategy-spec', str(cliff_spec), '--variant', 'v_cliff', '--dataset-meta', str(meta)])

    assert fail['verdict'] == 'FAIL'
    assert 'FIRE_COUNT_TOO_LOW' in ' '.join(fail.get('fail_reasons', []))

    cdoc = json.loads(Path(clustered['feasibility_report_path']).read_text(encoding='utf-8'))
    assert cdoc['verdict'] == 'PASS'
    assert 'SIGNAL_CLUSTERED' in cdoc.get('flags', [])

    cldoc = json.loads(Path(cliff['feasibility_report_path']).read_text(encoding='utf-8'))
    assert 'PARAM_CLIFF' in cldoc.get('flags', [])

    print(json.dumps({'fail': fail['feasibility_report_path'], 'cluster': clustered['feasibility_report_path'], 'cliff': cliff['feasibility_report_path']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
