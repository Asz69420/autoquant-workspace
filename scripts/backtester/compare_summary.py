#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--hl-result', required=True)
    ap.add_argument('--tv-json', required=True, help='JSON string with tv summary metrics')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    hl = json.loads(Path(args.hl_result).read_text(encoding='utf-8'))
    tv = json.loads(args.tv_json)
    h = hl.get('results', {})
    lines = [
        'TV vs HL summary',
        f"TV net_profit: {tv.get('net_profit')} | HL net_profit: {h.get('net_profit', h.get('net_return'))}",
        f"TV total_trades: {tv.get('total_trades')} | HL total_trades: {h.get('total_trades', h.get('trades'))}",
        f"TV win_rate: {tv.get('win_rate')} | HL win_rate: {h.get('win_rate')}",
        f"TV profit_factor: {tv.get('profit_factor')} | HL profit_factor: {h.get('profit_factor')}",
        f"TV max_drawdown: {tv.get('max_drawdown')} | HL max_drawdown: {h.get('max_drawdown', h.get('max_drawdown_proxy'))}",
    ]
    Path(args.out).write_text('\n'.join(lines), encoding='utf-8')
    print(args.out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
