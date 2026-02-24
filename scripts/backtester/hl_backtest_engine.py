#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, subprocess, sys, uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def parse_rules(lines: list[str]) -> dict[str, float]:
    out = {}
    for line in lines:
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = float(v.strip())
    return out


def ema(prev: float | None, price: float, period: int) -> float:
    a = 2.0 / (period + 1)
    return price if prev is None else (a * price + (1 - a) * prev)


def rsi_step(prev_close: float | None, close: float, avg_gain: float | None, avg_loss: float | None, period: int):
    if prev_close is None:
        return None, avg_gain, avg_loss
    ch = close - prev_close
    gain = max(ch, 0.0)
    loss = max(-ch, 0.0)
    if avg_gain is None or avg_loss is None:
        return None, gain, loss
    avg_gain = ((avg_gain * (period - 1)) + gain) / period
    avg_loss = ((avg_loss * (period - 1)) + loss) / period
    rs = (avg_gain / avg_loss) if avg_loss > 0 else 999.0
    return 100 - (100 / (1 + rs)), avg_gain, avg_loss


def apply_fill(raw_price: float, side: str, slippage_bps: float) -> tuple[float, float]:
    if side == 'buy':
        px = raw_price * (1 + slippage_bps / 10_000.0)
        return px, px - raw_price
    px = raw_price * (1 - slippage_bps / 10_000.0)
    return px, raw_price - px


