#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_INDEX = ROOT / 'artifacts' / 'library' / 'RUN_INDEX.json'

ASSET_ORDER = ['BTC', 'ETH', 'SOL']
TF_ORDER = ['15m', '1h', '4h']

MAX_WIDTH = 32
MAX_ROWS = 50
DIVIDER = '─' * MAX_WIDTH


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8-sig'))


def backtest_metrics(backtest_path: str) -> tuple[float | None, float | None]:
    if not backtest_path:
        return None, None
    p = Path(backtest_path)
    if not p.exists():
        return None, None
    try:
        j = json.loads(p.read_text(encoding='utf-8-sig'))
        results = j.get('results', {})

        wr = results.get('win_rate')
        wr_pct = (float(wr) * 100.0) if wr is not None else None

        dd_pct = None
        if results.get('max_drawdown_pct') is not None:
            dd_pct = float(results.get('max_drawdown_pct'))
        else:
            dd_raw = results.get('max_drawdown')
            if dd_raw is not None:
                dd_val = float(dd_raw)
                dd_pct = dd_val * 100.0 if abs(dd_val) <= 1.0 else dd_val
        if dd_pct is not None:
            dd_pct = max(min(dd_pct, 999.9), -999.9)

        return wr_pct, dd_pct
    except Exception:
        return None, None


def _fit(line: str) -> str:
    return line[:MAX_WIDTH]


def _fmt_dd(v: float | None) -> str:
    return 'n/a' if v is None else f'{v:.1f}'


def render_leaderboard(rows: list[dict]) -> tuple[str, dict]:
    if not rows:
        return '<pre>No strategies in leaderboard.</pre>', {'parse_mode': 'HTML'}

    lines: list[str] = []
    emitted = 0

    grouped: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        grouped.setdefault(r['asset'], {}).setdefault(r['tf'], []).append(r)

    for asset in [a for a in ASSET_ORDER if a in grouped] + [a for a in grouped if a not in ASSET_ORDER]:
        tfs = [t for t in TF_ORDER if t in grouped.get(asset, {})] + [t for t in grouped.get(asset, {}) if t not in TF_ORDER]
        any_tf = False

        for tf in tfs:
            sorted_rows = sorted(grouped[asset][tf], key=lambda x: (x.get('ppr', 0.0), x['pf'], x['pnl']), reverse=True)
            if not sorted_rows:
                continue

            deduped: list[dict] = []
            seen: set[tuple] = set()
            for x in sorted_rows:
                k = (round(x.get('ppr', 0.0), 2), round(x['pnl'], 1), round(x['pf'], 2), x['wr'], x['tc'], round(x['dd'], 1) if x.get('dd') is not None else None)
                if k in seen:
                    continue
                seen.add(k)
                deduped.append(x)
                if len(deduped) >= 3:
                    break

            if not deduped:
                continue
            any_tf = True

            lines.append(_fit(f'{asset} {tf}'))
            lines.append(_fit('TF  PPR  XPR   PF  WR  TC   DD'))
            lines.append(DIVIDER)

            for x in deduped:
                if emitted >= MAX_ROWS:
                    break
                tfv = str(x['tf'])[:2].ljust(2)
                ppr = f"{float(x.get('ppr', 0.0)):.1f}"[:4].rjust(4)
                xppr_v = float(x.get('xppr', 0.0) or 0.0)
                xppr = ('--' if xppr_v <= 0 else f"{xppr_v:.1f}")[:4].rjust(4)
                pf = f"{x['pf']:.2f}"[:4].rjust(4)
                wr = ('n/a' if x['wr'] is None else f"{x['wr']:.0f}%")[:3].rjust(3)
                tc = str(x['tc'])[:3].rjust(3)
                dd = _fmt_dd(x.get('dd'))[:5].rjust(5)
                lines.append(_fit(f'{tfv} {ppr} {xppr} {pf} {wr} {tc} {dd}'))
                emitted += 1

            lines.append('')
            if emitted >= MAX_ROWS:
                break

        if not any_tf:
            lines.append(_fit(f'{asset} (no data)'))
            lines.append('')

        if emitted >= MAX_ROWS:
            break

    if not lines:
        return '<pre>No strategies in leaderboard.</pre>', {'parse_mode': 'HTML'}

    body = '\n'.join(lines).rstrip('\n')
    rendered_text = f'<pre>{escape(body)}</pre>'
    return rendered_text, {'parse_mode': 'HTML'}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default='')
    ap.add_argument('--bucket', default='promoted', choices=['promoted', 'passed', 'all'])
    ap.add_argument('--json', action='store_true', dest='as_json')
    args = ap.parse_args()

    req = [x.strip().upper() for x in args.assets.replace('/', ',').split(',') if x.strip()]
    runs = load_json(RUN_INDEX)

    rows: list[dict] = []
    for r in runs:
        ds_list = r.get('datasets_tested') or []
        if not ds_list:
            continue

        ds = ds_list[0] if isinstance(ds_list, list) else ds_list
        asset = str(ds.get('symbol', '')).upper().strip()
        tf = str(ds.get('timeframe', '')).lower().strip()
        if req and asset not in req:
            continue

        try:
            net = float(r.get('net_profit', 0.0))
            pf = float(r.get('profit_factor', 0.0))
            tc = int(r.get('trades', 0))
            ppr = float(r.get('ppr_score', 0.0) or 0.0)
        except Exception:
            continue
        if tc <= 0:
            continue

        if args.bucket == 'promoted' and ppr < 3.0:
            continue
        if args.bucket == 'passed' and (ppr < 1.0 or ppr >= 3.0):
            continue

        bt = str((r.get('pointers') or {}).get('backtest_result') or '')
        wr, dd = backtest_metrics(bt)

        rows.append({
            'asset': asset,
            'tf': tf,
            'pnl': (net / 10000.0) * 100.0,
            'pf': pf,
            'ppr': ppr,
            'xppr': float(r.get('xppr_score', 0.0) or 0.0),
            'wr': wr,
            'tc': tc,
            'dd': dd,
        })

    rendered_text, send_opts = render_leaderboard(rows)
    if args.as_json:
        print(json.dumps({'rendered_text': rendered_text, 'send_opts': send_opts}, ensure_ascii=False))
    else:
        print(rendered_text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
