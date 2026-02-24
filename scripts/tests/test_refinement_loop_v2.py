#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def main() -> int:
    out = subprocess.check_output([
        PY,
        'scripts/pipeline/run_refinement_loop.py',
        '--promotion-run',
        'artifacts/promotions/20260225/promo_20260225_tpx_executable.promotion_run.json',
        '--max-iters',
        '3',
        '--improvement-threshold',
        '0.02',
    ], cwd=ROOT, text=True)
    info = json.loads(out)
    p = Path(info['refinement_cycle_path'])
    assert p.exists()
    doc = json.loads(p.read_text(encoding='utf-8'))

    assert doc['iterations_used'] <= 3
    assert 'best_score_delta' in doc
    assert doc['final_recommendation'] in ('NO_IMPROVEMENT', 'CANDIDATE_FOUND')

    for it in doc.get('history', []):
        assert it['explore_variants_count'] <= 3
        assert it['variants_total'] <= 10
        for r in it.get('results', []):
            c = r.get('complexity', {})
            assert 'indicator_count' in c and 'condition_count' in c and 'parameter_count' in c

    if doc['stop_reason'] == 'early_stop_no_improvement':
        assert doc['iterations_used'] < 3

    print(json.dumps({'refinement_cycle_path': str(p), 'iterations_used': doc['iterations_used']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
