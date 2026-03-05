#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _j(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')


def _hash_key(*parts: str) -> str:
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()


def _recent(path: Path, since: datetime) -> bool:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) >= since


def _run_entry_from_batch_run(batch_path: Path, r: dict, promotion_ptr: str | None = None, refinement_ptr: str | None = None) -> dict | None:
    bt_raw = str(r.get('backtest_result_path', '') or '')
    if not bt_raw:
        return None
    bt_path = Path(bt_raw)
    if not bt_path.exists() or bt_path.is_dir():
        return None
    bt = _j(bt_path)
    dataset_meta = str(r.get('dataset_meta_path', ''))
    strategy_spec = str(bt.get('inputs', {}).get('strategy_spec') or bt.get('inputs', {}).get('strategy_spec_path') or '')
    variant = str(bt.get('inputs', {}).get('variant') or r.get('variant_name') or '')
    sha = _hash_key(strategy_spec, variant, dataset_meta)
    res = bt.get('results', {})
    return {
        'id': bt.get('id'),
        'created_at': bt.get('created_at'),
        'strategy_spec_path': strategy_spec,
        'variant_name': variant,
        'fee_model_hash': bt.get('fee_model_hash') or bt.get('settings', {}).get('fee_model_hash'),
        'datasets_tested': [{'symbol': r.get('symbol'), 'timeframe': r.get('timeframe')}],
        'net_profit': res.get('net_profit', 0.0),
        'profit_factor': res.get('profit_factor', 0.0),
        'max_drawdown': res.get('max_drawdown', 0.0),
        'trades': res.get('total_trades', 0),
        'gate_pass': bool(r.get('gate_pass', True)),
        'sha256_inputs': sha,
        'pointers': {
            'backtest_result': str(bt_path),
            'trade_list': str(r.get('trade_list_path', '')),
            'refinement_cycle': refinement_ptr,
            'promotion_run': promotion_ptr,
            'batch_backtest': str(batch_path),
        },
    }


def _score(e: dict, initial_capital: float = 10000.0) -> float:
    pf = float(e.get('profit_factor', 0.0))
    # Guard sentinel/outlier PF from distorting ranking.
    if pf > 10.0:
        pf = 0.0
    dd_ratio = float(e.get('max_drawdown', 0.0)) / initial_capital
    trades = int(e.get('trades', 0))
    trade_penalty = 0.0 if trades >= 30 else (30 - trades) / 30.0
    gate_penalty = 0.0 if e.get('gate_pass') else 1.0
    return pf - dd_ratio - trade_penalty - gate_penalty


def _load_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        arr = _j(path)
        return arr if isinstance(arr, list) else []
    except Exception:
        return []


def _cap(items: list[dict], n: int) -> list[dict]:
    return items[:n]


