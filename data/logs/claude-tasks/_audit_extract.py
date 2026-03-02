import json, glob, sys

DIR = "C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228"
files = glob.glob(f"{DIR}/*.backtest_result.json")
print(f"Total files: {len(files)}", file=sys.stderr)

rows = []
for f in sorted(files):
    try:
        with open(f, "r") as fh:
            d = json.load(fh)
        r = d.get("results", {})
        inp = d.get("inputs", {})
        row = {
            "hash": d.get("id", ""),
            "variant": inp.get("variant", ""),
            "pf": r.get("profit_factor"),
            "trades": r.get("total_trades"),
            "dd": r.get("max_drawdown"),
            "win_rate": r.get("win_rate"),
            "net_pnl": r.get("net_profit"),
            "regime_breakdown": r.get("regime_breakdown"),
            "regime_pf": r.get("regime_pf"),
        }
        rows.append(row)
    except Exception as e:
        print(f"ERROR reading {f}: {e}", file=sys.stderr)

rows.sort(key=lambda x: x["hash"])
print(json.dumps(rows))
