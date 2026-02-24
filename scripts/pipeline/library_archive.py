#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path


def archive_old(artifacts_root: Path, older_than_days: int = 30) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    moved = []
    for p in artifacts_root.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(artifacts_root)
        if rel.parts[0] in ('archive', 'library'):
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
        if mtime >= cutoff:
            continue
        type_name = rel.parts[0]
        ym = mtime.strftime('%Y-%m')
        dst = artifacts_root / 'archive' / ym / type_name / Path(*rel.parts[1:])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dst))
        moved.append({'from': str(p), 'to': str(dst)})
    return {'moved_count': len(moved), 'moved': moved}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifacts-root', default='artifacts')
    ap.add_argument('--older-than-days', type=int, default=30)
    args = ap.parse_args()
    out = archive_old(Path(args.artifacts_root), args.older_than_days)
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
