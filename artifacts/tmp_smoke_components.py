import json,subprocess,sys,datetime,pathlib
ROOT=pathlib.Path('.').resolve(); PY=sys.executable

def run(args):
    out=subprocess.check_output([PY,*args],text=True,cwd=ROOT)
    return json.loads(out)

large_lines=['//@version=5','strategy("Huge Test", overlay=true)','/* block comment start\nline\n*/']
for i in range(750):
    large_lines.append(f'x{i}=close // c{i}')
large_lines.append('if close>open\n    strategy.entry("L", strategy.long)')
large_src='\n'.join(large_lines)
small_src='//@version=5\nindicator("Small Test", overlay=true)\n// comment\na=ta.sma(close,14)\nplot(a)\n'

L=run(['scripts/pipeline/emit_indicator_record.py','--tv-ref','manual:large-script','--name','Huge Script','--author','lab','--source-code',large_src,'--notes','[]','--signals','[]','--key-inputs','[]'])
S=run(['scripts/pipeline/emit_indicator_record.py','--tv-ref','manual:small-script','--name','Small Script','--author','lab','--source-code',small_src,'--notes','[]','--signals','[]','--key-inputs','[]'])
rcL=run(['scripts/pipeline/emit_research_card.py','--source-ref','manual:large-script','--source-type','manual','--raw-text','Large strategy component test','--title','Large Strategy'])
rcS=run(['scripts/pipeline/emit_research_card.py','--source-ref','manual:small-script','--source-type','manual','--raw-text','Small indicator component test','--title','Small Indicator'])
lmL=run(['scripts/pipeline/link_research_indicators.py','--research-card-path',rcL['research_card_path'],'--indicator-record-paths',json.dumps([L['indicator_record_path']])])
lmS=run(['scripts/pipeline/link_research_indicators.py','--research-card-path',rcS['research_card_path'],'--indicator-record-paths',json.dumps([S['indicator_record_path']])])

d=datetime.datetime.utcnow().strftime('%Y%m%d')
for tag,rc,ir,lm in [('large',rcL,L,lmL),('small',rcS,S,lmS)]:
    p=ROOT/'artifacts'/'bundles'/d/f'manual-{tag}.bundle.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    obj={'id':f'bundle_manual_{tag}','created_at':datetime.datetime.utcnow().isoformat()+'Z','source':'manual_smoke','research_card_path':rc['research_card_path'],'indicator_record_paths':[ir['indicator_record_path']],'linkmap_path':lm['linkmap_path'],'status':'NEW'}
    p.write_text(json.dumps(obj,indent=2),encoding='utf-8')

idx=ROOT/'artifacts'/'bundles'/'INDEX.json'
arr=[]
if idx.exists():
    arr=json.loads(idx.read_text(encoding='utf-8'))
prepend=[str((ROOT/'artifacts'/'bundles'/d/'manual-large.bundle.json').as_posix()),str((ROOT/'artifacts'/'bundles'/d/'manual-small.bundle.json').as_posix())]
for x in reversed(prepend):
    if x in arr: arr.remove(x)
    arr.insert(0,x)
idx.write_text(json.dumps(arr[:500],indent=2),encoding='utf-8')
print(json.dumps({'large_ir':L['indicator_record_path'],'small_ir':S['indicator_record_path']}))
