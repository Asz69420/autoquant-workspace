#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

MAX_ITERS = 3
MAX_VARIANTS_PER_ITER = 10
MAX_EXPLORE_PER_ITER = 3
IMPROVEMENT_THRESHOLD = 0.02


def _run(cmd: list[str], extra_env: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True, env=env)
    return p.stdout.strip()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _abs(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    return str(p if p.is_absolute() else (ROOT / p).resolve())


def _emit_thesis_from_promotion(promo: dict) -> str:
    linkmap_path = _abs(promo.get('input_linkmap_path'))
    lm = _load(linkmap_path)
    rc = _abs(lm.get('research_card_path'))
    ir = [_abs(p) for p in lm.get('indicator_record_paths', [])[:10]]
    reasoning_env = {
        'OPENCLAW_MODEL_ID': 'openai-codex/gpt-5.3-codex',
        'OPENCLAW_REASONING_EFFORT': 'high',
    }
    out = _run([PY, 'scripts/pipeline/emit_thesis.py', '--research-card-path', rc, '--indicator-record-paths', json.dumps(ir), '--linkmap-paths', json.dumps([linkmap_path])], extra_env=reasoning_env)
    thesis_path = json.loads(out)['thesis_path']
    _run([PY, 'scripts/pipeline/verify_pipeline_stage2.py', '--thesis', thesis_path])
    return thesis_path


def _emit_base_spec(thesis_path: str) -> str:
    reasoning_env = {
        'OPENCLAW_MODEL_ID': 'openai-codex/gpt-5.3-codex',
        'OPENCLAW_REASONING_EFFORT': 'high',
    }
    out = _run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', thesis_path], extra_env=reasoning_env)
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
    vv['complexity'] = {'indicator_count': len(vv['components']), 'condition_count': condition_count, 'parameter_count': len(vv.get('parameters', []))}
    return vv


def _variant_name(base: str, suffix: str) -> str:
    return f"{base[:40]}_{suffix}"[:80]


def _explore_catalog(base: dict) -> list[dict]:
    out = []
    for role in ['entry', 'confirmation', 'regime_gate']:
        v = _ensure_components_and_complexity(base)
        for c in v['components']:
            if c['indicator'].upper() == 'TPX':
                c['role'] = role
                c['notes'] = f'TPX role_swap to {role}'
        v['name'] = _variant_name(base['name'], f'role_{role}')
        out.append(v)

    v2 = _ensure_components_and_complexity(base)
    v2['name'] = _variant_name(base['name'], 'session_gate')
    v2['filters'] = (v2.get('filters', []) + ['session_gate=US (skip if unsupported)'])[:10]
    out.append(_ensure_components_and_complexity(v2))

    v3 = _ensure_components_and_complexity(base)
    v3['name'] = _variant_name(base['name'], 'remove_component')
    if v3['components']:
        v3['components'] = v3['components'][:-1]
    out.append(_ensure_components_and_complexity(v3))

    v4 = _ensure_components_and_complexity(base)
    v4['name'] = _variant_name(base['name'], 'builtin_gate')
    v4['components'] = (v4['components'] + [{'indicator': 'MA_SLOPE', 'role': 'regime_gate', 'notes': 'builtin slope regime filter'}])[:10]
    out.append(_ensure_components_and_complexity(v4))
    return out


def _exploit_mutations(base: dict) -> list[dict]:
    out = []
    sweeps = [(1.2, 1.8), (1.5, 2.2), (2.0, 3.0), (1.4, 2.0), (1.8, 2.6), (2.2, 3.2), (1.1, 1.6)]
    for i, (sm, tm) in enumerate(sweeps, 1):
        v = _ensure_components_and_complexity(base)
        v['name'] = _variant_name(base['name'], f'exploit_{i}')
        v['risk_policy']['stop_atr_mult'] = float(sm)
        v['risk_policy']['tp_atr_mult'] = float(tm)
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
    pf = float(summary.get('profit_factor', 0.0))
    dd_pct = float(summary.get('max_drawdown_pct', 0.0))
    total_trades = int(summary.get('total_trades', 0))

    # Base: profit factor (capped at 5 to prevent overfit outliers)
    pf_score = min(pf, 5.0)

    # Drawdown penalty: lower is better, scale 0-1
    dd_penalty = min(dd_pct / 50.0, 1.0)  # 50% DD = max penalty

    # Trade count factor: penalize < 30 trades (low confidence)
    trade_factor = min(total_trades / 30.0, 1.0)

    # Complexity penalty (keep existing logic)
    complexity_pen = 0.05 * max(0, int(complexity.get('indicator_count', 0)) - 2) + 0.03 * max(0, int(complexity.get('condition_count', 0)) - 8) + 0.02 * max(0, int(complexity.get('parameter_count', 0)) - 6)

    # Gate penalty: failed runs still kill score but not as extreme
    gate_pen = 5.0 if int(summary.get('failed_runs', 0)) > 0 else 0.0

    # Composite: PF weighted by trade confidence, minus drawdown and complexity
    score = (pf_score * trade_factor) - dd_penalty - complexity_pen - gate_pen
    return round(score, 6)


def _latest_meta(symbol: str, tf: str) -> Path:
    d = ROOT / 'artifacts' / 'data' / 'hyperliquid' / symbol / tf
    metas = sorted(d.glob('*.meta.json'))
    return metas[-1]


def _add_months(dt: datetime, months: int) -> datetime:
    # UTC naive-safe month arithmetic
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    d = min(dt.day, 28)
    return dt.replace(year=y, month=m, day=d)


def _holdout_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    if (end - start).days >= 180:
        w1 = (_add_months(end, -6), _add_months(end, -4))
        w2 = (_add_months(end, -3), _add_months(end, -2))
        w3 = (_add_months(end, -1), end)
        return [(max(start, a), min(end, b)) for a, b in [w1, w2, w3]]
    tail = end - timedelta(days=max(30, int((end - start).days * 0.5)))
    total = max(3, (end - tail).days)
    seg = total // 3
    a1, b1 = tail, tail + timedelta(days=seg)
    a2, b2 = b1, b1 + timedelta(days=seg)
    a3, b3 = b2, end
    return [(a1, b1), (a2, b2), (a3, b3)]


def _slice_training_meta(meta_path: Path, holdout: tuple[datetime, datetime], iter_idx: int) -> Path:
    meta = _load(meta_path)
    csv_path = Path(str(meta_path).replace('.meta.json', '.csv'))
    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8-sig', newline='')))
    hs, he = holdout
    keep = []
    for r in rows:
        t = datetime.fromisoformat(r['time'].replace('Z', '+00:00'))
        if hs.tzinfo is not None and t.tzinfo is None:
            t = t.replace(tzinfo=hs.tzinfo)
        if hs.tzinfo is None and t.tzinfo is not None:
            hs = hs.replace(tzinfo=t.tzinfo)
            he = he.replace(tzinfo=t.tzinfo)
        if hs <= t < he:
            continue
        keep.append(r)
    out_dir = ROOT / 'artifacts' / 'datasets' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"iter{iter_idx}_{meta.get('symbol')}_{meta.get('timeframe')}.csv"
    out_meta = out_dir / f"iter{iter_idx}_{meta.get('symbol')}_{meta.get('timeframe')}.meta.json"
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        fieldnames = list(rows[0].keys()) if rows else ['time', 'open', 'high', 'low', 'close']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(keep)
    start_t = keep[0]['time'] if keep else meta.get('start')
    end_t = keep[-1]['time'] if keep else meta.get('end')
    out_meta.write_text(json.dumps({'symbol': meta.get('symbol'), 'timeframe': meta.get('timeframe'), 'start': start_t, 'end': end_t}), encoding='utf-8')
    return out_meta


def _sobol_seed(strategy_spec_path: str, strategy_index_counter: int) -> int:
    h = hashlib.sha256(Path(strategy_spec_path).read_bytes()).hexdigest()
    return int(h[:8], 16) ^ int(strategy_index_counter)


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

    meta_ref = _load(_latest_meta('BTC', '4h'))
    start = datetime.fromisoformat(meta_ref['start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(meta_ref['end'].replace('Z', '+00:00'))
    holdouts = _holdout_windows(start, end)

    history, winner = [], None
    best_score, best_delta = None, None
    total_explore_used = 0
    strategy_index_counter = 0
    stop_reason = 'max_iterations_reached'
    final_recommendation = 'NO_IMPROVEMENT'

    for it in range(1, min(args.max_iters, MAX_ITERS) + 1):
        exploit = _exploit_mutations(champion)
        catalog = _explore_catalog(champion)
        sobol_seed = _sobol_seed(_abs(base_spec_path), strategy_index_counter)
        base_explore_index = (10 + strategy_index_counter) if it == 2 else strategy_index_counter
        explore = [catalog[(base_explore_index + i) % len(catalog)] for i in range(MAX_EXPLORE_PER_ITER)]
        total_explore_used += len(explore)

        variants = ([champion] + exploit + explore)[:MAX_VARIANTS_PER_ITER]
        iter_spec_path = _write_spec(base_spec, thesis_path, variants)

        holdout = holdouts[it - 1]
        train_metas = []
        for sym, tf in [('BTC', '1h'), ('BTC', '4h'), ('ETH', '1h'), ('ETH', '4h')]:
            m = _latest_meta(sym, tf)
            train_metas.append(str(_slice_training_meta(m, holdout, it)))
        meta_list_path = ROOT / 'artifacts' / 'datasets' / datetime.now().strftime('%Y%m%d') / f'iter{it}_datasets.json'
        meta_list_path.write_text(json.dumps(train_metas), encoding='utf-8')

        iter_results = []
        for v in variants:
            bout = _run([PY, 'scripts/pipeline/run_batch_backtests.py', '--strategy-spec', iter_spec_path, '--variant', v['name'], '--datasets', str(meta_list_path)])
            bi = json.loads(bout)
            b = _load(bi['batch_artifact_path'])
            summary = b.get('summary', {})
            score = _score_batch_summary(summary, v.get('complexity', {}))
            iter_results.append({'variant_name': v['name'], 'batch_backtest_path': bi['batch_artifact_path'], 'summary': summary, 'complexity': v.get('complexity', {}), 'score': score, 'explore': v in explore})

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
            'sobol_seed': sobol_seed,
            'base_explore_index': base_explore_index,
            'explore_variants_count': len(explore),
            'exploit_variants_count': len(exploit),
            'variants_total': len(variants),
            'holdout_window': {'start': holdout[0].isoformat(), 'end': holdout[1].isoformat()},
            'best_variant': iter_best['variant_name'],
            'best_score': iter_best['score'],
            'score_delta_vs_prev_best': delta,
            'results': iter_results,
        })

        strategy_index_counter += 1
        if delta is not None and delta < args.improvement_threshold:
            stop_reason = 'early_stop_no_improvement'
            break

    if winner and winner['summary'].get('failed_runs', 0) == 0:
        final_recommendation = 'CANDIDATE_FOUND'

    payload = {
        'schema_version': '2.1',
        'id': f"refine_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'seed': {'promotion_run_path': args.promotion_run, 'thesis_path': thesis_path, 'base_strategy_spec_path': base_spec_path},
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
