#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
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
RETRY_QUEUE_PATH = ROOT / 'data' / 'state' / 'youtube_retry_queue.json'
MAX_NEW = 2
MAX_RETRY_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = [15 * 60, 30 * 60, 60 * 60, 2 * 60 * 60, 4 * 60 * 60]
JITTER_MAX_SECONDS = 10 * 60
SHORTS_MAX_SECONDS = 90
MAX_VIDEO_SECONDS = 3600
CATEGORY_CONFIG_PATH = ROOT / 'data' / 'state' / 'youtube_channel_categories.json'
CONCEPT_CATEGORIES = {'TRADING_CONCEPT', 'NUANCED_CONCEPT', 'MARKET_STRUCTURE', 'RISK_EXECUTION', 'MACRO_CONTEXT'}
AUTO_CLASSIFY_CATEGORIES = ['INDICATOR_CONCEPT', 'TRADING_CONCEPT', 'NUANCED_CONCEPT', 'MARKET_STRUCTURE', 'RISK_EXECUTION', 'MACRO_CONTEXT']


def _j(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:
        return default


def _w(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        json.dump(obj, f, indent=2)


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


def _fetch_video_duration_seconds(video_id: str) -> int | None:
    """Return video duration in seconds via yt-dlp metadata, or None if unavailable."""
    url = f'https://www.youtube.com/watch?v={video_id}'
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        d = info.get('duration')
        if d is None:
            return None
        return int(d)
    except Exception:
        return None


def _notify_transcript_failure(video_id: str, title: str, detail: str):
    """Send a best-effort Telegram log-channel alert for transcript failures."""
    msg = f"YT transcript failed: {title} ({video_id})\n{str(detail)[:400]}"
    try:
        subprocess.run(
            [PY, 'scripts/tg_notify.py', msg, '--reason-code', 'YT_TRANSCRIPT_FAIL'],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        pass


def _notify_watch_skip(reason_code: str, title: str, duration_s: int):
    """Send best-effort Telegram log-channel alert for watch-list skips."""
    msg = f"{reason_code}: {title} ({duration_s}s)"
    try:
        subprocess.run(
            [PY, 'scripts/tg_notify.py', msg, '--reason-code', reason_code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        pass


def _notify_category_review(channel_name: str, title: str, video_id: str, top1: str, top2: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    msg = f"⚙️ Frodex review needed: {channel_name} | {title}\nTop candidates: {top1}, {top2}\nVideo: {url}"
    try:
        target_dm = (os.getenv('TELEGRAM_CMD_CHAT_ID') or '').strip()
        cmd = [PY, 'scripts/tg_notify.py', msg, '--reason-code', 'YT_CATEGORY_REVIEW']
        if target_dm:
            cmd += ['--chat-id', target_dm]
        subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        pass


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


def _research_card_has_sufficient_content(rc_path: str) -> bool:
    try:
        card = _j(Path(rc_path), {})
    except Exception:
        return False

    indicators = card.get('indicators_mentioned', []) if isinstance(card.get('indicators_mentioned', []), list) else []
    strategy_components = card.get('strategy_components', []) if isinstance(card.get('strategy_components', []), list) else []
    extracted_rules_raw = card.get('extracted_rules', []) if isinstance(card.get('extracted_rules', []), list) else []
    extracted_rules = [str(x).strip() for x in extracted_rules_raw if str(x).strip() and str(x).strip().lower() != 'not specified in content.']

    return bool(indicators or strategy_components or extracted_rules)


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


def _transcript(video_id: str, title: str = '') -> dict:
    url = f'https://www.youtube.com/watch?v={video_id}'
    out = _run('scripts/pipeline/transcript_resolver.py', '--video-id', video_id, '--url', url)
    if out.get('ok') or str(out.get('status', '')).upper() == 'RETRY_LATER':
        return out
    raise RuntimeError('; '.join(out.get('errors', []) or ['TRANSCRIPT_RESOLVE_FAILED']))


def _extract_hints(text: str):
    # lightweight TV hint extraction from transcript
    hints = set(re.findall(r'\b(?:ribbon|supertrend|vwap|macd|rsi|bollinger|stoch|adx)\b', text.lower()))
    return list(hints)[:2]


def _iso_to_dt(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except Exception:
        return None


def _load_retry_queue() -> dict[str, dict]:
    rows = _j(RETRY_QUEUE_PATH, [])
    out: dict[str, dict] = {}
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict) and r.get('video_id'):
                out[str(r['video_id'])] = dict(r)
    return out


def _save_retry_queue(q: dict[str, dict]):
    _w(RETRY_QUEUE_PATH, list(q.values()))


def _retry_allowed_now(q: dict[str, dict], video_id: str) -> bool:
    row = q.get(video_id)
    if not row:
        return True
    if str(row.get('status', '')).upper() == 'FAILED':
        return False
    dt = _iso_to_dt(str(row.get('next_retry_at', '') or ''))
    if dt is None:
        return True
    return datetime.now(UTC) >= dt


def _queue_retry(q: dict[str, dict], video_id: str, err: str, retry_after_hint: int | None = None) -> dict:
    now = datetime.now(UTC)
    prev = q.get(video_id, {})
    attempts = int(prev.get('attempts', 0)) + 1
    status = 'QUEUED'
    if attempts > MAX_RETRY_ATTEMPTS:
        attempts = MAX_RETRY_ATTEMPTS
        status = 'FAILED'
        next_retry_at = None
        retry_after = 0
        last_error = 'YOUTUBE_RATE_LIMIT_PERSISTENT'
    else:
        base = BACKOFF_BASE_SECONDS[attempts - 1]
        jitter = int(retry_after_hint or 0)
        if jitter <= 0:
            jitter = random.randint(0, JITTER_MAX_SECONDS)
        else:
            jitter = min(max(0, jitter), JITTER_MAX_SECONDS)
        retry_after = base + jitter
        next_retry_at = (now.timestamp() + retry_after)
        last_error = err[:280]

    row = {
        'video_id': video_id,
        'attempts': attempts,
        'status': status,
        'next_retry_at': (datetime.fromtimestamp(next_retry_at, tz=UTC).isoformat() if next_retry_at else ''),
        'last_error': last_error,
    }
    q[video_id] = row
    return row


def _load_channel_categories() -> tuple[dict[str, dict], dict[str, dict]]:
    cfg = _j(CATEGORY_CONFIG_PATH, {})
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    rows = cfg.get('channels', []) if isinstance(cfg, dict) else []
    for r in rows:
        if not isinstance(r, dict):
            continue
        cat = str(r.get('active_category') or '').strip().upper()
        if not cat:
            continue
        secondaries = [str(x).strip().upper() for x in (r.get('secondary_categories') or []) if str(x).strip()]
        row = {
            'active_category': cat,
            'secondary_categories': secondaries,
        }
        cid = str(r.get('channel_id') or '').strip()
        name = str(r.get('name') or '').strip().lower()
        if cid:
            by_id[cid] = row
        if name:
            by_name[name] = row
    return by_id, by_name


def _default_category_from_mode(mode: str) -> str:
    m = str(mode or '').strip().upper()
    if m == 'INDICATORS':
        return 'INDICATOR_CONCEPT'
    if m == 'CONCEPTS':
        return 'TRADING_CONCEPT'
    return 'REVIEW'


def _resolve_channel_category_config(ch: dict, by_id: dict[str, dict], by_name: dict[str, dict]) -> dict:
    cid = str(ch.get('channel_id') or '').strip()
    nm = str(ch.get('name') or '').strip().lower()
    if cid and cid in by_id:
        return dict(by_id[cid])
    if nm and nm in by_name:
        return dict(by_name[nm])
    return {
        'active_category': _default_category_from_mode(str(ch.get('mode') or '')),
        'secondary_categories': [],
    }


def _classify_video_category(title: str, rc_path: str, cfg: dict) -> tuple[str, bool, str, str]:
    active = str(cfg.get('active_category') or 'REVIEW').upper()
    secondaries = [str(x).upper() for x in (cfg.get('secondary_categories') or []) if str(x)]

    text_parts = [str(title or '')]
    card = _j(Path(rc_path), {})
    if isinstance(card, dict):
        for k in ['summary_bullets', 'extracted_rules', 'creator_notes', 'strategy_components']:
            v = card.get(k)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict):
                        text_parts.append(str(it.get('quote') or ''))
                        text_parts.append(str(it.get('note') or ''))
                        text_parts.append(str(it.get('description') or ''))
                    else:
                        text_parts.append(str(it))
        inds = card.get('indicators_mentioned')
        if isinstance(inds, list):
            text_parts.extend([str(x) for x in inds])

    blob = ' '.join(text_parts).lower()

    scores = {c: 0 for c in AUTO_CLASSIFY_CATEGORIES}
    if active in scores:
        scores[active] += 2
    for s in secondaries:
        if s in scores:
            scores[s] += 1

    indicator_keywords = ['indicator', 'tradingview', 'pine', 'ema', 'rsi', 'macd', 'stoch', 'adx', 'atr', 'supertrend', 'vortex', 'oscillator']
    trading_keywords = ['entry', 'exit', 'setup', 'strategy', 'signal', 'backtest', 'trade plan']
    nuanced_keywords = ['mindset', 'psychology', 'thesis', 'framework', 'process', 'narrative', 'behavior', 'edge']
    macro_keywords = ['macro', 'liquidity', 'fomc', 'cpi', 'rates', 'yield', 'dxy', 'economy', 'fed']
    risk_keywords = ['risk', 'execution', 'slippage', 'fees', 'position sizing', 'drawdown', 'sizing']
    structure_keywords = ['market structure', 'trend', 'regime', 'distribution', 'accumulation', 'cycle']

    if any(k in blob for k in indicator_keywords):
        scores['INDICATOR_CONCEPT'] += 4
    if any(k in blob for k in trading_keywords):
        scores['TRADING_CONCEPT'] += 3
    if any(k in blob for k in nuanced_keywords):
        scores['NUANCED_CONCEPT'] += 3
    if any(k in blob for k in macro_keywords):
        scores['MACRO_CONTEXT'] += 4
    if any(k in blob for k in risk_keywords):
        scores['RISK_EXECUTION'] += 3
    if any(k in blob for k in structure_keywords):
        scores['MARKET_STRUCTURE'] += 3

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top1, top2 = ranked[0], ranked[1]

    uncertain = (top1[1] <= 2) or ((top1[1] - top2[1]) <= 1)
    if uncertain:
        return 'REVIEW', True, top1[0], top2[0]

    return top1[0], False, top1[0], top2[0]


def main() -> int:
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': [], 'max_new_videos_per_run': 2})
    bundles = _j(BUNDLE_INDEX, [])
    ind_idx = _j(INDICATOR_INDEX, [])
    max_new = max(1, int(state.get('max_new_videos_per_run', MAX_NEW)))  # retained for telemetry/back-compat
    retry_queue = _load_retry_queue()
    category_by_id, category_by_name = _load_channel_categories()

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
        category_cfg = _resolve_channel_category_config(ch, category_by_id, category_by_name)
        channels_checked += 1
        latest = _fetch_latest(channel_id)
        if latest and not ch.get('last_seen_video_id'):
            ch['last_seen_video_id'] = latest[0]['video_id']
            seen_videos.add(latest[0]['video_id'])
        pending_items = [x for x in latest if x['video_id'] not in seen_videos]
        new_count = len(pending_items)
        new_total += new_count
        _log('YT_WATCH_CHECK', 'YT_WATCH_CHECK', f"channel={channel_id} new_count={new_count}", 'INFO')
        for item in pending_items:
            vid = item['video_id']
            if vid in seen_videos:
                dedup += 1
                continue

            duration_s = _fetch_video_duration_seconds(vid)
            if duration_s is not None and duration_s < SHORTS_MAX_SECONDS:
                _log('YT_VIDEO_SKIPPED_SHORT', 'SKIPPED_SHORT', f"SKIPPED_SHORT: {item['title']} ({duration_s}s)", 'INFO')
                seen_videos.add(vid)
                continue
            if duration_s is not None and duration_s > MAX_VIDEO_SECONDS:
                _log('YT_VIDEO_SKIPPED_LONG', 'SKIPPED_LONG', f"SKIPPED_LONG: {item['title']} ({duration_s}s)", 'INFO')
                _notify_watch_skip('SKIPPED_LONG', item['title'], duration_s)
                seen_videos.add(vid)
                continue

            if not _retry_allowed_now(retry_queue, vid):
                continue
            try:
                tr = _transcript(vid, item['title'])
                if str(tr.get('status', 'OK')).upper() == 'RETRY_LATER':
                    row = _queue_retry(retry_queue, vid, 'YOUTUBE_RATE_LIMIT', int(tr.get('retry_after_seconds') or 0))
                    _log('YT_TRANSCRIPT_RETRY', 'YT_TRANSCRIPT_RETRY', f"video_id={vid} attempts={row.get('attempts')} next_retry_at={row.get('next_retry_at')} status={row.get('status')}", 'WARN')
                    _notify_transcript_failure(vid, item['title'], f"RETRY_LATER: attempts={row.get('attempts')} next_retry_at={row.get('next_retry_at')}")
                    continue
                txt = tr.get('text', '')
                source_type = 'transcript' if tr.get('quality') == 'caption' else ('auto_transcript' if tr.get('quality') == 'auto_caption' else 'asr_transcript')
                rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', source_type, '--raw-text', txt, '--title', item['title'], '--author', ch.get('name', 'youtube'))
                _log('YT_VIDEO_INGESTED', 'YT_VIDEO_INGESTED', f"video_id={vid} method={tr.get('method','unknown')} quality={tr.get('quality','unknown')}", 'INFO', outputs=[rc['research_card_path']])
                if vid in retry_queue:
                    del retry_queue[vid]
            except Exception as e:
                _notify_transcript_failure(vid, item['title'], str(e))
                # fallback ingest so content-loop can still learn when transcript endpoint is unavailable for non-rate-limit reasons
                try:
                    raw = f"Manual concept ingest fallback. source_ref=https://www.youtube.com/watch?v={vid} title={item['title']} reason=TRANSCRIPT_UNAVAILABLE_AT_INGEST detail={str(e)[:280]}"
                    rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', 'youtube_url', '--raw-text', raw, '--title', item['title'], '--author', ch.get('name', 'youtube'))
                    _log('YT_VIDEO_INGESTED_FALLBACK', 'YT_VIDEO_INGESTED_FALLBACK', f"video_id={vid}", 'WARN', outputs=[rc['research_card_path']])
                except Exception:
                    failed += 1
                    continue

            if not _research_card_has_sufficient_content(rc['research_card_path']):
                _log('RESEARCH_CARD_REJECTED', 'insufficient_content', f"video_id={vid} reason=insufficient_content", 'WARN', outputs=[rc['research_card_path']])
                seen_videos.add(vid)
                continue

            content_category, needs_review, top1, top2 = _classify_video_category(item.get('title', ''), rc['research_card_path'], category_cfg)
            bundle_status = 'NEW'
            if needs_review:
                content_category = 'REVIEW_REQUIRED'
                bundle_status = 'REVIEW_REQUIRED'
                _log('YT_CATEGORY_REVIEW', 'YT_CATEGORY_REVIEW', f"video_id={vid} channel={ch.get('name','youtube')} top1={top1} top2={top2}", 'WARN')
                _notify_category_review(str(ch.get('name', 'youtube')), str(item.get('title', vid)), vid, top1, top2)
            elif content_category != str(category_cfg.get('active_category') or '').upper():
                _log('YT_CATEGORY_OVERRIDE', 'YT_CATEGORY_OVERRIDE', f"video_id={vid} from={category_cfg.get('active_category')} to={content_category}", 'INFO')

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
                'source_channel_name': str(ch.get('name', 'youtube')),
                'source_channel_id': channel_id,
                'content_category': content_category,
                'research_card_path': rc['research_card_path'],
                'indicator_record_paths': linked[:2],
                'linkmap_path': lm['linkmap_path'],
                'status': bundle_status,
            }
            _w(bpath, b)
            if bundle_status == 'REVIEW_REQUIRED':
                _log('BUNDLE_REVIEW_REQUIRED', 'BUNDLE_REVIEW_REQUIRED', f"source=youtube video_id={vid} category={content_category}", 'WARN', outputs=[str(bpath).replace('\\', '/')])
            else:
                _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=youtube video_id={vid} category={content_category}", 'INFO', outputs=[str(bpath).replace('\\', '/')])
                bundles = [str(bpath).replace('\\', '/')] + [x for x in bundles if x != str(bpath).replace('\\', '/')]
            seen_videos.add(vid)
            created.append(str(bpath).replace('\\', '/'))
            if bundle_status == 'NEW' and content_category in CONCEPT_CATEGORIES:
                concept_cards.append(str(rc['research_card_path']).replace('\\', '/'))
            processed += 1

        if latest and latest[0]['video_id'] in seen_videos:
            ch['last_seen_video_id'] = latest[0]['video_id']

    _w(BUNDLE_INDEX, bundles[:500])
    state['seen_video_ids'] = list(seen_videos)[-1000:]
    _w(STATE_PATH, state)
    _save_retry_queue(retry_queue)

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