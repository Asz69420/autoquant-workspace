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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--since-days', type=int, default=7)
    ap.add_argument('--artifacts-root', default='artifacts')
    ap.add_argument('--archive', action='store_true')
    ap.add_argument('--archive-days', type=int, default=30)
    args = ap.parse_args()

    artifacts_root = (ROOT / args.artifacts_root).resolve()
    lib_root = artifacts_root / 'library'
    run_idx_p = lib_root / 'RUN_INDEX.json'
    top_idx_p = lib_root / 'TOP_CANDIDATES.json'
    lessons_p = lib_root / 'LESSONS_INDEX.json'

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

    combined = sorted([_ensure_fee_model_hash(x) for x in (existing_runs + new_entries)], key=lambda x: x.get('created_at', ''), reverse=True)
    combined = _cap(combined, 500)
    _write(run_idx_p, combined)

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
        'top_count': len(top),
        'run_count': len(combined),
        'lessons_count': len(lessons),
        'example_top': top[0] if top else None,
        'new_indicators_added': new_indicators_added,
        'skipped_indicators_dedup': skipped_indicators_dedup,
        'archived': archived,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
