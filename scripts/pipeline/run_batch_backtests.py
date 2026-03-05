#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

try:
    _BACKTESTER_DIR = ROOT / 'scripts' / 'backtester'
    if str(_BACKTESTER_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKTESTER_DIR))
    from signal_templates import resolve_template  # type: ignore
except Exception:
    resolve_template = None


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _days_between(start: str, end: str) -> int:
    s = datetime.fromisoformat(start.replace('Z', '+00:00'))
    e = datetime.fromisoformat(end.replace('Z', '+00:00'))
    return (e - s).days


def _latest_meta(symbol: str, timeframe: str) -> str:
    d = ROOT / 'artifacts' / 'data' / 'hyperliquid' / symbol / timeframe
    metas = sorted(d.glob('*.meta.json'))
    if not metas:
        raise FileNotFoundError(f'No dataset meta found for {symbol} {timeframe}')

    scored: list[tuple[int, str, Path]] = []
    for m in metas:
        meta = _load_json(m)
        start = str(meta.get('start') or '')
        end = str(meta.get('end') or '')
        span_days = _days_between(start, end) if start and end else -1
        scored.append((span_days, end, m))

    preferred = [x for x in scored if x[0] >= 700]
    pool = preferred if preferred else scored
    best = sorted(pool, key=lambda x: (x[0], x[1]))[-1][2]
    return str(best)


def _resolve_datasets(arg: str) -> list[str]:
    if arg == 'default':
        return [
            _latest_meta('BTC', '15m'),
            _latest_meta('BTC', '1h'),
            _latest_meta('BTC', '4h'),
            _latest_meta('ETH', '15m'),
            _latest_meta('ETH', '1h'),
            _latest_meta('ETH', '4h'),
            _latest_meta('SOL', '15m'),
            _latest_meta('SOL', '1h'),
            _latest_meta('SOL', '4h'),
        ]
    p = Path(arg)
    if p.exists():
        if p.suffix == '.json' and str(p).endswith('.meta.json'):
            return [str(p)]
        loaded = json.loads(p.read_text(encoding='utf-8-sig'))
        if isinstance(loaded, list) and loaded:
            return [str(x) for x in loaded]
        raise ValueError('--datasets file must be a non-empty JSON array of meta paths, or a single *.meta.json path')
    return [x.strip() for x in arg.split(',') if x.strip()]


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def _is_allowed_spec_source(spec: dict) -> bool:
    src = str(spec.get('source') or '').strip().lower()
    return src == 'claude-advisor'


def _load_advisory_enforcement(advisory_path: str) -> dict:
    out = {
        'exclude_assets': set(),
        'exclude_timeframes': set(),
        'blacklist_templates': set(),
        'blacklist_directives': set(),
    }
    p = Path(advisory_path)
    if not p.exists():
        return out

    txt = p.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'##\s*Machine\s+Directives.*?```json\s*(\[.*?\])\s*```', txt, re.S | re.I)
    if not m:
        return out

    try:
        directives = json.loads(m.group(1))
    except Exception:
        return out

    if not isinstance(directives, list):
        return out

    for d in directives:
        if not isinstance(d, dict):
            continue
        action = str(d.get('action') or '').upper()
        target = str(d.get('target') or '').strip()
        if action == 'EXCLUDE_ASSET' and target:
            # Policy override: never hard-block assets via advisory directives.
            continue
        elif action == 'EXCLUDE_TIMEFRAME' and target:
            # Policy override: never hard-block timeframes via advisory directives.
            continue
        elif action == 'BLACKLIST_TEMPLATE' and target:
            out['blacklist_templates'].add(target.lower())
        elif action == 'BLACKLIST_DIRECTIVE' and target:
            out['blacklist_directives'].add(target.upper())

    return out


