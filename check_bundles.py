#!/usr/bin/env python3
import json, glob

files = list(glob.glob('artifacts/bundles/**/*.bundle.json', recursive=True))
print(f'Total bundles: {len(files)}')

status_counts = {}
for p in sorted(files):
    try:
        b = json.load(open(p, encoding='utf-8'))
        s = b.get('status', 'NEW')
        status_counts[s] = status_counts.get(s, 0) + 1
    except Exception as e:
        print(f'Error reading {p}: {e}')

print('\nStatus breakdown:')
for s in sorted(status_counts.keys()):
    print(f'  {s}: {status_counts[s]}')

# Show first 3 bundle details
print('\nFirst 3 bundles:')
for p in files[:3]:
    try:
        b = json.load(open(p, encoding='utf-8'))
        fname = p.split('/')[-1]
        print(f'  {fname}: status={b.get("status","?")}, attempt={b.get("attempt_count",0)}')
    except:
        pass
