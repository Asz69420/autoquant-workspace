#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
from urllib.request import urlopen
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
STATE_PATH = ROOT / 'data' / 'state' / 'tv_catalog_state.json'
BUNDLE_INDEX = ROOT / 'artifacts' / 'bundles' / 'INDEX.json'
INDICATOR_INDEX = ROOT / 'artifacts' / 'library' / 'INDICATOR_INDEX.json'


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
            '--run-id', f"tv-catalog-{int(datetime.now(UTC).timestamp())}",
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


def _tv_key(name: str, author: str) -> str:
    return re.sub(r'\s+', ' ', f'{name}|{author}'.strip().lower())


def _fetch_mode(mode: str):
    url = 'https://www.tradingview.com/scripts/'
    html = urlopen(url, timeout=20).read().decode('utf-8', errors='ignore')

    out = []
    seen = set()
    patt = re.compile(r'href="(https://www\.tradingview\.com/script/([A-Za-z0-9]+)[^"]*)"[^>]*data-qa-id="ui-lib-card-link-title"[^>]*>([^<]+)</a>', re.I)
    for m in patt.finditer(html):
        full_url, sid, raw_title = m.group(1), m.group(2), m.group(3)
        title = re.sub(r'\s+', ' ', raw_title).strip()
        chunk = html[m.end(): m.end() + 25000]
        ma = re.search(r'href="/u/[^"]+"[^>]*data-username="([^"]+)"', chunk, re.I)
        author = re.sub(r'\s+', ' ', ma.group(1)).strip() if ma else ''
        key = (sid, title, author)
        if key in seen:
            continue
        seen.add(key)
        out.append({'script_id': sid, 'url': full_url, 'name': title, 'author': author})

    if mode == 'top':
        return out[:30]
    return out[10:40]


def _is_invalid_candidate(name: str, author: str) -> bool:
    bad_fragments = ['adds volume', 'down ltf candle', '\n', '\r', 'open)']
    n = (name or '').lower()
    if not author or not author.strip():
        return True
    return any(x in n for x in bad_fragments)


def _emit_bundle(rc_path: str, ir_paths: list[str], key: str):
    lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc_path, '--indicator-record-paths', json.dumps(ir_paths))
    bday = datetime.now(UTC).strftime('%Y%m%d')
    safe = re.sub(r'[^a-zA-Z0-9._-]+', '_', key)[:32]
    bpath = ROOT / 'artifacts' / 'bundles' / bday / f'tv-{safe}.bundle.json'
    b = {'id': f'bundle_tv_{key[:16]}', 'created_at': datetime.now(UTC).isoformat(), 'source': 'tradingview_catalog', 'research_card_path': rc_path, 'indicator_record_paths': ir_paths, 'linkmap_path': lm['linkmap_path'], 'status': 'NEW'}
    _w(bpath, b)
    return str(bpath).replace('\\', '/')


