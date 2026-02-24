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
    thesis = str((ROOT / 'artifacts/thesis/20260224/thesis-20260224-1febddaab016.thesis.json').as_posix())

    out = run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', thesis])
    info = json.loads(out)
    spec = info['strategy_spec_path']

    run([PY, 'scripts/pipeline/verify_pipeline_stage3.py', '--strategy-spec', spec])

    idx = ROOT / 'artifacts/strategy_specs/INDEX.json'
    idx.parent.mkdir(parents=True, exist_ok=True)
    oversized = [f'fake/{i}.json' for i in range(250)]
    idx.write_text(json.dumps(oversized), encoding='utf-8')

    run([PY, 'scripts/pipeline/emit_strategy_spec.py', '--thesis-path', thesis])
    idx_len = len(json.loads(idx.read_text(encoding='utf-8')))
    assert idx_len <= 200

    d = json.loads((ROOT / spec).read_text(encoding='utf-8'))
    baseline_entry = d['variants'][0]['entry_long'][0]
    print(json.dumps({'strategy_spec_path': spec, 'variants': len(d['variants']), 'baseline_entry_long': baseline_entry, 'index_len': idx_len}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