def _variant_resolved_signature(
    variant_obj: dict,
    symbol: str,
    timeframe: str,
    strategy_scope: str = '',
) -> str:
    template_name = ''
    if resolve_template is not None:
        try:
            template_name = str(resolve_template(variant_obj) or '')
        except Exception:
            template_name = ''

    params = {}
    for p in (variant_obj.get('parameters') or []):
        if isinstance(p, dict) and p.get('name') is not None:
            params[str(p.get('name'))] = p.get('default')

    risk_policy = variant_obj.get('risk_policy') or {}
    execution_policy = variant_obj.get('execution_policy') or {}

    sig_obj = {
        'strategy_scope': strategy_scope,
        'template': template_name,
        'params': params,
        'risk_policy': {
            'stop_type': risk_policy.get('stop_type'),
            'stop_atr_mult': risk_policy.get('stop_atr_mult'),
            'tp_type': risk_policy.get('tp_type'),
            'tp_atr_mult': risk_policy.get('tp_atr_mult'),
            'risk_per_trade_pct': risk_policy.get('risk_per_trade_pct'),
        },
        'execution_policy': {
            'entry_fill': execution_policy.get('entry_fill'),
            'tie_break': execution_policy.get('tie_break'),
            'allow_reverse': execution_policy.get('allow_reverse'),
        },
        'symbol': symbol,
        'timeframe': timeframe,
    }
    raw = json.dumps(sig_obj, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _index_historical_signatures(lookback_days: int = 90, max_entries: int = 5000) -> set[str]:
    idx_path = ROOT / 'artifacts' / 'library' / 'RUN_INDEX.json'
    if not idx_path.exists():
        return set()

    entries = _load_json(idx_path)
    if not isinstance(entries, list):
        return set()

    cutoff = datetime.now(UTC) - timedelta(days=max(0, lookback_days))
    selected = entries[-max_entries:] if max_entries > 0 else entries
    out: set[str] = set()
    spec_cache: dict[str, dict] = {}

    for item in selected:
        try:
            created = str(item.get('created_at') or '')
            if created:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=UTC)
                if created_dt.astimezone(UTC) < cutoff:
                    continue

            ds = item.get('datasets_tested') or []
            if not ds:
                continue
            d0 = ds[0] if isinstance(ds, list) else ds
            symbol = str(d0.get('symbol') or '').upper()
            timeframe = str(d0.get('timeframe') or '').lower()
            if not symbol or not timeframe:
                continue

            spec_path = str(item.get('strategy_spec_path') or '')
            variant_name = str(item.get('variant_name') or '')
            if not spec_path or not variant_name:
                continue

            abs_spec = str((ROOT / spec_path).resolve()) if not Path(spec_path).is_absolute() else spec_path
            if abs_spec not in spec_cache:
                p = Path(abs_spec)
                if not p.exists():
                    spec_cache[abs_spec] = {}
                else:
                    spec_cache[abs_spec] = _load_json(p)
            spec = spec_cache.get(abs_spec) or {}
            variants = spec.get('variants') or []
            variant_obj = next((v for v in variants if str(v.get('name')) == variant_name), None)
            if not isinstance(variant_obj, dict):
                continue

            strategy_scope = str(spec.get('id') or Path(abs_spec).stem)
            sig = _variant_resolved_signature(
                variant_obj,
                symbol,
                timeframe,
                strategy_scope=strategy_scope,
            )
            out.add(sig)
        except Exception:
            continue

    return out


