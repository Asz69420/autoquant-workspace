#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 50 * 1024
MAX_INDEX = 200


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


def main() -> int:
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

    thesis = {
        'schema_version': '1.0',
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
