#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

MAX_JSON_BYTES = 60 * 1024
MAX_INDEX = 200
ROOT = Path(__file__).resolve().parents[2]

# Indicator Role Framework (from DaviddTech methodology)
# Every strategy should use: 1 Baseline + 1-2 Confirmation + 1 Vol/Gate
# Baseline: trend direction (which way is the market going?)
# Confirmation: entry/exit timing (when to get in/out?)
# Volume/Volatility: filter/gate (should we trade at all right now?)
EXECUTABLE_INDICATORS = {
    'EMA': 'ema', 'SMA': 'sma', 'T3': 't3', 'KAMA': 'kama', 'ALMA': 'alma',
    'RSI': 'rsi', 'ATR': 'atr', 'MACD': 'macd', 'Bollinger Bands': 'bbands',
    'Stochastic': 'stoch', 'ADX': 'adx', 'CCI': 'cci', 'Williams %R': 'willr',
    'OBV': 'obv', 'VWAP': 'vwap', 'Ichimoku': 'ichimoku', 'Supertrend': 'supertrend',
    'Donchian Channels': 'donchian', 'QQE': 'qqe', 'Choppiness Index': 'chop',
    'Vortex': 'vortex', 'STC': 'stc', 'Stiffness': 'stiffness'
}

INDICATOR_ROLES = {
    'baseline': ['ema', 'sma', 't3', 'kama', 'alma', 'hull_ma', 'supertrend', 'ichimoku'],
    'confirmation': ['rsi', 'macd', 'stochastic', 'cci', 'williams_r', 'qqe', 'vortex', 'stc', 'choppiness_index'],
    'volume_volatility': ['obv', 'vwap', 'atr', 'bollinger', 'donchian', 'adx', 'stiffness'],
}

TEMPLATE_COMBOS = {
    'ema_crossover': {'baseline': 'EMA', 'confirmation': 'EMA', 'volume_volatility': 'ATR'},
    'rsi_pullback': {'baseline': 'EMA', 'confirmation': 'RSI', 'volume_volatility': 'ATR'},
    'macd_confirmation': {'baseline': 'EMA', 'confirmation': 'MACD', 'volume_volatility': 'ATR'},
    'supertrend_follow': {'baseline': 'Supertrend', 'confirmation': 'ADX', 'volume_volatility': 'ATR'},
    'bollinger_breakout': {'baseline': 'Bollinger Bands', 'confirmation': 'RSI', 'volume_volatility': 'ATR'},
    'stochastic_reversal': {'baseline': 'EMA', 'confirmation': 'Stochastic', 'volume_volatility': 'ATR'},
    'ema_rsi_atr': {'baseline': 'EMA', 'confirmation': 'RSI', 'volume_volatility': 'ATR'},
}


