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
ASSET_EMOJI = {'BTC': '🟠', 'ETH': '🔵', 'SOL': '🟣'}
LINE = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'


def trunc(s: str, n: int = 18) -> str:
    s = (s or '').strip() or 'unknown'
    return s if len(s) <= n else s[: n - 1] + '…'


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))


def win_rate_pct(backtest_path: str) -> float | None:
    if not backtest_path:
        return None
    p = Path(backtest_path)
    if not p.exists():
        return None
    try:
        j = json.loads(p.read_text(encoding='utf-8'))
        wr = j.get('results', {}).get('win_rate')
        return (float(wr) * 100.0) if wr is not None else None
    except Exception:
        return None


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
        wr = win_rate_pct(bt)

        row = {
            'tf': tf,
            'pnl': (net / 10000.0) * 100.0,
            'pf': pf,
            'wr': wr,
            'tc': tc,
            'strat': trunc(str(r.get('variant_name') or 'unknown')),
        }
        grouped[asset][tf].append(row)

    out: list[str] = ['🤖 òQ [Codex]', '']

    for asset in assets:
        out.append(f"{ASSET_EMOJI.get(asset, '⚪')} {asset}")
        out.append('')

        any_tf = False
        for tf in TF_ORDER:
            rows = grouped.get(asset, {}).get(tf, [])
            if not rows:
                continue

            by_strat: dict[str, dict] = {}
            for x in rows:
                k = x['strat']
                old = by_strat.get(k)
                if old is None or (x['pnl'], x['pf']) > (old['pnl'], old['pf']):
                    by_strat[k] = x
            top = sorted(by_strat.values(), key=lambda x: (x['pnl'], x['pf']), reverse=True)[:3]
            if not top:
                continue

            any_tf = True
            out.append(tf)
            out.append('TF   P&L    PF    WR    TC   Strat')
            out.append(LINE)
            for x in top:
                pnl = f"{x['pnl']:+.1f}"
                pf = f"{x['pf']:.2f}"
                wr = 'n/a' if x['wr'] is None else f"{x['wr']:.0f}%"
                tc = str(x['tc'])
                out.append(f"{x['tf']:<3} {pnl:>6}  {pf:>4}  {wr:>4}  {tc:>3}  {x['strat']}")
            out.append('')

        if not any_tf:
            out.append('(no data)')
            out.append('')

    print('\n'.join(out).rstrip())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
