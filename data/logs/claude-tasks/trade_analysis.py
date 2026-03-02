import json
import os

os.chdir("C:/Users/Clamps/.openclaw/workspace")

files = {
    "5623e97b (Supertrend tail harvester 8:1, PF=1.921)": "artifacts/backtests/20260301/hl_20260301_5623e97b.trade_list.json",
    "54d2de29 (Supertrend no ADX gate 8:1, PF=1.907)": "artifacts/backtests/20260301/hl_20260301_54d2de29.trade_list.json",
    "199a8350 (Supertrend tight 7:1, PF=1.878)": "artifacts/backtests/20260301/hl_20260301_199a8350.trade_list.json",
    "85409ce4 (MACD 1h 7:1 cluster, PF=1.712)": "artifacts/backtests/20260301/hl_20260301_85409ce4.trade_list.json",
    "39ec9668 (Supertrend conviction tight, PF=1.916)": "artifacts/backtests/20260301/hl_20260301_39ec9668.trade_list.json",
    "d2bce0f1 (exit_change_exploit_6, PF=1.236)": "artifacts/backtests/20260302/hl_20260302_d2bce0f1.trade_list.json",
}

for label, path in files.items():
    with open(path) as f:
        data = json.load(f)
    trades = data.get("trades", data) if isinstance(data, dict) else data

    pnls = []
    dates = []
    for t in trades:
        pnl = t.get("pnl", 0)
        entry = t.get("entry_time", "")
        exit_t = t.get("exit_time", "")
        regime = t.get("regime", t.get("entry_regime", "unknown"))
        pnls.append({"pnl": pnl, "entry": entry, "exit": exit_t, "regime": regime})
        if entry:
            dates.append(entry)

    pnls_sorted = sorted(pnls, key=lambda x: x["pnl"], reverse=True)
    total_profit = sum(p["pnl"] for p in pnls if p["pnl"] > 0)
    total_loss = sum(p["pnl"] for p in pnls if p["pnl"] < 0)
    net = total_profit + total_loss

    print("=" * 80)
    print("FILE: %s" % label)
    print("Total trades: %d" % len(trades))
    print("Total profit (winners): $%.2f" % total_profit)
    print("Total loss (losers): $%.2f" % total_loss)
    print("Net: $%.2f" % net)

    if len(pnls_sorted) >= 2 and net != 0:
        top2 = pnls_sorted[0]["pnl"] + pnls_sorted[1]["pnl"]
        top5 = sum(p["pnl"] for p in pnls_sorted[:5])
        top10 = sum(p["pnl"] for p in pnls_sorted[:10])
        print("")
        print("PROFIT CONCENTRATION:")
        print("  Top 1 trade: $%.2f (%.1f%% of net)" % (pnls_sorted[0]["pnl"], pnls_sorted[0]["pnl"]/net*100))
        print("  Top 2 trades: $%.2f (%.1f%% of net)" % (top2, top2/net*100))
        print("  Top 5 trades: $%.2f (%.1f%% of net)" % (top5, top5/net*100))
        print("  Top 10 trades: $%.2f (%.1f%% of net)" % (top10, top10/net*100))
        rem_profit = total_profit - max(0, pnls_sorted[0]["pnl"]) - max(0, pnls_sorted[1]["pnl"])
        rem_pf = rem_profit / abs(total_loss) if total_loss != 0 else 0
        print("  PF without top 2 winning trades: %.3f" % rem_pf)

    if dates:
        months = {}
        for d in dates:
            ym = str(d)[:7]
            months[ym] = months.get(ym, 0) + 1
        print("")
        print("TIME DISTRIBUTION:")
        for ym in sorted(months.keys()):
            bar = "#" * months[ym]
            print("  %s: %3d trades %s" % (ym, months[ym], bar))

    regimes = {}
    regime_pnls = {}
    for p in pnls:
        r = p["regime"]
        regimes[r] = regimes.get(r, 0) + 1
        regime_pnls[r] = regime_pnls.get(r, 0) + p["pnl"]
    print("")
    print("REGIME DISTRIBUTION:")
    for r, c in sorted(regimes.items(), key=lambda x: x[1], reverse=True):
        pct = c / len(pnls) * 100
        rpnl = regime_pnls.get(r, 0)
        print("  %s: %d trades (%.1f%%), PnL=$%.2f" % (r, c, pct, rpnl))

    print("")
    print("TOP 5 WINNING TRADES:")
    for p in pnls_sorted[:5]:
        print("  $%.2f | %s -> %s | %s" % (p["pnl"], p["entry"], p["exit"], p["regime"]))
    print("")
    print("BOTTOM 5 LOSING TRADES:")
    for p in pnls_sorted[-5:]:
        print("  $%.2f | %s -> %s | %s" % (p["pnl"], p["entry"], p["exit"], p["regime"]))
    print("")
