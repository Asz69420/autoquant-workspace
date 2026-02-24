#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
FIX = ROOT / "scripts" / "tests" / "fixtures"


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(p.stdout.strip())


def main() -> int:
    ingest = run([
        PY,
        "scripts/data/ingest_tv_csv.py",
        "--input", str(FIX / "tv_sample.csv"),
        "--symbol", "BTCUSDT",
        "--timeframe", "1h",
        "--timezone", "+00:00",
    ])

    r1 = run([
        PY,
        "scripts/backtester/tv_parity_engine.py",
        "--dataset", ingest["dataset_csv"],
        "--meta", ingest["dataset_meta"],
        "--strategy-spec", str(FIX / "strategy_spec_tv_parity.json"),
        "--variant", "baseline",
        "--commission-pct", "0",
        "--fill-rule", "next_open",
        "--tie-break", "worst_case",
    ])

    r2 = run([
        PY,
        "scripts/backtester/tv_parity_engine.py",
        "--dataset", ingest["dataset_csv"],
        "--meta", ingest["dataset_meta"],
        "--strategy-spec", str(FIX / "strategy_spec_tv_parity.json"),
        "--variant", "baseline",
        "--commission-pct", "0",
        "--fill-rule", "next_open",
        "--tie-break", "worst_case",
    ])

    t1 = json.loads(Path(r1["trade_list"]).read_text(encoding="utf-8"))["trades"]
    t2 = json.loads(Path(r2["trade_list"]).read_text(encoding="utf-8"))["trades"]
    assert t1 == t2, "Deterministic trade output mismatch"

    b1 = json.loads(Path(r1["backtest_result"]).read_text(encoding="utf-8"))
    assert b1["settings"]["fill_rule"] == "next_open"
    assert b1["settings"]["tie_break"] == "worst_case"

    parity = run([
        PY,
        "scripts/backtester/compare_tv_trades.py",
        "--our", r1["trade_list"],
        "--tv", str(FIX / "tv_trades_sample.csv"),
    ])

    print(json.dumps({
        "dataset_meta": ingest["dataset_meta"],
        "trade_list": r1["trade_list"],
        "backtest_result": r1["backtest_result"],
        "parity_report": parity["parity_report"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