def main() -> int:
    st = _j(STATE_PATH, {'top_cursor': 0, 'seen_tv_keys': [], 'seen_script_ids': [], 'last_trending_seen': []})
    bundles = _j(BUNDLE_INDEX, [])
    idx = _j(INDICATOR_INDEX, [])
    by_key = {x.get('tv_key'): x for x in idx if isinstance(x, dict)}

    created = []
    added = 0
    skipped = 0

    top = _fetch_mode('top')
    _log('TV_CATALOG_CHECK', 'TV_CATALOG_CHECK', f'mode=TOP candidates={len(top)}', 'INFO')
    if top:
        c = st.get('top_cursor', 0) % len(top)
        cand = top[c]
        st['top_cursor'] = c + 1
        key = _tv_key(cand['name'], cand['author'])
        if _is_invalid_candidate(cand['name'], cand['author']):
            _log('TV_CATALOG_PARSE_INVALID', 'TV_CATALOG_PARSE_INVALID', f"skip top candidate name={cand['name']} author={cand['author']}", 'WARN')
            skipped += 1
        elif key not in st['seen_tv_keys']:
            try:
                ir = _run('scripts/pipeline/emit_indicator_record.py', '--tv-ref', f"tradingview:{cand['script_id']}", '--url', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--name', cand['name'], '--author', cand['author'], '--version', 'v1', '--key-inputs', json.dumps([]), '--signals', json.dumps([]), '--notes', json.dumps(['catalog_top']))
                _log('GRABBER_FETCH_OK', 'GRABBER_FETCH_OK', f"script_id={cand['script_id']} name={cand['name']}", 'INFO', outputs=[ir['indicator_record_path']])
            except Exception:
                _log('GRABBER_FETCH_FAIL', 'GRABBER_FETCH_FAIL', f"script_id={cand['script_id']} name={cand['name']}", 'WARN')
                skipped += 1
                ir = None
            if not ir:
                pass
            else:
                rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--source-type', 'tradingview_catalog', '--raw-text', f"Top catalog indicator: {cand['name']} by {cand['author']}", '--title', cand['name'], '--author', cand['author'])
                bp = _emit_bundle(rc['research_card_path'], [ir['indicator_record_path']], key)
                created.append(bp)
                _log('TV_INDICATOR_ADDED', 'TV_INDICATOR_ADDED', f"script_id={cand['script_id']} tv_key={key}", 'INFO', outputs=[ir['indicator_record_path']])
                _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=tradingview_catalog tv_key={key}", 'INFO', outputs=[bp])
            row = {'tv_key': key, 'script_id': cand['script_id'], 'name': cand['name'], 'author': cand['author'], 'indicator_record_path': ir['indicator_record_path'], 'first_seen_ts': datetime.now(UTC).isoformat(), 'sources': ['top']}
            idx = [row] + [x for x in idx if x.get('tv_key') != key]
            st['seen_tv_keys'].append(key)
            st['seen_script_ids'].append(cand['script_id'])
            added += 1
        else:
            skipped += 1

    tr = _fetch_mode('trending')
    _log('TV_CATALOG_CHECK', 'TV_CATALOG_CHECK', f'mode=TRENDING candidates={len(tr)}', 'INFO')
    for cand in tr[:8]:
        if len(created) >= 3:
            break
        key = _tv_key(cand['name'], cand['author'])
        if _is_invalid_candidate(cand['name'], cand['author']):
            _log('TV_CATALOG_PARSE_INVALID', 'TV_CATALOG_PARSE_INVALID', f"skip trending candidate name={cand['name']} author={cand['author']}", 'WARN')
            skipped += 1
            continue
        if key in st['seen_tv_keys']:
            skipped += 1
            continue
        try:
            ir = _run('scripts/pipeline/emit_indicator_record.py', '--tv-ref', f"tradingview:{cand['script_id']}", '--url', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--name', cand['name'], '--author', cand['author'], '--version', 'v1', '--key-inputs', json.dumps([]), '--signals', json.dumps([]), '--notes', json.dumps(['catalog_trending']))
            _log('GRABBER_FETCH_OK', 'GRABBER_FETCH_OK', f"script_id={cand['script_id']} name={cand['name']}", 'INFO', outputs=[ir['indicator_record_path']])
        except Exception:
            _log('GRABBER_FETCH_FAIL', 'GRABBER_FETCH_FAIL', f"script_id={cand['script_id']} name={cand['name']}", 'WARN')
            skipped += 1
            continue
        rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--source-type', 'tradingview_catalog', '--raw-text', f"Trending catalog indicator: {cand['name']} by {cand['author']}", '--title', cand['name'], '--author', cand['author'])
        bp = _emit_bundle(rc['research_card_path'], [ir['indicator_record_path']], key)
        created.append(bp)
        _log('TV_INDICATOR_ADDED', 'TV_INDICATOR_ADDED', f"script_id={cand['script_id']} tv_key={key}", 'INFO', outputs=[ir['indicator_record_path']])
        _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=trending tv_key={key}", 'INFO', outputs=[bp])
        row = {'tv_key': key, 'script_id': cand['script_id'], 'name': cand['name'], 'author': cand['author'], 'indicator_record_path': ir['indicator_record_path'], 'first_seen_ts': datetime.now(UTC).isoformat(), 'sources': ['trending']}
        idx = [row] + [x for x in idx if x.get('tv_key') != key]
        st['seen_tv_keys'].append(key)
        st['seen_script_ids'].append(cand['script_id'])
        st['last_trending_seen'].append(key)
        added += 1
        if len(st['last_trending_seen']) >= 2:
            break

    _w(INDICATOR_INDEX, idx[:500])
    _w(STATE_PATH, {**st, 'seen_tv_keys': st['seen_tv_keys'][-1000:], 'seen_script_ids': st['seen_script_ids'][-1000:], 'last_trending_seen': st['last_trending_seen'][-50:]})
    _w(BUNDLE_INDEX, (created + bundles)[:500])
    print(json.dumps({'created_bundles': created, 'new_indicators_added': added, 'skipped_dedup': skipped}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())