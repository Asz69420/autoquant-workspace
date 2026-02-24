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
    fixture_base = Path('scripts/tests/fixtures/pipeline_stage2')
    rc = str((ROOT / fixture_base / 'research_card.fixture.json').as_posix())
    ir = str((ROOT / fixture_base / 'indicator_record.fixture.json').as_posix())
    lm = str((ROOT / fixture_base / 'linkmap.fixture.json').as_posix())

    out = run([
        PY,
        'scripts/pipeline/emit_thesis.py',
        '--research-card-path', rc,
        '--indicator-record-paths', json.dumps([ir]),
        '--linkmap-paths', json.dumps([lm]),
    ])
    thesis_path = json.loads(out)['thesis_path']

    idx = ROOT / 'artifacts/thesis/INDEX.json'
    oversized = [f'fake/{i}.json' for i in range(250)]
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(json.dumps(oversized), encoding='utf-8')

    run([
        PY,
        'scripts/pipeline/emit_thesis.py',
        '--research-card-path', rc,
        '--indicator-record-paths', json.dumps([ir]),
        '--linkmap-paths', json.dumps([lm]),
    ])

    verify = run([
        PY,
        'scripts/pipeline/verify_pipeline_stage2.py',
        '--thesis', thesis_path,
        '--index', 'artifacts/thesis/INDEX.json',
    ])
    assert verify == 'OK'

    idx_len = len(json.loads(idx.read_text(encoding='utf-8')))
    assert idx_len <= 200

    print(json.dumps({'thesis_path': thesis_path, 'index_len': idx_len}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
