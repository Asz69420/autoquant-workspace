#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
INBOX = ROOT / 'data' / 'inbox' / 'transcripts'
PROCESSED = INBOX / 'processed'
FAILED = INBOX / 'failed'
BUNDLE_INDEX = ROOT / 'artifacts' / 'bundles' / 'INDEX.json'


def _run(*args: str) -> dict:
    out = subprocess.check_output([PY, *args], cwd=ROOT, text=True)
    return json.loads(out)


def _j(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _w(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def _log(action: str, reason: str, summary: str, status: str = 'INFO', outputs: list[str] | None = None):
    try:
        cmd = [
            PY, 'scripts/log_event.py',
            '--run-id', f"transcript-ingest-{int(datetime.now(UTC).timestamp())}",
            '--agent', 'Reader',
            '--model-id', 'openai-codex/gpt-5.3-codex',
            '--action', action,
            '--status-word', status,
            '--status-emoji', ('▶️' if status == 'START' else ('✅' if status == 'OK' else ('❌' if status == 'FAIL' else 'ℹ️'))),
            '--reason-code', reason,
            '--summary', summary,
        ]
        for o in (outputs or []):
            cmd += ['--outputs', str(o)]
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


def _bundle_for_research(video_id: str, source_ref: str, rc_path: str, lm_path: str) -> str:
    day = datetime.now(UTC).strftime('%Y%m%d')
    bdir = ROOT / 'artifacts' / 'bundles' / day
    bdir.mkdir(parents=True, exist_ok=True)
    bpath = bdir / f'{video_id}.bundle.json'
    b = {
        'id': f'bundle_{video_id}',
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'transcript_drop',
        'source_ref': source_ref,
        'video_id': video_id,
        'research_card_path': rc_path,
        'linkmap_path': lm_path,
        'indicator_record_paths': [],
        'status': 'NEW',
    }
    _w(bpath, b)
    idx = _j(BUNDLE_INDEX, [])
    p = str(bpath).replace('\\', '/')
    if p in idx:
        idx.remove(p)
    idx.insert(0, p)
    _w(BUNDLE_INDEX, idx[:500])
    return p


def _source_ref_from_stem(stem: str) -> str:
    s = stem.strip()
    if len(s) == 11 and all(c.isalnum() or c in '-_' for c in s):
        return f'https://www.youtube.com/watch?v={s}'
    return f'transcript_drop://{s}'


def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FAILED.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in INBOX.glob('*.txt') if p.is_file()])
    processed = 0
    failed = 0

    for fp in files:
        stem = fp.stem
        source_ref = _source_ref_from_stem(stem)
        _log('TRANSCRIPT_INGEST_START', 'TRANSCRIPT_INGEST_START', f'Ingest start file={fp.name}', 'START')
        try:
            raw = fp.read_text(encoding='utf-8', errors='ignore').strip()
            if not raw:
                raise RuntimeError('empty transcript file')
            rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', source_ref, '--source-type', 'transcript_drop', '--raw-text', raw, '--title', stem, '--author', 'manual-transcript-drop')
            lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc['research_card_path'], '--indicator-record-paths', '[]')
            bundle_path = _bundle_for_research(stem, source_ref, rc['research_card_path'], lm['linkmap_path'])
            fp.replace(PROCESSED / fp.name)
            processed += 1
            _log('TRANSCRIPT_INGEST_OK', 'TRANSCRIPT_INGEST_OK', f'Ingest ok file={fp.name} bundle={Path(bundle_path).name}', 'OK', outputs=[bundle_path, rc['research_card_path']])
        except Exception as e:
            failed += 1
            try:
                fp.replace(FAILED / fp.name)
            except Exception:
                pass
            _log('TRANSCRIPT_INGEST_FAIL', 'TRANSCRIPT_INGEST_FAIL', f'Ingest fail file={fp.name} detail={str(e)[:220]}', 'FAIL')

    print(json.dumps({'processed': processed, 'failed': failed, 'inbox': str(INBOX).replace('\\', '/')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
