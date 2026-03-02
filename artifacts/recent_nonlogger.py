import json
from pathlib import Path
for ln in Path('data/logs/actions.ndjson').read_text(encoding='utf-8',errors='ignore').splitlines()[-120:]:
    try:e=json.loads(ln)
    except:continue
    if (e.get('agent') or '')=='Logger':
        continue
    a=e.get('action')
    if a in {'DIRECTIVE_LOOP_SUMMARY','LAB_SUMMARY','GRABBER_SUMMARY'}:
        print(e.get('ts_iso'), e.get('agent'), a, e.get('status_word'), e.get('reason_code'), '|', e.get('summary'))