def _read_advisory_directives() -> dict:
    """Read Claude's strategy advisory for pipeline guidance.

    Supports both legacy keyword extraction and structured `Machine Directives` JSON blocks.
    """
    advisory_path = ROOT / "docs" / "claude-reports" / "STRATEGY_ADVISORY.md"
    if not advisory_path.exists():
        return {}
    try:
        text = advisory_path.read_text(encoding="utf-8")
        result: dict = {
            "advisory_read": True,
            "avoid_templates": [],
            "prefer_templates": [],
            "blacklist_variants": [],
            "blacklist_directive_types": [],
            "exclude_assets": [],
            "rr_floor_min": None,
            "stop_floor_min": None,
            "disable_refinement": False,
            "prioritize_claude_specs": False,
            "machine_directives": [],
        }

        # Structured parser: ## Machine Directives ```json [...] ```
        md_match = re.search(r"##\s*Machine\s+Directives.*?```json\s*(\[.*?\])\s*```", text, flags=re.IGNORECASE | re.DOTALL)
        if md_match:
            try:
                md = json.loads(md_match.group(1))
                if isinstance(md, list):
                    result["machine_directives"] = md
            except Exception:
                pass

        for item in result.get("machine_directives", []):
            if not isinstance(item, dict):
                continue
            action = str(item.get("action") or "").strip().upper()
            target = str(item.get("target") or "").strip()

            if action == "BLACKLIST_TEMPLATE" and target in TEMPLATE_COMBOS:
                result["avoid_templates"].append(target)
            elif action == "PREFER_TEMPLATE" and target in TEMPLATE_COMBOS:
                # Keep insertion order; final sort by priority handled below.
                result["prefer_templates"].append((target, int(item.get("priority") or 9999)))
            elif action == "BLACKLIST_VARIANT" and target:
                result["blacklist_variants"].append(target)
            elif action == "BLACKLIST_DIRECTIVE" and target:
                result["blacklist_directive_types"].append(target.upper())
            elif action == "EXCLUDE_ASSET" and target:
                result["exclude_assets"].append(target.upper())
            elif action == "RR_FLOOR":
                try:
                    result["rr_floor_min"] = float(item.get("minimum"))
                except Exception:
                    pass
            elif action == "STOP_FLOOR":
                try:
                    result["stop_floor_min"] = float(item.get("minimum"))
                except Exception:
                    pass
            elif action == "DISABLE_REFINEMENT":
                result["disable_refinement"] = True
            elif action == "PRIORITIZE_CLAUDE_SPECS":
                result["prioritize_claude_specs"] = True

        # Legacy keyword fallback (kept for compatibility)
        if not result["avoid_templates"] and ("BLACKLIST" in text.upper() or "STOP ITERATING" in text.upper() or "FAILING PATTERN" in text.upper()):
            failing = []
            in_failing = False
            for line in text.split("\n"):
                if "failing pattern" in line.lower() or "stop iterating" in line.lower():
                    in_failing = True
                    continue
                if in_failing and line.startswith("#"):
                    in_failing = False
                if in_failing and any(t in line.lower() for t in TEMPLATE_COMBOS):
                    for t in TEMPLATE_COMBOS:
                        if t in line.lower():
                            failing.append(t)
            result["avoid_templates"] = list(set(failing))

        if not result.get("prefer_templates") and ("PROMISING" in text.upper() or "EXPLORE" in text.upper()):
            promising = []
            in_promising = False
            for line in text.split("\n"):
                if "promising" in line.lower() or "explore" in line.lower():
                    in_promising = True
                    continue
                if in_promising and line.startswith("#"):
                    in_promising = False
                if in_promising and any(t in line.lower() for t in TEMPLATE_COMBOS):
                    for t in TEMPLATE_COMBOS:
                        if t in line.lower():
                            promising.append(t)
            result["prefer_templates"] = list(set(promising))

        # Normalize + dedup
        if result.get("prefer_templates") and isinstance(result["prefer_templates"], list) and result["prefer_templates"] and isinstance(result["prefer_templates"][0], tuple):
            pref = sorted(result["prefer_templates"], key=lambda x: x[1])
            result["prefer_templates"] = [p[0] for p in pref]
        result["avoid_templates"] = list(dict.fromkeys([str(x) for x in result.get("avoid_templates", []) if x]))
        result["prefer_templates"] = list(dict.fromkeys([str(x) for x in result.get("prefer_templates", []) if x]))
        result["blacklist_variants"] = list(dict.fromkeys([str(x) for x in result.get("blacklist_variants", []) if x]))
        result["blacklist_directive_types"] = list(dict.fromkeys([str(x).upper() for x in result.get("blacklist_directive_types", []) if x]))
        result["exclude_assets"] = list(dict.fromkeys([str(x).upper() for x in result.get("exclude_assets", []) if x]))
        return result
    except Exception:
        return {}


def _deduplicate_variants(variants: list[dict]) -> list[dict]:
    """Remove variants that produce identical signal logic."""
    if not variants:
        return variants
    seen_sigs = []
    unique_variants = []
    for v in variants:
        # Build a signature from the actual signal rules
        sig_parts = []
        for key in ('entry_long', 'entry_short', 'filters', 'exit_rules', 'risk_rules'):
            rules = v.get(key, [])
            sig_parts.append(json.dumps(sorted(str(r) for r in rules) if isinstance(rules, list) else [str(rules)]))
        sig = '|'.join(sig_parts)
        if sig not in seen_sigs:
            seen_sigs.append(sig)
            unique_variants.append(v)
        else:
            print(f"DEDUP_VARIANT_REMOVED name={v.get('name', '?')} (identical signal logic)", file=sys.stderr)
    return unique_variants


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
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def update_index(index_path: Path, pointer: str) -> None:
    items = []
    if index_path.exists():
        try:
            items = json.loads(index_path.read_text(encoding='utf-8-sig'))
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


def _canonical_indicator_token(s: str) -> str:
    t = str(s or '').lower().replace('%', '').replace('&', 'and')
    t = re.sub(r'[^a-z0-9]+', '_', t).strip('_')
    aliases = {
        'williams_r': 'williams_r', 'williams': 'williams_r', 'bollinger_bands': 'bollinger',
        'donchian_channels': 'donchian', 'choppiness_index': 'choppiness_index',
    }
    return aliases.get(t, t)


def _extract_indicator_tokens_from_variant(v: dict) -> set[str]:
    text_parts = []
    for k in ('name', 'description'):
        text_parts.append(str(v.get(k) or ''))
    for k in ('entry_long', 'entry_short', 'filters', 'exit_rules', 'risk_rules'):
        text_parts.extend(str(x) for x in (v.get(k) or []))
    blob = ' '.join(text_parts).lower()
    known = [_canonical_indicator_token(x) for x in EXECUTABLE_INDICATORS.keys()]
    out = {k for k in known if k and (k in blob or k.replace('_', ' ') in blob)}
    return out


