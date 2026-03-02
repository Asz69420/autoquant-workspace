import json, datetime
from pathlib import Path
from collections import Counter

p = Path('data/logs/actions.ndjson')
if not p.exists():
    print('NO_LOG')
    raise SystemExit

lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()[-2000:]
now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

for mins in (16, 60, 180):
    cutoff = now - datetime.timedelta(minutes=mins)
    events = []
    for ln in lines:
        try:
            e = json.loads(ln)
        except Exception:
            continue
        ts = e.get('ts_iso') or e.get('ts')
        if not ts:
            continue
        try:
            dt = datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
        except Exception:
            continue
        if dt >= cutoff:
            events.append(e)

    c = Counter((e.get('action') or '') for e in events if (e.get('agent') or '') != 'Logger')
    print(f'--- last {mins} min: events={len(events)} nonlogger={sum(c.values())}')
    for k, v in c.most_common(12):
        print(v, k)
    wanted = ['GRABBER_SUMMARY','BATCH_BACKTEST_SUMMARY','LIBRARIAN_SUMMARY','PROMOTION_SUMMARY','REFINEMENT_SUMMARY','DIRECTIVE_LOOP_SUMMARY','LAB_SUMMARY','INSIGHT_SUMMARY']
    vals = {w: c.get(w, 0) for w in wanted}
    print('wanted', vals)
    print()
