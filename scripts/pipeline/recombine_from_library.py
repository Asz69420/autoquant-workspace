#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INDICATOR_INDEX = ROOT / 'artifacts' / 'library' / 'INDICATOR_INDEX.json'
LESSONS_INDEX = ROOT / 'artifacts' / 'library' / 'LESSONS_INDEX.json'
STRATEGY_INDEX = ROOT / 'artifacts' / 'strategy_specs' / 'INDEX.json'
RESEARCH_INDEX = ROOT / 'artifacts' / 'research' / 'INDEX.json'
BUNDLE_INDEX = ROOT / 'artifacts' / 'bundles' / 'INDEX.json'

TEMPLATES = [
    {
        'name': 'EMA_TREND_ATR_EXITS',
        'description': 'EMA trend filter with ATR stop/target envelope.',
        'scaffold': 'EMA trend + ATR exits',
    },
    {
        'name': 'EMA_CROSS_ATR_EXITS',
        'description': 'EMA cross trigger with ATR exits and confidence gate.',
        'scaffold': 'EMA cross + ATR exits',
    },
    {
        'name': 'VWAP_MEAN_REVERSION_ATR_EXITS',
        'description': 'VWAP mean-reversion entries with ATR risk controls.',
        'scaffold': 'VWAP mean reversion + ATR exits',
    },
]


