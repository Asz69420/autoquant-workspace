import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace")
TMP = ROOT / "artifacts" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

strategies = [
    {
        "name": "cci_chop_fade_v2",
        "entry_long": ["CHOP_14_1_100 > 50", "CCI_20_0.015 < -100"],
        "entry_short": ["CHOP_14_1_100 > 50", "CCI_20_0.015 > 100"],
        "risk_policy": {
            "stop_type": "atr",
            "stop_atr_mult": 1.5,
            "tp_type": "atr",
            "tp_atr_mult": 12.0,
            "risk_per_trade_pct": 0.01,
        },
    },
    {
        "name": "cci_adx_chop_fade_v1",
        "entry_long": ["CHOP_14_1_100 > 50", "ADX_14 < 25", "CCI_20_0.015 < -100"],
        "entry_short": ["CHOP_14_1_100 > 50", "ADX_14 < 25", "CCI_20_0.015 > 100"],
        "risk_policy": {
            "stop_type": "atr",
            "stop_atr_mult": 1.5,
            "tp_type": "atr",
            "tp_atr_mult": 8.0,
            "risk_per_trade_pct": 0.01,
        },
    },
]

meta = r"C:\Users\Clamps\.openclaw\workspace\artifacts\data\hyperliquid\ETH\4h\20240227T040000Z-20260226T000000Z.meta.json"
out = []

for s in strategies:
    spec = {
        "schema_version": "1.0",
        "id": s["name"],
        "created_at": "2026-03-03T00:00:00Z",
        "source_thesis_path": "docs/shared/QUANDALF_ORDERS.md",
        "variants": [
            {
                "name": s["name"],
                "template_name": "spec_rules",
                "entry_long": s["entry_long"],
                "entry_short": s["entry_short"],
                "risk_policy": s["risk_policy"],
                "execution_policy": {
                    "entry_fill": "bar_close",
                    "tie_break": "worst_case",
                    "allow_reverse": True,
                },
                "parameters": [],
                "filters": [],
                "exit_rules": [],
                "risk_rules": [],
                "constraints": ["bar_close_execution", "no_pyramiding"],
            }
        ],
    }
    spec_path = TMP / f"{s['name']}_pending.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "backtester" / "hl_backtest_engine.py"),
        "--dataset-meta", meta,
        "--strategy-spec", str(spec_path),
        "--variant", s["name"],
        "--initial-capital", "10000",
    ]
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        out.append({"strategy": s["name"], "ok": False, "error": (p.stderr or p.stdout).strip()})
        continue

    j = json.loads(p.stdout.strip())
    bt = json.loads(Path(j["backtest_result"]).read_text(encoding="utf-8"))
    r = bt["results"]
    g = bt.get("gate", {})
    out.append({
        "strategy": s["name"],
        "ok": True,
        "backtest_result_path": j["backtest_result"],
        "trade_list_path": j["trade_list"],
        "profit_factor": r.get("profit_factor", 0.0),
        "win_rate": r.get("win_rate", 0.0),
        "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
        "net_profit_pct": r.get("net_profit_pct", 0.0),
        "total_trades": r.get("total_trades", 0),
        "total_return_on_capital_pct": r.get("total_return_on_capital_pct", 0.0),
        "regime_pf": r.get("regime_pf", {}),
        "gate_pass": g.get("gate_pass", True),
        "gate_reason": g.get("gate_reason", "OK"),
        "min_trades_required": g.get("min_trades_required", 0),
    })

res_path = TMP / "quandalf_pending_20260303_results.json"
res_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(str(res_path))
