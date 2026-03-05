import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace")
sys.path.insert(0, str(ROOT / 'scripts' / 'pipeline'))
from ppr_score import compute_ppr

p = ROOT / 'artifacts' / 'library' / 'TOP_CANDIDATES.json'
rows = json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else []
seen = set()
out = []
for r in rows:
    key = (r.get('strategy_spec_path', ''), r.get('variant_name', ''))
    if key in seen:
        continue
    seen.add(key)
    pf = float(r.get('profit_factor') or 0)
    dd = float(r.get('max_drawdown') or 0)
    dd_pct = (dd / 10000.0) * 100.0
    tr = int(r.get('trades') or 0)
    ppr = compute_ppr(profit_factor=pf, max_drawdown_pct=dd_pct, trade_count=tr)
    out.append({
        'strategy': Path(r.get('strategy_spec_path', '')).stem,
        'variant': r.get('variant_name', ''),
        'pf': round(pf, 3),
        'dd_pct': round(dd_pct, 2),
        'trades': tr,
        'ppr': ppr['score'],
        'decision': ppr['decision'],
    })
    if len(out) >= 12:
        break
print(json.dumps(out))
