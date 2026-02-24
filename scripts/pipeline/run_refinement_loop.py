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

MAX_ITERS = 3
MAX_VARIANTS_PER_ITER = 10
MAX_EXPLORE_PER_ITER = 3
IMPROVEMENT_THRESHOLD = 0.02


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _abs(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    return str(p if p.is_absolute() else (ROOT / p).resolve())


def _emit_thesis_from_promotion(promo: dict) -> str:
    linkmap_path = _abs(promo.get('input_linkmap_path'))
    if not linkmap_path:
        raise SystemExit('promotion_run missing input_linkmap_path')
    lm = _load(linkmap_path)
    rc = _abs(lm.get('research_card_path'))
    ir = [_abs(p) for p in lm.get('indicator_record_paths', [])[:10]]
    out = _run([
        PY, 'scripts/pipeline/emit_thesis.py',
        '--research-card-path', rc,
        '--indicator-record-paths', json.dumps(ir),
        '--linkmap-paths', json.dumps([linkmap_path]),
    ])
    thesis_path = json.loads(out)['thesis_path']
    _run([PY, 'scripts/pipeline/verify_pipeline_stage2.py', '--thesis', thesis_path])
    return thesis_path


def _emit_base_spec(thesis_path: str) -> str:
    out = _run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', thesis_path])
    return json.loads(out)['strategy_spec_path']


def _ensure_components_and_complexity(v: dict) -> dict:
    vv = deepcopy(v)
    comps = vv.get('components') or [
        {'indicator': 'TPX', 'role': 'confirmation', 'notes': 'pressure confirmation'},
        {'indicator': 'MACD-long', 'role': 'trend', 'notes': 'trend context'},
        {'indicator': 'MACD-short', 'role': 'entry', 'notes': 'entry alignment'},
    ]
    vv['components'] = comps[:10]
    condition_count = len(vv.get('entry_long', [])) + len(vv.get('entry_short', [])) + len(vv.get('filters', [])) + len(vv.get('exit_rules', []))
    vv['complexity'] = {
        'indicator_count': len(vv['components']),
        'condition_count': condition_count,
        'parameter_count': len(vv.get('parameters', [])),
    }
    return vv


def _variant_name(base: str, suffix: str) -> str:
    return f"{base[:40]}_{suffix}"[:80]


def _explore_mutations(base: dict) -> list[dict]:
    out = []
    # 1) role_swap TPX across entry/confirmation/regime_gate
    for role in ['entry', 'confirmation', 'regime_gate']:
        v = _ensure_components_and_complexity(base)
        for c in v['components']:
            if c['indicator'].upper() == 'TPX':
                c['role'] = role
                c['notes'] = f'TPX role_swap to {role}'
        v['name'] = _variant_name(base['name'], f'role_{role}')
        v['description'] = f'Explore role swap TPX->{role}'
        out.append(v)

    # 2) add_gate (session filter note if unsupported)
    v2 = _ensure_components_and_complexity(base)
    v2['name'] = _variant_name(base['name'], 'session_gate')
    v2['filters'] = (v2.get('filters', []) + ['session_gate=US (note: skip if unsupported)'])[:10]
    v2['components'] = (v2['components'] + [{'indicator': 'SESSION', 'role': 'regime_gate', 'notes': 'US session gate (conditional support)'}])[:10]
    v2 = _ensure_components_and_complexity(v2)
    out.append(v2)

    # 3) remove_component (one confirmation/filter)
    v3 = _ensure_components_and_complexity(base)
    v3['name'] = _variant_name(base['name'], 'remove_component')
    for i, c in enumerate(v3['components']):
        if c['role'] in ('confirmation', 'regime_gate'):
            del v3['components'][i]
            break
    v3 = _ensure_components_and_complexity(v3)
    out.append(v3)

    # 4) add_builtin_filter
    v4 = _ensure_components_and_complexity(base)
    v4['name'] = _variant_name(base['name'], 'builtin_gate')
    v4['components'] = (v4['components'] + [{'indicator': 'MA_SLOPE', 'role': 'regime_gate', 'notes': 'builtin slope regime filter'}])[:10]
    v4['filters'] = (v4.get('filters', []) + ['builtin_filter=ma_slope_positive'])[:10]
    v4 = _ensure_components_and_complexity(v4)
    out.append(v4)

    uniq = []
    seen = set()
    for v in out:
        if v['name'] in seen:
            continue
        seen.add(v['name'])
        uniq.append(v)
    return uniq[:MAX_EXPLORE_PER_ITER]


def _exploit_mutations(base: dict) -> list[dict]:
    out = []
    sweeps = [(1.2, 1.8), (1.5, 2.2), (2.0, 3.0), (1.4, 2.0), (1.8, 2.6), (2.2, 3.2), (1.1, 1.6)]
    for i, (sm, tm) in enumerate(sweeps, 1):
        v = _ensure_components_and_complexity(base)
        v['name'] = _variant_name(base['name'], f'exploit_{i}')
        v['risk_policy']['stop_atr_mult'] = float(sm)
        v['risk_policy']['tp_atr_mult'] = float(tm)
        v['description'] = f'Exploit ATR risk tweak stop={sm}, tp={tm}'
        out.append(v)
    return out[:MAX_VARIANTS_PER_ITER - MAX_EXPLORE_PER_ITER]


def _write_spec(template: dict, thesis_path: str, variants: list[dict]) -> str:
    spec = deepcopy(template)
    spec['id'] = f"strategy-spec-{datetime.now().strftime('%Y%m%d')}-refine-{uuid.uuid4().hex[:8]}"
    spec['source_thesis_path'] = thesis_path.replace('\\', '/')
    spec['variants'] = [_ensure_components_and_complexity(v) for v in variants][:MAX_VARIANTS_PER_ITER]
    out_dir = ROOT / 'artifacts' / 'strategy_specs' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{spec['id']}.strategy_spec.json"
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(out_path).replace('\\', '/')


def _score_batch_summary(summary: dict, complexity: dict) -> float:
    base_score = float(summary.get('profit_factor', 0.0)) - (float(summary.get('max_drawdown', 0.0)) / 10000.0)
    indicator_count = int(complexity.get('indicator_count', 0))
    condition_count = int(complexity.get('condition_count', 0))
    parameter_count = int(complexity.get('parameter_count', 0))
    complexity_pen = 0.05 * max(0, indicator_count - 2) + 0.03 * max(0, condition_count - 8) + 0.02 * max(0, parameter_count - 6)
    gate_pen = 1000.0 if int(summary.get('failed_runs', 0)) > 0 else 0.0
    return base_score - complexity_pen - gate_pen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--promotion-run', required=True)
    ap.add_argument('--max-iters', type=int, default=MAX_ITERS)
    ap.add_argument('--improvement-threshold', type=float, default=IMPROVEMENT_THRESHOLD)
    args = ap.parse_args()

    promo = _load(args.promotion_run)
    thesis_path = _emit_thesis_from_promotion(promo)
    base_spec_path = _emit_base_spec(thesis_path)
    base_spec = _load(_abs(base_spec_path))
    champion = _ensure_components_and_complexity(deepcopy(base_spec['variants'][0]))

    history = []
    best_score = None
    best_delta = None
    total_explore_used = 0
    stop_reason = 'max_iterations_reached'
    final_recommendation = 'NO_IMPROVEMENT'
    winner = None

    for it in range(1, min(args.max_iters, MAX_ITERS) + 1):
        exploit = _exploit_mutations(champion)
        explore = _explore_mutations(champion)
        total_explore_used += len(explore)

        variants = [champion] + exploit + explore
        variants = variants[:MAX_VARIANTS_PER_ITER]

        iter_spec_path = _write_spec(base_spec, thesis_path, variants)

        iter_results = []
        for v in variants:
            bout = _run([
                PY, 'scripts/pipeline/run_batch_backtests.py',
                '--strategy-spec', iter_spec_path,
                '--variant', v['name'],
            ])
            bi = json.loads(bout)
            b = _load(bi['batch_artifact_path'])
            summary = b.get('summary', {})
            score = _score_batch_summary(summary, v.get('complexity', {}))
            iter_results.append({
                'variant_name': v['name'],
                'batch_backtest_path': bi['batch_artifact_path'],
                'experiment_plan_path': bi.get('experiment_plan_path'),
                'summary': summary,
                'complexity': v.get('complexity', {}),
                'score': score,
                'explore': v in explore,
            })

        iter_results.sort(key=lambda x: x['score'], reverse=True)
        iter_best = iter_results[0]
        delta = None if best_score is None else (iter_best['score'] - best_score)
        if best_score is None or iter_best['score'] > best_score:
            best_score = iter_best['score']
            winner = iter_best
            for v in variants:
                if v['name'] == iter_best['variant_name']:
                    champion = deepcopy(v)
                    break
        if delta is not None:
            best_delta = delta

        history.append({
            'iteration': it,
            'explore_variants_count': len(explore),
            'exploit_variants_count': len(exploit),
            'variants_total': len(variants),
            'best_variant': iter_best['variant_name'],
            'best_score': iter_best['score'],
            'score_delta_vs_prev_best': delta,
            'results': iter_results,
        })

        if delta is not None and delta < args.improvement_threshold:
            stop_reason = 'early_stop_no_improvement'
            final_recommendation = 'NO_IMPROVEMENT'
            break

    if winner and winner['summary'].get('failed_runs', 0) == 0:
        final_recommendation = 'CANDIDATE_FOUND'

    payload = {
        'schema_version': '2.0',
        'id': f"refine_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'seed': {
            'promotion_run_path': args.promotion_run,
            'thesis_path': thesis_path,
            'base_strategy_spec_path': base_spec_path,
        },
        'iterations_used': len(history),
        'explore_variants_used_total': total_explore_used,
        'improvement_threshold': args.improvement_threshold,
        'best_score_delta': best_delta,
        'history': history,
        'winner': winner,
        'final_recommendation': final_recommendation,
        'stop_reason': stop_reason,
    }

    out_dir = ROOT / 'artifacts' / 'refinement' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{payload['id']}.refinement_cycle.json"
    out_path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')

    print(json.dumps({'refinement_cycle_path': str(out_path), 'iterations_used': len(history), 'explore_variants_used_total': total_explore_used, 'best_score_delta': best_delta}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
