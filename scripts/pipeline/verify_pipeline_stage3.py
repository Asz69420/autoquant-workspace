#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

MAX_JSON = 60 * 1024
MAX_INDEX = 200


def must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--index', default='artifacts/strategy_specs/INDEX.json')
    args = ap.parse_args()

    p = Path(args.strategy_spec)
    must(p.exists(), 'strategy spec missing')
    must(p.stat().st_size <= MAX_JSON, 'strategy spec exceeds 60KB')

    d = json.loads(p.read_text(encoding='utf-8'))
    must(d.get('schema_version') == '1.0', 'schema_version must be 1.0')
    variants = d.get('variants', [])
    must(1 <= len(variants) <= 5, 'variants must be 1..5')

    has_long = False
    has_short = False
    for v in variants:
        for k, cap in [('entry_long', 10), ('entry_short', 10), ('filters', 10), ('exit_rules', 10), ('risk_rules', 10), ('constraints', 10)]:
            arr = v.get(k, [])
            must(isinstance(arr, list), f'{k} must be list')
            must(len(arr) <= cap, f'{k} exceeds cap')
        if v.get('entry_long'):
            has_long = True
        if v.get('entry_short'):
            has_short = True
        params = v.get('parameters', [])
        must(isinstance(params, list), 'parameters must be list')
        for prm in params:
            must('min' in prm and 'max' in prm, 'parameter must include min/max')
            must(float(prm['min']) <= float(prm['max']), 'parameter min must be <= max')

    must(has_long and has_short, 'no non-empty entry_long/entry_short across variants')

    idx = Path(args.index)
    if idx.exists():
        arr = json.loads(idx.read_text(encoding='utf-8'))
        must(isinstance(arr, list), 'index must be list')
        must(len(arr) <= MAX_INDEX, 'index exceeds 200')

    print('OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