def validate_indicator_roles(spec: dict) -> tuple[bool, str]:
    variants = spec.get('variants') or []
    if not variants:
        return False, 'NO_VARIANTS'
    for v in variants:
        toks = _extract_indicator_tokens_from_variant(v)
        counts = {r: sum(1 for t in toks if t in set(INDICATOR_ROLES[r])) for r in INDICATOR_ROLES}
        if counts['baseline'] != 1:
            return False, f"ROLE_BASELINE_INVALID:{counts['baseline']}"
        if counts['confirmation'] < 1 or counts['confirmation'] > 2:
            return False, f"ROLE_CONFIRMATION_INVALID:{counts['confirmation']}"
        if counts['volume_volatility'] != 1:
            return False, f"ROLE_VOL_INVALID:{counts['volume_volatility']}"
        if any(c >= 3 for c in counts.values()):
            return False, 'ROLE_OVERWEIGHT'
    return True, 'OK'


def _fix_variant_roles(v: dict) -> dict:
    nv = copy.deepcopy(v)
    role_defaults = {
        'baseline': 'EMA', 'confirmation': 'RSI', 'volume_volatility': 'ATR'
    }
    # Strip ALL existing RoleFramework filters first, then add correct ones
    nv['filters'] = [f for f in (nv.get('filters') or []) if 'RoleFramework' not in str(f)]
    for role, ind in role_defaults.items():
        nv['filters'].append(f"RoleFramework[{role}]={ind}")
    return nv


def _ensure_role_compliant_variants(variants: list[dict]) -> tuple[list[dict], bool]:
    fixed = False
    out = []
    for v in variants:
        tmp_spec = {'variants': [v]}
        ok, _ = validate_indicator_roles(tmp_spec)
        if ok:
            out.append(v)
            continue
        nv = _fix_variant_roles(v)
        out.append(nv)
        fixed = True
    return out, fixed


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
        'Backtester executable indicators: EMA, SMA, RSI, ATR, MACD, Bollinger Bands, Stochastic, ADX, CCI, Williams %R, OBV, VWAP, Ichimoku, Supertrend, Donchian Channels.',
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

    # Accept research-card style evidence as evaluable input.
    if thesis.get('indicators_mentioned'):
        return True
    if thesis.get('strategy_components'):
        return True
    rules = thesis.get('extracted_rules') or []
    if isinstance(rules, list):
        actionable = [str(r).strip() for r in rules if str(r).strip() and str(r).strip().lower() != 'not specified in content.']
        if actionable:
            return True

    # Soft signal: mention of indicator usage in hypotheses/bullets/rules/components.
    text_pool = []
    text_pool.extend(thesis.get('thesis_bullets', []) or [])
    text_pool.extend(thesis.get('indicators_mentioned', []) or [])
    text_pool.extend(rules)
    for c in thesis.get('strategy_components', []) or []:
        if isinstance(c, dict):
            text_pool.extend([c.get('type', ''), c.get('description', '')])
    for h in thesis.get('hypotheses', []) or []:
        if isinstance(h, dict):
            text_pool.extend([h.get('statement', ''), h.get('rationale', '')])
    blob = ' '.join(str(x).lower() for x in text_pool if x)
    return any(k in blob for k in ['indicator', 'signal', 'trend', 'regime', 'confirmation', 'ohlcv', 'entry', 'exit', 'rsi', 'macd', 'ema', 'atr'])


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
        'Backtester executable indicators: EMA, SMA, RSI, ATR, MACD, Bollinger Bands, Stochastic, ADX, CCI, Williams %R, OBV, VWAP, Ichimoku, Supertrend, Donchian Channels.',
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
            obj = json.loads(p.read_text(encoding='utf-8-sig'))
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
            obj = json.loads(p.read_text(encoding='utf-8-sig'))
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


def _replace_conf_threshold_in_rules(rules: list[str], old_val: float, new_val: float) -> list[str]:
    out: list[str] = []
    for r in rules or []:
        s = str(r)
        s = re.sub(r'(confidence\s*(?:>=|>|<=|<)\s*)(\d+(?:\.\d+)?)', lambda m: m.group(1) + f"{new_val:.2f}", s, flags=re.IGNORECASE)
        s = re.sub(r'(confidence threshold\s*)(\d+(?:\.\d+)?)', lambda m: m.group(1) + f"{new_val:.2f}", s, flags=re.IGNORECASE)
        out.append(s)
    return out


def _get_param(v: dict, name: str) -> dict | None:
    for p in (v.get('parameters') or []):
        if isinstance(p, dict) and str(p.get('name')) == name:
            return p
    return None