def _j(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _w(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        json.dump(obj, f, indent=2)


def _to_ts(v: str | None) -> float:
    if not v:
        return 0.0
    s = str(v).replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def _times_used(row: dict) -> int:
    if isinstance(row.get('times_used'), int):
        return int(row['times_used'])
    src = row.get('sources') if isinstance(row.get('sources'), list) else []
    return max(0, len(src) - 1)


def _least_recent_ts(row: dict) -> float:
    for key in ('last_used_at', 'least_recently_used', 'last_seen_ts', 'first_seen_ts'):
        if row.get(key):
            return _to_ts(str(row.get(key)))
    return 0.0


def _newest_fallback_ts(row: dict) -> float:
    # Newest as deterministic final tie-break fallback
    for key in ('first_seen_ts', 'created_at'):
        if row.get(key):
            return _to_ts(str(row.get(key)))
    return 0.0


def _pick_indicator(rows: list[dict]) -> dict | None:
    candidates = [r for r in rows if isinstance(r, dict) and r.get('indicator_record_path')]
    if not candidates:
        return None
    candidates.sort(
        key=lambda r: (
            _times_used(r),
            _least_recent_ts(r),
            -_newest_fallback_ts(r),
            str(r.get('tv_key', '')).lower(),
        )
    )
    for r in candidates:
        p = str(r.get('indicator_record_path', '')).replace('\\', '/')
        if p and (ROOT / p).exists():
            return r
    return None


def _pick_template(indicator_key: str) -> dict:
    h = int(hashlib.sha256(indicator_key.encode('utf-8')).hexdigest(), 16)
    return TEMPLATES[h % len(TEMPLATES)]


def _pick_recent(list_path: Path, limit: int = 3) -> list[str]:
    arr = _j(list_path, [])
    if not isinstance(arr, list):
        return []
    out = []
    for p in arr:
        sp = str(p)
        if sp and (ROOT / sp).exists():
            out.append(sp.replace('\\', '/'))
        if len(out) >= limit:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output-root', default='artifacts/bundles')
    args = ap.parse_args()

    indicators = _j(INDICATOR_INDEX, [])
    indicator = _pick_indicator(indicators)
    if not indicator:
        # Fallback to any local indicator record (newest first)
        all_ir = sorted((ROOT / 'artifacts' / 'indicators').rglob('*.indicator_record.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        if all_ir:
            irp = all_ir[0]
            try:
                irj = json.loads(irp.read_text(encoding='utf-8'))
            except Exception:
                irj = {}
            indicator = {
                'name': irj.get('name', irp.stem),
                'author': irj.get('author', 'unknown'),
                'tv_key': (str(irj.get('name', irp.stem)) + '|'+ str(irj.get('author', 'unknown'))).lower(),
                'indicator_record_path': str(irp.relative_to(ROOT)).replace('\\', '/'),
                'sources': ['fallback_scan'],
            }
        else:
            print(json.dumps({
                'status': 'WARN',
                'reason_code': 'NO_INDICATOR_INDEX',
                'created': 0,
                'bundle_path': '',
            }))
            return 0

    indicator_path = str(indicator.get('indicator_record_path', '')).replace('\\', '/')
    ind_abs = ROOT / indicator_path
    if not ind_abs.exists():
        print(json.dumps({
            'status': 'WARN',
            'reason_code': 'INDICATOR_RECORD_MISSING',
            'created': 0,
            'bundle_path': '',
            'indicator_record_path': indicator_path,
        }))
        return 0

    template = _pick_template(str(indicator.get('tv_key') or indicator.get('name') or indicator_path))

    lessons = _pick_recent(LESSONS_INDEX, limit=3)
    recent_specs = _pick_recent(STRATEGY_INDEX, limit=3)
    research_refs = _pick_recent(RESEARCH_INDEX, limit=2)

    day = datetime.now(UTC).strftime('%Y%m%d')
    stamp = datetime.now(UTC).strftime('%Y%m%d%H%M%S')
    suffix = hashlib.sha256(f"{indicator_path}|{template['name']}|{stamp}".encode('utf-8')).hexdigest()[:8]
    rid = f'recombine-{stamp}-{suffix}'

    research_dir = ROOT / 'artifacts' / 'research' / day
    research_dir.mkdir(parents=True, exist_ok=True)
    raw_path = research_dir / f'{rid}.raw.txt'
    raw_text = (
        f"Library recombine candidate. Indicator: {indicator.get('name','unknown')} by {indicator.get('author','unknown')}. "
        f"Template scaffold: {template['scaffold']}. "
        f"Use as trend/confirmation/regime gate and emit executable strategy variants."
    )
    raw_path.write_text(raw_text, encoding='utf-8')

    card = {
        'schema_version': '1.0',
        'id': rid,
        'created_at': datetime.now(UTC).isoformat(),
        'source_type': 'library_recombine',
        'source_ref': f'library://recombine/{rid}',
        'title': f"Library Recombine: {indicator.get('name','indicator')} + {template['scaffold']}",
        'author': 'autopilot',
        'summary_bullets': [
            f"Recombine existing indicator {indicator.get('name','indicator')} with {template['scaffold']}.",
            f"Template: {template['description']}",
            'Objective: generate executable variants and avoid starvation without new external inputs.',
        ],
        'creator_notes': [
            {'timestamp': None, 'quote': 'Deterministic library recombine', 'note': 'Use least-used indicator first.'},
        ],
        'extracted_rules': [
            f"Apply scaffold {template['scaffold']} with ATR-based deterministic exits.",
            'Use indicator as trend/confirmation/regime gate depending on variant role.',
        ],
        'indicators_mentioned': [str(indicator.get('name', 'indicator'))],
        'tv_search_hints': [
            {
                'name': str(indicator.get('name', 'indicator')),
                'keywords': [k for k in str(indicator.get('name', '')).lower().split(' ') if k][:5],
                'confidence': 0.7,
                'author_hint': str(indicator.get('author', 'unknown')),
            }
        ],
        'timeframes_mentioned': ['1h'],
        'assets_mentioned': ['BTC'],
        'tags': ['recombine', 'library', 'pipeline-stage2'],
        'raw_pointer': str(raw_path).replace('\\', '/'),
        'truncated': False,
        'recombine_meta': {
            'template_name': template['name'],
            'template_scaffold': template['scaffold'],
            'indicator_record_path': indicator_path,
            'indicator_tv_key': indicator.get('tv_key'),
            'lessons_refs': lessons,
            'recent_strategy_specs': recent_specs,
            'recent_research_refs': research_refs,
        },
    }

    card_path = research_dir / f'{rid}.research_card.json'
    _w(card_path, card)

    bundle_rel = f"{args.output_root}/{day}/{rid}.bundle.json".replace('\\', '/')
    bundle_path = ROOT / bundle_rel
    bundle = {
        'id': f'bundle_{rid}',
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'library_recombine',
        'research_card_path': str(card_path.relative_to(ROOT)).replace('\\', '/'),
        'indicator_record_paths': [indicator_path],
        'linkmap_path': '',
        'status': 'NEW',
        'recombine': {
            'template_name': template['name'],
            'template_scaffold': template['scaffold'],
            'indicator_name': indicator.get('name'),
            'indicator_tv_key': indicator.get('tv_key'),
        },
    }
    _w(bundle_path, bundle)

    bundles = _j(BUNDLE_INDEX, [])
    if not isinstance(bundles, list):
        bundles = []
    brel = str(bundle_path.relative_to(ROOT)).replace('\\', '/')
    bundles = [brel] + [x for x in bundles if str(x) != brel]
    _w(BUNDLE_INDEX, bundles[:500])

    print(json.dumps({
        'status': 'OK',
        'reason_code': None,
        'created': 1,
        'bundle_path': brel,
        'indicator_name': indicator.get('name', 'unknown'),
        'template_name': template['name'],
        'research_card_path': str(card_path.relative_to(ROOT)).replace('\\', '/'),
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