def _min_trades_required(meta: dict, gates: dict) -> int:
    timeframe = str(meta.get('timeframe', '')).lower()
    start = meta.get('start')
    end = meta.get('end')
    if not timeframe or not start or not end:
        return 0
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except ValueError:
        return 0
    days = (end_dt - start_dt).days
    if days < 700:
        return 0
    return int(gates.get('min_trades', {}).get('2y', {}).get(timeframe, 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset-meta', required=True)
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--variant', required=True)
    ap.add_argument('--initial-capital', type=float, default=10000.0)
    ap.add_argument('--fill-rule', default='bar_close', choices=['bar_close', 'next_open'])
    ap.add_argument('--cost-config', default='config/backtest_costs.json')
    ap.add_argument('--gate-config', default='config/backtest_gates.json')
    ap.add_argument('--fee-mode', choices=['taker', 'maker'], default='')
    ap.add_argument('--slippage-bps', type=float, default=-1.0)
    args = ap.parse_args()

    meta = json.loads(Path(args.dataset_meta).read_text(encoding='utf-8'))
    csv_path = Path(args.dataset_meta.replace('.meta.json', '.csv'))
    spec = json.loads(Path(args.strategy_spec).read_text(encoding='utf-8'))
    variant = next(v for v in spec['variants'] if v['name'] == args.variant)
    rules = parse_rules(variant.get('risk_rules', []))
    costs = json.loads((ROOT / args.cost_config).read_text(encoding='utf-8'))
    gates = json.loads((ROOT / args.gate_config).read_text(encoding='utf-8')) if (ROOT / args.gate_config).exists() else {}

    fee_mode = args.fee_mode or costs.get('fee_mode', 'taker')
    fee_bps = float(costs.get('hl_taker_fee_bps', 4.5) if fee_mode == 'taker' else costs.get('hl_maker_fee_bps', 1.5))
    slippage_bps = args.slippage_bps if args.slippage_bps >= 0 else float(costs.get('hl_slippage_bps', 1.0))

    atr_period = int(rules.get('atr_period', 14))
    sl_mult = float(rules.get('stop_atr_mult', 1.5))
    tp_mult = float(rules.get('take_profit_atr_mult', 2.0))

    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8-sig', newline='')))
    bars = [{
        'time': r['time'], 'open': float(r['open']), 'high': float(r['high']), 'low': float(r['low']), 'close': float(r['close'])
    } for r in rows]

    # indicators
    ema9 = ema21 = ema50 = ema200 = None
    prev_ema9 = prev_ema21 = prev_ema50 = None
    prev_close = None
    avg_gain = avg_loss = None
    rsi = None
    trs = []
    atr = None

    is_trendpullback = 'trendpullback' in args.variant.lower()
    ema_trend = int(rules.get('ema_trend', 200))
    ema_slope = int(rules.get('ema_slope', 50))
    rsi_period = int(rules.get('rsi_period', 14))
    rsi_long_max = float(rules.get('rsi_long_max', 40))
    rsi_short_min = float(rules.get('rsi_short_min', 60))

    trades = []
    pos = None
    total_fees_paid = 0.0
    total_slippage_cost_est = 0.0
    signals_seen_long = 0
    signals_seen_short = 0
    entries_taken = 0
    exits_taken = 0
    total_bars_in_position = 0

    for i, b in enumerate(bars):
        tr = max(b['high'] - b['low'], abs(b['high'] - (prev_close if prev_close is not None else b['close'])), abs(b['low'] - (prev_close if prev_close is not None else b['close'])))
        trs.append(tr)
        if len(trs) > atr_period:
            trs.pop(0)
        atr = sum(trs) / len(trs)

        prev_ema9, prev_ema21, prev_ema50 = ema9, ema21, ema50
        ema9 = ema(ema9, b['close'], 9)
        ema21 = ema(ema21, b['close'], 21)
        ema50 = ema(ema50, b['close'], ema_slope)
        ema200 = ema(ema200, b['close'], ema_trend)

        rsi, avg_gain, avg_loss = rsi_step(prev_close, b['close'], avg_gain, avg_loss, rsi_period)

        if is_trendpullback:
            ema50_up = prev_ema50 is not None and ema50 > prev_ema50
            ema50_dn = prev_ema50 is not None and ema50 < prev_ema50
            long_sig = (ema200 is not None and b['close'] > ema200 and ema50_up and rsi is not None and rsi < rsi_long_max)
            short_sig = (ema200 is not None and b['close'] < ema200 and ema50_dn and rsi is not None and rsi > rsi_short_min)
        else:
            long_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 <= prev_ema21 and ema9 > ema21
            short_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 >= prev_ema21 and ema9 < ema21

        if long_sig:
            signals_seen_long += 1
        if short_sig:
            signals_seen_short += 1
        if pos is not None:
            total_bars_in_position += 1

        def close_position(raw_exit_price: float, reason: str):
            nonlocal pos, total_fees_paid, total_slippage_cost_est, exits_taken
            if pos is None:
                return
            qty = 1.0
            exit_side = 'sell' if pos['side'] == 'long' else 'buy'
            exit_px, exit_slip = apply_fill(raw_exit_price, exit_side, slippage_bps)
            total_slippage_cost_est += exit_slip * qty
            gross = ((exit_px - pos['entry_price']) if pos['side'] == 'long' else (pos['entry_price'] - exit_px)) * qty
            fees = (pos['entry_price'] * qty + exit_px * qty) * (fee_bps / 10_000.0)
            total_fees_paid += fees
            pnl = gross - fees
            trades.append({'entry_time': pos['entry_time'], 'entry_price': round(pos['entry_price'], 8), 'exit_time': b['time'], 'exit_price': round(exit_px, 8), 'side': pos['side'], 'qty': qty, 'pnl': round(pnl, 8), 'reason': reason, 'bars_held': max(1, i - pos['entry_idx'] + 1)})
            exits_taken += 1
            pos = None

        if pos is not None:
            if (pos['side'] == 'long' and short_sig) or (pos['side'] == 'short' and long_sig):
                close_position(b['close'], 'reversal')
                eside = 'sell' if short_sig else 'buy'
                ep, eslip = apply_fill(b['close'], eside, slippage_bps)
                total_slippage_cost_est += eslip
                pos = {'side': 'short' if short_sig else 'long', 'entry_price': ep, 'entry_time': b['time'], 'entry_idx': i}
                entries_taken += 1
                prev_close = b['close']
                continue

            stop = pos['entry_price'] - sl_mult * atr if pos['side'] == 'long' else pos['entry_price'] + sl_mult * atr
            tp = pos['entry_price'] + tp_mult * atr if pos['side'] == 'long' else pos['entry_price'] - tp_mult * atr
            hit_sl = (b['low'] <= stop) if pos['side'] == 'long' else (b['high'] >= stop)
            hit_tp = (b['high'] >= tp) if pos['side'] == 'long' else (b['low'] <= tp)
            if hit_sl or hit_tp:
                reason = 'sl' if hit_sl else 'tp'
                if hit_sl and hit_tp:
                    reason = 'sl'
                close_position(stop if reason == 'sl' else tp, reason)

        if pos is None and (long_sig or short_sig):
            raw_ep = b['close'] if args.fill_rule == 'bar_close' else (bars[i + 1]['open'] if i + 1 < len(bars) else b['close'])
            et = b['time'] if args.fill_rule == 'bar_close' else (bars[i + 1]['time'] if i + 1 < len(bars) else b['time'])
            eside = 'buy' if long_sig else 'sell'
            ep, eslip = apply_fill(raw_ep, eside, slippage_bps)
            total_slippage_cost_est += eslip
            pos = {'side': 'long' if long_sig else 'short', 'entry_price': ep, 'entry_time': et, 'entry_idx': i}
            entries_taken += 1

        prev_close = b['close']

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    eq = peak = maxdd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        maxdd = max(maxdd, peak - eq)

    total = len(trades)
    net = sum(pnls)
    bars_tested = len(bars)
    avg_bars_in_trade = (sum(t['bars_held'] for t in trades) / total) if total else 0.0
    coverage = {
        'bars_tested': bars_tested,
        'time_in_market_pct': round((total_bars_in_position / bars_tested), 8) if bars_tested else 0.0,
        'avg_bars_in_trade': round(avg_bars_in_trade, 8),
        'entry_signals_seen': {
            'long': signals_seen_long,
            'short': signals_seen_short,
            'total': signals_seen_long + signals_seen_short,
        },
        'entries_taken': entries_taken,
        'exits_taken': exits_taken,
    }
    min_trades_required = _min_trades_required(meta, gates)
    gate_pass = total >= min_trades_required if min_trades_required > 0 else True
    gate_reason = 'OK' if gate_pass else 'INSUFFICIENT_TRADES'

    result = {
        'schema_version': '1.0',
        'id': f"hl_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'inputs': {'dataset_meta': args.dataset_meta, 'dataset_csv': str(csv_path), 'strategy_spec': args.strategy_spec, 'variant': args.variant},
        'settings': {'entry_fill_rule': args.fill_rule, 'tie_break': 'worst_case', 'fee_mode': fee_mode, 'fee_bps': fee_bps, 'slippage_bps': slippage_bps},
        'results': {
            'net_profit': round(net, 8),
            'net_profit_pct': round((net / args.initial_capital), 8) if args.initial_capital else None,
            'total_trades': total,
            'win_rate': round((len(wins) / total), 8) if total else 0.0,
            'profit_factor': round((sum(wins) / abs(sum(losses))) if losses else (999.0 if wins else 0.0), 8),
            'max_drawdown': round(maxdd, 8),
            'total_fees_paid': round(total_fees_paid, 8),
            'total_slippage_cost_est': round(total_slippage_cost_est, 8),
            'start_ts': meta.get('start'),
            'end_ts': meta.get('end')
        },
        'coverage': coverage,
        'gate': {
            'min_trades_required': min_trades_required,
            'gate_pass': gate_pass,
            'gate_reason': gate_reason,
        }
    }

    day = ROOT / 'artifacts' / 'backtests' / datetime.now().strftime('%Y%m%d')
    day.mkdir(parents=True, exist_ok=True)
    trade_path = day / f"{result['id']}.trade_list.json"
    bt_path = day / f"{result['id']}.backtest_result.json"
    trade_path.write_text(json.dumps({'schema_version': '1.0', 'id': result['id'], 'created_at': result['created_at'], 'trades': trades}, separators=(',', ':')), encoding='utf-8')
    blob = json.dumps(result, separators=(',', ':'))
    if len(blob.encode('utf-8')) > 80 * 1024:
        raise SystemExit('BACKTEST_RESULT_TOO_LARGE')
    bt_path.write_text(blob, encoding='utf-8')

    relax_suggestion_path = None
    if not gate_pass:
        cmd = [
            sys.executable,
            str((ROOT / 'scripts/pipeline/emit_relax_suggestion.py').resolve()),
            '--strategy-spec-path', args.strategy_spec,
            '--variant', args.variant,
            '--symbol', str(meta.get('symbol', 'unknown')),
            '--timeframe', str(meta.get('timeframe', 'unknown')),
            '--start', str(meta.get('start', '')),
            '--end', str(meta.get('end', '')),
            '--observed-trades', str(total),
            '--min-trades-required', str(min_trades_required),
            '--id', result['id'],
        ]
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
        relax_suggestion_path = json.loads(p.stdout)['relax_suggestion_path']

    out = {'trade_list': str(trade_path), 'backtest_result': str(bt_path)}
    if relax_suggestion_path:
        out['relax_suggestion_path'] = relax_suggestion_path
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
