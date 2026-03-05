import json
from pathlib import Path
ROOT=Path(r"C:\Users\Clamps\.openclaw\workspace")

def load(p):
  if not p.exists(): return []
  try:return json.loads(p.read_text(encoding='utf-8-sig'))
  except:return []

def src(sp):
  p=Path(sp)
  if not p.is_absolute(): p=(ROOT/p).resolve()
  if not p.exists(): return ''
  try:return str(json.loads(p.read_text(encoding='utf-8-sig')).get('source') or '').strip().lower()
  except:return ''

for name in ['RUN_INDEX.json','PASSED_INDEX.json','PROMOTED_INDEX.json','TOP_CANDIDATES.json']:
  arr=load(ROOT/'artifacts'/'library'/name)
  bad=0
  for r in arr:
    if not isinstance(r,dict): bad+=1; continue
    if src(str(r.get('strategy_spec_path') or ''))!='claude-advisor': bad+=1
  print(name,len(arr),bad)

idx=load(ROOT/'artifacts'/'strategy_specs'/'INDEX.json')
bad=0
for p in idx:
  if src(str(p))!='claude-advisor': bad+=1
print('strategy_specs/INDEX.json',len(idx),bad)
