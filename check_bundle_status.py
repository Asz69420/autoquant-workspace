#!/usr/bin/env python3
import json, glob

bundles = glob.glob('artifacts/bundles/**/*.bundle.json', recursive=True)
print(f'Bundles: {len(bundles)}')

for p in bundles[:5]:
    try:
        b = json.load(open(p, encoding='utf-8'))
        status = b.get('status', 'N/A')
        attempt = b.get('attempt_count', 0)
        print(f'  {p.split("/")[-1]}: status={status}, attempt={attempt}')
    except Exception as e:
        print(f'  {p}: ERROR {e}')
