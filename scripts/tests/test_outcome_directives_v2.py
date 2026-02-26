#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def main() -> int:
    day = datetime.now(timezone.utc).strftime('%Y%m%d')
    run_id = f'test-v2-{int(datetime.now(timezone.utc).timestamp())}'

    strategy_spec = ROOT / 'artifacts' / 'strategy_specs' / day / 'fixture_same_family.strategy_spec.json'
    _write_json(strategy_spec, {
        'schema_version': '1.1',
        'id': 'fixture_same_family',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_thesis_path': 'artifacts/theses/fake.json',
        'variants': [{'name': 'TemplateA'}],
    })

    backtest_result = ROOT / 'artifacts' / 'backtests' / day / 'fixture.backtest_result.json'
    _write_json(backtest_result, {
        'schema_version': '1.0',
        'id': 'bt-fixture',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'inputs': {'dataset_path': 'x', 'strategy_spec_path': str(strategy_spec).replace('\\', '/'), 'variant': 'TemplateA'},
        'settings': {'commission_pct': 0.001, 'slippage': 0, 'fill_rule': 'next_open', 'tie_break': 'worst_case'},
        'results': {'trades': 8, 'net_return': -0.2, 'max_drawdown_proxy': 0.41, 'win_rate': 0.3, 'profit_factor': 0.8},
        'gate': {'min_trades_required': 20, 'gate_pass': False, 'gate_reason': 'LOW_TRADES'}
    })

    batch = ROOT / 'artifacts' / 'backtests' / day / 'batch-fixture-v2.json'
    _write_json(batch, {
        'schema_version': '1.0',
        'id': 'batch-fixture',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'strategy_spec_path': str(strategy_spec).replace('\\', '/'),
        'variant': 'TemplateA',
        'runs': [{
            'variant_name': 'TemplateA',
            'symbol': 'BTC',
            'timeframe': '1h',
            'dataset_meta_path': 'meta.json',
            'backtest_result_path': str(backtest_result).replace('\\', '/'),
            'trade_list_path': 'trade_list.json',
            'gate_pass': False,
            'profit_factor': 0.8,
            'max_drawdown': 0.41,
            'trades': 8,
        }],
        'summary': {'total_runs': 1, 'failed_runs': 0, 'net_profit': -100, 'trades': 8, 'profit_factor': 0.8, 'max_drawdown': 0.41}
    })

    refine = ROOT / 'artifacts' / 'refinements' / day / 'fixture_refinement.json'
    _write_json(refine, {'final_recommendation': 'NO_IMPROVEMENT'})

    outcome_out = _run([PY, 'scripts/pipeline/analyser_outcome_worker.py', '--run-id', run_id, '--batch-artifact', str(batch), '--refinement-artifact', str(refine)])
    lines = [ln for ln in outcome_out.splitlines() if ln.strip()]
    outcome_meta = json.loads(lines[-1])
    outcome = json.loads(Path(outcome_meta['outcome_notes_path']).read_text(encoding='utf-8'))

    assert outcome['schema_version'] == '2.0'
    assert outcome['verdict'] == 'REJECT'
    assert 1 <= len(outcome['failure_reasons']) <= 5
    assert 1 <= len(outcome['directives']) <= 5
    assert any(fr['code'] == 'LOW_TRADE_COUNT' for fr in outcome['failure_reasons'])
    assert any(fr['code'] == 'HIGH_DRAWDOWN' for fr in outcome['failure_reasons'])
    assert any(fr['code'] == 'PF_BELOW_1' for fr in outcome['failure_reasons'])

    thesis = ROOT / 'artifacts' / 'theses' / day / 'fixture_thesis.json'
    _write_json(thesis, {
        'id': 'fixture_same_family',
        'strategy_family': 'fixture_same_family',
        'template': 'TemplateA',
        'constraints': [],
        'required_data': ['ohlcv'],
        'candidate_signals': [{'name': 'sigA'}],
        'hypotheses': [],
    })

    sp_out = _run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', str(thesis)])
    sp_meta = json.loads(sp_out)
    sp = json.loads(Path(sp_meta['strategy_spec_path']).read_text(encoding='utf-8'))
    directive_variants = [v for v in sp['variants'] if v.get('origin') == 'DIRECTIVE']

    assert len(sp['variants']) >= 3
    assert len(directive_variants) >= 1
    assert all(v.get('directive_refs') for v in directive_variants)

    print(json.dumps({
        'outcome_notes_path': outcome_meta['outcome_notes_path'],
        'verdict': outcome['verdict'],
        'directives': len(outcome['directives']),
        'strategy_spec_path': sp_meta['strategy_spec_path'],
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
