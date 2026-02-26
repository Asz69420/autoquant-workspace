#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


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


def _log(status_word: str, reason: str, summary: str):
    cmd = [
        PY, 'scripts/log_event.py',
        '--run-id', f"analyser-content-{int(datetime.now(UTC).timestamp())}",
        '--agent', 'Analyser',
        '--model-id', 'openai-codex/gpt-5.3-codex',
        '--action', 'ANALYSER_CONTENT_SUMMARY',
        '--status-word', status_word,
        '--status-emoji', ('OK' if status_word == 'OK' else ('WARN' if status_word == 'WARN' else 'FAIL')),
        '--reason-code', reason,
        '--summary', summary,
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def _run(*args: str) -> str:
    return subprocess.check_output([PY, *args], cwd=ROOT, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--research-cards-json', required=True)
    ap.add_argument('--max-items', type=int, default=2)
    args = ap.parse_args()

    try:
        cards = json.loads(args.research_cards_json)
    except Exception:
        cards = []
    cards = [str(x) for x in cards if str(x).strip()][: max(1, args.max_items)]

    processed = 0
    failed = 0
    key_ideas = []
    hooks = []
    autos = []

    for rc_path in cards:
        p = Path(rc_path)
        if not p.exists():
            failed += 1
            continue
        try:
            rc = json.loads(p.read_text(encoding='utf-8'))
            title = str(rc.get('title') or p.stem)
            source = str(rc.get('source_ref') or '')
            key_ideas.append(f'{title}: extract repeatable concept from source context')
            hooks.append(f'{title}: convert concept to testable entry/exit hypothesis')
            autos.append(f'{title}: record ingestion evidence pointer for doctrine traceability')
            processed += 1
        except Exception:
            failed += 1

    day = datetime.now(UTC).strftime('%Y%m%d')
    out_dir = ROOT / 'artifacts' / 'thesis_packs' / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'content-loop-{int(datetime.now(UTC).timestamp())}.concept_thesis.json'
    payload = {
        'id': f'concept-thesis-{int(datetime.now(UTC).timestamp())}',
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'analyser_content_worker',
        'processed_research_cards': cards,
        'key_ideas': key_ideas[:10],
        'trading_relevant_concept_hooks': hooks[:10],
        'proposed_automation_improvements_for_autoquant': autos[:10],
    }
    _w(out_path, payload)

    doctrine_update_path = ''
    try:
        out = _run('scripts/pipeline/update_analyser_doctrine.py', '--thesis-pack', str(out_path).replace('\\', '/'))
        lines = [x.strip() for x in out.splitlines() if x.strip()]
        if lines:
            doctrine_update_path = lines[-1]
    except Exception:
        failed += 1

    status = 'OK' if failed == 0 else ('WARN' if processed > 0 else 'FAIL')
    summary = f'Analyser content: processed={processed} failed={failed}'
    _log(status, 'ANALYSER_CONTENT_SUMMARY', summary)
    print(json.dumps({'processed': processed, 'failed': failed, 'thesis_pack_path': str(out_path).replace('\\', '/'), 'doctrine_update_path': doctrine_update_path}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
