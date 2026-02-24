#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _abs(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str((ROOT / p).resolve())


def _emit_thesis_from_promotion(promo: dict) -> str:
    linkmap_path = _abs(promo.get('input_linkmap_path'))
    if not linkmap_path:
        raise SystemExit('promotion_run missing input_linkmap_path')
    lm = _load(linkmap_path)
    rc = _abs(lm.get('research_card_path'))
    ir = [_abs(p) for p in lm.get('indicator_record_paths', [])[:10]]
    out = _run([
        PY,
        'scripts/pipeline/emit_thesis.py',
        '--research-card-path',
        rc,
        '--indicator-record-paths',
        json.dumps(ir),
        '--linkmap-paths',
        json.dumps([linkmap_path]),
    ])
    thesis_path = json.loads(out)['thesis_path']
    _run([PY, 'scripts/pipeline/verify_pipeline_stage2.py', '--thesis', thesis_path])
    return thesis_path


def _emit_base_spec(thesis_path: str) -> str:
    out = _run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', thesis_path])
    return json.loads(out)['strategy_spec_path']


def _build_refined_spec(base_spec_path: str, thesis_path: str) -> str:
    spec = _load(_abs(base_spec_path))

    baseline = deepcopy(spec['variants'][0])
    baseline['name'] = 'baseline_creator'

    variants = [baseline]

    # TPX threshold sweep 20/30/40 (bounded, notes-only thresholding)
    for lvl in [20, 30, 40]:
        v = deepcopy(baseline)
        v['name'] = f'tpx_threshold_{lvl}'
        v['description'] = f'TPX control-level sweep at {lvl} (bounded proposal).'
        rr = list(v.get('risk_rules', []))
        rr.append(f'TPX threshold note={lvl}')
        v['risk_rules'] = rr[:10]
        variants.append(v)

    # Role swaps (TPX filter vs entry)
    for role in ['filter', 'entry']:
        v = deepcopy(baseline)
        v['name'] = f'tpx_role_{role}'
        v['description'] = f'Role swap: TPX as {role} (bounded proposal).'
        rr = list(v.get('risk_rules', []))
        rr.append(f'TPX role note={role}')
        v['risk_rules'] = rr[:10]
        variants.append(v)

    # risk policy sweep (ATR multipliers)
    for stop_mult, tp_mult in [(1.2, 1.8), (1.5, 2.2), (2.0, 3.0)]:
        v = deepcopy(baseline)
        v['name'] = f"atr_risk_{str(stop_mult).replace('.', 'p')}_{str(tp_mult).replace('.', 'p')}"
        v['description'] = f'Risk sweep ATR stop={stop_mult}, tp={tp_mult}.'
        v['risk_policy']['stop_atr_mult'] = float(stop_mult)
        v['risk_policy']['tp_atr_mult'] = float(tp_mult)
        variants.append(v)

    variants = variants[:10]
    spec['variants'] = variants
    spec['id'] = f"strategy-spec-{datetime.now().strftime('%Y%m%d')}-refine-{uuid.uuid4().hex[:8]}"
    spec['source_thesis_path'] = thesis_path.replace('\\', '/')

    out_dir = ROOT / 'artifacts' / 'strategy_specs' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{spec['id']}.strategy_spec.json"
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(out_path).replace('\\', '/')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--promotion-run', required=True)
    args = ap.parse_args()

    promo = _load(args.promotion_run)
    thesis_path = _emit_thesis_from_promotion(promo)
    base_spec_path = _emit_base_spec(thesis_path)
    refined_spec_path = _build_refined_spec(base_spec_path, thesis_path)

    refined_spec = _load(refined_spec_path)
    variant_names = [v.get('name') for v in refined_spec.get('variants', [])][:10]

    variant_batches: list[dict] = []
    for vn in variant_names:
        batch_out = _run([
            PY,
            'scripts/pipeline/run_batch_backtests.py',
            '--strategy-spec',
            refined_spec_path,
            '--variant',
            vn,
        ])
        bi = json.loads(batch_out)
        b = _load(bi['batch_artifact_path'])
        s = b.get('summary', {})
        score = float(s.get('net_profit', 0.0)) - 0.2 * float(s.get('max_drawdown', 0.0)) + 100.0 * float(s.get('profit_factor', 0.0)) + (10000.0 if int(s.get('failed_runs', 0)) == 0 else 0.0)
        variant_batches.append({
            'variant_name': vn,
            'batch_artifact_path': bi['batch_artifact_path'],
            'experiment_plan_path': bi.get('experiment_plan_path'),
            'summary': s,
            'score': score,
        })

    variant_batches.sort(key=lambda x: x['score'], reverse=True)
    winner = variant_batches[0] if variant_batches else None

    payload = {
        'schema_version': '1.0',
        'id': f"refine_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'seed': {
            'promotion_run_path': args.promotion_run,
            'thesis_path': thesis_path,
            'strategy_spec_path': refined_spec_path,
        },
        'variants': [v.get('name') for v in _load(refined_spec_path).get('variants', [])][:10],
        'results': {
            'variant_batches': variant_batches[:10],
        },
        'winner': {
            'variant_name': winner.get('variant_name') if winner else None,
            'batch_backtest_path': winner.get('batch_artifact_path') if winner else None,
            'experiment_plan_path': winner.get('experiment_plan_path') if winner else None,
            'net_profit': winner.get('summary', {}).get('net_profit') if winner else None,
            'trades': winner.get('summary', {}).get('trades') if winner else None,
            'profit_factor': winner.get('summary', {}).get('profit_factor') if winner else None,
            'max_drawdown': winner.get('summary', {}).get('max_drawdown') if winner else None,
            'failed_runs': winner.get('summary', {}).get('failed_runs') if winner else None,
            'score': winner.get('score') if winner else None,
        },
        'stop_reason': 'bounded_variant_catalog_exhausted',
    }

    out_dir = ROOT / 'artifacts' / 'refinement' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{payload['id']}.refinement_cycle.json"
    out_path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')

    print(json.dumps({'refinement_cycle_path': str(out_path), 'winner': payload['winner']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
