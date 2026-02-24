#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        ar = Path(td) / 'artifacts'
        # fixture backtest + batch
        bt = {
            'id': 'hl_fixture_1',
            'created_at': '2026-02-25T00:00:00Z',
            'inputs': {'strategy_spec': 'artifacts/strategy_specs/x.json', 'variant': 'v1'},
            'results': {'net_profit': 10, 'total_trades': 40, 'win_rate': 0.5, 'profit_factor': 1.2, 'max_drawdown': 100},
            'gate': {'gate_pass': True},
        }
        bt_path = ar / 'backtests/20260225/hl_fixture_1.backtest_result.json'
        tl_path = ar / 'backtests/20260225/hl_fixture_1.trade_list.json'
        _write(bt_path, bt)
        _write(tl_path, {'id': 'hl_fixture_1', 'trades': []})
        batch = {
            'id': 'batch_fixture_1',
            'created_at': '2026-02-25T00:00:00Z',
            'runs': [{
                'variant_name': 'v1', 'symbol': 'BTC', 'timeframe': '1h',
                'dataset_meta_path': 'artifacts/data/hyperliquid/BTC/1h/a.meta.json',
                'backtest_result_path': str(bt_path), 'trade_list_path': str(tl_path), 'gate_pass': True,
                'net_profit': 10, 'trades': 40, 'profit_factor': 1.2, 'max_drawdown': 100,
            }],
            'summary': {'total_runs': 1, 'failed_runs': 0, 'net_profit': 10, 'trades': 40, 'profit_factor': 1.2, 'max_drawdown': 100},
        }
        _write(ar / 'batches/20260225/batch_fixture_1.batch_backtest.json', batch)

        # old file for archive test
        old = ar / 'backtests/20250101/old.backtest_result.json'
        _write(old, {'old': True})
        old_ts = time.time() - 60 * 60 * 24 * 40
        os.utime(old, (old_ts, old_ts))

        out = subprocess.check_output([
            PY, str((ROOT / 'scripts/pipeline/run_librarian.py').resolve()),
            '--artifacts-root', str(ar),
            '--since-days', '3650',
            '--archive',
            '--archive-days', '30',
        ], text=True)
        j = json.loads(out)

        top = json.loads(Path(j['top_candidates_path']).read_text(encoding='utf-8'))
        run = json.loads(Path(j['run_index_path']).read_text(encoding='utf-8'))
        lessons = json.loads(Path(j['lessons_index_path']).read_text(encoding='utf-8'))

        assert len(top) <= 100
        assert len(run) <= 500
        assert len(lessons) <= 50

        # dedup: run twice should mark duplicate and not increase top
        out2 = subprocess.check_output([
            PY, str((ROOT / 'scripts/pipeline/run_librarian.py').resolve()),
            '--artifacts-root', str(ar),
            '--since-days', '3650',
        ], text=True)
        j2 = json.loads(out2)
        top2 = json.loads(Path(j2['top_candidates_path']).read_text(encoding='utf-8'))
        assert len(top2) <= len(top)

        archived_target = ar / 'archive'
        assert archived_target.exists()

        print(json.dumps({'top': len(top2), 'run': len(run), 'lessons': len(lessons)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
