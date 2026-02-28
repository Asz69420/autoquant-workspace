#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, subprocess, sys, uuid
from datetime import UTC, datetime
from pathlib import Path

import contextlib
import io
import pandas as pd

from signal_templates import resolve_template, get_signals

try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pandas_ta as pta
except Exception:
    pta = None

ROOT = Path(__file__).resolve().parents[2]


INDICATOR_REGISTRY: dict[str, dict] = {
    'EMA': {'engine': 'pandas_ta', 'columns': ['EMA_9', 'EMA_21', 'EMA_50', 'EMA_200']},
    'SMA': {'engine': 'pandas_ta', 'columns': ['SMA_20', 'SMA_50', 'SMA_200']},
    'T3': {'engine': 'pandas_ta', 'columns': ['T3_10_0.7']},
    'KAMA': {'engine': 'pandas_ta', 'columns': ['KAMA_10_2_30']},
    'ALMA': {'engine': 'pandas_ta', 'columns': ['ALMA_9_6.0_0.85']},
    'RSI': {'engine': 'pandas_ta', 'columns': ['RSI_14']},
    'QQE': {'engine': 'pandas_ta', 'columns': ['QQE_14_5_4.236']},
    'ATR': {'engine': 'pandas_ta', 'columns': ['ATR_14']},
    'MACD': {'engine': 'pandas_ta', 'columns': ['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']},
    'STC': {'engine': 'pandas_ta', 'columns': ['STC_10_12_26_0.5']},
    'Bollinger Bands': {'engine': 'pandas_ta', 'columns': ['BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0']},
    'Stochastic': {'engine': 'pandas_ta', 'columns': ['STOCHk_14_3_3', 'STOCHd_14_3_3']},
    'ADX': {'engine': 'pandas_ta', 'columns': ['ADX_14']},
    'Choppiness Index': {'engine': 'pandas_ta', 'columns': ['CHOP_14_1_100']},
    'Vortex': {'engine': 'pandas_ta', 'columns': ['VTXP_14', 'VTXM_14']},
    'Stiffness': {'engine': 'pandas_ta', 'columns': ['STIFFNESS_20_3_100']},
    'CCI': {'engine': 'pandas_ta', 'columns': ['CCI_20_0.015']},
    'Williams %R': {'engine': 'pandas_ta', 'columns': ['WILLR_14']},
    'OBV': {'engine': 'pandas_ta', 'columns': ['OBV']},
    'VWAP': {'engine': 'pandas_ta', 'columns': ['VWAP_D']},
    'Ichimoku': {'engine': 'pandas_ta', 'columns': ['ISA_9', 'ISB_26', 'ITS_9', 'IKS_26']},
    'Supertrend': {'engine': 'pandas_ta', 'columns': ['SUPERT_7_3.0', 'SUPERTd_7_3.0']},
    'Donchian Channels': {'engine': 'pandas_ta', 'columns': ['DCL_20_20', 'DCM_20_20', 'DCU_20_20']},
}


