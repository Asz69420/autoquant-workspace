import json
from pathlib import Path

p = Path('artifacts/library/TOP_CANDIDATES.json')
if not p.exists():
    print('NO_TOP_CANDIDATES')
    raise SystemExit(0)
arr = json.loads(p.read_text(encoding='utf-8'))
for i, x in enumerate(arr[:10], 1):
    print(f"{i}. {x.get('variant_name','?')} ; PF={x.get('profit_factor','?')} ; Net={x.get('net_profit','?')} ; DD={x.get('max_drawdown','?')} ; Trades={x.get('trades','?')} ; Score={x.get('score','?')}")
