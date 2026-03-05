import json
from pathlib import Path
from datetime import datetime

ROOT=Path(r"C:\Users\Clamps\.openclaw\workspace")
TS=datetime.now().strftime('%Y%m%d-%H%M%S')
ARCH=ROOT/'artifacts'/'library'/'archive'/f'non-claude-{TS}'
ARCH.mkdir(parents=True, exist_ok=True)


def jload(p,default):
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding='utf-8-sig'))
    except: return default

def jwrite(p,data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, separators=(',',':')), encoding='utf-8')

def spec_source(spath:str)->str:
    if not spath: return ''
    p=Path(spath)
    if not p.is_absolute(): p=(ROOT/p).resolve()
    if not p.exists(): return ''
    try:
        return str(json.loads(p.read_text(encoding='utf-8-sig')).get('source') or '').strip().lower()
    except:
        return ''

def is_claude_row(r:dict)->bool:
    return spec_source(str(r.get('strategy_spec_path') or ''))=='claude-advisor'

report={}
for name in ['RUN_INDEX.json','TOP_CANDIDATES.json','PASSED_INDEX.json','PASSED_HOT_7D.json','PASSED_WARM_14D.json','PROMOTED_INDEX.json']:
    p=ROOT/'artifacts'/'library'/name
    arr=jload(p,[])
    if not isinstance(arr,list):
        continue
    keep=[]; rem=[]
    for r in arr:
        if isinstance(r,dict) and is_claude_row(r): keep.append(r)
        else: rem.append(r)
    if rem:
        jwrite(ARCH/f'removed__{name}', rem)
    if keep!=arr:
        jwrite(p, keep)
    report[name]={'before':len(arr),'after':len(keep),'removed':len(rem)}

# strategy spec index filtering
sp_idx=ROOT/'artifacts'/'strategy_specs'/'INDEX.json'
sp_arr=jload(sp_idx,[])
if isinstance(sp_arr,list):
    keep=[]; rem=[]
    for s in sp_arr:
        src=spec_source(str(s))
        if src=='claude-advisor': keep.append(s)
        else: rem.append({'path':s,'source':src})
    if rem:
        jwrite(ARCH/'removed__strategy_specs_INDEX.json', rem)
    if keep!=sp_arr:
        jwrite(sp_idx, keep)
    report['strategy_specs/INDEX.json']={'before':len(sp_arr),'after':len(keep),'removed':len(rem)}

jwrite(ARCH/'report.json', report)
print(json.dumps({'archive_dir':str(ARCH), 'report':report}))
