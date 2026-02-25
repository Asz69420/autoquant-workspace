#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import re

MAX_JSON_BYTES = 50 * 1024
MAX_INDEX = 200
ROOT = Path(__file__).resolve().parents[2]


def _set_reasoning_effort_for_analyser() -> None:
    model_id = (os.getenv('OPENCLAW_MODEL_ID') or 'openai-codex/gpt-5.3-codex').strip()
    effort = 'default'
    if 'gpt-5.3-codex' in model_id:
        os.environ['OPENAI_REASONING_EFFORT'] = 'high'
        os.environ['OPENCLAW_REASONING_EFFORT'] = 'high'
        effort = 'high'

    cmd = [
        sys.executable,
        'scripts/log_event.py',
        '--run-id', f"reasoning-analyser-{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
        '--agent', 'oQ',
        '--model-id', model_id,
        '--action', 'analyser_reasoning',
        '--status-word', 'INFO',
        '--status-emoji', 'ℹ️',
        '--reason-code', 'REASONING_EFFORT_SET',
        '--summary', f'stage=Analyser effort={effort}',
        '--outputs', f'model={model_id}'
    ]
    try:
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def jload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def update_index(path: Path, pointer: str) -> None:
    items = []
    if path.exists():
        try:
            items = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            items = []
    if pointer in items:
        items.remove(pointer)
    items.insert(0, pointer)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items[:MAX_INDEX], indent=2), encoding='utf-8')


def non_empty(lines: list[str], limit: int, max_len: int) -> list[str]:
    out = []
    for x in lines:
        s = str(x).strip()
        if s and s not in out:
            out.append(s[:max_len])
        if len(out) >= limit:
            break
    return out