def _set_param(v: dict, name: str, value: float, pmin: float | None = None, pmax: float | None = None, step: float | None = None) -> None:
    p = _get_param(v, name)
    if p is None:
        p = {'name': name, 'default': float(value)}
        if pmin is not None:
            p['min'] = float(pmin)
        if pmax is not None:
            p['max'] = float(pmax)
        if step is not None:
            p['step'] = float(step)
        v.setdefault('parameters', []).append(p)
    else:
        p['default'] = float(value)


def _apply_directive(base: dict, directive: dict, idx: int, magnitude: float = 1.0) -> dict:
    v = copy.deepcopy(base)
    d_type = str(directive.get('type') or '')
    params = directive.get('params') or {}
    v['name'] = f"directive_variant_{idx}_{d_type.lower()}"
    v['description'] = f"Directive-driven variant from {d_type}."
    v['origin'] = 'DIRECTIVE'
    v['directive_refs'] = [str(directive.get('id'))]

    if d_type in {'THRESHOLD_SWEEP', 'PARAM_SWEEP', 'ENTRY_TIGHTEN'}:
        cp = _get_param(v, 'confidence_threshold')
        old_default = float(cp.get('default', 0.6)) if cp else 0.6
        base_delta = float(params.get('confidence_threshold_delta', 0.05))
        delta = abs(base_delta) * float(magnitude)
        new_default = old_default + delta
        if cp:
            cmin = float(cp.get('min', 0.45))
            cmax = float(cp.get('max', 0.95))
        else:
            cmin, cmax = 0.45, 0.95
        new_default = max(cmin, min(cmax, round(new_default, 2)))
        _set_param(v, 'confidence_threshold', new_default, pmin=cmin, pmax=cmax, step=0.01)
        v['entry_long'] = _replace_conf_threshold_in_rules(v.get('entry_long') or [], old_default, new_default)
        v['entry_short'] = _replace_conf_threshold_in_rules(v.get('entry_short') or [], old_default, new_default)

        mv = _get_param(v, 'min_volume')
        if mv is not None:
            _set_param(v, 'min_volume', round(float(mv.get('default', 0)) * (1.0 + 0.1 * magnitude), 4), pmin=float(mv.get('min', 0.0)), pmax=float(mv.get('max', 1e12)), step=float(mv.get('step', 1.0)))
        ma = _get_param(v, 'min_atr')
        if ma is not None:
            _set_param(v, 'min_atr', round(float(ma.get('default', 0)) * (1.0 + 0.1 * magnitude), 6), pmin=float(ma.get('min', 0.0)), pmax=float(ma.get('max', 1e9)), step=float(ma.get('step', 0.0001)))

    elif d_type == 'ENTRY_RELAX':
        cp = _get_param(v, 'confidence_threshold')
        old_default = float(cp.get('default', 0.6)) if cp else 0.6
        delta = abs(float(params.get('confidence_threshold_delta', 0.05))) * float(magnitude)
        new_default = old_default - delta
        if cp:
            cmin = float(cp.get('min', 0.45))
            cmax = float(cp.get('max', 0.95))
        else:
            cmin, cmax = 0.45, 0.95
        new_default = max(cmin, min(cmax, round(new_default, 2)))
        _set_param(v, 'confidence_threshold', new_default, pmin=cmin, pmax=cmax, step=0.01)
        v['entry_long'] = _replace_conf_threshold_in_rules(v.get('entry_long') or [], old_default, new_default)
        v['entry_short'] = _replace_conf_threshold_in_rules(v.get('entry_short') or [], old_default, new_default)

    elif d_type == 'EXIT_CHANGE':
        stop = float(params.get('stop_atr_mult', v.get('risk_policy', {}).get('stop_atr_mult', 1.5)))
        tp = float(params.get('tp_atr_mult', v.get('risk_policy', {}).get('tp_atr_mult', 2.0)))
        stop *= float(magnitude)
        tp *= float(magnitude)
        rp = copy.deepcopy(v.get('risk_policy') or {})
        rp['stop_type'] = rp.get('stop_type', 'atr')
        rp['tp_type'] = rp.get('tp_type', 'atr')
        rp['stop_atr_mult'] = round(stop, 4)
        rp['tp_atr_mult'] = round(tp, 4)
        v['risk_policy'] = rp
        _set_param(v, 'stop_atr_mult', round(stop, 4), pmin=0.1, pmax=20.0, step=0.1)
        _set_param(v, 'tp_atr_mult', round(tp, 4), pmin=0.1, pmax=40.0, step=0.1)

    elif d_type == 'GATE_ADJUST':
        rp = copy.deepcopy(v.get('risk_policy') or {})
        for k, val in params.items():
            if isinstance(val, (int, float, bool)):
                rp[str(k)] = val
        v['risk_policy'] = rp

    elif d_type == 'ROLE_SWAP':
        entries = list(v.get('entry_long') or [])
        filts = list(v.get('filters') or [])
        if entries and filts:
            e0 = entries.pop(0)
            f0 = filts.pop(0)
            entries.insert(0, str(f0))
            filts.insert(0, str(e0))
            v['entry_long'] = entries
            v['filters'] = filts

    elif d_type == 'TEMPLATE_SWITCH':
        target = str(params.get('target') or '').strip().lower()
        if target not in TEMPLATE_COMBOS:
            current_filters = [str(f) for f in v.get('filters', []) if 'RoleFramework' in str(f)]
            current_key = next((k for k, combo in TEMPLATE_COMBOS.items() if any(combo['confirmation'] in f for f in current_filters)), 'ema_rsi_atr')
            candidates = [k for k in TEMPLATE_COMBOS if k != current_key]
            target = candidates[hash(v.get('name', '')) % len(candidates)] if candidates else 'macd_confirmation'
        combo = TEMPLATE_COMBOS[target]
        v['filters'] = [f for f in (v.get('filters') or []) if 'RoleFramework' not in str(f)]
        for role, indicator in combo.items():
            v['filters'].append(f'RoleFramework[{role}]={indicator}')
        v['description'] = f"Template switch to {target}: baseline={combo['baseline']}, confirmation={combo['confirmation']}."
        v['components'] = [
            {'indicator': combo['baseline'], 'role': 'trend', 'notes': f'{target} baseline'},
            {'indicator': combo['confirmation'], 'role': 'confirmation', 'notes': f'{target} confirmation'},
            {'indicator': combo['volume_volatility'], 'role': 'regime_gate', 'notes': f'{target} volatility gate'},
        ]

    return v


