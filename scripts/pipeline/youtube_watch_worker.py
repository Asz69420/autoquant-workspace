#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
STATE_PATH = ROOT / 'data' / 'state' / 'youtube_watchlist.json'
BUNDLE_INDEX = ROOT / 'artifacts' / 'bundles' / 'INDEX.json'
INDICATOR_INDEX = ROOT / 'artifacts' / 'library' / 'INDICATOR_INDEX.json'
MAX_NEW = 2


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


def _run(*args: str) -> dict:
    out = subprocess.check_output([PY, *args], cwd=ROOT, text=True)
    return json.loads(out)


def _log(action: str, reason: str, summary: str, status: str = 'INFO', inputs: list[str] | None = None, outputs: list[str] | None = None):
    try:
        cmd = [
            PY, 'scripts/log_event.py',
            '--run-id', f"yt-watch-{int(datetime.now(UTC).timestamp())}",
            '--agent', 'oQ',
            '--model-id', 'openai-codex/gpt-5.3-codex',
            '--action', action,
            '--status-word', status,
            '--status-emoji', 'INFO' if status == 'INFO' else ('WARN' if status == 'WARN' else 'FAIL'),
            '--reason-code', reason,
            '--summary', summary,
        ]
        for x in (inputs or []):
            cmd += ['--input', str(x)]
        for x in (outputs or []):
            cmd += ['--output', str(x)]
        subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception:
        pass


def _fetch_latest(channel_id: str):
    rss = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    xml = urlopen(rss, timeout=20).read()
    root = ET.fromstring(xml)
    ns = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    items = []
    for e in root.findall('a:entry', ns):
        vid = e.find('yt:videoId', ns)
        title = e.find('a:title', ns)
        if vid is None:
            continue
        items.append({'video_id': vid.text, 'title': title.text if title is not None else vid.text})
    return items


def _transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    t = api.fetch(video_id, languages=['en'])
    return '\n'.join([x.text for x in t])


def _extract_hints(text: str):
    # lightweight TV hint extraction from transcript
    hints = set(re.findall(r'\b(?:ribbon|supertrend|vwap|macd|rsi|bollinger|stoch|adx)\b', text.lower()))
    return list(hints)[:2]


def main() -> int:
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': []})
    bundles = _j(BUNDLE_INDEX, [])
    ind_idx = _j(INDICATOR_INDEX, [])
    seen_tv = {x.get('tv_key') for x in ind_idx if isinstance(x, dict)}

    created = []
    seen_videos = set(state.get('seen_video_ids', []))
    channels_checked = 0
    processed = 0
    dedup = 0
    failed = 0
    new_total = 0
    for ch in state.get('channels', []):
        channel_id = ch.get('channel_id', '')
        if not channel_id:
            continue
        channels_checked += 1
        latest = _fetch_latest(channel_id)
        new_count = len([x for x in latest if x['video_id'] not in seen_videos])
        new_total += new_count
        _log('YT_WATCH_CHECK', 'YT_WATCH_CHECK', f"channel={channel_id} new_count={new_count}", 'INFO')
        for item in latest:
            if len(created) >= MAX_NEW:
                break
            vid = item['video_id']
            if vid in seen_videos:
                dedup += 1
                continue
            try:
                txt = _transcript(vid)
                rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', 'transcript', '--raw-text', txt, '--title', item['title'], '--author', ch.get('name', 'youtube'))
                _log('YT_VIDEO_INGESTED', 'YT_VIDEO_INGESTED', f"video_id={vid}", 'INFO', outputs=[rc['research_card_path']])
            except Exception:
                failed += 1
                continue

            linked = []
            for h in _extract_hints(txt):
                tv_key = f'{h}|catalog'
                for row in ind_idx:
                    if row.get('tv_key') == tv_key and row.get('indicator_record_path'):
                        linked.append(row['indicator_record_path'])

            lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc['research_card_path'], '--indicator-record-paths', json.dumps(linked[:2]))
            bday = datetime.now(UTC).strftime('%Y%m%d')
            bpath = ROOT / 'artifacts' / 'bundles' / bday / f'{vid}.bundle.json'
            b = {
                'id': f'bundle_{vid}',
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'youtube',
                'video_id': vid,
                'research_card_path': rc['research_card_path'],
                'indicator_record_paths': linked[:2],
                'linkmap_path': lm['linkmap_path'],
                'status': 'NEW',
            }
            _w(bpath, b)
            _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=youtube video_id={vid}", 'INFO', outputs=[str(bpath).replace('\\', '/')])
            bundles = [str(bpath).replace('\\', '/')] + [x for x in bundles if x != str(bpath).replace('\\', '/')]
            seen_videos.add(vid)
            created.append(str(bpath).replace('\\', '/'))
            processed += 1

    _w(BUNDLE_INDEX, bundles[:500])
    state['seen_video_ids'] = list(seen_videos)[-1000:]
    _w(STATE_PATH, state)
    _log('YT_WATCH_SUMMARY', 'YT_WATCH_SUMMARY', f"YT: channels={channels_checked} new={new_total} processed={processed} dedup={dedup} failed={failed}", 'INFO')
    print(json.dumps({'created_bundles': created, 'count': len(created)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())