def build_indicator_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if pta is None:
        return out
    v = out['volume'] if 'volume' in out.columns else pd.Series(1.0, index=out.index)

    def _safe_apply(name: str, fn):
        nonlocal out
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                val = fn()
            if isinstance(val, pd.Series):
                out[name] = val
            elif isinstance(val, pd.DataFrame) and not val.empty:
                out = out.join(val)
        except Exception as e:
            print(f"WARN indicator_compute_failed={name} err={str(e)[:120]}", file=sys.stderr)

    _safe_apply('EMA_9', lambda: pta.ema(out['close'], length=9))
    _safe_apply('EMA_21', lambda: pta.ema(out['close'], length=21))
    _safe_apply('EMA_50', lambda: pta.ema(out['close'], length=50))
    _safe_apply('EMA_200', lambda: pta.ema(out['close'], length=200))
    _safe_apply('SMA_20', lambda: pta.sma(out['close'], length=20))
    _safe_apply('SMA_50', lambda: pta.sma(out['close'], length=50))
    _safe_apply('SMA_200', lambda: pta.sma(out['close'], length=200))
    _safe_apply('T3_10_0.7', lambda: pta.t3(out['close'], length=10, a=0.7))
    _safe_apply('KAMA_10_2_30', lambda: pta.kama(out['close'], length=10, fast=2, slow=30))
    _safe_apply('ALMA_9_6.0_0.85', lambda: pta.alma(out['close'], length=9, sigma=6.0, distribution_offset=0.85))
    _safe_apply('RSI_14', lambda: pta.rsi(out['close'], length=14))
    _safe_apply('ATR_14', lambda: pta.atr(out['high'], out['low'], out['close'], length=14))
    _safe_apply('MACD', lambda: pta.macd(out['close'], fast=12, slow=26, signal=9))
    _safe_apply('STC', lambda: pta.stc(out['close'], tclength=10, fast=12, slow=26, factor=0.5))
    _safe_apply('QQE', lambda: pta.qqe(out['close'], length=14, smooth=5, factor=4.236))
    _safe_apply('BBANDS', lambda: pta.bbands(out['close'], length=20, std=2.0))
    _safe_apply('STOCH', lambda: pta.stoch(out['high'], out['low'], out['close'], k=14, d=3, smooth_k=3))
    _safe_apply('ADX', lambda: pta.adx(out['high'], out['low'], out['close'], length=14))
    _safe_apply('CHOP_14_1_100', lambda: pta.chop(out['high'], out['low'], out['close'], length=14, atr_length=1, scalar=100))
    _safe_apply('VORTEX', lambda: pta.vortex(out['high'], out['low'], out['close'], length=14))
    _safe_apply('STIFFNESS_20_3_100', lambda: pta.stiffness(out['close'], length=20, ma_length=3, stiff_length=100))
    _safe_apply('CCI_20_0.015', lambda: pta.cci(out['high'], out['low'], out['close'], length=20))
    _safe_apply('WILLR_14', lambda: pta.willr(out['high'], out['low'], out['close'], length=14))
    _safe_apply('OBV', lambda: pta.obv(out['close'], v))

    out['VWAP_D'] = pd.NA
    _safe_apply('ICHIMOKU', lambda: pta.ichimoku(out['high'], out['low'], out['close'])[0] if isinstance(pta.ichimoku(out['high'], out['low'], out['close']), tuple) else None)
    _safe_apply('SUPERTREND', lambda: pta.supertrend(out['high'], out['low'], out['close'], length=7, multiplier=3.0))
    _safe_apply('DONCHIAN', lambda: pta.donchian(out['high'], out['low'], lower_length=20, upper_length=20))
    return out


def parse_rules(lines: list[str]) -> dict[str, float]:
    out = {}
    for line in lines:
        if '=' in line:
            k, v = line.split('=', 1)
            try:
                out[k.strip()] = float(v.strip())
            except ValueError:
                continue
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


def _classify_regime_from_adx(adx_value: float | None) -> str:
    if adx_value is None:
        return 'transitional'
    if adx_value > 25.0:
        return 'trending'
    if adx_value < 20.0:
        return 'ranging'
    return 'transitional'