def _directive_variants(seed: dict, directives: list[dict]) -> list[dict]:
    if not directives:
        return []

    advisory = _read_advisory_directives()
    blacklisted_directive_types = set(advisory.get("blacklist_directive_types", []))
    blacklisted_variants = set(advisory.get("blacklist_variants", []))

    filtered_directives = []
    for d in directives:
        d_type = str((d or {}).get('type') or '').upper()
        if d_type and d_type in blacklisted_directive_types:
            print(f"DIRECTIVE_SKIPPED_BLACKLIST type={d_type}", file=sys.stderr)
            continue
        filtered_directives.append(d)

    if not filtered_directives:
        return []

    chosen = filtered_directives[:3]
    out: list[dict] = []
    for i, d in enumerate(chosen[:2], start=1):
        out.append(_apply_directive(seed, d, i, magnitude=1.0))

    if 'directive_exploration' not in blacklisted_variants:
        explore = copy.deepcopy(seed)
        explore['name'] = 'directive_exploration'
        explore['description'] = 'Exploration variant generated from directive context.'
        explore['origin'] = 'EXPLORATION'
        explore['directive_refs'] = [str(d.get('id')) for d in chosen]
        for j, d in enumerate(chosen[:2], start=1):
            explore = _apply_directive(explore, d, j, magnitude=0.5)
        explore['name'] = 'directive_exploration'
        explore['description'] = 'Exploration variant generated from directive context.'
        explore['origin'] = 'EXPLORATION'
        explore['directive_refs'] = [str(d.get('id')) for d in chosen]
        out.append(explore)
    else:
        print("VARIANT_SKIPPED_BLACKLIST name=directive_exploration", file=sys.stderr)

    # Template diversity: always include one variant with a different signal template
    import hashlib as _div_hl
    diversity = copy.deepcopy(seed)
    family_hash = _div_hl.sha256(str(seed.get('name', '')).encode()).hexdigest()
    all_templates = list(TEMPLATE_COMBOS.keys())
    # Read advisory to avoid failing templates
    avoid = set(advisory.get("avoid_templates", []))
    prefer = list(advisory.get("prefer_templates", []))

    # Remove current template and avoided templates from candidates
    current_filters = [str(f) for f in seed.get('filters', []) if 'RoleFramework' in str(f)]
    current_key = next((k for k, combo in TEMPLATE_COMBOS.items() if any(combo['confirmation'] in f for f in current_filters)), '')
    candidates = [t for t in all_templates if t != current_key and t not in avoid]
    if not candidates:
        candidates = [t for t in all_templates if t != current_key]

    # Prefer advisory-recommended templates, otherwise rotate by cycle count
    if prefer:
        preferred_available = [t for t in prefer if t in candidates]
        if preferred_available:
            # Rotate through preferred templates using timestamp to avoid repetition
            cycle_idx = int(datetime.now().strftime('%H')) // 2
            pick = preferred_available[cycle_idx % len(preferred_available)]
        else:
            cycle_idx = int(datetime.now().strftime('%H%M'))
            pick = candidates[cycle_idx % len(candidates)]
    else:
        cycle_idx = int(datetime.now().strftime('%H%M'))
        pick = candidates[cycle_idx % len(candidates)]

    diversity['filters'] = [f for f in (diversity.get('filters') or []) if 'RoleFramework' not in str(f)]
    diversity_directive = {'id': 'd_diversity', 'type': 'TEMPLATE_SWITCH', 'params': {'target': pick}}
    diversity = _apply_directive(diversity, diversity_directive, len(out) + 1, magnitude=1.0)
    diversity['name'] = 'template_diversity'
    diversity['description'] = f"Forced template diversity: {pick}"
    diversity['origin'] = 'DIVERSITY'
    out.append(diversity)

    if blacklisted_variants:
        kept = []
        for v in out:
            vn = str(v.get('name') or '')
            if vn and vn in blacklisted_variants:
                print(f"VARIANT_SKIPPED_BLACKLIST name={vn}", file=sys.stderr)
                continue
            kept.append(v)
        out = kept

    return out[:4]


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


