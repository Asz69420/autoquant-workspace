#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--research-card-path', required=True)
    ap.add_argument('--linkmap-path', default='')
    args = ap.parse_args()

    indicator_paths = []
    link_paths = []
    if args.linkmap_path:
        lp = Path(args.linkmap_path)
        if lp.exists():
            lm = json.loads(lp.read_text(encoding='utf-8'))
            indicator_paths = lm.get('indicator_record_paths', [])[:10]
            link_paths = [args.linkmap_path]

    cmd = [
        sys.executable,
        'scripts/pipeline/emit_thesis.py',
        '--research-card-path', args.research_card_path,
        '--indicator-record-paths', json.dumps(indicator_paths),
        '--linkmap-paths', json.dumps(link_paths),
    ]
    out = subprocess.check_output(cmd, text=True)
    print(out.strip())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