def _index_recent_batch_signatures(lookback_days: int = 14, max_batch_files: int = 200) -> set[str]:
    batch_root = ROOT / 'artifacts' / 'batches'
    if not batch_root.exists():
        return set()

    cutoff = datetime.now(UTC) - timedelta(days=max(0, lookback_days))
    files = sorted(batch_root.rglob('*.batch_backtest.json'))[-max_batch_files:]
    out: set[str] = set()
    spec_cache: dict[str, dict] = {}

    for bf in files:
        try:
            bj = _load_json(bf)
            created = str(bj.get('created_at') or '')
            if created:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=UTC)
                if created_dt.astimezone(UTC) < cutoff:
                    continue

            spec_path = str(bj.get('strategy_spec_path') or '')
            if not spec_path:
                continue
            abs_spec = str((ROOT / spec_path).resolve()) if not Path(spec_path).is_absolute() else spec_path
            if abs_spec not in spec_cache:
                p = Path(abs_spec)
                spec_cache[abs_spec] = _load_json(p) if p.exists() else {}
            spec = spec_cache.get(abs_spec) or {}
            variants = spec.get('variants') or []

            for run in (bj.get('runs') or []):
                variant_name = str(run.get('variant_name') or '')
                symbol = str(run.get('symbol') or '').upper()
                timeframe = str(run.get('timeframe') or '').lower()
                if not variant_name or not symbol or not timeframe:
                    continue
                variant_obj = next((v for v in variants if str(v.get('name')) == variant_name), None)
                if not isinstance(variant_obj, dict):
                    continue
                strategy_scope = str(spec.get('id') or Path(abs_spec).stem)
                sig = _variant_resolved_signature(
                    variant_obj,
                    symbol,
                    timeframe,
                    strategy_scope=strategy_scope,
                )
                out.add(sig)
        except Exception:
            continue

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy-spec', required=True)
    ap.add_argument('--variant', required=True, help='variant name or "all"')
    ap.add_argument('--datasets', default='default', help='default | csv list of dataset meta paths | JSON file path')
    ap.add_argument('--max-runs', type=int, default=24)
    ap.add_argument('--dedup-lookback-days', type=int, default=90)
    ap.add_argument('--dedup-max-history', type=int, default=5000)
    ap.add_argument('--disable-history-dedup', action='store_true')
    ap.add_argument('--advisory-path', default='docs/claude-reports/STRATEGY_ADVISORY.md')
    args = ap.parse_args()

    spec = _load_json(args.strategy_spec)
    if not _is_allowed_spec_source(spec):
        raise SystemExit('SPEC_SOURCE_NOT_ALLOWED: source must be claude-advisor')
    strategy_scope = str(spec.get('id') or Path(args.strategy_spec).stem)
    enforcement = _load_advisory_enforcement(args.advisory_path)
    variant_objects = {str(v.get('name')): v for v in spec.get('variants', []) if isinstance(v, dict) and v.get('name')}
    variants = [v['name'] for v in spec.get('variants', [])]
    selected_variants = variants if args.variant == 'all' else [args.variant]
    for v in selected_variants:
        if v not in variants:
            raise ValueError(f'variant not found in spec: {v}')

    dataset_metas = _resolve_datasets(args.datasets)

    runs = []
    in_batch_seen = set()
    historical_seen = set()
    history_skips = 0
    in_batch_skips = 0
    directive_blocked_skips = 0

    if not args.disable_history_dedup:
        historical_seen = _index_historical_signatures(
            lookback_days=args.dedup_lookback_days,
            max_entries=args.dedup_max_history,
        )
        historical_seen.update(
            _index_recent_batch_signatures(
                lookback_days=min(args.dedup_lookback_days, 30),
                max_batch_files=200,
            )
        )

    for variant in selected_variants:
        variant_obj = variant_objects.get(variant, {})
        for dataset_meta in dataset_metas:
            meta = _load_json(dataset_meta)
            symbol = str(meta.get('symbol') or '')
            timeframe = str(meta.get('timeframe') or '')
            sig = _variant_resolved_signature(
                variant_obj,
                symbol,
                timeframe,
                strategy_scope=strategy_scope,
            )

            if sig in historical_seen:
                history_skips += 1
                print(f"DEDUP_SKIP_HISTORY variant={variant} symbol={symbol} timeframe={timeframe}", file=sys.stderr)
                continue

            if sig in in_batch_seen:
                in_batch_skips += 1
                print(f"DEDUP_SKIP_BATCH variant={variant} symbol={symbol} timeframe={timeframe}", file=sys.stderr)
                continue

            resolved_template = ''
            if resolve_template is not None:
                try:
                    resolved_template = str(resolve_template(variant_obj) or '').lower()
                except Exception:
                    resolved_template = ''

            directive_block_reason = None
            if symbol.upper() in enforcement['exclude_assets']:
                directive_block_reason = f"EXCLUDE_ASSET:{symbol.upper()}"
            elif timeframe.lower() in enforcement['exclude_timeframes']:
                directive_block_reason = f"EXCLUDE_TIMEFRAME:{timeframe.lower()}"
            elif resolved_template and resolved_template in enforcement['blacklist_templates']:
                directive_block_reason = f"BLACKLIST_TEMPLATE:{resolved_template}"
            elif any(str(x).upper() in enforcement['blacklist_directives'] for x in [variant_obj.get('origin', ''), variant_obj.get('name', '')]):
                directive_block_reason = "BLACKLIST_DIRECTIVE"

            if directive_block_reason:
                directive_blocked_skips += 1
                runs.append({
                    'variant_name': variant,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'dataset_meta_path': dataset_meta,
                    'backtest_result_path': '',
                    'trade_list_path': '',
                    'gate_pass': False,
                    'status': 'SKIPPED',
                    'skip_reason': 'DIRECTIVE_BLOCKED',
                    'directive_block_reason': directive_block_reason,
                    'feasibility_report_path': '',
                    'feasibility_flags': [],
                    'net_profit': 0.0,
                    'trades': 0,
                    'profit_factor': 0.0,
                    'max_drawdown': 0.0,
                    'ppr_score': 0.0,
                    'ppr_decision': 'SKIPPED',
                })
                continue

            in_batch_seen.add(sig)
            fout = _run([
                PY,
                'scripts/pipeline/check_feasibility.py',
                '--strategy-spec',
                args.strategy_spec,
                '--variant',
                variant,
                '--dataset-meta',
                dataset_meta,
            ])
            f = json.loads(fout)
            if f.get('verdict') == 'FAIL':
                run = {
                    'variant_name': variant,
                    'symbol': meta.get('symbol'),
                    'timeframe': meta.get('timeframe'),
                    'dataset_meta_path': dataset_meta,
                    'backtest_result_path': '',
                    'trade_list_path': '',
                    'gate_pass': False,
                    'status': 'SKIPPED',
                    'skip_reason': 'FEASIBILITY_FAIL',
                    'feasibility_report_path': f.get('feasibility_report_path'),
                    'feasibility_flags': f.get('flags', []),
                    'net_profit': 0.0,
                    'trades': 0,
                    'profit_factor': 0.0,
                    'max_drawdown': 0.0,
                    'ppr_score': 0.0,
                    'ppr_decision': 'SKIPPED',
                }
                runs.append(run)
                continue

            out = _run([
                PY,
                'scripts/backtester/hl_backtest_engine.py',
                '--dataset-meta',
                dataset_meta,
                '--strategy-spec',
                args.strategy_spec,
                '--variant',
                variant,
            ])
            info = json.loads(out)
            bt = _load_json(info['backtest_result'])
            run = {
                'variant_name': variant,
                'symbol': meta.get('symbol'),
                'timeframe': meta.get('timeframe'),
                'dataset_meta_path': dataset_meta,
                'backtest_result_path': info['backtest_result'],
                'trade_list_path': info['trade_list'],
                'feasibility_report_path': f.get('feasibility_report_path'),
                'feasibility_flags': f.get('flags', []),
                'status': 'EXECUTED',
                'gate_pass': bool(bt.get('gate', {}).get('gate_pass', True)),
                'net_profit': bt.get('results', {}).get('net_profit', 0.0),
                'trades': bt.get('results', {}).get('total_trades', 0),
                'profit_factor': bt.get('results', {}).get('profit_factor', 0.0),
                'max_drawdown': bt.get('results', {}).get('max_drawdown', 0.0),
                'ppr_score': bt.get('ppr', {}).get('score', 0.0) if isinstance(bt.get('ppr'), dict) else 0.0,
                'ppr_decision': bt.get('ppr', {}).get('decision', 'NA') if isinstance(bt.get('ppr'), dict) else 'NA',
            }
            if info.get('relax_suggestion_path'):
                run['relax_suggestion_path'] = info['relax_suggestion_path']
            runs.append(run)

    if args.max_runs > 0:
        runs = runs[:args.max_runs]
    attempted = len(selected_variants) * len(dataset_metas)
    dedup_skipped_total = history_skips + in_batch_skips + directive_blocked_skips
    summary = {
        'total_runs': len(runs),
        'attempted_runs': attempted,
        'dedup_skipped_total': dedup_skipped_total,
        'dedup_skipped_history': history_skips,
        'dedup_skipped_batch': in_batch_skips,
        'directive_blocked_skips': directive_blocked_skips,
        'failed_runs': sum(1 for r in runs if not r['gate_pass']),
        'net_profit': round(sum(float(r.get('net_profit', 0.0)) for r in runs), 8),
        'trades': int(sum(int(r.get('trades', 0)) for r in runs)),
        'profit_factor': round(sum(float(r.get('profit_factor', 0.0)) for r in runs) / len(runs), 8) if runs else 0.0,
        'max_drawdown': round(max((float(r.get('max_drawdown', 0.0)) for r in runs), default=0.0), 8),
        'ppr_pass_count': sum(1 for r in runs if str(r.get('ppr_decision', '')).upper() == 'PASS'),
        'ppr_promote_count': sum(1 for r in runs if str(r.get('ppr_decision', '')).upper() == 'PROMOTE'),
        'ppr_fail_count': sum(1 for r in runs if str(r.get('ppr_decision', '')).upper() == 'FAIL'),
        'ppr_suspect_count': sum(1 for r in runs if str(r.get('ppr_decision', '')).upper() == 'SUSPECT'),
    }

    batch = {
        'schema_version': '1.0',
        'id': f"batch_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
        'created_at': datetime.now(UTC).isoformat(),
        'strategy_spec_path': args.strategy_spec,
        'variant': args.variant,
        'runs': runs,
        'summary': summary,
    }

    out_dir = ROOT / 'artifacts' / 'batches' / datetime.now().strftime('%Y%m%d')
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_path = out_dir / f"{batch['id']}.batch_backtest.json"
    batch_path.write_text(json.dumps(batch, separators=(',', ':')), encoding='utf-8')

    experiment_plan_path = None
    if summary['failed_runs'] > 0:
        p = _run([
            PY,
            'scripts/pipeline/emit_experiment_plan.py',
            '--batch-artifact',
            str(batch_path),
        ])
        experiment_plan_path = json.loads(p).get('experiment_plan_path')

    print(json.dumps({
        'batch_artifact_path': str(batch_path),
        'experiment_plan_path': experiment_plan_path,
        'failed_runs': summary['failed_runs'],
        'attempted_runs': summary['attempted_runs'],
        'dedup_skipped_total': summary['dedup_skipped_total'],
        'dedup_skipped_history': summary['dedup_skipped_history'],
        'dedup_skipped_batch': summary['dedup_skipped_batch'],
        'directive_blocked_skips': summary['directive_blocked_skips'],
        'ppr_pass_count': summary['ppr_pass_count'],
        'ppr_promote_count': summary['ppr_promote_count'],
        'ppr_fail_count': summary['ppr_fail_count'],
        'ppr_suspect_count': summary['ppr_suspect_count'],
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

