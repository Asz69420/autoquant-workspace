#!/usr/bin/env python3
import json, subprocess, time
from pathlib import Path
from datetime import datetime, UTC

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / 'data' / 'state' / 'youtube_watchlist.json'
CHANNEL = {
    'name': 'DaviddTech',
    'url': 'https://www.youtube.com/@DaviddTech/videos',
    'enabled': True,
    'mode': 'CONCEPTS',
    'channel_id': 'UC7NJLsf6IonOy8QI8gt5BeA',
}
URL = CHANNEL['url']


def run(cmd, timeout=300):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def run_json(cmd, timeout=300):
    cp = run(cmd, timeout=timeout)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or f'command failed: {cmd}')[:1200])
    lines = (cp.stdout or '').strip().splitlines()
    if not lines:
        raise RuntimeError('empty json output')
    return json.loads(lines[-1])


def update_watchlist():
    data = json.loads(WATCHLIST.read_text(encoding='utf-8-sig'))
    channels = data.get('channels', [])
    found = False
    for ch in channels:
        if ch.get('channel_id') == CHANNEL['channel_id'] or ch.get('name') == CHANNEL['name'] or ch.get('url') == CHANNEL['url']:
            found = True
            for k, v in CHANNEL.items():
                ch[k] = v
            break
    if not found:
        channels.append(CHANNEL)
        data['channels'] = channels
    WATCHLIST.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return found


def get_latest_10():
    cp = run(['yt-dlp', '--flat-playlist', '--playlist-end', '10', '-J', URL], timeout=180)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or 'yt-dlp failed')[:2000])
    obj = json.loads(cp.stdout)
    out = []
    for e in obj.get('entries') or []:
        vid = e.get('id')
        if not vid:
            continue
        out.append({'id': vid, 'title': e.get('title') or vid, 'url': f'https://www.youtube.com/watch?v={vid}'})
    if len(out) < 10:
        raise RuntimeError(f'expected 10 videos, got {len(out)}')
    return out[:10]


def load_indicator_paths():
    for p in [ROOT / 'artifacts' / 'indicators' / 'INDEX.json', ROOT / 'indicators' / 'INDEX.json']:
        if p.exists():
            try:
                arr = json.loads(p.read_text(encoding='utf-8-sig'))
                if isinstance(arr, list):
                    return arr
            except Exception:
                pass
    return []


def ensure_bundle(video, rc_path, lm_path, resolver):
    day = datetime.now(UTC).strftime('%Y%m%d')
    bdir = ROOT / 'artifacts' / 'bundles' / day
    bdir.mkdir(parents=True, exist_ok=True)
    bpath = bdir / f"{video['id']}.bundle.json"
    bundle = {
        'id': f"bundle_{video['id']}",
        'created_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'source': 'youtube_manual',
        'source_ref': video['url'],
        'research_card_path': rc_path.replace('\\', '/'),
        'linkmap_path': lm_path.replace('\\', '/'),
        'indicator_record_paths': [],
        'status': 'NEW',
        'attempts': 0,
        'transcript_method': (resolver or {}).get('method', 'none'),
        'transcript_quality': (resolver or {}).get('quality', 'none'),
        'last_error': '' if (resolver or {}).get('ok') else 'TRANSCRIPT_UNAVAILABLE_AT_INGEST',
    }
    bpath.write_text(json.dumps(bundle, indent=2), encoding='utf-8')

    ipath = ROOT / 'artifacts' / 'bundles' / 'INDEX.json'
    index = []
    if ipath.exists():
        try:
            x = json.loads(ipath.read_text(encoding='utf-8-sig'))
            if isinstance(x, list):
                index = x
        except Exception:
            pass
    spath = str(bpath).replace('\\', '/')
    if spath in index:
        index.remove(spath)
    index.insert(0, spath)
    ipath.write_text(json.dumps(index, indent=2), encoding='utf-8')
    return spath


def summarize_card(card_path):
    c = json.loads(Path(card_path).read_text(encoding='utf-8-sig'))
    return c


def main():
    pre = update_watchlist()
    videos = get_latest_10()
    indicators_idx = load_indicator_paths()

    results, bundles = [], []
    concept_cards = []
    all_ind = set()
    rules, risk, params, comps, tfs = [], [], [], [], set()

    for i, v in enumerate(videos):
        print(f"[{i+1}/10] processing {v['id']}", flush=True)
        rec = {'video_id': v['id'], 'title': v['title'], 'url': v['url'], 'ok': False, 'reason': ''}
        try:
            resolver = run_json(['python', 'scripts/pipeline/transcript_resolver.py', '--video-id', v['id'], '--url', v['url']], timeout=360)
            txt = (resolver or {}).get('text') or ''
            if not txt:
                raise RuntimeError('transcript empty')
            st = 'transcript'
            if resolver.get('quality') == 'auto_caption': st = 'auto_transcript'
            if resolver.get('quality') == 'asr': st = 'asr_transcript'
            rc = run_json(['python', 'scripts/pipeline/emit_research_card.py', '--source-ref', v['url'], '--source-type', st, '--raw-text', txt, '--title', v['title'], '--author', 'DaviddTech'], timeout=180)
            lm = run_json(['python', 'scripts/pipeline/link_research_indicators.py', '--research-card-path', rc['research_card_path'], '--indicator-record-paths', json.dumps(indicators_idx)], timeout=120)
            bpath = ensure_bundle(v, rc['research_card_path'], lm['linkmap_path'], resolver)
            concept_cards.append(str(rc['research_card_path']).replace('\\', '/'))
            card = summarize_card(rc['research_card_path'])
            for x in card.get('indicators_mentioned', []) or []: all_ind.add(x)
            for x in card.get('extracted_rules', []) or []:
                if x not in rules: rules.append(x)
            for x in card.get('risk_management_notes', []) or []:
                if x not in risk: risk.append(x)
            for x in card.get('parameters_set', []) or []:
                if x not in params: params.append(x)
            for x in card.get('strategy_components', []) or []:
                if x not in comps: comps.append(x)
            for x in card.get('timeframes_mentioned', []) or []: tfs.add(x)
            bundles.append(bpath)
            rec['ok'] = True
            rec['reason'] = 'ingested'
        except subprocess.TimeoutExpired as e:
            rec['reason'] = f'timeout: {e.cmd}'
        except Exception as e:
            rec['reason'] = str(e)[:600]
        results.append(rec)
        if i < 9:
            print('sleeping 60s...', flush=True)
            time.sleep(60)

    if concept_cards:
        try:
            run_json(['python', 'scripts/pipeline/analyser_content_worker.py', '--research-cards-json', json.dumps(concept_cards), '--max-items', '2'], timeout=180)
        except Exception:
            pass

    out = {
        'watchlist_entry_preexisted': pre,
        'videos': videos,
        'results': results,
        'success_count': sum(1 for r in results if r['ok']),
        'failed': [r for r in results if not r['ok']],
        'key_indicators': sorted(all_ind),
        'strategy': {
            'entry_exit_rules': rules[:50],
            'timeframes': sorted(tfs),
            'risk_management': risk[:50],
            'parameters': params[:50],
            'components': comps[:50],
        },
        'bundle_paths': bundles,
    }
    rp = ROOT / 'artifacts' / 'daviddtech_ingest_report.json'
    rp.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({'report_path': str(rp).replace('\\', '/'), 'success_count': out['success_count'], 'failed_count': len(out['failed'])}))

if __name__ == '__main__':
    main()
