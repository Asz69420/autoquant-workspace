#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
INDICATOR_ARCHIVE_INDEX = ROOT / 'artifacts' / 'library' / 'INDICATOR_ARCHIVE_INDEX.json'
HOT_LIBRARY_CAP = 500
ARCHIVE_LIBRARY_CAP = 10000


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
            '--run-id', f"tv-catalog-{int(datetime.now(UTC).timestamp())}",
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


def _infer_indicator_hints(name: str) -> list[str]:
    tokens = (name or '').upper()
    known = ['MACD', 'EMA', 'SMA', 'RSI', 'ATR', 'VWAP', 'CCI', 'ADX', 'STOCH', 'BOLLINGER', 'ICHIMOKU', 'SUPER', 'KAMA', 'ALMA', 'T3', 'DONCHIAN', 'VORTEX', 'QQE', 'OBV']
    hints = []
    for k in known:
      if k in tokens:
        hints.append(k)
    return hints[:6]


def _fetch_script_context(url: str, title: str, author: str) -> str:
    if not url:
        return f'TradingView catalog indicator: {title} by {author}.'
    try:
        html = urlopen(url, timeout=20).read().decode('utf-8', errors='ignore')
    except Exception:
        return f'TradingView catalog indicator: {title} by {author}.'

    desc = ''
    m_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.I)
    if m_desc:
        desc = re.sub(r'\s+', ' ', m_desc.group(1)).strip()

    snippet = ''
    m_og = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html, re.I)
    if m_og:
        snippet = re.sub(r'\s+', ' ', m_og.group(1)).strip()

    hints = _infer_indicator_hints(title)
    hint_line = ('Possible indicators: ' + ', '.join(hints) + '.') if hints else ''
    parts = [
      f'TradingView indicator: {title} by {author}.',
      desc,
      snippet,
      hint_line,
      f'Source URL: {url}'
    ]
    text = ' '.join([p for p in parts if p])
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:4000]


def _emit_bundle(rc_path: str, ir_paths: list[str], key: str):
    lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc_path, '--indicator-record-paths', json.dumps(ir_paths))
    bday = datetime.now(UTC).strftime('%Y%m%d')
    safe = re.sub(r'[^a-zA-Z0-9._-]+', '_', key)[:32]
    bpath = ROOT / 'artifacts' / 'bundles' / bday / f'tv-{safe}.bundle.json'
    b = {'id': f'bundle_tv_{key[:16]}', 'created_at': datetime.now(UTC).isoformat(), 'source': 'tradingview_catalog', 'research_card_path': rc_path, 'indicator_record_paths': ir_paths, 'linkmap_path': lm['linkmap_path'], 'status': 'NEW'}
    _w(bpath, b)
    return str(bpath).replace('\\', '/')