def _safe_pf(wins: float, losses_abs: float) -> float:
    if losses_abs > 0.0:
        return wins / losses_abs
    return 999.0 if wins > 0.0 else 0.0


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
    template_name = resolve_template(variant)
    variant_params = {}
    for p in variant.get('parameters', []):
        if isinstance(p, dict) and 'name' in p and 'default' in p:
            variant_params[p['name']] = p['default']
    rules = parse_rules(variant.get('risk_rules', []))
    for k, v in rules.items():
        variant_params[k] = v
    if not isinstance(variant.get('risk_policy'), dict) or not isinstance(variant.get('execution_policy'), dict):
        raise SystemExit('reason_code=STRATEGYSPEC_MISSING_RISK_POLICY')

    risk_policy = variant['risk_policy']
    execution_policy = variant['execution_policy']
    cost_config_path = ROOT / args.cost_config
    costs = json.loads(cost_config_path.read_text(encoding='utf-8'))
    fee_model_hash = hashlib.sha256(cost_config_path.read_bytes()).hexdigest()
    gates = json.loads((ROOT / args.gate_config).read_text(encoding='utf-8')) if (ROOT / args.gate_config).exists() else {}

    fee_mode = args.fee_mode or costs.get('fee_mode', 'taker')
    fee_bps = float(costs.get('hl_taker_fee_bps', 4.5) if fee_mode == 'taker' else costs.get('hl_maker_fee_bps', 1.5))
    slippage_bps = args.slippage_bps if args.slippage_bps >= 0 else float(costs.get('hl_slippage_bps', 1.0))

    atr_period = int(rules.get('atr_period', 14))
    stop_type = str(risk_policy.get('stop_type', 'none'))
    tp_type = str(risk_policy.get('tp_type', 'none'))
    sl_mult = float(risk_policy.get('stop_atr_mult', 0.0)) if stop_type == 'atr' else 0.0
    tp_mult = float(risk_policy.get('tp_atr_mult', 0.0)) if tp_type == 'atr' else 0.0

    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8-sig', newline='')))
    bars = [{
        'time': r['time'], 'open': float(r['open']), 'high': float(r['high']), 'low': float(r['low']), 'close': float(r['close']), 'volume': float(r.get('volume', 1.0) or 1.0)
    } for r in rows]

    df = pd.DataFrame(bars)
    ind_df = build_indicator_frame(df)

    # indicators
    ema9 = ema21 = ema50 = ema200 = None
    prev_ema9 = prev_ema21 = prev_ema50 = None
    prev_close = None
    avg_gain = avg_loss = None
    rsi = None
    trs = []
    atr = None

    entry_fill = str(execution_policy.get('entry_fill', args.fill_rule))
    tie_break = str(execution_policy.get('tie_break', 'worst_case'))
    allow_reverse = bool(execution_policy.get('allow_reverse', True))

    rsi_period = int(rules.get('rsi_period', 14))

    trades = []
    pos = None
    total_fees_paid = 0.0
    adx_series: list[float | None] = []
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
        atr_fallback = sum(trs) / len(trs)

        prev_ema9, prev_ema21, prev_ema50 = ema9, ema21, ema50
        ema9 = ema(ema9, b['close'], 9)
        ema21 = ema(ema21, b['close'], 21)
        ema50 = ema(ema50, b['close'], 50)
        ema200 = ema(ema200, b['close'], 200)

        rsi, avg_gain, avg_loss = rsi_step(prev_close, b['close'], avg_gain, avg_loss, rsi_period)

        # Prefer pandas-ta indicators when present; fallback to legacy custom calculations.
        adx_val = None
        try:
            rowi = ind_df.iloc[i]
            for nm, var in [('EMA_9', 'ema9'), ('EMA_21', 'ema21'), ('EMA_50', 'ema50'), ('EMA_200', 'ema200')]:
                val = rowi.get(nm)
                if pd.notna(val):
                    if var == 'ema9':
                        ema9 = float(val)
                    elif var == 'ema21':
                        ema21 = float(val)
                    elif var == 'ema50':
                        ema50 = float(val)
                    elif var == 'ema200':
                        ema200 = float(val)
            rv = rowi.get('RSI_14')
            if pd.notna(rv):
                rsi = float(rv)
            av = rowi.get('ATR_14')
            atr = float(av) if pd.notna(av) else atr_fallback
            adx_raw = rowi.get('ADX_14')
            if pd.notna(adx_raw):
                adx_val = float(adx_raw)
        except Exception:
            atr = atr_fallback
            adx_val = None
        adx_series.append(adx_val)

        long_sig, short_sig = get_signals(template_name, ind_df, i, variant_params)

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
            trades.append({'entry_time': pos['entry_time'], 'entry_price': round(pos['entry_price'], 8), 'exit_time': b['time'], 'exit_price': round(exit_px, 8), 'side': pos['side'], 'qty': qty, 'pnl': round(pnl, 8), 'pnl_pct': round((pnl / pos['entry_price']) * 100, 4), 'reason': reason, 'bars_held': max(1, i - pos['entry_idx'] + 1), 'entry_regime': pos.get('entry_regime', 'transitional'), 'entry_adx': (round(float(pos['entry_adx']), 8) if pos.get('entry_adx') is not None else None)})
            exits_taken += 1
            pos = None

        if pos is not None:
            if allow_reverse and ((pos['side'] == 'long' and short_sig) or (pos['side'] == 'short' and long_sig)):
                close_position(b['close'], 'reversal')
                eside = 'sell' if short_sig else 'buy'
                ep, eslip = apply_fill(b['close'], eside, slippage_bps)
                total_slippage_cost_est += eslip
                regime = _classify_regime_from_adx(adx_series[i] if i < len(adx_series) else None)
                pos = {'side': 'short' if short_sig else 'long', 'entry_price': ep, 'entry_time': b['time'], 'entry_idx': i, 'entry_regime': regime, 'entry_adx': (adx_series[i] if i < len(adx_series) else None)}
                entries_taken += 1
                prev_close = b['close']
                continue

            stop = pos['entry_price'] - sl_mult * atr if (stop_type == 'atr' and pos['side'] == 'long') else (pos['entry_price'] + sl_mult * atr if stop_type == 'atr' else None)
            tp = pos['entry_price'] + tp_mult * atr if (tp_type == 'atr' and pos['side'] == 'long') else (pos['entry_price'] - tp_mult * atr if tp_type == 'atr' else None)
            hit_sl = ((b['low'] <= stop) if pos['side'] == 'long' else (b['high'] >= stop)) if stop is not None else False
            hit_tp = ((b['high'] >= tp) if pos['side'] == 'long' else (b['low'] <= tp)) if tp is not None else False
            if hit_sl or hit_tp:
                reason = 'sl' if hit_sl else 'tp'
                if hit_sl and hit_tp:
                    if tie_break in ('tp_first', 'best_case'):
                        reason = 'tp'
                    else:
                        reason = 'sl'
                close_position((stop if reason == 'sl' else tp), reason)

        if pos is None and (long_sig or short_sig):
            raw_ep = b['close'] if entry_fill == 'bar_close' else (bars[i + 1]['open'] if i + 1 < len(bars) else b['close'])
            et = b['time'] if entry_fill == 'bar_close' else (bars[i + 1]['time'] if i + 1 < len(bars) else b['time'])
            eside = 'buy' if long_sig else 'sell'
            ep, eslip = apply_fill(raw_ep, eside, slippage_bps)
            total_slippage_cost_est += eslip
            regime = _classify_regime_from_adx(adx_series[i] if i < len(adx_series) else None)
            pos = {'side': 'long' if long_sig else 'short', 'entry_price': ep, 'entry_time': et, 'entry_idx': i, 'entry_regime': regime, 'entry_adx': (adx_series[i] if i < len(adx_series) else None)}
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

    regime_counts = {'trending': 0, 'ranging': 0, 'transitional': 0}
    regime_wins = {'trending': 0.0, 'ranging': 0.0, 'transitional': 0.0}
    regime_losses_abs = {'trending': 0.0, 'ranging': 0.0, 'transitional': 0.0}
    regime_trade_counts = {'trending': 0, 'ranging': 0, 'transitional': 0}
    regime_win_counts = {'trending': 0, 'ranging': 0, 'transitional': 0}
    for t in trades:
        rg = str(t.get('entry_regime') or 'transitional').lower()
        if rg not in regime_counts:
            rg = 'transitional'
        regime_counts[rg] += 1
        regime_trade_counts[rg] += 1
        pnl = float(t.get('pnl', 0.0) or 0.0)
        if pnl > 0:
            regime_wins[rg] += pnl
            regime_win_counts[rg] += 1
        elif pnl < 0:
            regime_losses_abs[rg] += abs(pnl)

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
        'fee_model_hash': fee_model_hash,
        'settings': {'entry_fill_rule': entry_fill, 'tie_break': tie_break, 'fee_mode': fee_mode, 'fee_bps': fee_bps, 'slippage_bps': slippage_bps, 'cost_config_path': str(cost_config_path), 'fee_model_hash': fee_model_hash},
        'indicator_registry': INDICATOR_REGISTRY,
        'results': {
            'net_profit': round(net, 8),
            'net_profit_pct': round((net / args.initial_capital), 8) if args.initial_capital else None,
            'total_trades': total,
            'win_rate': round((len(wins) / total), 8) if total else 0.0,
            'profit_factor': round((sum(wins) / abs(sum(losses))) if losses else (999.0 if wins else 0.0), 8),
            'max_drawdown': round(maxdd, 8),
            'max_drawdown_pct': round((maxdd / peak * 100) if peak > 0 else 0.0, 4),
            'total_return_pct': round((eq / abs(trades[0]['entry_price']) * 100) if trades and trades[0]['entry_price'] != 0 else 0.0, 4),
            'avg_trade_pnl_pct': round((sum(t['pnl'] / t['entry_price'] * 100 for t in trades) / len(trades)) if trades else 0.0, 4),
            'total_fees_paid': round(total_fees_paid, 8),
            'total_slippage_cost_est': round(total_slippage_cost_est, 8),
            'start_ts': meta.get('start'),
            'end_ts': meta.get('end'),
            'regime_breakdown': {
                'trending_trades': int(regime_counts['trending']),
                'ranging_trades': int(regime_counts['ranging']),
                'transitional_trades': int(regime_counts['transitional']),
            },
            'regime_pf': {
                'trending': round(_safe_pf(regime_wins['trending'], regime_losses_abs['trending']), 8),
                'ranging': round(_safe_pf(regime_wins['ranging'], regime_losses_abs['ranging']), 8),
                'transitional': round(_safe_pf(regime_wins['transitional'], regime_losses_abs['transitional']), 8),
            },
            'regime_wr': {
                'trending': round((regime_win_counts['trending'] / regime_trade_counts['trending']) if regime_trade_counts['trending'] else 0.0, 8),
                'ranging': round((regime_win_counts['ranging'] / regime_trade_counts['ranging']) if regime_trade_counts['ranging'] else 0.0, 8),
                'transitional': round((regime_win_counts['transitional'] / regime_trade_counts['transitional']) if regime_trade_counts['transitional'] else 0.0, 8),
            },
            'dominant_regime': max(regime_counts, key=lambda k: regime_counts[k]) if total else 'transitional'
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
