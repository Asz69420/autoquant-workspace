#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / 'artifacts' / 'library' / 'RUN_INDEX.json'

ASSET_ORDER = ['BTC', 'ETH', 'SOL']
TF_ORDER = ['15m', '1h', '4h']
LINE = '━━━━━━━━━━━━━━━━━━━━━━━━'
TF_W = 2
PNL_W = 6
PF_W = 4
WR_W = 3
TC_W = 3
DD_W = 5


def _fmt_dd(value: float | None) -> str:
    if value is None:
        return 'n/a'
    v = max(min(float(value), 999.9), -999.9)
    return f"{v:.1f}"


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))


def backtest_metrics(backtest_path: str) -> tuple[float | None, float | None]:
    if not backtest_path:
        return None, None
    p = Path(backtest_path)
    if not p.exists():
        return None, None
    try:
        j = json.loads(p.read_text(encoding='utf-8'))
        results = j.get('results', {})
        wr = results.get('win_rate')
        wr_pct = (float(wr) * 100.0) if wr is not None else None

        dd_raw = results.get('max_drawdown')
        dd_pct = None
        if dd_raw is not None:
            dd_val = float(dd_raw)
            dd_pct = dd_val * 100.0 if abs(dd_val) <= 1.0 else dd_val
        return wr_pct, dd_pct
    except Exception:
        return None, None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default='')
    args = ap.parse_args()

    req = [x.strip().upper() for x in args.assets.replace('/', ',').split(',') if x.strip()]
    req = [x for x in req if x]
    assets = [a for a in ASSET_ORDER if (not req or a in req)]
    if req:
        for r in req:
            if r not in assets:
                assets.append(r)

    runs = load_json(RUN_INDEX)

    grouped: dict[str, dict[str, list[dict]]] = {a: {tf: [] for tf in TF_ORDER} for a in assets}

    for r in runs:
        ds_list = r.get('datasets_tested') or []
        if not ds_list:
            continue
        ds = ds_list[0] if isinstance(ds_list, list) else ds_list
        asset = str(ds.get('symbol', '')).upper().strip()
        tf = str(ds.get('timeframe', '')).lower().strip()
        if asset not in grouped or tf not in TF_ORDER:
            continue

        try:
            net = float(r.get('net_profit', 0.0))
            pf = float(r.get('profit_factor', 0.0))
            tc = int(r.get('trades', 0))
        except Exception:
            continue
        if tc <= 0:
            continue

        bt = str((r.get('pointers') or {}).get('backtest_result') or '')
        wr, dd = backtest_metrics(bt)

        row = {
            'tf': tf,
            'pnl': (net / 10000.0) * 100.0,
            'pf': pf,
            'wr': wr,
            'tc': tc,
            'dd': dd,
        }
        grouped[asset][tf].append(row)

    out: list[str] = []

    for ai, asset in enumerate(assets):
        any_tf = False
        for tf in TF_ORDER:
            rows = grouped.get(asset, {}).get(tf, [])
            if not rows:
                continue

            deduped: list[dict] = []
            seen: set[tuple] = set()
            for x in sorted(rows, key=lambda z: (z['pnl'], z['pf']), reverse=True):
                key = (round(x['pnl'], 1), round(x['pf'], 2), x['wr'], x['tc'], None if x.get('dd') is None else round(x['dd'], 1))
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(x)
                if len(deduped) >= 3:
                    break
            top = deduped
            if not top:
                continue

            any_tf = True
            out.append(f"{asset} {tf}")
            header = (
                f"{'TF'.ljust(TF_W)} "
                f"{'P&L'.rjust(PNL_W)} "
                f"{'PF'.rjust(PF_W)} "
                f"{'WR'.rjust(WR_W)} "
                f"{'TC'.rjust(TC_W)} "
                f"{'DD'.rjust(DD_W)}"
            )
            out.append(header)
            out.append(LINE)
            for x in top:
                pnl = f"{x['pnl']:+.1f}"[:PNL_W]
                pf = f"{x['pf']:.2f}"[:PF_W]
                wr = ('n/a' if x['wr'] is None else f"{x['wr']:.0f}%")[:WR_W]
                tc = str(x['tc'])[:TC_W]
                dd = _fmt_dd(x.get('dd'))[:DD_W]
                row = (
                    f"{x['tf'][:TF_W].ljust(TF_W)} "
                    f"{pnl.rjust(PNL_W)} "
                    f"{pf.rjust(PF_W)} "
                    f"{wr.rjust(WR_W)} "
                    f"{tc.rjust(TC_W)} "
                    f"{dd.rjust(DD_W)}"
                )
                out.append(row)
            out.append('')

        if not any_tf:
            out.append(f"{asset} (no data)")
            out.append('')

    print('\n'.join(out).rstrip())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
