#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _parse_rules(lines: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in lines:
        if '=' in line:
            k, v = line.split('=', 1)
            try:
                out[k.strip()] = float(v.strip())
            except ValueError:
                continue
    return out


def _ema(prev: float | None, price: float, period: int) -> float:
    a = 2.0 / (period + 1)
    return price if prev is None else (a * price + (1 - a) * prev)


def _estimate_signals(closes: list[float], variant: dict) -> tuple[int, int, int]:
    rules = _parse_rules(variant.get('risk_rules', []))
    is_trendpullback = 'trendpullback' in variant.get('name', '').lower()

    ema9 = ema21 = ema50 = ema200 = None
    prev_ema9 = prev_ema21 = prev_ema50 = None

    long_n = short_n = 0
    rsi_long_max = float(rules.get('rsi_long_max', 40))
    rsi_short_min = float(rules.get('rsi_short_min', 60))
    # cheap proxy RSI: directional persistence on last 14 closes
    for i, c in enumerate(closes):
        prev_ema9, prev_ema21, prev_ema50 = ema9, ema21, ema50
        ema9 = _ema(ema9, c, 9)
        ema21 = _ema(ema21, c, 21)
        ema50 = _ema(ema50, c, int(rules.get('ema_slope', 50)))
        ema200 = _ema(ema200, c, int(rules.get('ema_trend', 200)))

        if i < 15:
            continue
        window = closes[max(0, i - 14): i + 1]
        up = sum(1 for j in range(1, len(window)) if window[j] > window[j - 1])
        rsi_proxy = (up / max(1, len(window) - 1)) * 100.0

        if is_trendpullback:
            ema50_up = prev_ema50 is not None and ema50 > prev_ema50
            ema50_dn = prev_ema50 is not None and ema50 < prev_ema50
            long_sig = ema200 is not None and c > ema200 and ema50_up and rsi_proxy < rsi_long_max
            short_sig = ema200 is not None and c < ema200 and ema50_dn and rsi_proxy > rsi_short_min
        else:
            long_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 <= prev_ema21 and ema9 > ema21
            short_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 >= prev_ema21 and ema9 < ema21

        long_n += 1 if long_sig else 0
        short_n += 1 if short_sig else 0

    return long_n, short_n, long_n + short_n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--variant', required=True)
    ap.add_argument('--dataset-meta', required=True)
    ap.add_argument('--gate-config', default='config/feasibility_gates.json')
    args = ap.parse_args()

    spec = _load(args.strategy_spec)
    variant = next(v for v in spec.get('variants', []) if v.get('name') == args.variant)
    meta = _load(args.dataset_meta)
    tf = str(meta.get('timeframe', '')).lower()

    gates = _load(ROOT / args.gate_config)
    min_bars = int(gates.get('min_bars', {}).get(tf, 1000))
    min_signals = int(gates.get('min_signals', {}).get(tf, 10))

    csv_path = Path(args.dataset_meta.replace('.meta.json', '.csv'))
    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8-sig', newline='')))
    closes = [float(r['close']) for r in rows]

    bars_available = len(closes)
    bars_required = min_bars

    required_fields_ok = isinstance(variant.get('risk_policy'), dict) and isinstance(variant.get('execution_policy'), dict)
    timeframe_ok = tf in ('1h', '4h')
    history_ok = bars_available >= bars_required

    parameter_ranges_ok = True
    rp = variant.get('risk_policy', {}) if isinstance(variant.get('risk_policy'), dict) else {}
    if rp:
        if float(rp.get('stop_atr_mult', 0)) < 0 or float(rp.get('tp_atr_mult', 0)) < 0:
            parameter_ranges_ok = False

    long_n, short_n, total_n = _estimate_signals(closes, variant)
    signal_frequency_estimate_ok = total_n >= min_signals

    fail_reasons = []
    suggestion = []
    if not timeframe_ok:
        fail_reasons.append('unsupported timeframe')
        suggestion.append('use 1h or 4h dataset')
    if not history_ok:
        fail_reasons.append('insufficient history')
        suggestion.append('use longer history dataset')
    if not required_fields_ok:
        fail_reasons.append('missing risk_policy or execution_policy')
        suggestion.append('emit StrategySpec schema v1.1+')
    if not signal_frequency_estimate_ok:
        fail_reasons.append('estimated signals below threshold')
        suggestion.append('relax threshold or remove filter')
    if not parameter_ranges_ok:
        fail_reasons.append('invalid parameter ranges')
        suggestion.append('fix negative/invalid risk params')

    verdict = 'PASS' if not fail_reasons else 'FAIL'

    payload = {
        'schema_version': '1.0',
        'id': f"feas_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'inputs': {
            'strategy_spec_path': args.strategy_spec,
            'variant_name': args.variant,
            'dataset_meta_path': args.dataset_meta,
        },
        'checks': {
            'history_ok': history_ok,
            'timeframe_ok': timeframe_ok,
            'signal_frequency_estimate_ok': signal_frequency_estimate_ok,
            'parameter_ranges_ok': parameter_ranges_ok,
            'required_fields_ok': required_fields_ok,
        },
        'metrics': {
            'bars_available': bars_available,
            'bars_required': bars_required,
            'estimated_signal_count': {'long': long_n, 'short': short_n, 'total': total_n},
            'estimated_trades_min': total_n,
        },
        'verdict': verdict,
        'fail_reasons': fail_reasons[:10],
        'suggestion': suggestion[:5],
    }

    out_dir = ROOT / 'artifacts' / 'feasibility' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{payload['id']}.feasibility_report.json"
    out_path.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')

    print(json.dumps({'feasibility_report_path': str(out_path), 'verdict': verdict, 'fail_reasons': payload['fail_reasons']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
