import json
from pathlib import Path
from collections import defaultdict

wanted = ['GRABBER_SUMMARY','BATCH_BACKTEST_SUMMARY','LIBRARIAN_SUMMARY','PROMOTION_SUMMARY','REFINEMENT_SUMMARY','DIRECTIVE_LOOP_SUMMARY','LAB_SUMMARY','INSIGHT_SUMMARY']
seen = defaultdict(list)

for ln in Path('data/logs/actions.ndjson').read_text(encoding='utf-8', errors='ignore').splitlines()[-3000:]:
    try:
        e = json.loads(ln)
    except:
        continue
    a = e.get('action')
    if a in wanted and (e.get('agent') or '') != 'Logger':
        seen[a].append((e.get('ts_iso'), e.get('summary'), e.get('agent')))

for a in wanted:
    print('\n===',a)
    for ts,s,ag in seen[a][-3:]:
        print(ts, '|', ag, '|', s)
