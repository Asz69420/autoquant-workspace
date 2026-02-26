#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 60 * 1024
MAX_INDEX = 200
ROOT = Path(__file__).resolve().parents[2]


def _set_reasoning_effort_for_strategist() -> None:
    model_id = (os.getenv('OPENCLAW_MODEL_ID') or 'openai-codex/gpt-5.3-codex').strip()
    effort = 'default'
    if 'gpt-5.3-codex' in model_id:
        os.environ['OPENAI_REASONING_EFFORT'] = 'high'
        os.environ['OPENCLAW_REASONING_EFFORT'] = 'high'
        effort = 'high'

    cmd = [
        sys.executable,
        'scripts/log_event.py',
        '--run-id', f"reasoning-strategist-{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
        '--agent', 'oQ',
        '--model-id', model_id,
        '--action', 'strategist_reasoning',
        '--status-word', 'INFO',
        '--status-emoji', 'ℹ️',
        '--reason-code', 'REASONING_EFFORT_SET',
        '--summary', f'stage=Strategist effort={effort}',
        '--outputs', f'model={model_id}'
    ]
    try:
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


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


def _with_structured_policies(variant: dict, *, stop_atr_mult: float, tp_atr_mult: float, entry_fill: str = 'bar_close', tie_break: str = 'worst_case', allow_reverse: bool = True, risk_pct: float = 1.0, note: str = '') -> dict:
    v = copy.deepcopy(variant)
    notes = unique(v.get('risk_rules', []), 10)
    if note:
        notes = unique(notes + [note], 10)
    v['risk_rules'] = notes
    v['risk_policy'] = {
        'stop_type': 'atr',
        'stop_atr_mult': float(stop_atr_mult),
        'tp_type': 'atr',
        'tp_atr_mult': float(tp_atr_mult),
        'risk_per_trade_pct': float(risk_pct),
    }
    v['execution_policy'] = {
        'entry_fill': entry_fill,
        'tie_break': tie_break,
        'allow_reverse': bool(allow_reverse),
    }
    return v


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
        'Risk note: ATR placeholder used for backtester compatibility when discretionary/swing stop is implied.',
        'Risk note: risk per trade target is 1%.',
        'Take profit objective maps to ATR multiple for deterministic execution.',
    ], 10)

    parameters = [
        {"name": "confidence_threshold", "min": 0.5, "max": 0.9, "step": 0.05, "default": 0.6},
        {"name": "max_bars_in_trade", "min": 3, "max": 50, "step": 1, "default": 15},
        {"name": "risk_r", "min": 0.25, "max": 2.0, "step": 0.25, "default": 1.0},
    ]

    if req:
        filters = unique(filters + [f"Data required: {req[0]}"], 10)

    base = {
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
    return _with_structured_policies(base, stop_atr_mult=1.5, tp_atr_mult=2.0, entry_fill='bar_close', tie_break='worst_case', allow_reverse=True, risk_pct=1.0)


def variant_perturbation(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'param_perturbation'
    v['description'] = 'Single parameter perturbation on confidence threshold.'
    for p in v['parameters']:
        if p['name'] == 'confidence_threshold':
            p['default'] = min(p['max'], round(float(p.get('default', 0.6)) + 0.1, 2))
            break
    return _with_structured_policies(v, stop_atr_mult=1.7, tp_atr_mult=2.2, entry_fill='bar_close', tie_break='worst_case', allow_reverse=True, risk_pct=1.0)


def variant_remove_component(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'remove_component'
    v['description'] = 'Remove one non-critical filter component.'
    if v['filters']:
        v['filters'] = v['filters'][1:] or v['filters']
    return _with_structured_policies(v, stop_atr_mult=1.5, tp_atr_mult=1.8, entry_fill='bar_close', tie_break='worst_case', allow_reverse=True, risk_pct=1.0)


def variant_threshold_mutation(base: dict) -> dict:
    v = copy.deepcopy(base)
    v['name'] = 'threshold_mutation'
    v['description'] = 'Mutation on exit threshold and bar hold duration.'
    v['exit_rules'] = unique(v['exit_rules'] + ['Exit if confidence drops below 0.45.'], 10)
    for p in v['parameters']:
        if p['name'] == 'max_bars_in_trade':
            p['default'] = max(p['min'], int(p.get('default', 15) - 3))
    return _with_structured_policies(v, stop_atr_mult=1.3, tp_atr_mult=2.0, entry_fill='next_open', tie_break='stop_first', allow_reverse=False, risk_pct=0.75)


def _indicator_evaluable(thesis: dict) -> bool:
    if not isinstance(thesis, dict):
        return False
    if thesis.get('candidate_signals'):
        return True
    if thesis.get('combo_proposals'):
        return True
    if thesis.get('required_data'):
        return True

    # Soft signal: mention of indicator usage in hypotheses or bullets
    text_pool = []
    text_pool.extend(thesis.get('thesis_bullets', []) or [])
    for h in thesis.get('hypotheses', []) or []:
        if isinstance(h, dict):
            text_pool.extend([h.get('statement', ''), h.get('rationale', '')])
    blob = ' '.join(str(x).lower() for x in text_pool if x)
    return any(k in blob for k in ['indicator', 'signal', 'trend', 'regime', 'confirmation', 'ohlcv'])


def _fallback_templates(thesis: dict) -> list[dict]:
    constraints = unique(thesis.get('constraints', []), 10)
    req = unique(thesis.get('required_data', []), 10)
    indicator_names = unique([
        cp.get('indicator', '') for cp in (thesis.get('combo_proposals', []) or []) if isinstance(cp, dict)
    ], 5)
    indicator_hint = indicator_names[0] if indicator_names else 'catalog_indicator'

    common_filters = unique([
        'No repaint sources only.',
        'Bar-close execution only.',
        f'Indicator evaluable: {indicator_hint}',
    ] + constraints + ([f'Data required: {req[0]}'] if req else []), 10)

    common_exit = unique([
        'Exit on opposite directional confirmation.',
        'Exit on max bars in trade threshold.',
        'Exit if confidence drops below 0.45.',
    ], 10)

    params = [
        {"name": "confidence_threshold", "min": 0.45, "max": 0.9, "step": 0.05, "default": 0.6},
        {"name": "max_bars_in_trade", "min": 3, "max": 50, "step": 1, "default": 15},
        {"name": "risk_r", "min": 0.25, "max": 2.0, "step": 0.25, "default": 1.0},
    ]

    trend = {
        'name': 'FALLBACK_TEMPLATE_TREND',
        'description': f'Fallback executable template: use {indicator_hint} as trend direction gate.',
        'entry_long': unique([
            f'Long when {indicator_hint} trend state is bullish at bar close.',
            'Require confidence >= 0.60.',
        ], 10),
        'entry_short': unique([
            f'Short when {indicator_hint} trend state is bearish at bar close.',
            'Require confidence >= 0.60.',
        ], 10),
        'filters': common_filters,
        'exit_rules': common_exit,
        'risk_rules': unique(['Fallback template: trend gate mode.'], 10),
        'parameters': copy.deepcopy(params),
        'constraints': constraints,
    }

    confirmation = {
        'name': 'FALLBACK_TEMPLATE_CONFIRMATION',
        'description': f'Fallback executable template: use {indicator_hint} as confirmation with baseline trend proxy.',
        'entry_long': unique([
            'Long only if baseline trend proxy is up.',
            f'And {indicator_hint} confirms bullish pressure.',
        ], 10),
        'entry_short': unique([
            'Short only if baseline trend proxy is down.',
            f'And {indicator_hint} confirms bearish pressure.',
        ], 10),
        'filters': common_filters,
        'exit_rules': common_exit,
        'risk_rules': unique(['Fallback template: confirmation mode.'], 10),
        'parameters': copy.deepcopy(params),
        'constraints': constraints,
    }

    regime = {
        'name': 'FALLBACK_TEMPLATE_REGIME_GATE',
        'description': f'Fallback executable template: use {indicator_hint} as regime gate to enable/disable entries.',
        'entry_long': unique([
            'Long on baseline directional trigger.',
            f'Only when {indicator_hint} regime gate allows risk-on.',
        ], 10),
        'entry_short': unique([
            'Short on baseline directional trigger.',
            f'Only when {indicator_hint} regime gate allows risk-off.',
        ], 10),
        'filters': common_filters,
        'exit_rules': common_exit,
        'risk_rules': unique(['Fallback template: regime gate mode.'], 10),
        'parameters': copy.deepcopy(params),
        'constraints': constraints,
    }

    return [
        _with_structured_policies(trend, stop_atr_mult=1.5, tp_atr_mult=2.0, entry_fill='bar_close', tie_break='worst_case', allow_reverse=True, risk_pct=1.0),
        _with_structured_policies(confirmation, stop_atr_mult=1.6, tp_atr_mult=2.1, entry_fill='bar_close', tie_break='worst_case', allow_reverse=True, risk_pct=1.0),
        _with_structured_policies(regime, stop_atr_mult=1.4, tp_atr_mult=1.9, entry_fill='next_open', tie_break='stop_first', allow_reverse=False, risk_pct=0.75),
    ][:3]


def _latest_outcome_guidance(limit: int = 5) -> list[str]:
    out_root = ROOT / 'artifacts' / 'outcomes'
    files = sorted(out_root.glob('**/outcome_notes_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    notes: list[str] = []
    for p in files[: max(1, limit)]:
        try:
            obj = json.loads(p.read_text(encoding='utf-8'))
            if str(obj.get('schema_version')) == '2.0':
                for h in (obj.get('next_experiments') or [])[:2]:
                    hs = str(h).strip()
                    if hs:
                        notes.append(f'Outcome-guided experiment: {hs}')
                for f in (obj.get('failure_reasons') or [])[:1]:
                    fs = str((f or {}).get('short') or '').strip()
                    if fs:
                        notes.append(f'Avoid prior failure pattern: {fs}')
            else:
                for h in (obj.get('next_hypotheses') or [])[:2]:
                    hs = str(h).strip()
                    if hs:
                        notes.append(f'Outcome-guided hypothesis: {hs}')
                for f in (obj.get('what_failed') or [])[:1]:
                    fs = str(f).strip()
                    if fs:
                        notes.append(f'Avoid prior failure pattern: {fs}')
        except Exception:
            continue
    return unique(notes, 10)


def _collect_v2_directives(limit_notes: int = 5, strategy_family: str = '', template: str = '') -> list[dict]:
    out_root = ROOT / 'artifacts' / 'outcomes'
    files = sorted(out_root.glob('**/outcome_notes_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    directives: list[dict] = []
    for p in files[: max(1, limit_notes)]:
        try:
            obj = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if str(obj.get('schema_version')) != '2.0':
            continue
        note_family = str(obj.get('strategy_family') or '')
        note_template = str(obj.get('template') or '')
        family_ok = (not strategy_family) or (strategy_family == note_family)
        template_ok = (not template) or (template == note_template)
        if not (family_ok or template_ok):
            continue
        for d in (obj.get('directives') or [])[:5]:
            if isinstance(d, dict) and d.get('id') and d.get('type'):
                directives.append(d)
    return directives[:5]


def _apply_directive(base: dict, directive: dict, idx: int) -> dict:
    v = copy.deepcopy(base)
    d_type = str(directive.get('type') or '')
    params = directive.get('params') or {}
    v['name'] = f"directive_variant_{idx}_{d_type.lower()}"
    v['description'] = f"Directive-driven variant from {d_type}."
    v['origin'] = 'DIRECTIVE'
    v['directive_refs'] = [str(directive.get('id'))]

    if d_type in {'THRESHOLD_SWEEP', 'PARAM_SWEEP'}:
        for p in v.get('parameters', []):
            if p.get('name') == 'confidence_threshold' and isinstance(p.get('default'), (int, float)):
                p['default'] = max(p.get('min', 0.45), min(p.get('max', 0.9), round(float(p['default']) + 0.05, 2)))
    elif d_type == 'ENTRY_TIGHTEN':
        v['filters'] = unique((v.get('filters') or []) + ['Directive: tighter entry gating enabled.'], 10)
    elif d_type == 'ENTRY_RELAX':
        for p in v.get('parameters', []):
            if p.get('name') == 'confidence_threshold' and isinstance(p.get('default'), (int, float)):
                p['default'] = max(p.get('min', 0.45), round(float(p['default']) - 0.05, 2))
    elif d_type == 'EXIT_CHANGE':
        v['exit_rules'] = unique((v.get('exit_rules') or []) + ['Directive: revised stop/take-profit profile.'], 10)
    elif d_type == 'GATE_ADJUST':
        v['risk_rules'] = unique((v.get('risk_rules') or []) + [f"Directive gate adjust: {json.dumps(params, sort_keys=True)}"], 10)
    elif d_type == 'ROLE_SWAP':
        v['entry_long'] = unique((v.get('entry_long') or []) + ['Directive: swapped confirmation and entry role mapping.'], 10)
    elif d_type == 'TEMPLATE_SWITCH':
        target = str(params.get('target') or 'alternate_template')
        v['description'] = f"Directive template switch toward {target}."

    return v


def _directive_variants(seed: dict, directives: list[dict]) -> list[dict]:
    if not directives:
        return []
    chosen = directives[:3]
    out: list[dict] = []
    for i, d in enumerate(chosen[:2], start=1):
        out.append(_apply_directive(seed, d, i))

    explore = copy.deepcopy(seed)
    explore['name'] = 'directive_exploration'
    explore['description'] = 'Exploration variant generated from directive context.'
    explore['origin'] = 'EXPLORATION'
    explore['directive_refs'] = [str(d.get('id')) for d in chosen]
    explore['filters'] = unique((explore.get('filters') or []) + ['Directive exploration: combine moderate entry + exit changes.'], 10)
    out.append(explore)
    return out[:3]


def _apply_outcome_guidance(variants: list[dict], limit: int = 5) -> list[dict]:
    guidance = _latest_outcome_guidance(limit=limit)
    if not guidance:
        return variants
    out: list[dict] = []
    for v in variants:
        nv = copy.deepcopy(v)
        nv['risk_rules'] = unique((nv.get('risk_rules') or []) + guidance[:3], 10)
        nv['filters'] = unique((nv.get('filters') or []) + guidance[:2], 10)
        out.append(nv)
    return out


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    toks = set(re.findall(r'[a-z0-9_]{3,}', text.lower()))
    stop = {'with', 'from', 'that', 'this', 'have', 'into', 'only', 'when', 'then', 'long', 'short', 'risk', 'rule', 'rules', 'data', 'signal', 'signals'}
    return {t for t in toks if t not in stop}


def _thesis_keywords(thesis: dict) -> set[str]:
    chunks: list[str] = []
    for k in ('id', 'strategy_family', 'template', 'thesis', 'thesis_text', 'summary'):
        v = thesis.get(k)
        if isinstance(v, str):
            chunks.append(v)
    for k in ('constraints', 'required_data', 'thesis_bullets', 'tags'):
        arr = thesis.get(k) or []
        if isinstance(arr, list):
            chunks.extend(str(x) for x in arr if x)
    for s in thesis.get('candidate_signals', []) or []:
        if isinstance(s, dict):
            chunks.extend(str(s.get(k, '')) for k in ('name', 'description', 'signal', 'indicator'))
        elif s:
            chunks.append(str(s))
    return _tokenize(' '.join(chunks))


def _load_library_candidates(limit: int = 10) -> list[dict]:
    idx = ROOT / 'artifacts' / 'library' / 'INDICATOR_INDEX.json'
    if not idx.exists():
        return []
    try:
        rows = json.loads(idx.read_text(encoding='utf-8'))
    except Exception:
        return []
    if not isinstance(rows, list):
        return []
    return [r for r in rows[: max(10, limit * 5)] if isinstance(r, dict)]


def _pick_library_augmented_variant(thesis: dict, variants: list[dict], max_candidates: int = 10) -> dict | None:
    if not variants:
        return None
    lib_rows = _load_library_candidates(limit=max_candidates)
    if not lib_rows:
        return None

    kw = _thesis_keywords(thesis)
    if not kw:
        return None

    scored: list[tuple[int, dict, list[str]]] = []
    for row in lib_rows:
        text_parts = [
            str(row.get('name') or ''),
            str(row.get('tv_key') or ''),
            str(row.get('author') or ''),
            str(row.get('script_id') or ''),
            ' '.join(str(x) for x in (row.get('tags') or []) if x),
            ' '.join(str(x) for x in (row.get('keywords') or []) if x),
        ]
        toks = _tokenize(' '.join(text_parts))
        overlap = sorted(list(kw.intersection(toks)))
        if overlap:
            scored.append((len(overlap), row, overlap))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], str(x[1].get('name') or '').lower()))
    top = scored[:max_candidates]
    refs = unique([
        str(item[1].get('indicator_record_path') or item[1].get('script_id') or item[1].get('tv_key') or item[1].get('name') or '')
        for item in top
    ], max_candidates)
    if not refs:
        return None

    base = copy.deepcopy(variants[0])
    base['name'] = 'library_augmented'
    base['description'] = 'Library-augmented variant selected by thesis↔indicator keyword overlap.'
    base['origin'] = 'LIBRARY_AUGMENTED'
    base['indicator_refs'] = refs
    base['filters'] = unique((base.get('filters') or []) + ['Library augmented: indicator candidates attached from INDICATOR_INDEX keyword overlap.'], 10)
    return base


def main() -> int:
    _set_reasoning_effort_for_strategist()

    ap = argparse.ArgumentParser()
    ap.add_argument('--thesis-path', required=True)
    ap.add_argument('--output-root', default='artifacts/strategy_specs')
    ap.add_argument('--generation-origin', default='')
    ap.add_argument('--trigger-outcome-note', default='')
    ap.add_argument('--trigger-backfill-spec', default='')
    args = ap.parse_args()

    thesis = jload(args.thesis_path)
    candidate_signals = thesis.get('candidate_signals', []) if isinstance(thesis, dict) else []

    if candidate_signals:
        baseline = build_baseline(thesis)
        variants = [
            baseline,
            variant_perturbation(baseline),
            variant_remove_component(baseline),
            variant_threshold_mutation(baseline),
        ][:5]
    else:
        if not _indicator_evaluable(thesis):
            print(json.dumps({
                'status': 'BLOCKED',
                'reason_code': 'INDICATOR_NOT_EVALUABLE',
                'suggestion': 'Indicator cannot be evaluated from available thesis/card data.',
                'variants': 0,
                'strategy_spec_path': '',
            }))
            return 0
        variants = _fallback_templates(thesis)

    strategy_family = str(thesis.get('strategy_family') or thesis.get('id') or '')
    template = str(thesis.get('template') or '')
    directives = _collect_v2_directives(limit_notes=5, strategy_family=strategy_family, template=template)
    if directives:
        variants = _directive_variants(variants[0], directives)

    variants = _apply_outcome_guidance(variants, limit=5)

    lib_aug = _pick_library_augmented_variant(thesis, variants, max_candidates=10)
    if lib_aug is not None and len(variants) < 5:
        variants = variants + [lib_aug]

    if len(variants) == 0:
        print(json.dumps({
            'status': 'BLOCKED',
            'reason_code': 'NO_VARIANTS_COMPILED',
            'suggestion': 'Indicator not mapped to executable signals yet; needs rule extraction or builtin mapping.',
            'variants': 0,
            'strategy_spec_path': '',
        }))
        return 0

    sid = f"strategy-spec-{datetime.now().strftime('%Y%m%d')}-{thesis.get('id','thesis')[-12:]}"
    spec = {
        'schema_version': '1.1',
        'id': sid,
        'created_at': now_iso(),
        'source_thesis_path': args.thesis_path.replace('\\', '/'),
        'variants': variants,
    }

    generation_origin = str(args.generation_origin or '').strip()
    if generation_origin:
        spec['generation_origin'] = generation_origin
    trigger_outcome_note = str(args.trigger_outcome_note or '').strip()
    if trigger_outcome_note:
        spec['trigger_outcome_note'] = trigger_outcome_note.replace('\\', '/')
    trigger_backfill_spec = str(args.trigger_backfill_spec or '').strip()
    if trigger_backfill_spec:
        spec['trigger_backfill_spec'] = trigger_backfill_spec.replace('\\', '/')

    payload = json.dumps(spec, ensure_ascii=False, indent=2)
    if len(payload.encode('utf-8')) > MAX_JSON_BYTES:
        raise SystemExit('StrategySpec JSON exceeds 60KB')

    out_dir = Path(args.output_root) / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sid}.strategy_spec.json"
    out_path.write_text(payload, encoding='utf-8')

    update_index(Path(args.output_root) / 'INDEX.json', str(out_path).replace('\\', '/'))
    print(json.dumps({'status':'OK','reason_code':None,'strategy_spec_path': str(out_path).replace('\\', '/'), 'variants': len(variants), 'baseline_entry_long': variants[0]['entry_long'][:1]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
