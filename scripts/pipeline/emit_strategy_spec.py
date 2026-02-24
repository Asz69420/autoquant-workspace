#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 60 * 1024
MAX_INDEX = 200


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def jload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def update_index(index_path: Path, pointer: str) -> None:
    items = []
    if index_path.exists():
        try:
            items = json.loads(index_path.read_text(encoding='utf-8'))
        except Exception:
            items = []
    if pointer in items:
        items.remove(pointer)
    items.insert(0, pointer)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(items[:MAX_INDEX], indent=2), encoding='utf-8')


def unique(items: list[str], limit: int) -> list[str]:
    out = []
    for x in items:
        s = str(x).strip()
        if s and s not in out:
            out.append(s[:240])
        if len(out) >= limit:
            break
    return out


def build_baseline(thesis: dict) -> dict:
    constraints = unique(thesis.get('constraints', []), 10)
    req = unique(thesis.get('required_data', []), 10)
    hyps = thesis.get('hypotheses', [])
    sigs = thesis.get('candidate_signals', [])

    entry_long = unique([
        'Require trend/confirmation alignment on bar close.',
        'Require candidate signal confidence >= 0.60.',
        'Require thesis regime match before long entry.',
    ] + [f"Use signal: {s.get('name','signal')}" for s in sigs], 10)

    entry_short = unique([
        'Require inverse trend/confirmation alignment on bar close.',
        'Require candidate signal confidence >= 0.60.',
        'Reject short if thesis regime does not support reversal.',
    ] + [f"Use signal: {s.get('name','signal')}" for s in sigs], 10)

    filters = unique([
        'No repaint sources only.',
        'Bar-close execution only.',
    ] + constraints, 10)

    exit_rules = unique([
        'Exit on signal invalidation.',
        'Exit on opposite alignment signal.',
        'Exit on max bars in trade threshold.',
    ] + [f"Hypothesis failure mode guard: {m}" for h in hyps for m in h.get('failure_modes', [])], 10)

    risk_rules = unique([
        'Risk per trade <= 1R.',
        'Stop at structure invalidation level.',
        'Take profit with minimum 2R objective.',
    ], 10)

    parameters = [
        {"name": "confidence_threshold", "min": 0.5, "max": 0.9, "step": 0.05, "default": 0.6},
        {"name": "max_bars_in_trade", "min": 3, "max": 50, "step": 1, "default": 15},
        {"name": "risk_r", "min": 0.25, "max": 2.0, "step": 0.25, "default": 1.0},
    ]

    if req:
        filters = unique(filters + [f"Data required: {req[0]}"], 10)

    return {
        'name': 'baseline',
        'description': 'Direct deterministic mapping from thesis signals, constraints, and hypotheses.',
        'entry_long': entry_long,
        'entry_short': entry_short,
        'filters': filters,
        'exit_rules': exit_rules,
        'risk_rules': risk_rules,
        'parameters': parameters,
        'constraints': constraints,
    }


def variant_perturbation(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'param_perturbation'
    v['description'] = 'Single parameter perturbation on confidence threshold.'
    for p in v['parameters']:
        if p['name'] == 'confidence_threshold':
            p['default'] = min(p['max'], round(float(p.get('default', 0.6)) + 0.1, 2))
            break
    return v


def variant_remove_component(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'remove_component'
    v['description'] = 'Remove one non-critical filter component.'
    if v['filters']:
        v['filters'] = v['filters'][1:] or v['filters']
    return v


def variant_threshold_mutation(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'threshold_mutation'
    v['description'] = 'Mutation on exit threshold and bar hold duration.'
    v['exit_rules'] = unique(v['exit_rules'] + ['Exit if confidence drops below 0.45.'], 10)
    for p in v['parameters']:
        if p['name'] == 'max_bars_in_trade':
            p['default'] = max(p['min'], int(p.get('default', 15) - 3))
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--thesis-path', required=True)
    ap.add_argument('--output-root', default='artifacts/strategy_specs')
    args = ap.parse_args()

    thesis = jload(args.thesis_path)
    baseline = build_baseline(thesis)
    variants = [
        baseline,
        variant_perturbation(baseline),
        variant_remove_component(baseline),
        variant_threshold_mutation(baseline),
    ][:5]

    sid = f"strategy-spec-{datetime.now().strftime('%Y%m%d')}-{thesis.get('id','thesis')[-12:]}"
    spec = {
        'schema_version': '1.0',
        'id': sid,
        'created_at': now_iso(),
        'source_thesis_path': args.thesis_path.replace('\\', '/'),
        'variants': variants,
    }

    payload = json.dumps(spec, ensure_ascii=False, indent=2)
    if len(payload.encode('utf-8')) > MAX_JSON_BYTES:
        raise SystemExit('StrategySpec JSON exceeds 60KB')

    out_dir = Path(args.output_root) / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sid}.strategy_spec.json"
    out_path.write_text(payload, encoding='utf-8')

    update_index(Path(args.output_root) / 'INDEX.json', str(out_path).replace('\\', '/'))
    print(json.dumps({'strategy_spec_path': str(out_path).replace('\\', '/'), 'variants': len(variants), 'baseline_entry_long': variants[0]['entry_long'][:1]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