def _ensure_fee_model_hash(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return entry
    if entry.get('fee_model_hash'):
        return entry
    bt_ptr = str(entry.get('pointers', {}).get('backtest_result') or '')
    if bt_ptr:
        try:
            bt = _j(Path(bt_ptr))
            fee_hash = bt.get('fee_model_hash') or bt.get('settings', {}).get('fee_model_hash')
            if fee_hash:
                entry['fee_model_hash'] = fee_hash
        except Exception:
            pass
    if 'fee_model_hash' not in entry:
        entry['fee_model_hash'] = None
    return entry


def _parse_created_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    txt = str(value).strip()
    try:
        return datetime.fromisoformat(txt.replace('Z', '+00:00')).astimezone(UTC)
    except Exception:
        return datetime.now(UTC)


def _passed_key(entry: dict) -> str:
    ptr = str(entry.get('pointers', {}).get('backtest_result') or '')
    return _hash_key(str(entry.get('sha256_inputs') or ''), ptr, str(entry.get('id') or ''))


def _load_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for ln in path.read_text(encoding='utf-8-sig', errors='ignore').splitlines():
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue
    return rows


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = '\n'.join(json.dumps(r, separators=(',', ':')) for r in rows)
    if body:
        body += '\n'
    path.write_text(body, encoding='utf-8')


def _collect_recent_passed(shards_dir: Path, days: int) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows: list[dict] = []
    if not shards_dir.exists():
        return rows
    for p in sorted(shards_dir.glob('*.passed.ndjson')):
        for r in _load_ndjson(p):
            if _parse_created_at(str(r.get('created_at') or '')) >= since:
                rows.append(r)
    dedup: dict[str, dict] = {}
    for r in rows:
        dedup[_passed_key(r)] = r
    return sorted(dedup.values(), key=lambda x: x.get('created_at', ''), reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--since-days', type=int, default=7)
    ap.add_argument('--artifacts-root', default='artifacts')
    ap.add_argument('--archive', action='store_true')
    ap.add_argument('--archive-days', type=int, default=30)
    ap.add_argument('--hot-days', type=int, default=7)
    ap.add_argument('--warm-days', type=int, default=14)
    args = ap.parse_args()

    artifacts_root = (ROOT / args.artifacts_root).resolve()
    lib_root = artifacts_root / 'library'
    run_idx_p = lib_root / 'RUN_INDEX.json'
    top_idx_p = lib_root / 'TOP_CANDIDATES.json'
    lessons_p = lib_root / 'LESSONS_INDEX.json'
    passed_idx_p = lib_root / 'PASSED_INDEX.json'  # backward-compat alias (hot window)
    passed_hot_p = lib_root / 'PASSED_HOT_7D.json'
    passed_warm_p = lib_root / 'PASSED_WARM_14D.json'
    passed_summary_p = lib_root / 'PASSED_INDEX_SUMMARY.json'
    passed_shards_dir = lib_root / 'passed'

    since = datetime.now(UTC) - timedelta(days=args.since_days)

    existing_runs = [_ensure_fee_model_hash(x) for x in _load_index(run_idx_p)]
    seen_sha = {x.get('sha256_inputs') for x in existing_runs if isinstance(x, dict)}

    promo_map = {}
    for p in (artifacts_root / 'promotions').rglob('*.promotion_run.json'):
        try:
            j = _j(p)
            sp = j.get('strategy_spec_artifact_path')
            if sp:
                promo_map[str(Path(sp))] = str(p)
        except Exception:
            continue

    refine_map = {}
    for p in (artifacts_root / 'refinement').rglob('*.refinement_cycle.json'):
        try:
            j = _j(p)
            sp = j.get('seed', {}).get('strategy_spec_path')
            if sp:
                refine_map[str(Path(sp))] = str(p)
        except Exception:
            continue

    new_entries = []
    for batch in (artifacts_root / 'batches').rglob('*.batch_backtest.json'):
        if not _recent(batch, since):
            continue
        bj = _j(batch)
        for r in bj.get('runs', []):
            e = _run_entry_from_batch_run(batch, r)
            if not e:
                continue
            sp_norm = str(Path(e['strategy_spec_path'])) if e.get('strategy_spec_path') else ''
            e['pointers']['promotion_run'] = promo_map.get(sp_norm)
            e['pointers']['refinement_cycle'] = refine_map.get(sp_norm)
            if e['sha256_inputs'] in seen_sha:
                e['status'] = 'DUPLICATE'
            else:
                e['status'] = 'NEW'
                seen_sha.add(e['sha256_inputs'])
            new_entries.append(e)

    combined_all = sorted([_ensure_fee_model_hash(x) for x in (existing_runs + new_entries)], key=lambda x: x.get('created_at', ''), reverse=True)

    # Preserve real winners permanently in index: 1.0 < PF <= 10.0.
    pinned = []
    remainder = []
    seen_ptr = set()

    for e in combined_all:
        ptr = str(e.get('pointers', {}).get('backtest_result') or '')
        if ptr and ptr in seen_ptr:
            continue
        if ptr:
            seen_ptr.add(ptr)

        try:
            pf = float(e.get('profit_factor', 0.0))
        except Exception:
            pf = 0.0

        # Drop invalid/sentinel outliers from RUN_INDEX.
        if pf > 10.0:
            continue

        if 1.0 < pf <= 10.0:
            pinned.append(e)
        else:
            remainder.append(e)

    pinned = sorted(pinned, key=lambda x: x.get('created_at', ''), reverse=True)
    remainder = sorted(remainder, key=lambda x: x.get('created_at', ''), reverse=True)

    if len(pinned) >= 500:
        combined = pinned[:500]
    else:
        combined = pinned + remainder[: (500 - len(pinned))]

    _write(run_idx_p, combined)

    # Passed library (scalable): append/merge into monthly shards (never capped), then expose hot/warm windows.
    if not passed_shards_dir.exists():
        passed_shards_dir.mkdir(parents=True, exist_ok=True)

    passed_source = [e for e in new_entries if bool(e.get('gate_pass', False))]
    # One-time seed when shards are empty: bootstrap from current combined view.
    if not list(passed_shards_dir.glob('*.passed.ndjson')):
        passed_source = [e for e in combined if bool(e.get('gate_pass', False))]

    by_month: dict[str, list[dict]] = {}
    for e in passed_source:
        dt = _parse_created_at(str(e.get('created_at') or ''))
        mon = dt.strftime('%Y-%m')
        by_month.setdefault(mon, []).append(e)

    for mon, items in by_month.items():
        shard = passed_shards_dir / f'{mon}.passed.ndjson'
        existing = _load_ndjson(shard)
        merged: dict[str, dict] = {}
        for r in existing:
            merged[_passed_key(r)] = r
        for r in items:
            merged[_passed_key(r)] = r
        out_rows = sorted(merged.values(), key=lambda x: x.get('created_at', ''), reverse=True)
        _write_ndjson(shard, out_rows)

    passed_hot = _collect_recent_passed(passed_shards_dir, days=args.hot_days)
    passed_warm = _collect_recent_passed(passed_shards_dir, days=args.warm_days)

    # Backward compat: PASSED_INDEX.json points at hot window for lightweight consumers.
    _write(passed_hot_p, passed_hot)
    _write(passed_warm_p, passed_warm)
    _write(passed_idx_p, passed_hot)

    # Future-proof summary index (small payload): aggregate windows + templates/families from warm window.
    by_family_passed: dict[str, int] = {}
    by_template_passed: dict[str, int] = {}
    for e in passed_warm:
        fam = Path(e.get('strategy_spec_path', 'unknown')).stem
        by_family_passed[fam] = by_family_passed.get(fam, 0) + 1
        tmpl = str(e.get('variant_name', '')).strip().lower() or 'unknown'
        by_template_passed[tmpl] = by_template_passed.get(tmpl, 0) + 1

    shard_files = sorted(passed_shards_dir.glob('*.passed.ndjson'))

    passed_summary = {
        'generated_at': datetime.now(UTC).isoformat(),
        'source': str(run_idx_p).replace('\\', '/'),
        'storage': {
            'type': 'monthly_ndjson_shards',
            'dir': str(passed_shards_dir).replace('\\', '/'),
            'shards': [p.name for p in shard_files],
        },
        'windows': {
            'hot_days': int(args.hot_days),
            'warm_days': int(args.warm_days),
            'hot_path': str(passed_hot_p).replace('\\', '/'),
            'warm_path': str(passed_warm_p).replace('\\', '/'),
            'hot_count': len(passed_hot),
            'warm_count': len(passed_warm),
        },
        'passed_index_path': str(passed_idx_p).replace('\\', '/'),
        'top_families': [
            {'family': k, 'count': v}
            for k, v in sorted(by_family_passed.items(), key=lambda kv: kv[1], reverse=True)[:50]
        ],
        'top_templates': [
            {'template': k, 'count': v}
            for k, v in sorted(by_template_passed.items(), key=lambda kv: kv[1], reverse=True)[:50]
        ],
    }
    _write(passed_summary_p, passed_summary)

    top_pool = [e for e in combined if e.get('status') != 'DUPLICATE']
    for e in top_pool:
        e['score'] = _score(e)
    top_pool.sort(key=lambda x: x.get('score', -999), reverse=True)
    top = _cap(top_pool, 100)
    _write(top_idx_p, top)

    by_family = {}
    for e in combined:
        fam = Path(e.get('strategy_spec_path', 'unknown')).stem
        by_family.setdefault(fam, []).append(e)
    lessons = []
    for fam, arr in by_family.items():
        if len(arr) < 2:
            continue
        all_weak = all((not x.get('gate_pass', False)) or float(x.get('profit_factor', 0.0)) < 1.0 for x in arr)
        if all_weak:
            lessons.append({
                'pattern': f'{fam}: repeated weak outcomes',
                'evidence_ptrs': [x.get('pointers', {}).get('backtest_result') for x in arr[:5]],
                'suggestion': 'Tighten entry quality or reduce execution churn before further sweeps.',
            })
    lessons = _cap(lessons, 50)
    _write(lessons_p, lessons)

    # Indicator dedup index (bounded)
    indicator_idx_path = lib_root / 'INDICATOR_INDEX.json'
    existing_ind = _load_index(indicator_idx_path)
    by_key = {str(x.get('tv_key')): x for x in existing_ind if isinstance(x, dict) and x.get('tv_key')}
    new_indicators_added = 0
    skipped_indicators_dedup = 0

    for ir_path in (artifacts_root / 'indicators').rglob('*.indicator_record.json'):
        try:
            ir = _j(ir_path)
        except Exception:
            continue
        name = str(ir.get('name', ''))
        author = str(ir.get('author', 'unknown'))
        tv_ref = str(ir.get('tv_ref', ''))
        script_id = tv_ref.split(':', 1)[1] if tv_ref.startswith('tradingview:') else ''
        tv_key = (name + '|' + author).strip().lower()
        row = {
            'tv_key': tv_key,
            'script_id': script_id or None,
            'name': name,
            'author': author,
            'indicator_record_path': str(ir_path).replace('\\', '/'),
            'first_seen_ts': str(ir.get('created_at') or datetime.now(UTC).isoformat()),
            'sources': ['librarian'],
        }
        if tv_key in by_key:
            skipped_indicators_dedup += 1
            prev = by_key[tv_key]
            src = prev.get('sources', []) if isinstance(prev.get('sources', []), list) else []
            prev['sources'] = (src + ['librarian'])[-10:]
        else:
            by_key[tv_key] = row
            new_indicators_added += 1

    indicator_rows = list(by_key.values())
    indicator_rows.sort(key=lambda x: str(x.get('first_seen_ts', '')), reverse=True)
    _write(indicator_idx_path, _cap(indicator_rows, 500))

    archived = None
    if args.archive:
        out = subprocess.check_output([
            PY, str((ROOT / 'scripts/pipeline/library_archive.py').resolve()),
            '--artifacts-root', str(artifacts_root),
            '--older-than-days', str(args.archive_days),
        ], text=True)
        archived = json.loads(out)

    print(json.dumps({
        'top_candidates_path': str(top_idx_p),
        'lessons_index_path': str(lessons_p),
        'run_index_path': str(run_idx_p),
        'passed_index_path': str(passed_idx_p),
        'passed_hot_path': str(passed_hot_p),
        'passed_warm_path': str(passed_warm_p),
        'passed_summary_path': str(passed_summary_p),
        'passed_shards_dir': str(passed_shards_dir),
        'top_count': len(top),
        'run_count': len(combined),
        'lessons_count': len(lessons),
        'passed_hot_count': len(passed_hot),
        'passed_warm_count': len(passed_warm),
        'example_top': top[0] if top else None,
        'new_indicators_added': new_indicators_added,
        'skipped_indicators_dedup': skipped_indicators_dedup,
        'archived': archived,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
