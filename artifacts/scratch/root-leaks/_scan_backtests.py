import json, os, glob

base = "C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303"
files = sorted(glob.glob(os.path.join(base, "*.backtest_result.json")))
for f in files:
    with open(f) as fh:
        d = json.load(fh)
    r = d.get("results", {})
    inp = d.get("inputs", {})
    ds = inp.get("dataset_meta", inp.get("dataset_csv", ""))
    parts = ds.replace("\\", "/").split("/")
    asset = "UNK"
    tf = "UNK"
    for i, p in enumerate(parts):
        if p == "hyperliquid" and i+2 < len(parts):
            asset = parts[i+1]
            tf = parts[i+2]
            break
    variant = inp.get("variant", "UNK")
    trades = r.get("total_trades", 0)
    pf = r.get("profit_factor", 0)
    wr = r.get("win_rate", 0)
    dd = r.get("max_drawdown_pct", 0)
    pnl = r.get("net_profit_pct", 0)
    rpf = r.get("regime_pf", {})
    rbd = r.get("regime_breakdown", {})
    tpf = rpf.get("trending", "N/A")
    rapf = rpf.get("ranging", "N/A")
    trpf = rpf.get("transitional", "N/A")
    tt = rbd.get("trending_trades", 0)
    rt = rbd.get("ranging_trades", 0)
    trt = rbd.get("transitional_trades", 0)
    fname = os.path.basename(f)
    print(f"{fname}|{variant}|{asset}|{tf}|{trades}|{pf:.4f}|{wr:.4f}|{dd:.2f}|{pnl:.2f}|{tpf}|{rapf}|{trpf}|{tt}|{rt}|{trt}")
