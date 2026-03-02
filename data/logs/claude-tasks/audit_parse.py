import json, os, glob

base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228'
bt_files = glob.glob(os.path.join(base, '*.backtest_result.json'))
results = []
for f in bt_files:
    try:
        d = json.load(open(f))
        r = d.get('results', d)
        h = os.path.basename(f).replace('.backtest_result.json', '')
        pf = r.get('profit_factor', 0)
        trades = r.get('total_trades', 0)
        results.append({'hash': h, 'pf': pf, 'trades': trades})
    except:
        pass
results.sort(key=lambda x: x['pf'], reverse=True)
print('TOP 30 BY PF:')
for r in results[:30]:
    print(f'  {r["hash"]}  PF={r["pf"]}  T={r["trades"]}')
print(f'Total={len(results)}')
zeros = [r for r in results if r['trades'] == 0]
print(f'ZeroTrade={len(zeros)}')
for r in zeros:
    print(f'  ZERO: {r["hash"]}')
low = [r for r in results if 0 < r['trades'] <= 5]
print(f'VeryLow(1-5)={len(low)}')
for r in low:
    print(f'  LOW: {r["hash"]}  PF={r["pf"]}  T={r["trades"]}')