def load_doctrine_guidance(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {'strategy': [], 'automation': []}
    lines = path.read_text(encoding='utf-8').splitlines()
    section = None
    out = {'strategy': [], 'automation': []}
    bullet_re = re.compile(r'^- \[[^\]]+\]\s+(.*)$')
    for line in lines:
        s = line.strip()
        if s == '## 2) Strategy hypothesis heuristics':
            section = 'strategy'
            continue
        if s == '## 3) Automation/system heuristics':
            section = 'automation'
            continue
        if s.startswith('## '):
            section = None
            continue
        if section in out:
            m = bullet_re.match(s)
            if m:
                out[section].append(m.group(1).strip())
    out['strategy'] = out['strategy'][:5]
    out['automation'] = out['automation'][:5]
    return out


def build_combo_proposals(indicators: list[dict], rc: dict, timeframe: str, doctrine_strategy: list[str]) -> list[dict]:
    names = [i.get('name', 'unknown') for i in indicators][:5]
    tpx = next((n for n in names if 'pressure' in n.lower() or 'tpx' in n.lower()), names[0] if names else 'TPX')
    doctrine_hint = doctrine_strategy[0] if doctrine_strategy else ''
    proposals = [
        {
            'indicator': tpx,
            'role': 'confirmation',
            'description': f'Confirm long only when {tpx} bullish pressure is above control level (>=30) on {timeframe} bar close.',
            'confidence': 0.76,
            'doctrine_hint': doctrine_hint,
        },
        {
            'indicator': 'MACD-long',
            'role': 'trend',
            'description': 'Use longer MACD side of zero as trend direction gate before entries.',
            'confidence': 0.71,
            'doctrine_hint': doctrine_hint,
        },
        {
            'indicator': 'MACD-short',
            'role': 'entry',
            'description': 'Trigger entries when shorter MACD aligns with longer MACD direction.',
            'confidence': 0.69,
            'doctrine_hint': doctrine_hint,
        },
        {
            'indicator': tpx,
            'role': 'regime_gate',
            'description': f'Gate entries when {tpx} stays above control threshold to avoid weak-pressure chop.',
            'confidence': 0.66,
            'doctrine_hint': doctrine_hint,
        },
        {
            'indicator': 'ATR14',
            'role': 'exit',
            'description': 'Derived idea: use ATR-based stop/TP envelope for deterministic testability of swing-style stops.',
            'confidence': 0.62,
            'doctrine_hint': doctrine_hint,
        },
    ]
    return proposals[:5]


def build_mutation_catalog(doctrine_automation: list[str]) -> list[dict]:
    hint = doctrine_automation[0] if doctrine_automation else ''
    return [
        {'type': 'threshold', 'suggestion': 'Sweep TPX control level', 'bounds': '20,30,40', 'doctrine_hint': hint},
        {'type': 'risk', 'suggestion': 'Sweep ATR stop/TP multipliers', 'bounds': 'stop:1.2-2.0,tp:1.8-3.0', 'doctrine_hint': hint},
        {'type': 'execution', 'suggestion': 'Entry fill rule sweep', 'bounds': 'bar_close|next_open', 'doctrine_hint': hint},
        {'type': 'filter', 'suggestion': 'Role swap TPX confirmation/filter', 'bounds': 'confirmation|filter|entry', 'doctrine_hint': hint},
    ][:10]


def main() -> int:
    _set_reasoning_effort_for_analyser()

    ap = argparse.ArgumentParser()
    ap.add_argument('--research-card-path', required=True)
    ap.add_argument('--indicator-record-paths', default='[]')
    ap.add_argument('--linkmap-paths', default='[]')
    ap.add_argument('--output-root', default='artifacts/thesis')
    args = ap.parse_args()

    rc_paths = [args.research_card_path][:5]
    ir_paths = json.loads(args.indicator_record_paths)[:10]
    lm_paths = json.loads(args.linkmap_paths)[:5]

    rc = jload(rc_paths[0])
    indicators = [jload(p) for p in ir_paths if Path(p).exists()]
    doctrine = load_doctrine_guidance(Path('docs/DOCTRINE/analyser-doctrine.md'))

    in_hashes = []
    for p in rc_paths + ir_paths + lm_paths:
        pp = Path(p)
        if pp.exists():
            obj = json.loads(pp.read_text(encoding='utf-8'))
            in_hashes.append(obj.get('sha256', sha256_file(pp)))
    sha256_inputs = hashlib.sha256('|'.join(in_hashes).encode('utf-8')).hexdigest()

    card_title = rc.get('title') or 'Research-derived thesis'
    mentioned_inds = rc.get('indicators_mentioned', [])[:5]
    indicator_names = [i.get('name', 'unknown') for i in indicators][:5]
    signal_inds = non_empty(mentioned_inds + indicator_names, 5, 120)

    bullets = non_empty(rc.get('summary_bullets', []), 10, 400)
    if not bullets:
        bullets = ['Momentum + structure alignment can be tested against reversal risk.']

    timeframe = (rc.get('timeframes_mentioned') or ['1h'])[0]
    asset = (rc.get('assets_mentioned') or ['BTC'])[0]

    hypotheses = [{
        'statement': f"{asset} continuation edge appears when signal alignment persists on {timeframe}.",
        'rationale': 'Research and indicator mentions converge on trend-continuation logic with confirmation filters.',
        'falsifiable_test': f"Backtest {asset} on {timeframe}: require >=55% win rate and positive expectancy over 200+ trades; reject if unmet.",
        'expected_regime': 'Trending, medium-volatility sessions',
        'failure_modes': [
            'Range-bound chop erodes edge',
            'Signal lag after volatility shock',
            'Indicator disagreement at entry',
        ],
    }][:5]

    candidate_signals = [{
        'name': 'alignment_entry',
        'description': 'Enter only when primary trend signal and confirmation filter agree on bar close.',
        'uses_indicators': signal_inds[:5],
        'timeframe_bias': timeframe,
        'confidence': 0.68,
    }][:10]

    combo_proposals = build_combo_proposals(indicators, rc, timeframe, doctrine.get('strategy', [])) if indicators else []
    mutation_catalog = build_mutation_catalog(doctrine.get('automation', [])) if indicators else []

    thesis = {
        'schema_version': '1.1',
        'id': f"thesis-{datetime.now().strftime('%Y%m%d')}-{sha256_inputs[:12]}",
        'created_at': now_iso(),
        'inputs': {
            'research_card_paths': rc_paths,
            'indicator_record_paths': ir_paths,
            'linkmap_paths': lm_paths,
        },
        'title': card_title[:120],
        'thesis_bullets': bullets[:10],
        'hypotheses': hypotheses,
        'candidate_signals': candidate_signals,
        'role_catalog': ['trend', 'entry', 'confirmation', 'regime_gate', 'exit'],
        'combo_proposals': combo_proposals[:10],
        'mutation_catalog': mutation_catalog[:10],
        'required_data': non_empty([
            f'{asset} OHLCV on {timeframe}',
            'Indicator values at bar close',
            'Fee/slippage assumptions',
        ], 10, 200),
        'constraints': non_empty([
            'no repaint',
            'bot-friendly',
            'chart timeframe only',
            'bar-close execution',
        ], 10, 200),
        'tags': non_empty((rc.get('tags') or []) + ['thesis', 'pipeline-stage2'], 20, 60),
        'guidance': {
            'doctrine_path': 'docs/DOCTRINE/analyser-doctrine.md',
            'strategy_heuristics_used': doctrine.get('strategy', [])[:3],
            'automation_heuristics_used': doctrine.get('automation', [])[:3],
        },
        'sha256_inputs': sha256_inputs,
    }

    payload = json.dumps(thesis, ensure_ascii=False, indent=2)
    if len(payload.encode('utf-8')) > MAX_JSON_BYTES:
        raise SystemExit('Thesis JSON exceeds 50KB')

    out_dir = Path(args.output_root) / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{thesis['id']}.thesis.json"
    out_path.write_text(payload, encoding='utf-8')

    update_index(Path(args.output_root) / 'INDEX.json', str(out_path).replace('\\', '/'))
    print(json.dumps({'thesis_path': str(out_path).replace('\\', '/')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
