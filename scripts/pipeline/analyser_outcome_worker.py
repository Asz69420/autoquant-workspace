#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from scripts.lib import llm_client

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
DIRECTIVE_TYPES = {
    'ROLE_SWAP', 'THRESHOLD_SWEEP', 'PARAM_SWEEP', 'ENTRY_TIGHTEN', 'ENTRY_RELAX', 'EXIT_CHANGE', 'GATE_ADJUST', 'TEMPLATE_SWITCH'
}
DOCTRINE_PATH = ROOT / 'docs' / 'DOCTRINE' / 'analyser-doctrine.md'


@dataclass
class DoctrinePrinciples:
    regime_required: bool
    risk_gating: bool
    macd_confirmation_over_entry: bool
    refs: list[dict]


def _j(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return default


def _log(status_word: str, reason: str, summary: str):
    cmd = [
        PY, 'scripts/log_event.py',
        '--run-id', f"analyser-outcome-{int(datetime.now(UTC).timestamp())}",
        '--agent', 'Analyser',
        '--model-id', 'openai-codex/gpt-5.3-codex',
        '--action', 'ANALYSER_OUTCOME_SUMMARY',
        '--status-word', status_word,
        '--status-emoji', ('OK' if status_word == 'OK' else ('WARN' if status_word == 'WARN' else 'FAIL')),
        '--reason-code', reason,
        '--summary', summary,
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def latest_file(pattern: str) -> Path | None:
    files = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _load_doctrine_principles(path: Path = DOCTRINE_PATH) -> DoctrinePrinciples:
    refs: list[dict] = []
    regime_required = False
    risk_gating = False
    macd_confirmation_over_entry = False
    if not path.exists():
        return DoctrinePrinciples(False, False, False, refs)

    for line in path.read_text(encoding='utf-8-sig').splitlines():
        s = line.strip()
        if not s.startswith('- ['):
            continue
        m = re.match(r'^- \[(?P<id>[^\]]+)\]\s+(?P<text>.+)$', s)
        if not m:
            continue
        did = m.group('id')
        text = m.group('text')
        low = text.lower()

        if ('regime assumptions' in low) or ('regime gate' in low) or ('session gating' in low):
            regime_required = True
            refs.append({'id': did, 'theme': 'regime_required', 'text': text[:220]})
        if ('risk gating' in low) or ('risk limit enforcement' in low) or ('drawdown' in low):
            risk_gating = True
            refs.append({'id': did, 'theme': 'risk_gating', 'text': text[:220]})
        if 'macd' in low and 'confirmation' in low and 'entry' in low:
            macd_confirmation_over_entry = True
            refs.append({'id': did, 'theme': 'macd_confirmation_over_entry', 'text': text[:220]})

    dedup = []
    seen = set()
    for r in refs:
        k = (r.get('id'), r.get('theme'))
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    return DoctrinePrinciples(regime_required, risk_gating, macd_confirmation_over_entry, dedup[:10])


def _load_strategy_variant_context(batch: dict, best_run: dict) -> dict:
    strategy_path = str(batch.get('strategy_spec_path') or '')
    variant_name = str(best_run.get('variant_name') or batch.get('variant') or '')
    spec = _j(Path(strategy_path), {}) if strategy_path else {}
    variants = spec.get('variants') if isinstance(spec, dict) else []
    selected = {}
    if isinstance(variants, list):
        for v in variants:
            if isinstance(v, dict) and str(v.get('name') or '') == variant_name:
                selected = v
                break
        if not selected and variants and isinstance(variants[0], dict):
            selected = variants[0]
    return {'strategy_path': strategy_path, 'variant_name': variant_name, 'variant': selected if isinstance(selected, dict) else {}}


def _has_regime_filter(variant: dict) -> bool:
    texts = []
    for k in ('filters', 'entry_long', 'entry_short', 'risk_rules', 'description'):
        v = variant.get(k)
        if isinstance(v, list):
            texts.extend([str(x) for x in v])
        elif isinstance(v, str):
            texts.append(v)
    blob = ' '.join(texts).lower()
    return any(x in blob for x in ('regime', 'session gate', 'risk-on', 'risk-off', 'volatility gate'))


def _macd_used_as_entry(variant: dict) -> bool:
    entry_blob = ' '.join(str(x) for x in (variant.get('entry_long') or []) + (variant.get('entry_short') or [])).lower()
    filt_blob = ' '.join(str(x) for x in (variant.get('filters') or [])).lower()
    return ('macd' in entry_blob) and ('confirmation' not in entry_blob or 'macd' not in filt_blob)


def _apply_doctrine_influence(base_directives: list[dict], doctrine: DoctrinePrinciples, variant_ctx: dict, dd: float) -> tuple[list[dict], list[dict]]:
    directives = list(base_directives)
    refs_used: list[dict] = []
    variant = variant_ctx.get('variant') or {}

    if doctrine.regime_required and not _has_regime_filter(variant):
        directives.insert(0, {
            'id': 'd_doctrine_regime',
            'type': 'GATE_ADJUST',
            'params': {'require_regime_filter': True, 'regime_gate': 'trend_or_volatility'},
            'rationale': 'Doctrine: regime assumptions/gating required; strategy lacks explicit regime filter.',
            'priority': 1,
        })
        refs_used.extend([r for r in doctrine.refs if r.get('theme') == 'regime_required'][:2])

    if doctrine.macd_confirmation_over_entry and _macd_used_as_entry(variant):
        directives.insert(0, {
            'id': 'd_doctrine_macd_role',
            'type': 'ROLE_SWAP',
            'params': {'swap': 'macd_entry->confirmation'},
            'rationale': 'Doctrine: prefer MACD as confirmation over direct entry trigger.',
            'priority': 1,
        })
        refs_used.extend([r for r in doctrine.refs if r.get('theme') == 'macd_confirmation_over_entry'][:2])

    if doctrine.risk_gating and dd > 0.20:
        directives.insert(0, {
            'id': 'd_doctrine_risk_gate',
            'type': 'GATE_ADJUST',
            'params': {'max_drawdown_cap': 0.20, 'risk_gate_required': True},
            'rationale': 'Doctrine: risk gating before complexity on drawdown-heavy strategies.',
            'priority': 1,
        })
        refs_used.extend([r for r in doctrine.refs if r.get('theme') == 'risk_gating'][:2])

    out = []
    seen = set()
    for d in directives:
        key = (str(d.get('type') or ''), json.dumps(d.get('params') or {}, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        out.append(d)

    return out[:5], refs_used[:10]


def _extract_metrics(batch: dict) -> tuple[float, float, int, dict, str, str]:
    runs = batch.get('runs') or []
    summary = batch.get('summary') or {}
    best = runs[0] if runs else {}
    if runs:
        best = sorted(runs, key=lambda r: (float(r.get('profit_factor', 0.0) or 0.0), -float(r.get('max_drawdown', 1.0) or 1.0), int(r.get('trades', 0) or 0)), reverse=True)[0]
    pf = float(best.get('profit_factor', summary.get('profit_factor', 0.0)) or 0.0)
    dd = float(best.get('max_drawdown', summary.get('max_drawdown', 1.0)) or 1.0)
    trades = int(best.get('trades', summary.get('trades', 0)) or 0)
    strategy_path = str(batch.get('strategy_spec_path') or '')
    strategy_family = Path(strategy_path).stem if strategy_path else 'unknown_strategy'
    template = str(best.get('variant_name') or batch.get('variant') or 'unknown_template')
    return pf, dd, trades, best, strategy_family, template


def _classify_verdict(pf_after_costs: float, max_drawdown: float, trades: int) -> str:
    if trades < 20 or pf_after_costs < 1.0 or max_drawdown > 0.30:
        return 'REJECT'
    if pf_after_costs < 1.2 or max_drawdown > 0.20:
        return 'REVISE'
    return 'ACCEPT'


def _extract_regime_context(best_run: dict) -> dict:
    out = {'available': False, 'regime_breakdown': {}, 'regime_pf': {}, 'regime_wr': {}, 'dominant_regime': '', 'good_regimes': [], 'bad_regimes': [], 'all_good': False, 'all_bad': False, 'single_good': False}
    bp = str(best_run.get('backtest_result_path') or '')
    if not bp:
        return out
    bobj = _j(Path(bp), {})
    res = bobj.get('results') if isinstance(bobj, dict) else {}
    if not isinstance(res, dict):
        return out
    regime_pf = res.get('regime_pf') or {}
    regime_wr = res.get('regime_wr') or {}
    regime_breakdown = res.get('regime_breakdown') or {}
    dominant = str(res.get('dominant_regime') or '')
    if not isinstance(regime_pf, dict) or not regime_pf:
        return out
    good, bad = [], []
    for rg in ('trending', 'ranging', 'transitional'):
        pf = float(regime_pf.get(rg, 0.0) or 0.0)
        if pf >= 1.05:
            good.append(rg)
        elif pf < 0.95:
            bad.append(rg)
    out.update({'available': True, 'regime_breakdown': regime_breakdown, 'regime_pf': {k: float(v or 0.0) for k, v in regime_pf.items()}, 'regime_wr': {k: float(v or 0.0) for k, v in regime_wr.items()}, 'dominant_regime': dominant, 'good_regimes': good, 'bad_regimes': bad, 'all_good': (len(good) >= 3), 'all_bad': (len(bad) >= 3), 'single_good': (len(good) == 1 and len(bad) >= 1)})
    return out


def _failure_reasons(pf: float, dd: float, trades: int, evidence: str, refinement: dict) -> list[dict]:
    out: list[dict] = []
    if trades < 20:
        out.append({'code': 'LOW_TRADE_COUNT', 'short': f'Trade count below gate: {trades} < 20', 'evidence_pointer': evidence})
    if dd > 0.30:
        out.append({'code': 'HIGH_DRAWDOWN', 'short': f'Max drawdown too high: {dd:.3f} > 0.30', 'evidence_pointer': evidence})
    if pf < 1.0:
        out.append({'code': 'PF_BELOW_1', 'short': f'Profit factor after costs below 1.0: {pf:.3f}', 'evidence_pointer': evidence})
    rec = str(refinement.get('final_recommendation') or '')
    if rec == 'NO_IMPROVEMENT':
        out.append({'code': 'NO_IMPROVEMENT', 'short': 'Refinement reported no improvement', 'evidence_pointer': 'refinement_cycle.final_recommendation'})
    if not out:
        out.append({'code': 'MARGIN_RISK', 'short': 'No hard fail; tune thresholds to improve margin of safety', 'evidence_pointer': evidence})
    return out[:5]


def _extract_pf_from_note(note: dict) -> float | None:
    metrics = note.get('metrics') or {}
    pf = metrics.get('profit_factor_after_costs')
    if isinstance(pf, (int, float)):
        return float(pf)
    for fr in note.get('failure_reasons') or []:
        if str(fr.get('code')) == 'PF_BELOW_1':
            txt = str(fr.get('short') or '')
            m = re.search(r'([0-9]+(?:\.[0-9]+)?)', txt)
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    pass
    return None


def _load_recent_family_notes(strategy_family: str, limit: int = 5) -> list[dict]:
    if not strategy_family:
        return []
    notes: list[dict] = []
    for p in ROOT.glob('artifacts/outcomes/**/outcome_notes_*.json'):
        obj = _j(p, {})
        if str(obj.get('strategy_family') or '') != strategy_family:
            continue
        notes.append(obj)
    notes.sort(key=lambda n: str(n.get('created_at') or ''), reverse=True)
    return notes[:max(0, limit)]


def load_strategy_spec(backtest_result: dict) -> dict:
    if not isinstance(backtest_result, dict):
        return {}
    inputs = backtest_result.get('inputs') or {}
    spec_path = str(inputs.get('strategy_spec') or backtest_result.get('strategy_spec_path') or '')
    if spec_path:
        p = Path(spec_path)
        if p.exists():
            return _j(p, {})
        rp = ROOT / spec_path
        if rp.exists():
            return _j(rp, {})
    spec_id = str(backtest_result.get('spec_id') or '')
    if spec_id:
        for p in ROOT.glob('artifacts/strategy_specs/**/*.strategy_spec.json'):
            if spec_id in p.name:
                return _j(p, {})
    return {}


def load_family_outcome_history(family_name: str, limit: int = 5) -> list[dict]:
    return _load_recent_family_notes(family_name, limit=limit)


def _append_doctrine_insight(family: str, insight: str, source_backtest: str, confidence: str) -> bool:
    if not insight:
        return False
    p = ROOT / 'artifacts' / 'doctrine_updates' / 'analyser_insights.ndjson'
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {'timestamp': datetime.now(UTC).isoformat(), 'family': family, 'insight': insight.strip(), 'source_backtest': source_backtest, 'confidence': confidence or ''}
    with open(p, 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return True


def _maybe_trigger_doctrine_synthesis() -> None:
    insights = ROOT / 'artifacts' / 'doctrine_updates' / 'analyser_insights.ndjson'
    if not insights.exists():
        return
    with open(insights, 'r', encoding='utf-8') as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    count = len(lines)
    updates = sorted((ROOT / 'artifacts' / 'doctrine_updates').glob('**/*.doctrine_update.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    hours_since_last = 999999.0
    if updates:
        last = datetime.fromtimestamp(updates[0].stat().st_mtime, tz=UTC)
        hours_since_last = (datetime.now(UTC) - last).total_seconds() / 3600.0
    should_trigger = (count >= 50) or (count >= 10 and hours_since_last > 24.0)
    if not should_trigger:
        return
    cmd = [PY, 'scripts/pipeline/update_analyser_doctrine.py', '--insights-file', 'artifacts/doctrine_updates/analyser_insights.ndjson']
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if p.returncode != 0:
        _log('WARN', 'DOCTRINE_SYNTHESIS_TODO', 'TODO: update_analyser_doctrine.py --insights-file not wired yet; auto-trigger skipped')
        return
    ts = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    archived = insights.with_name(f'analyser_insights_{ts}.ndjson')
    insights.replace(archived)


def compress_spec(spec: dict) -> str:
    if not isinstance(spec, dict):
        return 'name=unknown; asset=unknown; timeframe=unknown; indicators=unknown; entry=unknown; exit=unknown; risk=unknown'
    variants = spec.get('variants') or []
    v = variants[0] if isinstance(variants, list) and variants and isinstance(variants[0], dict) else {}
    name = str(spec.get('id') or v.get('name') or 'unknown')
    family = str(spec.get('strategy_family') or name)

    indicator_terms = ['ema', 'sma', 't3', 'kama', 'alma', 'rsi', 'macd', 'stochastic', 'cci', 'williams', 'qqe', 'vortex', 'stc', 'obv', 'vwap', 'atr', 'bollinger', 'donchian', 'adx', 'stiffness', 'supertrend', 'ichimoku']
    txt = ' '.join(
        [str(v.get('description') or '')] +
        [str(x) for k in ('entry_long', 'entry_short', 'filters', 'exit_rules', 'risk_rules') for x in (v.get(k) or [])]
    ).lower()
    indicators = [t for t in indicator_terms if t in txt]
    indicators = list(dict.fromkeys(indicators))[:8]

    params = []
    for p in (v.get('parameters') or [])[:6]:
        if isinstance(p, dict) and p.get('name') is not None:
            params.append(f"{p.get('name')}={p.get('default')}")

    entry_summary = '; '.join([str(x) for x in (v.get('entry_long') or [])[:2]])[:220]
    exit_summary = '; '.join([str(x) for x in (v.get('exit_rules') or [])[:2]])[:220]
    riskp = v.get('risk_policy') if isinstance(v.get('risk_policy'), dict) else {}
    risk_summary = f"stop={riskp.get('stop_type')}:{riskp.get('stop_atr_mult')}, tp={riskp.get('tp_type')}:{riskp.get('tp_atr_mult')}, risk_pct={riskp.get('risk_per_trade_pct')}"

    out = (
        f"name={name}; family={family}; asset=unknown; timeframe=unknown; "
        f"indicators={','.join(indicators) or 'none'}; params={','.join(params) or 'none'}; "
        f"entry={entry_summary or 'n/a'}; exit={exit_summary or 'n/a'}; risk={risk_summary}"
    )
    return out[:800]


def select_relevant_doctrine(doctrine: str, indicators: list[str]) -> str:
    lines = [ln.strip() for ln in str(doctrine or '').splitlines() if ln.strip().startswith('- [')]
    if not lines:
        return (doctrine or '')[:1000]
    inds = [str(x).lower() for x in (indicators or [])]

    def score(line: str) -> int:
        low = line.lower()
        s = 0
        if any(i and i in low for i in inds):
            s += 3
        if any(k in low for k in ['regime', 'risk gating', 'drawdown', 'session gate']):
            s += 2
        return s

    ranked = sorted(lines, key=lambda x: score(x), reverse=True)
    chosen = ranked[:5] if ranked else lines[:5]
    txt = '\n'.join(chosen)
    return txt[:1000]


def build_analyser_prompt(backtest_result: dict, strategy_spec: dict, doctrine: str, outcome_history: list[dict]) -> tuple[str, str]:
    system = 'Quant analyser. Return JSON only: verdict, reasoning, directives, regime_recommendation, confidence, doctrine_update.'
    res = (backtest_result or {}).get('results', {}) if isinstance(backtest_result, dict) else {}
    inputs = (backtest_result or {}).get('inputs', {}) if isinstance(backtest_result, dict) else {}
    regime_pf = res.get('regime_pf') or {}
    regime_wr = res.get('regime_wr') or {}
    regime_breakdown = res.get('regime_breakdown') or {}

    spec_summary = compress_spec(strategy_spec)
    indicators = re.findall(r'indicators=([^;]+)', spec_summary)
    indicator_list = [x.strip() for x in (indicators[0].split(',') if indicators else []) if x.strip() and x.strip() != 'none']
    doctrine_text = select_relevant_doctrine(doctrine, indicator_list)

    hist_rows = []
    for h in (outcome_history or [])[:5]:
        verdict = str(h.get('verdict') or '')
        dtypes = [str(d.get('type') or '') for d in (h.get('directives') or [])[:3] if isinstance(d, dict)]
        reason = ''
        if h.get('llm_reasoning'):
            reason = str(h.get('llm_reasoning'))
        elif h.get('failure_reasons'):
            fr = h.get('failure_reasons') or []
            reason = str((fr[0] or {}).get('short') if fr and isinstance(fr[0], dict) else '')
        hist_rows.append(f"{verdict}: {reason[:80]} | directives={','.join(dtypes)[:80]}")
    history_compact = '\n'.join(hist_rows)[:500]

    contract = (
        '{"verdict":"ACCEPT|REJECT","reasoning":"...","directives":[{"type":"ROLE_SWAP|THRESHOLD_SWEEP|PARAM_SWEEP|ENTRY_TIGHTEN|ENTRY_RELAX|EXIT_CHANGE|GATE_ADJUST|TEMPLATE_SWITCH","params":{},"reasoning":"..."}],'
        '"regime_recommendation":{"add_filter":true|false,"allowed_regimes":["trending"|"ranging"|"transitional"]},"confidence":"low|medium|high","doctrine_update":"string|null"}'
    )

    user = (
        'Strategy Summary\n' + spec_summary + '\n\n'
        'Backtest Results\n'
        f"PF={float(res.get('profit_factor', 0.0) or 0.0):.4f}; WR={float(res.get('win_rate', 0.0) or 0.0) * 100:.2f}%; DD={float(res.get('max_drawdown', 0.0) or 0.0) * 100:.2f}%; Trades={int(res.get('total_trades', 0) or 0)}; TF={inputs.get('variant') or inputs.get('dataset_meta') or 'unknown'}; Asset={inputs.get('dataset_csv') or 'unknown'}\n\n"
        'Regime\n'
        f"trend(PF={float(regime_pf.get('trending', 0.0) or 0.0):.4f},WR={float(regime_wr.get('trending', 0.0) or 0.0) * 100:.1f}%,N={int(regime_breakdown.get('trending_trades', 0) or 0)}); "
        f"range(PF={float(regime_pf.get('ranging', 0.0) or 0.0):.4f},WR={float(regime_wr.get('ranging', 0.0) or 0.0) * 100:.1f}%,N={int(regime_breakdown.get('ranging_trades', 0) or 0)}); "
        f"trans(PF={float(regime_pf.get('transitional', 0.0) or 0.0):.4f},WR={float(regime_wr.get('transitional', 0.0) or 0.0) * 100:.1f}%,N={int(regime_breakdown.get('transitional_trades', 0) or 0)}); dom={res.get('dominant_regime', 'unknown')}\n\n"
        'Doctrine (top 5 relevant)\n' + doctrine_text + '\n\n'
        'Recent Outcomes\n' + history_compact + '\n\n'
        'Rules: ACCEPT only if PF>1.0 and Trades>50. Generate 1-3 directives, valid types only, specific params.\n'
        'Return JSON exactly:\n' + contract
    )
    return system[:200], user[:8000]


def _directive_history_stats(notes: list[dict]) -> dict[str, dict]:
    if not notes:
        return {}
    chronological = list(reversed(notes))
    stats: dict[str, dict] = {}
    for i in range(len(chronological) - 1):
        prev_note = chronological[i]
        next_note = chronological[i + 1]
        pf_prev = _extract_pf_from_note(prev_note)
        pf_next = _extract_pf_from_note(next_note)
        if pf_prev is None or pf_next is None:
            continue
        delta = float(pf_next - pf_prev)
        for d in prev_note.get('directives') or []:
            dt = str(d.get('type') or '')
            if dt not in DIRECTIVE_TYPES:
                continue
            rec = stats.setdefault(dt, {'tried': 0, 'improved': 0, 'worsened': 0, 'flat': 0, 'avg_delta_pf': 0.0})
            rec['tried'] += 1
            rec['avg_delta_pf'] += delta
            if delta > 1e-9:
                rec['improved'] += 1
            elif delta < -1e-9:
                rec['worsened'] += 1
            else:
                rec['flat'] += 1
    for rec in stats.values():
        if rec['tried']:
            rec['avg_delta_pf'] = rec['avg_delta_pf'] / rec['tried']
    return stats


def _opposite_directive(d: dict) -> dict | None:
    typ = str(d.get('type') or '')
    params = dict(d.get('params') or {})
    if typ == 'ENTRY_TIGHTEN':
        return {'type': 'ENTRY_RELAX', 'params': {'confidence_threshold_delta': -abs(float(params.get('confidence_threshold_delta', 0.05)))}, 'rationale': 'Opposite of prior tightening after PF deterioration.'}
    if typ == 'ENTRY_RELAX':
        return {'type': 'ENTRY_TIGHTEN', 'params': {'confidence_threshold_delta': abs(float(params.get('confidence_threshold_delta', -0.05)))}, 'rationale': 'Opposite of prior relaxation after PF deterioration.'}
    if typ == 'EXIT_CHANGE':
        return {'type': 'EXIT_CHANGE', 'params': {'stop_atr_mult': float(params.get('stop_atr_mult', 1.2)) * 1.25, 'tp_atr_mult': float(params.get('tp_atr_mult', 1.8)) * 1.25}, 'rationale': 'Opposite direction: widen exits after worse PF.'}
    if typ == 'PARAM_SWEEP':
        p = dict(params)
        rng = p.get('range')
        if isinstance(rng, list) and len(rng) == 2:
            p['range'] = [rng[1], rng[0]]
        return {'type': 'PARAM_SWEEP', 'params': p, 'rationale': 'Flip sweep direction after worse PF.'}
    if typ == 'ROLE_SWAP':
        return {'type': 'TEMPLATE_SWITCH', 'params': {'target': 'FALLBACK_TEMPLATE_TREND'}, 'rationale': 'Alternate structural change after role swap underperformed.'}
    if typ == 'TEMPLATE_SWITCH':
        return {'type': 'ROLE_SWAP', 'params': {'swap': 'entry<->confirmation'}, 'rationale': 'Alternate structural change after template switch underperformed.'}
    return None


def _amplify_directive(d: dict) -> dict:
    out = json.loads(json.dumps(d))
    t = str(out.get('type') or '')
    p = out.setdefault('params', {})
    if t in {'ENTRY_TIGHTEN', 'ENTRY_RELAX'} and 'confidence_threshold_delta' in p:
        p['confidence_threshold_delta'] = round(float(p['confidence_threshold_delta']) * 1.5, 4)
    elif t == 'EXIT_CHANGE':
        if 'stop_atr_mult' in p:
            p['stop_atr_mult'] = round(float(p['stop_atr_mult']) * 1.15, 4)
        if 'tp_atr_mult' in p:
            p['tp_atr_mult'] = round(float(p['tp_atr_mult']) * 1.15, 4)
    elif t == 'PARAM_SWEEP':
        if 'step' in p:
            p['step'] = max(0.01, round(float(p['step']) * 0.75, 4))
    out['rationale'] = str(out.get('rationale') or '') + ' (amplified after prior PF improvement)'
    return out


def _apply_history_to_directives(base_directives: list[dict], history_stats: dict[str, dict]) -> list[dict]:
    adjusted: list[dict] = []
    for d in base_directives:
        t = str(d.get('type') or '')
        stat = history_stats.get(t)
        if stat and stat.get('worsened', 0) > stat.get('improved', 0):
            opp = _opposite_directive(d)
            if opp:
                nd = dict(d)
                nd['type'] = opp['type']
                nd['params'] = opp['params']
                nd['rationale'] = opp['rationale']
                adjusted.append(nd)
            continue
        if stat and stat.get('improved', 0) > 0 and stat.get('avg_delta_pf', 0.0) > 0:
            adjusted.append(_amplify_directive(d))
        else:
            adjusted.append(d)
    adjusted.sort(key=lambda d: 0 if str(d.get('type') or '') not in history_stats else 1)
    out: list[dict] = []
    for i, d in enumerate(adjusted, start=1):
        dt = str(d.get('type') or '')
        if dt not in DIRECTIVE_TYPES:
            continue
        clean = {'id': f'd{i}', 'type': dt, 'params': d.get('params') or {}, 'rationale': str(d.get('rationale') or ''), 'priority': int(d.get('priority', i))}
        if clean not in out:
            out.append(clean)
        if len(out) >= 5:
            break
    return out


def _directives_from_failures(failures: list[dict], verdict: str) -> list[dict]:
    directives: list[dict] = []
    idx = 1
    for f in failures:
        code = f['code']
        if code == 'LOW_TRADE_COUNT':
            directives.append({'id': f'd{idx}', 'type': 'ENTRY_RELAX', 'params': {'confidence_threshold_delta': -0.05}, 'rationale': 'Increase participation to clear minimum trade gate.', 'priority': 1}); idx += 1
            directives.append({'id': f'd{idx}', 'type': 'THRESHOLD_SWEEP', 'params': {'parameter': 'confidence_threshold', 'range': [0.5, 0.7], 'step': 0.05}, 'rationale': 'Sweep entry threshold to recover trade frequency.', 'priority': 2}); idx += 1
        elif code == 'HIGH_DRAWDOWN':
            directives.append({'id': f'd{idx}', 'type': 'ENTRY_TIGHTEN', 'params': {'confidence_threshold_delta': 0.05}, 'rationale': 'Tighten entry quality to reduce adverse excursions.', 'priority': 1}); idx += 1
            directives.append({'id': f'd{idx}', 'type': 'EXIT_CHANGE', 'params': {'stop_atr_mult': 1.2, 'tp_atr_mult': 1.8}, 'rationale': 'Adjust exits to cap drawdown.', 'priority': 2}); idx += 1
        elif code == 'PF_BELOW_1':
            directives.append({'id': f'd{idx}', 'type': 'PARAM_SWEEP', 'params': {'parameter': 'risk_r', 'range': [0.5, 1.5], 'step': 0.25}, 'rationale': 'Re-balance payoff profile to improve PF.', 'priority': 1}); idx += 1
            directives.append({'id': f'd{idx}', 'type': 'ROLE_SWAP', 'params': {'swap': 'entry<->confirmation'}, 'rationale': 'Test alternate component role assignment for better edge.', 'priority': 3}); idx += 1
        elif code == 'NO_IMPROVEMENT':
            directives.append({'id': f'd{idx}', 'type': 'TEMPLATE_SWITCH', 'params': {'target': 'FALLBACK_TEMPLATE_CONFIRMATION'}, 'rationale': 'Switch template when local refinement stalls.', 'priority': 2}); idx += 1
        elif code == 'MARGIN_RISK':
            directives.append({'id': f'd{idx}', 'type': 'GATE_ADJUST', 'params': {'min_trades_required': 25}, 'rationale': 'Raise reliability gate under acceptable baseline.', 'priority': 3}); idx += 1
    if verdict == 'REJECT' and len(directives) < 2:
        directives.append({'id': f'd{idx}', 'type': 'GATE_ADJUST', 'params': {'max_drawdown_cap': 0.25}, 'rationale': 'Enforce stricter DD cap before promotion.', 'priority': 1})
    out = []
    for d in directives:
        if d['type'] in DIRECTIVE_TYPES and d not in out:
            out.append(d)
        if len(out) >= 5:
            break
    return out[:5] if out else [{'id': 'd1', 'type': 'GATE_ADJUST', 'params': {'min_trades_required': 20}, 'rationale': 'Default deterministic gate hygiene.', 'priority': 3}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--batch-artifact', default='')
    ap.add_argument('--refinement-artifact', default='')
    ap.add_argument('--disable-doctrine', action='store_true')
    ap.add_argument('--no-llm', action='store_true')
    args = ap.parse_args()

    batch_path = Path(args.batch_artifact) if args.batch_artifact else latest_file('artifacts/batches/**/batch_*.batch_backtest.json')
    ref_path = Path(args.refinement_artifact) if args.refinement_artifact else latest_file('artifacts/refinement/**/*.refinement_cycle.json')
    lessons_path = ROOT / 'artifacts' / 'library' / 'LESSONS_INDEX.json'
    batch = _j(batch_path, {}) if batch_path else {}
    refinement = _j(ref_path, {}) if ref_path else {}
    _ = _j(lessons_path, [])

    sources_used: list[str] = []
    if batch_path and batch_path.exists():
        sources_used.append(str(batch_path).replace('\\', '/'))
    if ref_path and ref_path.exists():
        sources_used.append(str(ref_path).replace('\\', '/'))
    if lessons_path.exists():
        sources_used.append(str(lessons_path).replace('\\', '/'))

    pf, dd, trades, best_run, strategy_family, template = _extract_metrics(batch)
    verdict = _classify_verdict(pf, dd, trades)
    evidence = (best_run.get('backtest_result_path') or (sources_used[0] if sources_used else 'artifacts/backtests/unknown'))
    regime_ctx = _extract_regime_context(best_run)

    failures = _failure_reasons(pf, dd, trades, str(evidence), refinement)
    base_directives = _directives_from_failures(failures, verdict)
    if regime_ctx.get('single_good'):
        good_regime = str((regime_ctx.get('good_regimes') or [''])[0]); verdict = 'REVISE'
        base_directives = [{'id': 'd_regime_filter_only', 'type': 'GATE_ADJUST', 'params': {'require_regime_filter': True, 'allowed_regime': good_regime}, 'rationale': f"Regime-aware: strategy shows edge mainly in {good_regime}; restrict trading to that regime.", 'priority': 1}] + [d for d in base_directives if d.get('type') != 'GATE_ADJUST']
    elif regime_ctx.get('all_bad'):
        verdict = 'REJECT'
        base_directives = [{'id': 'd_regime_pivot', 'type': 'TEMPLATE_SWITCH', 'params': {'target': 'FALLBACK_TEMPLATE_TREND', 'reason': 'all_regimes_underperform'}, 'rationale': 'Regime-aware: underperforms across all regimes; pivot to fundamentally different structure.', 'priority': 1}] + base_directives
    elif regime_ctx.get('all_good'):
        verdict = 'ACCEPT'
        base_directives = [{'id': 'd_regime_refine', 'type': 'PARAM_SWEEP', 'params': {'parameter': 'risk_r', 'range': [0.75, 1.75], 'step': 0.25, 'reason': 'all_regimes_strong'}, 'rationale': 'Regime-aware: robust across regimes; prioritise refinement over structural changes.', 'priority': 1}] + base_directives

    variant_ctx = _load_strategy_variant_context(batch, best_run)
    doctrine_refs: list[dict] = []
    doctrine = DoctrinePrinciples(False, False, False, [])
    doctrine_directives = list(base_directives)
    if not args.disable_doctrine:
        doctrine = _load_doctrine_principles(DOCTRINE_PATH)
        doctrine_directives, doctrine_refs = _apply_doctrine_influence(base_directives, doctrine, variant_ctx, dd)

    recent_notes = _load_recent_family_notes(strategy_family, limit=5)
    history_stats = _directive_history_stats(recent_notes)
    directives = _apply_history_to_directives(doctrine_directives, history_stats)

    analysis_source = 'rules'
    llm_reasoning = None
    llm_confidence = None
    regime_recommendation = None
    doctrine_update = None

    if not args.no_llm:
        bt_obj = _j(Path(str(best_run.get('backtest_result_path') or '')), {}) if best_run.get('backtest_result_path') else {}
        strategy_spec_obj = load_strategy_spec(bt_obj)
        doctrine_text = DOCTRINE_PATH.read_text(encoding='utf-8-sig') if DOCTRINE_PATH.exists() else ''
        outcome_history = load_family_outcome_history(strategy_family, limit=5)
        system_prompt, user_prompt = build_analyser_prompt(bt_obj, strategy_spec_obj, doctrine_text, outcome_history)
        _log('INFO', 'LLM_PROMPT_SIZE', f'prompt_length_chars={len(system_prompt) + len(user_prompt)}')
        raw = llm_client.llm_complete(user_prompt, system=system_prompt, agent='main', timeout=120)
        use_llm = False
        llm_result: dict = {}
        if raw:
            parsed = llm_client.parse_llm_json(raw)
            if isinstance(parsed, dict):
                llm_result = parsed
                if all(k in llm_result for k in ['verdict', 'reasoning', 'directives', 'confidence']):
                    use_llm = True

        if use_llm:
            v = str(llm_result.get('verdict', '')).upper()
            if v in {'ACCEPT', 'REJECT', 'REVISE'}:
                verdict = v
            llm_dirs = llm_result.get('directives', []) if isinstance(llm_result.get('directives'), list) else []
            safe_dirs = []
            for i, d in enumerate(llm_dirs[:3], start=1):
                if not isinstance(d, dict):
                    continue
                dt = str(d.get('type') or '')
                if dt not in DIRECTIVE_TYPES:
                    continue
                safe_dirs.append({'id': f'd{i}', 'type': dt, 'params': d.get('params') if isinstance(d.get('params'), dict) else {}, 'rationale': str(d.get('reasoning') or d.get('rationale') or ''), 'priority': i})
            if safe_dirs:
                directives = safe_dirs
            analysis_source = 'llm'
            llm_reasoning = str(llm_result.get('reasoning') or '')
            llm_confidence = str(llm_result.get('confidence') or '')
            regime_recommendation = llm_result.get('regime_recommendation') if isinstance(llm_result.get('regime_recommendation'), dict) else None
            doctrine_update = llm_result.get('doctrine_update')
            if doctrine_update is not None:
                doctrine_update = str(doctrine_update).strip() if str(doctrine_update).strip().lower() != 'null' else None
            if doctrine_update:
                _append_doctrine_insight(strategy_family, doctrine_update, str(best_run.get('backtest_result_path') or ''), llm_confidence or '')
                _maybe_trigger_doctrine_synthesis()
            _log('INFO', 'LLM_PATH', f'Outcome analysis used LLM for strategy_family={strategy_family}')
        else:
            _log('WARN', 'LLM_FALLBACK', 'LLM call failed, using rules')
    else:
        _log('INFO', 'RULES_PATH', f'Outcome analysis used rules-only for strategy_family={strategy_family}')

    next_experiments = [f"Apply {d['type']} with params={json.dumps(d['params'], sort_keys=True)}" for d in directives[:5]]

    day = datetime.now(UTC).strftime('%Y%m%d')
    out_dir = ROOT / 'artifacts' / 'outcomes' / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'outcome_notes_{args.run_id}.json'
    payload = {
        'schema_version': '2.0', 'id': f'outcome-notes-{args.run_id}', 'run_id': args.run_id, 'created_at': datetime.now(UTC).isoformat(),
        'verdict': verdict, 'strategy_family': strategy_family, 'template': template,
        'metrics': {'profit_factor_after_costs': pf, 'max_drawdown': dd, 'trades': trades, 'regime_breakdown': regime_ctx.get('regime_breakdown', {}), 'regime_pf': regime_ctx.get('regime_pf', {}), 'regime_wr': regime_ctx.get('regime_wr', {}), 'dominant_regime': regime_ctx.get('dominant_regime', '')},
        'regime_analysis': {'available': bool(regime_ctx.get('available')), 'good_regimes': regime_ctx.get('good_regimes', []), 'bad_regimes': regime_ctx.get('bad_regimes', []), 'all_good': bool(regime_ctx.get('all_good')), 'all_bad': bool(regime_ctx.get('all_bad')), 'single_good': bool(regime_ctx.get('single_good'))},
        'failure_reasons': failures[:5], 'directives': directives[:5], 'analysis_source': analysis_source, 'doctrine_refs': doctrine_refs[:10],
        'directive_history': {'notes_considered': len(recent_notes), 'history_window': [{'id': str(n.get('id') or ''), 'created_at': str(n.get('created_at') or ''), 'verdict': str(n.get('verdict') or ''), 'profit_factor_after_costs': _extract_pf_from_note(n), 'directive_types': [str(d.get('type') or '') for d in (n.get('directives') or [])[:5]]} for n in recent_notes], 'directive_type_stats': history_stats, 'doctrine_enabled': (not args.disable_doctrine), 'doctrine_principles': {'regime_required': doctrine.regime_required, 'risk_gating': doctrine.risk_gating, 'macd_confirmation_over_entry': doctrine.macd_confirmation_over_entry}},
        'next_experiments': next_experiments[:5], 'sources_used': sources_used[:10],
    }
    if analysis_source == 'llm':
        payload['llm_reasoning'] = llm_reasoning
        payload['llm_confidence'] = llm_confidence
        payload['regime_recommendation'] = regime_recommendation
        if doctrine_update:
            payload['doctrine_update'] = doctrine_update

    out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    summary_line = f'ANALYSER_OUTCOME_SUMMARY — processed=1 verdict={verdict} directives={len(directives[:5])}'
    _log('OK', 'ANALYSER_OUTCOME_SUMMARY', summary_line)
    print(summary_line)
    print(json.dumps({'processed': 1, 'verdict': verdict, 'directives': len(directives[:5]), 'outcome_notes_path': str(out_path).replace('\\', '/')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
