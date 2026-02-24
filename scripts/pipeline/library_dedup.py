#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def is_duplicate(sha256_inputs: str, run_index_path: Path) -> bool:
    if not run_index_path.exists():
        return False
    try:
        arr = json.loads(run_index_path.read_text(encoding='utf-8'))
    except Exception:
        return False
    seen = {str(x.get('sha256_inputs', '')) for x in arr if isinstance(x, dict)}
    return sha256_inputs in seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sha256-inputs', required=True)
    ap.add_argument('--run-index', default='artifacts/library/RUN_INDEX.json')
    args = ap.parse_args()

    dup = is_duplicate(args.sha256_inputs, Path(args.run_index))
    print(json.dumps({'duplicate': dup}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
