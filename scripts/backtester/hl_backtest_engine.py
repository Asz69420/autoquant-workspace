#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def parse_rules(lines: list[str]) -> dict[str, float]:
    out = {}
    for line in lines:
        if '=' in line:
            k,v = line.split('=',1)
            out[k.strip()] = float(v.strip())
    return out


def ema(prev: float|None, price: float, period: int) -> float:
    a = 2.0/(period+1)
    return price if prev is None else (a*price + (1-a)*prev)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset-meta', required=True)
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--variant', default='HL_EMA9_21_ATR14_SL1p5_TP2')
    ap.add_argument('--initial-capital', type=float, default=10000.0)
    ap.add_argument('--fill-rule', default='bar_close', choices=['bar_close','next_open'])
    args = ap.parse_args()

    meta = json.loads(Path(args.dataset_meta).read_text(encoding='utf-8'))
    csv_path = Path(args.dataset_meta.replace('.meta.json', '.csv'))
    spec = json.loads(Path(args.strategy_spec).read_text(encoding='utf-8'))
    variant = next(v for v in spec['variants'] if v['name']==args.variant)
    rules = parse_rules(variant.get('risk_rules', []))
    atr_period = int(rules.get('atr_period', 14))
    sl_mult = float(rules.get('stop_atr_mult', 1.5))
    tp_mult = float(rules.get('take_profit_atr_mult', 2.0))

    rows = list(csv.DictReader(csv_path.open('r', encoding='utf-8-sig', newline='')))
    bars = [{
        'time': r['time'], 'open': float(r['open']), 'high': float(r['high']), 'low': float(r['low']), 'close': float(r['close']), 'volume': float(r.get('volume',0) or 0)
    } for r in rows]

    ema9 = ema21 = None
    prev_ema9 = prev_ema21 = None
    trs = []
    prev_close = None
    atr = None

    trades=[]
    pos=None

    for i,b in enumerate(bars):
        tr = max(b['high']-b['low'], abs(b['high']-(prev_close if prev_close is not None else b['close'])), abs(b['low']-(prev_close if prev_close is not None else b['close'])))
        trs.append(tr)
        if len(trs) > atr_period:
            trs.pop(0)
        atr = sum(trs)/len(trs)

        prev_ema9, prev_ema21 = ema9, ema21
        ema9 = ema(ema9, b['close'], 9)
        ema21 = ema(ema21, b['close'], 21)

        long_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 <= prev_ema21 and ema9 > ema21
        short_sig = prev_ema9 is not None and prev_ema21 is not None and prev_ema9 >= prev_ema21 and ema9 < ema21

        if pos is not None:
            # reversal first
            if (pos['side']=='long' and short_sig) or (pos['side']=='short' and long_sig):
                xp = b['close']
                pnl = (xp-pos['entry_price']) if pos['side']=='long' else (pos['entry_price']-xp)
                trades.append({'entry_time':pos['entry_time'],'entry_price':round(pos['entry_price'],8),'exit_time':b['time'],'exit_price':round(xp,8),'side':pos['side'],'qty':1.0,'pnl':round(pnl,8),'reason':'reversal','bars_held':max(1,i-pos['entry_idx']+1)})
                pos = {'side':'short' if pos['side']=='long' else 'long','entry_price':b['close'],'entry_time':b['time'],'entry_idx':i}
                prev_close = b['close']
                continue

            stop = pos['entry_price'] - sl_mult*atr if pos['side']=='long' else pos['entry_price'] + sl_mult*atr
            tp = pos['entry_price'] + tp_mult*atr if pos['side']=='long' else pos['entry_price'] - tp_mult*atr
            hit_sl = (b['low'] <= stop) if pos['side']=='long' else (b['high'] >= stop)
            hit_tp = (b['high'] >= tp) if pos['side']=='long' else (b['low'] <= tp)
            if hit_sl or hit_tp:
                reason='sl' if hit_sl else 'tp'
                if hit_sl and hit_tp:
                    reason='sl'
                xp = stop if reason=='sl' else tp
                pnl = (xp-pos['entry_price']) if pos['side']=='long' else (pos['entry_price']-xp)
                trades.append({'entry_time':pos['entry_time'],'entry_price':round(pos['entry_price'],8),'exit_time':b['time'],'exit_price':round(xp,8),'side':pos['side'],'qty':1.0,'pnl':round(pnl,8),'reason':reason,'bars_held':max(1,i-pos['entry_idx']+1)})
                pos=None

        if pos is None and (long_sig or short_sig):
            ep = b['close'] if args.fill_rule=='bar_close' else (bars[i+1]['open'] if i+1<len(bars) else b['close'])
            et = b['time'] if args.fill_rule=='bar_close' else (bars[i+1]['time'] if i+1<len(bars) else b['time'])
            pos={'side':'long' if long_sig else 'short','entry_price':ep,'entry_time':et,'entry_idx':i}

        prev_close = b['close']

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p>0]
    losses = [p for p in pnls if p<0]
    eq=0.0; peak=0.0; maxdd=0.0
    for p in pnls:
        eq += p; peak=max(peak,eq); maxdd=max(maxdd, peak-eq)

    total=len(trades)
    net=sum(pnls)
    result = {
        'schema_version':'1.0',
        'id': f"hl_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'inputs': {'dataset_meta': args.dataset_meta, 'dataset_csv': str(csv_path), 'strategy_spec': args.strategy_spec, 'variant': args.variant},
        'settings': {'entry_fill_rule': args.fill_rule, 'tie_break':'worst_case', 'fees':0},
        'results': {
            'net_profit': round(net,8),
            'net_profit_pct': round((net/args.initial_capital),8) if args.initial_capital else None,
            'total_trades': total,
            'win_rate': round((len(wins)/total),8) if total else 0.0,
            'profit_factor': round((sum(wins)/abs(sum(losses))) if losses else (999.0 if wins else 0.0),8),
            'max_drawdown': round(maxdd,8),
            'start_ts': meta.get('start'),
            'end_ts': meta.get('end')
        }
    }

    day = ROOT / 'artifacts' / 'backtests' / datetime.now().strftime('%Y%m%d')
    day.mkdir(parents=True, exist_ok=True)
    trade_path = day / f"{result['id']}.trade_list.json"
    bt_path = day / f"{result['id']}.backtest_result.json"
    trade_path.write_text(json.dumps({'schema_version':'1.0','id':result['id'],'created_at':result['created_at'],'trades':trades}, separators=(',',':')), encoding='utf-8')
    blob = json.dumps(result, separators=(',',':'))
    if len(blob.encode('utf-8')) > 80*1024:
        raise SystemExit('BACKTEST_RESULT_TOO_LARGE')
    bt_path.write_text(blob, encoding='utf-8')
    print(json.dumps({'trade_list':str(trade_path),'backtest_result':str(bt_path)}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
