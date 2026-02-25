#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def main() -> int:
    out = run([
        PY,
        'scripts/pipeline/emit_insight_card.py',
        '--title', 'Mean reversion after regime fakeout',
        '--concept', 'Watch for failed breakout then fade back to VWAP with strict 1R stop.',
        '--tags', 'mean-reversion,vwap',
        '--roles', 'entry,risk',
        '--confidence', '0.64',
    ])
    card_path_1 = json.loads(out)['insight_card_path']
    cp1 = ROOT / card_path_1
    card = json.loads(cp1.read_text(encoding='utf-8'))

    assert card['schema_version'] == '1.0'
    assert card['source'] == 'manual'
    assert card['status'] == 'NEW'
    assert len(card['title']) <= 120
    assert len(card['concept']) <= 2000
    assert len(card['tags']) <= 10
    assert len(card['suggested_roles']) <= 6

    idx = ROOT / 'artifacts/insights/INDEX.json'
    oversized = [f'artifacts/insights/20260101/fake-{i}.insight_card.json' for i in range(250)]
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(json.dumps(oversized), encoding='utf-8')

    out2 = run([
        PY,
        'scripts/pipeline/emit_insight_card.py',
        '--title', 'Breakout continuation with ATR trail',
        '--concept', 'Trend-confirm and trail stop with ATR as volatility expands.',
    ])
    card_path_2 = json.loads(out2)['insight_card_path']

    idx_len = len(json.loads(idx.read_text(encoding='utf-8')))
    assert idx_len <= 200

    run([
        PY,
        'scripts/pipeline/process_insight_cycle.py',
        '--max-refinements',
        '0',
    ])

    card_after_1 = json.loads((ROOT / card_path_1).read_text(encoding='utf-8'))
    card_after_2 = json.loads((ROOT / card_path_2).read_text(encoding='utf-8'))
    assert card_after_1['status'] == 'PROCESSED' or card_after_2['status'] == 'PROCESSED'

    chosen = card_path_1 if card_after_1['status'] == 'PROCESSED' else card_path_2
    print(json.dumps({'insight_card_path': chosen, 'index_len': idx_len, 'status_1': card_after_1['status'], 'status_2': card_after_2['status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