def _spec_keywords(spec: dict) -> set[str]:
    chunks: list[str] = []
    for k in ('id', 'source_thesis_path', 'generation_origin'):
        v = spec.get(k)
        if isinstance(v, str):
            chunks.append(v)
    for v in spec.get('variants', []) or []:
        if not isinstance(v, dict):
            continue
        for k in ('name', 'description'):
            vv = v.get(k)
            if isinstance(vv, str):
                chunks.append(vv)
        for k in ('entry_long', 'entry_short', 'filters', 'exit_rules', 'risk_rules'):
            arr = v.get(k) or []
            if isinstance(arr, list):
                chunks.extend(str(x) for x in arr if x)
    return _tokenize(' '.join(chunks))


def _load_library_candidates(limit: int = 10) -> list[dict]:
    idx = ROOT / 'artifacts' / 'library' / 'INDICATOR_INDEX.json'
    if not idx.exists():
        return []
    try:
        rows = json.loads(idx.read_text(encoding='utf-8-sig'))
    except Exception:
        return []
    if not isinstance(rows, list):
        return []
    return [r for r in rows[: max(10, limit * 5)] if isinstance(r, dict)]


def _pick_library_augmented_variant_for_keywords(keywords: set[str], variants: list[dict], max_candidates: int = 10) -> dict | None:
    if not variants:
        return None
    lib_rows = _load_library_candidates(limit=max_candidates)
    if not lib_rows:
        return None

    if not keywords:
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
        overlap = sorted(list(keywords.intersection(toks)))
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
    base['description'] = 'Library-augmented variant selected by keyword overlap.'
    base['origin'] = 'LIBRARY_AUGMENTED'
    base['indicator_refs'] = refs
    base['filters'] = unique((base.get('filters') or []) + ['Library augmented: indicator candidates attached from INDICATOR_INDEX keyword overlap.'], 10)
    return base


def _pick_library_augmented_variant(thesis: dict, variants: list[dict], max_candidates: int = 10) -> dict | None:
    return _pick_library_augmented_variant_for_keywords(_thesis_keywords(thesis), variants, max_candidates=max_candidates)


def _directives_from_outcome_notes(path: str) -> list[dict]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    try:
        obj = json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception:
        return []
    out: list[dict] = []
    for d in (obj.get('directives') or [])[:5]:
        if isinstance(d, dict) and d.get('id') and d.get('type'):
            out.append(d)
    return out


