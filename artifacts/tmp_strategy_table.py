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
    dd = float(x.get('max_drawdown') or 0.0)
    trades = int(x.get('trades') or 0)
    # approximate capital baseline used by engine
    net_pct = (net / 10000.0) * 100.0
    # win rate not present in run index; leave n/a
    win = None
    rows.append({
        'symbol': sym,
        'strategy': name,
        'tf': tf,
        'net': net,
        'net_pct': net_pct,
        'win': win,
        'pf': pf,
        'trades': trades,
        'dd': dd,
    })

# dedupe by symbol+strategy+tf keep best net
best = {}
for r in rows:
    k = (r['symbol'], r['strategy'], r['tf'])
    if k not in best or r['net'] > best[k]['net']:
        best[k] = r
rows = list(best.values())

asset_order = {'BTC': 0, 'ETH': 1}
rows.sort(key=lambda r: (asset_order.get(r['symbol'], 99), -r['net'], -r['pf']))
rows = rows[:30]

# print machine-readable for assistant
for r in rows[:20]:
    w = 'n/a' if r['win'] is None else f"{r['win']*100:.2f}%"
    print(f"{r['symbol']}|{r['strategy']}|{r['tf']}|{r['net']:.2f}|{r['net_pct']:.2f}%|{w}|{r['pf']:.3f}|{r['trades']}")
