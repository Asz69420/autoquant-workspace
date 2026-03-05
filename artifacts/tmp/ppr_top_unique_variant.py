import json, sys
from pathlib import Path
ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace")
sys.path.insert(0, str(ROOT / 'scripts' / 'pipeline'))
from ppr_score import compute_ppr
rows = json.loads((ROOT / 'artifacts' / 'library' / 'TOP_CANDIDATES.json').read_text(encoding='utf-8-sig'))
best = {}
for r in rows:
    v = str(r.get('variant_name') or 'unknown')
    pf=float(r.get('profit_factor') or 0)
    dd_pct=(float(r.get('max_drawdown') or 0)/10000.0)*100.0
    tr=int(r.get('trades') or 0)
    ppr=compute_ppr(profit_factor=pf,max_drawdown_pct=dd_pct,trade_count=tr)
    cur=best.get(v)
    rec={
      'variant': v,
      'strategy': Path(r.get('strategy_spec_path','')).stem,
      'pf': round(pf,3),
      'dd_pct': round(dd_pct,2),
      'trades': tr,
      'ppr': ppr['score'],
      'decision': ppr['decision']
    }
    if cur is None or rec['ppr']>cur['ppr']:
      best[v]=rec
out=sorted(best.values(), key=lambda x: x['ppr'], reverse=True)[:10]
print(json.dumps(out))
