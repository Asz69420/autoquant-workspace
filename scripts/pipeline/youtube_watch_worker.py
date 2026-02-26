#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen
from urllib.parse import urlparse
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


def _log(action: str, reason: str, summary: str, status: str = 'INFO', inputs: list[str] | None = None, outputs: list[str] | None = None, agent: str = 'oQ'):
    try:
        cmd = [
            PY, 'scripts/log_event.py',
            '--run-id', f"yt-watch-{int(datetime.now(UTC).timestamp())}",
            '--agent', agent,
            '--model-id', 'openai-codex/gpt-5.3-codex',
            '--action', action,
            '--status-word', status,
            '--status-emoji', ('OK' if status == 'OK' else ('INFO' if status == 'INFO' else ('WARN' if status == 'WARN' else 'FAIL'))),
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


def _resolve_channel_id(url: str, fallback: str = '') -> str:
    if fallback:
        return fallback
    try:
        p = urlparse(url)
        parts = [x for x in p.path.split('/') if x]
        if len(parts) >= 2 and parts[0].lower() == 'channel' and parts[1].startswith('UC'):
            return parts[1]
        html = urlopen(url, timeout=20).read().decode('utf-8', errors='ignore')
        m = re.search(r'"channelId"\s*:\s*"(UC[0-9A-Za-z_-]{20,})"', html)
        if m:
            return m.group(1)
        m2 = re.search(r'channel/(UC[0-9A-Za-z_-]{20,})', html)
        if m2:
            return m2.group(1)
    except Exception:
        return ''
    return ''


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


def _resolve_existing_indicators(rc_path: str, ind_idx: list[dict]) -> list[str]:
    try:
        card = _j(Path(rc_path), {})
    except Exception:
        card = {}
    hints = card.get('tv_search_hints', []) if isinstance(card, dict) else []
    names = []
    for h in hints:
        if isinstance(h, dict) and h.get('name'):
            names.append(str(h.get('name')).lower())
        if isinstance(h, dict):
            for kw in h.get('keywords', []) or []:
                names.append(str(kw).lower())
    out = []
    for row in ind_idx:
        if not isinstance(row, dict):
            continue
        ir = row.get('indicator_record_path')
        tv_key = str(row.get('tv_key', '')).lower()
        nm = str(row.get('name', '')).lower()
        if not ir:
            continue
        if any(n and (n in tv_key or n in nm) for n in names):
            p = str(ir).replace('\\', '/')
            if p not in out:
                out.append(p)
        if len(out) >= 2:
            break
    return out


def _append_usage_note(linkmap_path: str, *, channel_name: str, channel_url: str, video_id: str):
    try:
        lm_path = Path(linkmap_path)
        lm = _j(lm_path, {})
        notes = lm.get('usage_notes', []) if isinstance(lm.get('usage_notes', []), list) else []
        notes.append({
            'source': 'youtube',
            'channel': channel_name,
            'channel_url': channel_url,
            'video_url': f'https://www.youtube.com/watch?v={video_id}',
            'video_id': video_id,
            'noted_at': datetime.now(UTC).isoformat(),
        })
        lm['usage_notes'] = notes[-20:]
        _w(lm_path, lm)
    except Exception:
        pass


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
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': [], 'max_new_videos_per_run': 2})
    bundles = _j(BUNDLE_INDEX, [])
    ind_idx = _j(INDICATOR_INDEX, [])
    max_new = max(1, int(state.get('max_new_videos_per_run', MAX_NEW)))

    created = []
    seen_videos = set(state.get('seen_video_ids', []))
    channels_checked = 0
    processed = 0
    dedup = 0
    failed = 0
    new_total = 0
    concept_cards = []
    for ch in state.get('channels', []):
        if ch.get('enabled', True) is False:
            continue
        channel_url = str(ch.get('url', '') or '')
        channel_id = _resolve_channel_id(channel_url, str(ch.get('channel_id', '') or ''))
        if not channel_id:
            failed += 1
            continue
        ch['channel_id'] = channel_id
        channels_checked += 1
        latest = _fetch_latest(channel_id)
        if latest and not ch.get('last_seen_video_id'):
            ch['last_seen_video_id'] = latest[0]['video_id']
            seen_videos.add(latest[0]['video_id'])
        marker = str(ch.get('last_seen_video_id', '') or '')
        unseen_since_marker = []
        for x in latest:
            if marker and x['video_id'] == marker:
                break
            unseen_since_marker.append(x)
        new_count = len([x for x in unseen_since_marker if x['video_id'] not in seen_videos])
        new_total += new_count
        _log('YT_WATCH_CHECK', 'YT_WATCH_CHECK', f"channel={channel_id} new_count={new_count}", 'INFO')
        for item in unseen_since_marker:
            if len(created) >= max_new:
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
                # fallback ingest so content-loop can still learn when transcript endpoint is rate-limited
                try:
                    raw = f"Manual concept ingest fallback. source_ref=https://www.youtube.com/watch?v={vid} title={item['title']}"
                    rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', 'youtube_url', '--raw-text', raw, '--title', item['title'], '--author', ch.get('name', 'youtube'))
                    _log('YT_VIDEO_INGESTED_FALLBACK', 'YT_VIDEO_INGESTED_FALLBACK', f"video_id={vid}", 'WARN', outputs=[rc['research_card_path']])
                except Exception:
                    failed += 1
                    continue

            linked = _resolve_existing_indicators(rc['research_card_path'], ind_idx)

            lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc['research_card_path'], '--indicator-record-paths', json.dumps(linked[:2]))
            _append_usage_note(lm['linkmap_path'], channel_name=str(ch.get('name', 'youtube')), channel_url=channel_url, video_id=vid)
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
            if str(ch.get('mode', '')).upper() == 'CONCEPTS':
                concept_cards.append(str(rc['research_card_path']).replace('\\', '/'))
            processed += 1

        if latest:
            ch['last_seen_video_id'] = latest[0]['video_id']
            seen_videos.add(latest[0]['video_id'])

    _w(BUNDLE_INDEX, bundles[:500])
    state['seen_video_ids'] = list(seen_videos)[-1000:]
    _w(STATE_PATH, state)

    if concept_cards:
        try:
            _run('scripts/pipeline/analyser_content_worker.py', '--research-cards-json', json.dumps(concept_cards), '--max-items', '2')
        except Exception:
            pass
    y_status = 'OK'
    if failed > 0 and processed == 0 and new_total > 0:
        y_status = 'FAIL'
    elif failed > 0 or channels_checked == 0:
        y_status = 'WARN'
    _log('YT_WATCH_SUMMARY', 'YT_WATCH_SUMMARY', f"YT: channels={channels_checked} new={new_total} processed={processed} dedup={dedup} failed={failed}", y_status, agent='Reader')
    print(json.dumps({'created_bundles': created, 'count': len(created)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())