def _latest_llm_outcome_note(max_age_hours: int = 24) -> tuple[str, dict]:
    out_root = ROOT / 'artifacts' / 'outcomes'
    files = sorted(out_root.glob('**/outcome_notes_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(max_age_hours)))
    for p in files:
        try:
            mtime_utc = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime_utc < cutoff:
                continue
            obj = json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception:
            continue
        if str(obj.get('schema_version') or '') != '2.0':
            continue
        if str(obj.get('analysis_source') or '').lower() != 'llm':
            continue
        return str(p).replace('\\', '/'), obj
    return '', {}


def main() -> int:
    _set_reasoning_effort_for_strategist()

    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['thesis', 'directive-only'], default='thesis')
    ap.add_argument('--thesis-path', default='')
    ap.add_argument('--source-spec', default='')
    ap.add_argument('--outcome-notes', default='')
    ap.add_argument('--output-root', default='artifacts/strategy_specs')
    ap.add_argument('--generation-origin', default='')
    ap.add_argument('--trigger-outcome-note', default='')
    ap.add_argument('--trigger-backfill-spec', default='')
    args = ap.parse_args()

    thesis: dict = {}
    source_spec: dict = {}
    variants: list[dict] = []
    source_thesis_path = ''
    consumed_outcome_path = ''
    consumed_outcome_verdict = ''
    consumed_directives: list[dict] = []
    try:
        max_outcome_note_age_hours = int(os.getenv('STRATEGIST_MAX_OUTCOME_NOTE_AGE_HOURS', '24'))
    except Exception:
        max_outcome_note_age_hours = 24

    if args.mode == 'directive-only':
        if not args.source_spec or not args.outcome_notes:
            print(json.dumps({'status': 'BLOCKED', 'reason_code': 'DIRECTIVE_ONLY_INPUT_MISSING', 'variants': 0, 'strategy_spec_path': ''}))
            return 0
        source_spec = jload(args.source_spec)
        source_variants = [v for v in (source_spec.get('variants') or []) if isinstance(v, dict)]
        if not source_variants:
            print(json.dumps({'status': 'BLOCKED', 'reason_code': 'SOURCE_SPEC_NO_VARIANTS', 'variants': 0, 'strategy_spec_path': ''}))
            return 0
        directives = _directives_from_outcome_notes(args.outcome_notes)
        consumed_outcome_path = args.outcome_notes.replace('\\', '/')
        try:
            consumed_outcome_verdict = str(jload(args.outcome_notes).get('verdict') or '').upper()
        except Exception:
            consumed_outcome_verdict = ''
        consumed_directives = directives[:5]
        if directives:
            variants = _directive_variants(source_variants[0], directives)
        else:
            variants = [copy.deepcopy(source_variants[0])]
            variants[0]['name'] = 'directive_fallback_retest'
            variants[0]['description'] = 'Fallback retest variant when directives are unavailable.'
        variants = _apply_outcome_guidance(variants, limit=5)
        kw = _spec_keywords(source_spec)
        lib_aug = _pick_library_augmented_variant_for_keywords(kw, variants, max_candidates=10)
        if lib_aug is not None and len(variants) < 5:
            variants = variants + [lib_aug]
    else:
        if not args.thesis_path:
            print(json.dumps({'status': 'BLOCKED', 'reason_code': 'THESIS_PATH_REQUIRED', 'variants': 0, 'strategy_spec_path': ''}))
            return 0
        thesis = jload(args.thesis_path)
        source_thesis_path = args.thesis_path.replace('\\', '/')
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

        llm_path, llm_note = _latest_llm_outcome_note(max_age_hours=max_outcome_note_age_hours)
        llm_verdict = str(llm_note.get('verdict') or '').upper()
        llm_directives = [d for d in (llm_note.get('directives') or []) if isinstance(d, dict) and d.get('id') and d.get('type')]

        if llm_path:
            consumed_outcome_path = llm_path
            consumed_outcome_verdict = llm_verdict
            consumed_directives = llm_directives[:5]
            consumed_tags = ','.join([str(d.get('type')) for d in consumed_directives])
            print(f"STRATEGIST_DIRECTIVES_CONSUMED source={llm_path} verdict={llm_verdict} directives={consumed_tags}", file=sys.stderr)

        if llm_verdict == 'ACCEPT':
            print(json.dumps({
                'status': 'PROMOTE',
                'reason_code': 'ACCEPT_PROMOTE_NO_REGEN',
                'strategy_spec_path': '',
                'variants': 0,
                'mode': args.mode,
                'consumed_outcome_notes_path': consumed_outcome_path,
                'consumed_outcome_verdict': consumed_outcome_verdict,
            }))
            return 0

        if llm_verdict in {'REVISE', 'REJECT'} and llm_directives:
            variants = _directive_variants(variants[0], llm_directives)
        else:
            directives = _collect_v2_directives(limit_notes=5, strategy_family=strategy_family, template=template)
            if directives:
                variants = _directive_variants(variants[0], directives)
                consumed_directives = directives[:5]

        variants = _apply_outcome_guidance(variants, limit=5)

        lib_aug = _pick_library_augmented_variant(thesis, variants, max_candidates=10)
        if lib_aug is not None and len(variants) < 5:
            variants = variants + [lib_aug]

    if len(variants) == 0 and args.mode == 'thesis':
        # Fail-open fallback: if directive path produced no variants, regenerate baseline/template variants.
        fallback_variants: list[dict] = []
        candidate_signals = thesis.get('candidate_signals', []) if isinstance(thesis, dict) else []
        if candidate_signals:
            baseline = build_baseline(thesis)
            fallback_variants = [
                baseline,
                variant_perturbation(baseline),
                variant_remove_component(baseline),
                variant_threshold_mutation(baseline),
            ][:5]
        elif _indicator_evaluable(thesis):
            fallback_variants = _fallback_templates(thesis)

        if fallback_variants:
            variants = _apply_outcome_guidance(fallback_variants, limit=5)

    if len(variants) == 0:
        print(json.dumps({
            'status': 'BLOCKED',
            'reason_code': 'NO_VARIANTS_COMPILED',
            'suggestion': 'Indicator not mapped to executable signals yet; needs rule extraction or builtin mapping.',
            'variants': 0,
            'strategy_spec_path': '',
        }))
        return 0

    id_suffix = (source_spec.get('id', 'spec') if args.mode == 'directive-only' else thesis.get('id', 'thesis'))[-12:]
    sid = f"strategy-spec-{datetime.now().strftime('%Y%m%d')}-{id_suffix}"
    if args.mode == 'directive-only':
        sid = f"{sid}-{uuid.uuid4().hex[:8]}"
    # --- Advisory integration + deduplication ---
    advisory = _read_advisory_directives()
    if advisory.get("advisory_read"):
        spec_meta_advisory = {
            "avoid_templates": advisory.get("avoid_templates", []),
            "prefer_templates": advisory.get("prefer_templates", []),
            "coverage_option": "Optional (non-blocking): expand qualified strategies to multi-asset and/or multi-timeframe test matrix when confidence is high.",
        }
        print(f"ADVISORY_READ avoid={advisory.get('avoid_templates', [])} prefer={advisory.get('prefer_templates', [])}", file=sys.stderr)
    else:
        spec_meta_advisory = {
            "coverage_option": "Optional (non-blocking): expand qualified strategies to multi-asset and/or multi-timeframe test matrix when confidence is high.",
        }
    variants = _deduplicate_variants(variants)
    variants, roles_fixed = _ensure_role_compliant_variants(variants)

    # Strategy-variant contract: keep variants focused (1..5 max) so generation stays dominant.
    if len(variants) > 5:
        variants = variants[:5]
    spec = {
        'schema_version': '1.1',
        'id': sid,
        'created_at': now_iso(),
        'source': 'claude-advisor',
        'variants': variants,
        'advisory_context': spec_meta_advisory if spec_meta_advisory else None,
        'backtester_executable_indicators': list(EXECUTABLE_INDICATORS.keys()),
        'backtester_executable_indicator_map': EXECUTABLE_INDICATORS,
        'indicator_roles': INDICATOR_ROLES,
    }
    if args.mode == 'directive-only':
        spec['source_spec_path'] = args.source_spec.replace('\\', '/')
        spec['source_outcome_notes_path'] = args.outcome_notes.replace('\\', '/')
        spec['consumed_outcome_notes_path'] = args.outcome_notes.replace('\\', '/')
    elif source_thesis_path:
        spec['source_thesis_path'] = source_thesis_path

    if consumed_outcome_path:
        spec['consumed_outcome_notes_path'] = consumed_outcome_path
    if consumed_outcome_verdict:
        spec['consumed_outcome_verdict'] = consumed_outcome_verdict
    if consumed_directives:
        spec['consumed_directives'] = [
            {
                'id': str(d.get('id')),
                'type': str(d.get('type')),
                'params': d.get('params', {}),
            }
            for d in consumed_directives
        ]

    generation_origin = str(args.generation_origin or '').strip()
    if generation_origin:
        spec['generation_origin'] = generation_origin
    trigger_outcome_note = str(args.trigger_outcome_note or '').strip()
    if trigger_outcome_note:
        spec['trigger_outcome_note'] = trigger_outcome_note.replace('\\', '/')
    trigger_backfill_spec = str(args.trigger_backfill_spec or '').strip()
    if trigger_backfill_spec:
        spec['trigger_backfill_spec'] = trigger_backfill_spec.replace('\\', '/')

    ok_roles, role_reason = validate_indicator_roles(spec)
    if not ok_roles:
        print(f"WARN role_validation_after_fix={role_reason}", file=sys.stderr)
    if roles_fixed:
        print("WARN role_framework_fix_applied=1", file=sys.stderr)

    payload = json.dumps(spec, ensure_ascii=False, separators=(',', ':'))
    if len(payload.encode('utf-8')) > MAX_JSON_BYTES:
        raise SystemExit('StrategySpec JSON exceeds 60KB')

    out_dir = Path(args.output_root) / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sid}.strategy_spec.json"

    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', dir=str(out_path.parent), delete=False, encoding='utf-8')
    try:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, str(out_path))
    except Exception:
        try:
            tmp.close()
        except Exception:
            pass
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise

    update_index(Path(args.output_root) / 'INDEX.json', str(out_path).replace('\\', '/'))
    print(json.dumps({'status':'OK','reason_code':None,'strategy_spec_path': str(out_path).replace('\\', '/'), 'variants': len(variants), 'mode': args.mode}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
