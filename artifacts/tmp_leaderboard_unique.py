import json
from pathlib import Path

p = Path('artifacts/library/TOP_CANDIDATES.json')
arr = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
best = {}
for x in arr:
    k = x.get('variant_name','?')
    s = float(x.get('score', -1e9) or -1e9)
    if k not in best or s > float(best[k].get('score', -1e9) or -1e9):
        best[k] = x
rows = sorted(best.values(), key=lambda x: float(x.get('score', -1e9) or -1e9), reverse=True)[:10]
for i, x in enumerate(rows, 1):
    print(f"{i}. {x.get('variant_name','?')} ; PF={x.get('profit_factor','?')} ; Net={x.get('net_profit','?')} ; DD={x.get('max_drawdown','?')} ; Trades={x.get('trades','?')} ; Score={x.get('score','?')}")
