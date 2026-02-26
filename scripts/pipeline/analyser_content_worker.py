#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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


def _slug(s: str) -> str:
    x = re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')
    return x or 'unknown'


def _channel_from_card(rc: dict) -> tuple[str, str]:
    author = str(rc.get('author') or '').strip()
    src = str(rc.get('source_ref') or '').strip()
    if author:
        return _slug(author), author
    try:
        u = urlparse(src)
        if 'youtube.com' in u.netloc or 'youtu.be' in u.netloc:
            q = parse_qs(u.query)
            vid = (q.get('v') or [''])[0]
            if vid:
                return 'michaelionita', 'MichaelIonita' if 'michael' in src.lower() else ('youtube', 'YouTube')
    except Exception:
        pass
    if 'michael' in src.lower() or 'ionita' in src.lower():
        return 'michaelionita', 'MichaelIonita'
    return 'youtube', 'YouTube'


def _append_channel_pack(day: str, channel_slug: str, channel_name: str, video_ids: list[str], concept_thesis_path: str, key_signals: list[str]) -> str:
    p = ROOT / 'artifacts' / 'thesis_packs' / day / f'{channel_slug}-latest.concepts_thesis_pack.json'
    cur = _j(p, {
        'channel_slug': channel_slug,
        'channel_name': channel_name,
        'created_at': datetime.now(UTC).isoformat(),
        'video_ids': [],
        'concept_thesis_paths': [],
        'key_signals': [],
    })
    cur['channel_slug'] = channel_slug
    cur['channel_name'] = channel_name
    cur['created_at'] = datetime.now(UTC).isoformat()
    cur['video_ids'] = (video_ids + [x for x in cur.get('video_ids', []) if x not in video_ids])[:50]
    cur['concept_thesis_paths'] = ([concept_thesis_path] + [x for x in cur.get('concept_thesis_paths', []) if x != concept_thesis_path])[:50]
    prev = cur.get('key_signals', [])
    ctr = Counter()
    for x in prev:
        if isinstance(x, dict):
            ctr[str(x.get('signal', ''))] += int(x.get('count', 0))
    for s in key_signals:
        ctr[s] += 1
    cur['key_signals'] = [{'signal': k, 'count': v} for k, v in ctr.most_common(20) if k]
    _w(p, cur)
    return str(p).replace('\\', '/')


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
    channel_slug = ''
    channel_name = ''
    video_ids: list[str] = []

    for rc_path in cards:
        p = Path(rc_path)
        if not p.exists():
            failed += 1
            continue
        try:
            rc = json.loads(p.read_text(encoding='utf-8'))
            title = str(rc.get('title') or p.stem)
            source = str(rc.get('source_ref') or '')
            if not channel_slug:
                channel_slug, channel_name = _channel_from_card(rc)
            m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', source)
            if m:
                video_ids.append(m.group(1))
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
    channel_pack_path = ''
    try:
        if not channel_slug:
            channel_slug, channel_name = ('youtube', 'YouTube')
        channel_pack_path = _append_channel_pack(day, channel_slug, channel_name or channel_slug, list(dict.fromkeys(video_ids))[:50], str(out_path).replace('\\', '/'), key_ideas[:10])
        out = _run('scripts/pipeline/update_analyser_doctrine.py', '--thesis-pack', channel_pack_path)
        lines = [x.strip() for x in out.splitlines() if x.strip()]
        if lines:
            doctrine_update_path = lines[-1]
    except Exception:
        failed += 1

    status = 'OK' if failed == 0 else ('WARN' if processed > 0 else 'FAIL')
    summary = f'Analyser content: processed={processed} failed={failed}'
    _log(status, 'ANALYSER_CONTENT_SUMMARY', summary)
    print(json.dumps({'processed': processed, 'failed': failed, 'thesis_pack_path': str(out_path).replace('\\', '/'), 'channel_pack_path': channel_pack_path, 'doctrine_update_path': doctrine_update_path}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
