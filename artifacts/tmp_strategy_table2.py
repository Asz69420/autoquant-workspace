import json
from pathlib import Path

p = Path('artifacts/library/RUN_INDEX.json')
arr = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []

rows = []
for x in arr:
    dsets = x.get('datasets_tested') or []
    if not dsets:
        continue
    ds = dsets[0] if isinstance(dsets, list) and dsets else {}
    sym = str(ds.get('symbol') or '?')
    tf = str(ds.get('timeframe') or '?')
    name = str(x.get('variant_name') or '?')
    net = float(x.get('net_profit') or 0.0)
    pf = float(x.get('profit_factor') or 0.0)
    trades = int(x.get('trades') or 0)
    bt = str(x.get('pointers', {}).get('backtest_result') or '')
    win = None
    if bt:
        bp = Path(bt)
        if bp.exists():
            try:
                bj = json.loads(bp.read_text(encoding='utf-8'))
                w = bj.get('results', {}).get('win_rate')
                if w is not None:
                    win = float(w) * 100.0
            except Exception:
                pass
    net_pct = (net / 10000.0) * 100.0
    rows.append({
        'symbol': sym, 'strategy': name, 'tf': tf,
        'net': net, 'net_pct': net_pct, 'win': win, 'pf': pf, 'trades': trades,
    })

best = {}
for r in rows:
    k = (r['symbol'], r['strategy'], r['tf'])
    if k not in best or r['net'] > best[k]['net']:
        best[k] = r
rows = list(best.values())

assets = ['BTC', 'ETH']
out = []
for a in assets:
    subset = [r for r in rows if r['symbol'] == a]
    subset.sort(key=lambda r: (-r['net'], -r['pf']))
    out.extend(subset[:8])

for r in out:
    win = 'n/a' if r['win'] is None else f"{r['win']:.2f}%"
    print(f"{r['symbol']}|{r['strategy']}|{r['tf']}|{r['net']:.2f}|{r['net_pct']:.2f}%|{win}|{r['pf']:.3f}|{r['trades']}")
