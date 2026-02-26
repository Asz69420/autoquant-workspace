#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

MAX_THESIS_JSON = 50 * 1024
MAX_INDEX = 200


def must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def check_schema_like(thesis: dict) -> None:
    must(thesis.get('schema_version') in ('1.0', '1.1'), 'schema_version must be 1.0 or 1.1')
    must(len(thesis.get('title', '')) <= 120 and thesis.get('title'), 'invalid title')
    must(len(thesis.get('thesis_bullets', [])) <= 10, 'thesis_bullets cap exceeded')
    must(len(thesis.get('hypotheses', [])) <= 5, 'hypotheses cap exceeded')
    for h in thesis.get('hypotheses', []):
        for key in ['statement', 'rationale', 'falsifiable_test', 'expected_regime']:
            must(bool(h.get(key)), f'missing hypothesis.{key}')
        must(len(h.get('failure_modes', [])) <= 5, 'failure_modes cap exceeded')
    must(len(thesis.get('candidate_signals', [])) <= 10, 'candidate_signals cap exceeded')
    for c in thesis.get('candidate_signals', []):
        must(0 <= float(c.get('confidence', -1)) <= 1, 'confidence out of range')
        must(len(c.get('uses_indicators', [])) <= 5, 'uses_indicators cap exceeded')
    for k, cap in [('required_data', 10), ('constraints', 10), ('tags', 20)]:
        must(len(thesis.get(k, [])) <= cap, f'{k} cap exceeded')
    role_catalog = thesis.get('role_catalog', [])
    must(len(role_catalog) <= 10, 'role_catalog cap exceeded')
    for r in role_catalog:
        must(r in ['trend', 'entry', 'confirmation', 'regime_gate', 'exit'], 'invalid role_catalog role')
    must(len(thesis.get('combo_proposals', [])) <= 10, 'combo_proposals cap exceeded')
    for c in thesis.get('combo_proposals', []):
        must(c.get('role') in ['trend', 'entry', 'confirmation', 'regime_gate', 'exit'], 'invalid combo_proposals.role')
        must(len(str(c.get('description', ''))) <= 160 and bool(c.get('description')), 'invalid combo_proposals.description')
        must(0 <= float(c.get('confidence', -1)) <= 1, 'combo_proposals confidence out of range')
    must(len(thesis.get('mutation_catalog', [])) <= 10, 'mutation_catalog cap exceeded')
    for m in thesis.get('mutation_catalog', []):
        must(m.get('type') in ['threshold', 'risk', 'execution', 'filter'], 'invalid mutation_catalog.type')
        must(bool(m.get('suggestion')) and bool(m.get('bounds')), 'mutation_catalog missing fields')
    inputs = thesis.get('inputs', {})
    must(len(inputs.get('research_card_paths', [])) <= 5, 'research_card_paths cap exceeded')
    must(len(inputs.get('indicator_record_paths', [])) <= 10, 'indicator_record_paths cap exceeded')
    must(len(inputs.get('linkmap_paths', [])) <= 5, 'linkmap_paths cap exceeded')
    must(bool(thesis.get('sha256_inputs')), 'sha256_inputs missing')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--thesis', required=True)
    ap.add_argument('--index', default='artifacts/thesis/INDEX.json')
    args = ap.parse_args()

    tpath = Path(args.thesis)
    must(tpath.exists(), 'thesis missing')
    must(tpath.stat().st_size <= MAX_THESIS_JSON, 'Thesis JSON exceeds 50KB')
    thesis = json.loads(tpath.read_text(encoding='utf-8-sig'))
    check_schema_like(thesis)

    idx = Path(args.index)
    if idx.exists():
        arr = json.loads(idx.read_text(encoding='utf-8-sig'))
        must(isinstance(arr, list), 'INDEX must be list')
        must(len(arr) <= MAX_INDEX, 'INDEX exceeds 200')

    print('OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
