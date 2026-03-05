import json
from pathlib import Path
ROOT=Path(r"C:\Users\Clamps\.openclaw\workspace")
run_idx=ROOT/'artifacts'/'library'/'RUN_INDEX.json'
pas_idx=ROOT/'artifacts'/'library'/'PASSED_INDEX.json'
prom_idx=ROOT/'artifacts'/'library'/'PROMOTED_INDEX.json'

def load(p):
    if not p.exists(): return []
    try: return json.loads(p.read_text(encoding='utf-8-sig'))
    except: return []

def audit(rows):
    total=len(rows)
    claude_path=0
    non_claude_path=0
    unknown=0
    specs={}
    for r in rows:
        sp=str(r.get('strategy_spec_path') or '')
        if 'claude' in sp.lower(): claude_path+=1
        elif sp: non_claude_path+=1
        else: unknown+=1
        if sp: specs[sp]=None
    src_counts={}
    for sp in specs:
        p=Path(sp)
        if not p.is_absolute(): p=(ROOT/p).resolve()
        src='MISSING'
        if p.exists():
            try:
                j=json.loads(p.read_text(encoding='utf-8-sig'))
                src=str(j.get('source') or '').strip() or 'UNSET'
            except:
                src='PARSE_ERROR'
        src_counts[src]=src_counts.get(src,0)+1
    return {
        'total_rows': total,
        'claude_path_rows': claude_path,
        'non_claude_path_rows': non_claude_path,
        'unknown_path_rows': unknown,
        'unique_specs': len(specs),
        'spec_source_counts': dict(sorted(src_counts.items(), key=lambda kv: kv[1], reverse=True)[:10])
    }

out={
  'RUN_INDEX': audit(load(run_idx)),
  'PASSED_INDEX': audit(load(pas_idx)),
  'PROMOTED_INDEX': audit(load(prom_idx)),
}
print(json.dumps(out))