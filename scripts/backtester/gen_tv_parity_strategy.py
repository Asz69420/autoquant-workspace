#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PINE = """//@version=6
strategy(\"TV Parity EMA9/EMA21 ATR14\", overlay=true, initial_capital=10000)
emaFast = ta.ema(close, 9)
emaSlow = ta.ema(close, 21)
atr = ta.atr(14)
longCond = ta.crossover(emaFast, emaSlow)
shortCond = ta.crossunder(emaFast, emaSlow)
if (longCond)
    strategy.entry(\"L\", strategy.long)
if (shortCond)
    strategy.entry(\"S\", strategy.short)
strategy.exit(\"XL\", \"L\", stop=strategy.position_avg_price - 1.5 * atr, limit=strategy.position_avg_price + 2.0 * atr)
strategy.exit(\"XS\", \"S\", stop=strategy.position_avg_price + 1.5 * atr, limit=strategy.position_avg_price - 2.0 * atr)
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="ema_atr_parity")
    args = ap.parse_args()

    day = datetime.now().strftime("%Y%m%d")
    out = ROOT / "artifacts" / "strategy_specs" / day
    out.mkdir(parents=True, exist_ok=True)
    sid = f"tv-parity-{day}-ema9-ema21"

    spec = {
        "schema_version": "1.0",
        "id": sid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_thesis_path": "generated://tv_parity",
        "variants": [
            {
                "name": args.variant,
                "description": "EMA9/EMA21 crossover with ATR14 exits",
                "entry_long": ["close_gt_open"],
                "entry_short": ["close_lt_open"],
                "filters": [],
                "exit_rules": [],
                "risk_rules": ["stop_loss_pct=0.015", "take_profit_pct=0.02"],
                "parameters": [],
                "constraints": []
            }
        ]
    }
    spec_path = out / f"{sid}.strategy_spec.json"
    pine_path = out / f"{sid}.pine"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    pine_path.write_text(PINE, encoding="utf-8")
    print(json.dumps({"strategy_spec_path": str(spec_path), "pine_path": str(pine_path), "pine": PINE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
