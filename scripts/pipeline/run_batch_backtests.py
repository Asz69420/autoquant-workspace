#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _days_between(start: str, end: str) -> int:
    s = datetime.fromisoformat(start.replace('Z', '+00:00'))
    e = datetime.fromisoformat(end.replace('Z', '+00:00'))
    return (e - s).days


def _latest_meta(symbol: str, timeframe: str) -> str:
    d = ROOT / 'artifacts' / 'data' / 'hyperliquid' / symbol / timeframe
    metas = sorted(d.glob('*.meta.json'))
    if not metas:
        raise FileNotFoundError(f'No dataset meta found for {symbol} {timeframe}')
    preferred = []
    fallback = []
    for m in metas:
        meta = _load_json(m)
        if 'start' in meta and 'end' in meta and _days_between(meta['start'], meta['end']) >= 700:
            preferred.append(m)
        else:
            fallback.append(m)
    pool = preferred if preferred else fallback
    return str(sorted(pool)[-1])


def _resolve_datasets(arg: str) -> list[str]:
    if arg == 'default':
        return [
            _latest_meta('BTC', '1h'),
            _latest_meta('BTC', '4h'),
            _latest_meta('ETH', '1h'),
            _latest_meta('ETH', '4h'),
        ]
    p = Path(arg)
    if p.exists():
        if p.suffix == '.json' and str(p).endswith('.meta.json'):
            return [str(p)]
        loaded = json.loads(p.read_text(encoding='utf-8-sig'))
        if isinstance(loaded, list) and loaded:
            return [str(x) for x in loaded]
        raise ValueError('--datasets file must be a non-empty JSON array of meta paths, or a single *.meta.json path')
    return [x.strip() for x in arg.split(',') if x.strip()]


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--variant', required=True, help='variant name or "all"')
    ap.add_argument('--datasets', default='default', help='default | csv list of dataset meta paths | JSON file path')
    args = ap.parse_args()

    spec = _load_json(args.strategy_spec)
    variants = [v['name'] for v in spec.get('variants', [])]
    selected_variants = variants if args.variant == 'all' else [args.variant]
    for v in selected_variants:
        if v not in variants:
            raise ValueError(f'variant not found in spec: {v}')

    dataset_metas = _resolve_datasets(args.datasets)

    runs = []
    for variant in selected_variants:
        for dataset_meta in dataset_metas:
            meta = _load_json(dataset_meta)
            fout = _run([
                PY,
                'scripts/pipeline/check_feasibility.py',
                '--strategy-spec',
                args.strategy_spec,
                '--variant',
                variant,
                '--dataset-meta',
                dataset_meta,
            ])
            f = json.loads(fout)
            if f.get('verdict') == 'FAIL':
                run = {
                    'variant_name': variant,
                    'symbol': meta.get('symbol'),
                    'timeframe': meta.get('timeframe'),
                    'dataset_meta_path': dataset_meta,
                    'backtest_result_path': '',
                    'trade_list_path': '',
                    'gate_pass': False,
                    'status': 'SKIPPED',
                    'skip_reason': 'FEASIBILITY_FAIL',
                    'feasibility_report_path': f.get('feasibility_report_path'),
                    'feasibility_flags': f.get('flags', []),
                    'net_profit': 0.0,
                    'trades': 0,
                    'profit_factor': 0.0,
                    'max_drawdown': 0.0,
                }
                runs.append(run)
                continue

            out = _run([
                PY,
                'scripts/backtester/hl_backtest_engine.py',
                '--dataset-meta',
                dataset_meta,
                '--strategy-spec',
                args.strategy_spec,
                '--variant',
                variant,
            ])
            info = json.loads(out)
            bt = _load_json(info['backtest_result'])
            run = {
                'variant_name': variant,
                'symbol': meta.get('symbol'),
                'timeframe': meta.get('timeframe'),
                'dataset_meta_path': dataset_meta,
                'backtest_result_path': info['backtest_result'],
                'trade_list_path': info['trade_list'],
                'feasibility_report_path': f.get('feasibility_report_path'),
                'feasibility_flags': f.get('flags', []),
                'status': 'EXECUTED',
                'gate_pass': bool(bt.get('gate', {}).get('gate_pass', True)),
                'net_profit': bt.get('results', {}).get('net_profit', 0.0),
                'trades': bt.get('results', {}).get('total_trades', 0),
                'profit_factor': bt.get('results', {}).get('profit_factor', 0.0),
                'max_drawdown': bt.get('results', {}).get('max_drawdown', 0.0),
            }
            if info.get('relax_suggestion_path'):
                run['relax_suggestion_path'] = info['relax_suggestion_path']
            runs.append(run)

    runs = runs[:10]
    summary = {
        'total_runs': len(runs),
        'failed_runs': sum(1 for r in runs if not r['gate_pass']),
        'net_profit': round(sum(float(r.get('net_profit', 0.0)) for r in runs), 8),
        'trades': int(sum(int(r.get('trades', 0)) for r in runs)),
        'profit_factor': round(sum(float(r.get('profit_factor', 0.0)) for r in runs) / len(runs), 8) if runs else 0.0,
        'max_drawdown': round(max((float(r.get('max_drawdown', 0.0)) for r in runs), default=0.0), 8),
    }

    batch = {
        'schema_version': '1.0',
        'id': f"batch_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'strategy_spec_path': args.strategy_spec,
        'variant': args.variant,
        'runs': runs,
        'summary': summary,
    }

    out_dir = ROOT / 'artifacts' / 'batches' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_path = out_dir / f"{batch['id']}.batch_backtest.json"
    batch_path.write_text(json.dumps(batch, separators=(',', ':')), encoding='utf-8')

    experiment_plan_path = None
    if summary['failed_runs'] > 0:
        p = _run([
            PY,
            'scripts/pipeline/emit_experiment_plan.py',
            '--batch-artifact',
            str(batch_path),
        ])
        experiment_plan_path = json.loads(p).get('experiment_plan_path')

    print(json.dumps({'batch_artifact_path': str(batch_path), 'experiment_plan_path': experiment_plan_path, 'failed_runs': summary['failed_runs']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