def _ir_meta(ir_path: str) -> dict:
    try:
        return json.loads(Path(ir_path).read_text(encoding='utf-8-sig'))
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-new-indicators-per-run', type=int, default=2)
    ap.add_argument('--max-candidates-evaluated', type=int, default=20)
    args = ap.parse_args()
    max_new_indicators_per_run = max(1, int(args.max_new_indicators_per_run))
    max_candidates_evaluated = max(1, int(args.max_candidates_evaluated))

    st = _j(STATE_PATH, {'top_cursor': 0, 'trending_cursor': 0, 'seen_tv_keys': [], 'seen_script_ids': [], 'last_trending_seen': []})
    bundles = _j(BUNDLE_INDEX, [])
    idx = _j(INDICATOR_INDEX, [])
    archive_idx = _j(INDICATOR_ARCHIVE_INDEX, [])

    created = []
    added = 0
    skipped = 0
    invalid = 0
    grabber_ok = 0
    grabber_fail = 0
    too_large_skipped_count = 0

    top = _fetch_mode('top')
    _log('TV_CATALOG_CHECK', 'TV_CATALOG_CHECK', f'mode=TOP candidates={len(top)}', 'INFO')
    evaluated_count = 0
    if top:
        while evaluated_count < min(len(top), max_candidates_evaluated) and added < max_new_indicators_per_run:
            top_cursor = int(st.get('top_cursor', 0))
            idx_sel = top_cursor % len(top)
            cand = top[idx_sel]
            st['top_cursor'] = top_cursor + 1
            evaluated_count += 1
            key = _tv_key(cand['name'], cand['author'])

            if _is_invalid_candidate(cand['name'], cand['author']):
                _log('TV_CATALOG_PARSE_INVALID', 'TV_CATALOG_PARSE_INVALID', f"skip top candidate name={cand['name']} author={cand['author']}", 'WARN')
                skipped += 1
                invalid += 1
                continue
            if key in st['seen_tv_keys']:
                skipped += 1
                continue

            context_text = _fetch_script_context(cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), cand['name'], cand['author'])
            hint_list = _infer_indicator_hints(cand['name'])
            try:
                ir = _run('scripts/pipeline/emit_indicator_record.py', '--tv-ref', f"tradingview:{cand['script_id']}", '--url', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--name', cand['name'], '--author', cand['author'], '--version', 'v1', '--key-inputs', json.dumps(hint_list), '--signals', json.dumps(hint_list), '--notes', json.dumps(['catalog_top', 'source=tv_page_context']))
                _log('GRABBER_FETCH_OK', 'GRABBER_FETCH_OK', f"script_id={cand['script_id']} name={cand['name']}", 'INFO', outputs=[ir['indicator_record_path']])
                grabber_ok += 1
            except Exception:
                _log('GRABBER_FETCH_FAIL', 'GRABBER_FETCH_FAIL', f"script_id={cand['script_id']} name={cand['name']}", 'WARN')
                skipped += 1
                grabber_fail += 1
                continue

            ir_meta = _ir_meta(ir['indicator_record_path'])
            if ir_meta.get('pine_too_large') is True:
                too_large_skipped_count += 1
                _log('COMPONENT_TOO_LARGE', 'COMPONENT_TOO_LARGE', 'Component too large; skipped', 'WARN', outputs=[ir['indicator_record_path']])
            else:
                rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--source-type', 'tradingview_catalog', '--raw-text', context_text, '--title', cand['name'], '--author', cand['author'])
                bp = _emit_bundle(rc['research_card_path'], [ir['indicator_record_path']], key)
                created.append(bp)
                _log('TV_INDICATOR_ADDED', 'TV_INDICATOR_ADDED', f"script_id={cand['script_id']} tv_key={key}", 'INFO', outputs=[ir['indicator_record_path']])
                _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=tradingview_catalog tv_key={key}", 'INFO', outputs=[bp])

            row = {'tv_key': key, 'script_id': cand['script_id'], 'name': cand['name'], 'author': cand['author'], 'indicator_record_path': ir['indicator_record_path'], 'first_seen_ts': datetime.now(UTC).isoformat(), 'sources': ['top']}
            idx = [row] + [x for x in idx if x.get('tv_key') != key]
            archive_idx = [row] + [x for x in archive_idx if x.get('tv_key') != key]
            st['seen_tv_keys'].append(key)
            st['seen_script_ids'].append(cand['script_id'])
            added += 1


    tr = _fetch_mode('trending')
    _log('TV_CATALOG_CHECK', 'TV_CATALOG_CHECK', f'mode=TRENDING candidates={len(tr)}', 'INFO')
    trending_evaluated = 0
    if tr:
        while trending_evaluated < min(len(tr), max_candidates_evaluated) and added < max_new_indicators_per_run:
            trending_cursor = int(st.get('trending_cursor', 0))
            idx_sel = trending_cursor % len(tr)
            cand = tr[idx_sel]
            st['trending_cursor'] = trending_cursor + 1
            trending_evaluated += 1

            key = _tv_key(cand['name'], cand['author'])
            if _is_invalid_candidate(cand['name'], cand['author']):
                _log('TV_CATALOG_PARSE_INVALID', 'TV_CATALOG_PARSE_INVALID', f"skip trending candidate name={cand['name']} author={cand['author']}", 'WARN')
                skipped += 1
                invalid += 1
                continue
            if key in st['seen_tv_keys']:
                skipped += 1
                continue

            context_text = _fetch_script_context(cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), cand['name'], cand['author'])
            hint_list = _infer_indicator_hints(cand['name'])
            try:
                ir = _run('scripts/pipeline/emit_indicator_record.py', '--tv-ref', f"tradingview:{cand['script_id']}", '--url', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--name', cand['name'], '--author', cand['author'], '--version', 'v1', '--key-inputs', json.dumps(hint_list), '--signals', json.dumps(hint_list), '--notes', json.dumps(['catalog_trending', 'source=tv_page_context']))
                _log('GRABBER_FETCH_OK', 'GRABBER_FETCH_OK', f"script_id={cand['script_id']} name={cand['name']}", 'INFO', outputs=[ir['indicator_record_path']])
                grabber_ok += 1
            except Exception:
                _log('GRABBER_FETCH_FAIL', 'GRABBER_FETCH_FAIL', f"script_id={cand['script_id']} name={cand['name']}", 'WARN')
                skipped += 1
                grabber_fail += 1
                continue

            ir_meta = _ir_meta(ir['indicator_record_path'])
            if ir_meta.get('pine_too_large') is True:
                too_large_skipped_count += 1
                _log('COMPONENT_TOO_LARGE', 'COMPONENT_TOO_LARGE', 'Component too large; skipped', 'WARN', outputs=[ir['indicator_record_path']])
            else:
                rc = _run('scripts/pipeline/emit_research_card.py', '--source-ref', cand.get('url', f"https://www.tradingview.com/script/{cand['script_id']}/"), '--source-type', 'tradingview_catalog', '--raw-text', context_text, '--title', cand['name'], '--author', cand['author'])
                bp = _emit_bundle(rc['research_card_path'], [ir['indicator_record_path']], key)
                created.append(bp)
                _log('TV_INDICATOR_ADDED', 'TV_INDICATOR_ADDED', f"script_id={cand['script_id']} tv_key={key}", 'INFO', outputs=[ir['indicator_record_path']])
                _log('BUNDLE_CREATED', 'BUNDLE_CREATED', f"source=trending tv_key={key}", 'INFO', outputs=[bp])

            row = {'tv_key': key, 'script_id': cand['script_id'], 'name': cand['name'], 'author': cand['author'], 'indicator_record_path': ir['indicator_record_path'], 'first_seen_ts': datetime.now(UTC).isoformat(), 'sources': ['trending']}
            idx = [row] + [x for x in idx if x.get('tv_key') != key]
            archive_idx = [row] + [x for x in archive_idx if x.get('tv_key') != key]
            st['seen_tv_keys'].append(key)
            st['seen_script_ids'].append(cand['script_id'])
            st['last_trending_seen'].append(key)
            added += 1

    _w(INDICATOR_INDEX, idx[:HOT_LIBRARY_CAP])
    _w(INDICATOR_ARCHIVE_INDEX, archive_idx[:ARCHIVE_LIBRARY_CAP])
    _w(STATE_PATH, {**st, 'top_cursor': int(st.get('top_cursor', 0)), 'trending_cursor': int(st.get('trending_cursor', 0)), 'seen_tv_keys': st['seen_tv_keys'][-1000:], 'seen_script_ids': st['seen_script_ids'][-1000:], 'last_trending_seen': st['last_trending_seen'][-50:]})
    _w(BUNDLE_INDEX, (created + bundles)[:500])
    g_status = 'OK'
    if grabber_fail > 0 and grabber_ok == 0:
        g_status = 'FAIL'
    elif grabber_fail > 0 or grabber_ok == 0 or too_large_skipped_count > 0:
        g_status = 'WARN'
    tv_status = 'OK'
    if added == 0 and (grabber_fail > 0 or invalid > 0):
        tv_status = 'FAIL'
    elif added == 0 or skipped > 0 or invalid > 0:
        tv_status = 'WARN'
    _log('GRABBER_SUMMARY', 'GRABBER_SUMMARY', f"Grabber: fetched={grabber_ok} dedup={skipped} failed={grabber_fail} too_large_skipped_count={too_large_skipped_count}", g_status, agent='Grabber')
    _log('TV_CATALOG_SUMMARY', 'TV_CATALOG_SUMMARY', f"TV: mode=TOP/TRENDING added={added} dedup={skipped} invalid={invalid} too_large_skipped={too_large_skipped_count}", tv_status, agent='TV Catalog')
    print(json.dumps({'created_bundles': created, 'new_indicators_added': added, 'skipped_dedup': skipped, 'invalid': invalid, 'grabber_ok': grabber_ok, 'grabber_fail': grabber_fail, 'too_large_skipped_count': too_large_skipped_count}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
