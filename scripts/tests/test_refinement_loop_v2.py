#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def main() -> int:
    out = subprocess.check_output([
        PY, 'scripts/pipeline/run_refinement_loop.py',
        '--promotion-run', 'artifacts/promotions/20260225/promo_20260225_tpx_executable.promotion_run.json',
        '--max-iters', '3', '--improvement-threshold', '0.02',
    ], cwd=ROOT, text=True)
    info = json.loads(out)
    p = Path(info['refinement_cycle_path'])
    doc = json.loads(p.read_text(encoding='utf-8'))

    assert doc['iterations_used'] <= 3
    for it in doc.get('history', []):
        assert it['explore_variants_count'] <= 3

    windows = []
    for it in doc.get('history', []):
        hs = datetime.fromisoformat(it['holdout_window']['start'])
        he = datetime.fromisoformat(it['holdout_window']['end'])
        windows.append((hs, he))
    for i in range(len(windows)):
        for j in range(i + 1, len(windows)):
            a, b = windows[i]
            c, d = windows[j]
            assert b <= c or d <= a, 'holdout windows overlap'

    seeds = [it['sobol_seed'] for it in doc.get('history', [])]
    if len(seeds) >= 2:
        assert seeds[0] != seeds[1], 'sobol seed should differ by strategy_index_counter'

    print(json.dumps({'refinement_cycle_path': str(p), 'iterations_used': doc['iterations_used']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
