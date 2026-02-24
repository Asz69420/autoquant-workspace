#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _parse_rule_map(rules: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for rule in rules:
        if '=' in rule:
            k, v = rule.split('=', 1)
            try:
                out[k.strip()] = float(v.strip())
            except ValueError:
                continue
    return out


def _heuristics(spec: dict, variant_name: str) -> tuple[list[str], list[str]]:
    variant = next((v for v in spec.get('variants', []) if v.get('name') == variant_name), spec.get('variants', [{}])[0])
    rules = variant.get('risk_rules', [])
    rule_map = _parse_rule_map(rules)

    blockers: list[str] = []
    suggestions: list[str] = []

    if len(rules) >= 6:
        blockers.append('too many filters')

    rsi_long_max = rule_map.get('rsi_long_max')
    rsi_short_min = rule_map.get('rsi_short_min')
    if (rsi_long_max is not None and rsi_long_max <= 40) or (rsi_short_min is not None and rsi_short_min >= 60):
        blockers.append('threshold too strict')
        if rsi_long_max is not None:
            suggestions.append(f'raise RSI threshold from <{int(rsi_long_max)} to <{int(rsi_long_max + 5)}')

    if 'ema_trend=200' in rules or 'ema_slope=50' in rules:
        blockers.append('trend filter rarely true')
        suggestions.append('remove EMA50 slope filter')

    tp_mult = rule_map.get('take_profit_atr_mult')
    if tp_mult is not None and tp_mult >= 3.0:
        suggestions.append('reduce TP multiple')

    if not blockers:
        blockers.append('threshold too strict')
    if not suggestions:
        suggestions.append('loosen one entry filter threshold by 5-10%')

    return blockers[:3], suggestions[:5]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy-spec-path', required=True)
    ap.add_argument('--variant', required=True)
    ap.add_argument('--symbol', required=True)
    ap.add_argument('--timeframe', required=True)
    ap.add_argument('--start', required=True)
    ap.add_argument('--end', required=True)
    ap.add_argument('--observed-trades', type=int, required=True)
    ap.add_argument('--min-trades-required', type=int, required=True)
    ap.add_argument('--id', required=True)
    args = ap.parse_args()

    spec = _load_json(args.strategy_spec_path)
    blockers, relaxations = _heuristics(spec, args.variant)

    payload = {
        'schema_version': '1.0',
        'id': args.id,
        'created_at': datetime.now(UTC).isoformat(),
        'strategy_spec_path': args.strategy_spec_path,
        'dataset': {
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start': args.start,
            'end': args.end,
        },
        'observed_trades': args.observed_trades,
        'min_trades_required': args.min_trades_required,
        'suspected_blockers': blockers,
        'suggested_relaxations': relaxations,
    }

    out_dir = Path('artifacts/suggestions') / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{args.id}.relax_suggestion.json'
    out_path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'relax_suggestion_path': str(out_path)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
