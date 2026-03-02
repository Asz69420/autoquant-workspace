import json, glob, os

# Key trade lists to check - top PF performers from March 1
trade_list_files = [
    # Supertrend tail harvester 8:1 (PF=1.921, 85 trades)
    "artifacts/backtests/20260301/hl_20260301_5623e97b.trade_list.json",
    # Supertrend no ADX gate 8:1 (PF=1.907, 99 trades)
    "artifacts/backtests/20260301/hl_20260301_54d2de29.trade_list.json",
    # Supertrend tight 7:1 (PF=1.878, 85 trades)
    "artifacts/backtests/20260301/hl_20260301_199a8350.trade_list.json",
    # MACD 1h 7:1 cluster exemplar (PF=1.712, 161 trades)
    "artifacts/backtests/20260301/hl_20260301_85409ce4.trade_list.json",
    # Supertrend conviction tight (PF=1.916, 23 trades - overfit suspect)
    "artifacts/backtests/20260301/hl_20260301_39ec9668.trade_list.json",
    # March 2 top - exit_change_exploit_6 (PF=1.236, 117 trades)
    "artifacts/backtests/20260302/hl_20260302_d2bce0f1.trade_list.json",
]

for tlf in trade_list_files:
    if not os.path.exists(tlf):
        # Try glob for partial match
        base = os.path.basename(tlf).replace(".trade_list.json", "")
        matches = glob.glob("artifacts/backtests/*/" + base + ".trade_list.json")
        if matches:
            tlf = matches[0]
        else:
            print("NOT FOUND: " + tlf)
            continue

    try:
        with open(tlf) as fh:
            data = json.load(fh)

        trades = data if isinstance(data, list) else data.get("trades", data.get("trade_list", []))

        if not trades:
            print("\n" + os.path.basename(tlf) + ": NO TRADES or unknown format")
            if isinstance(data, dict):
                print("  Keys: " + str(list(data.keys())))
                print("  Sample: " + json.dumps(data, indent=2)[:500])
            else:
                print("  Keys: list")
            continue

        print("\n" + "=" * 80)
        print("FILE: " + os.path.basename(tlf))
        print("Total trades: " + str(len(trades)))

        # Extract PnL per trade
        pnls = []
        dates = []
        for t in trades:
            pnl = t.get("pnl", t.get("profit", t.get("net_pnl", t.get("realized_pnl", 0))))
            entry_time = t.get("entry_time", t.get("entry_date", t.get("open_time", "")))
            exit_time = t.get("exit_time", t.get("exit_date", t.get("close_time", "")))
            regime = t.get("regime", "unknown")
            pnls.append({"pnl": pnl, "entry": entry_time, "exit": exit_time, "regime": regime})
            if entry_time:
                dates.append(entry_time)

        # Sort by PnL descending
        pnls_sorted = sorted(pnls, key=lambda x: x["pnl"], reverse=True)

        total_profit = sum(p["pnl"] for p in pnls if p["pnl"] > 0)
        total_loss = sum(p["pnl"] for p in pnls if p["pnl"] < 0)
        net = total_profit + total_loss

        print("Total profit (winners): $%.2f" % total_profit)
        print("Total loss (losers): $%.2f" % total_loss)
        print("Net: $%.2f" % net)

        # Top-N concentration
        if len(pnls_sorted) >= 2 and net != 0:
            top2 = pnls_sorted[0]["pnl"] + pnls_sorted[1]["pnl"]
            top5 = sum(p["pnl"] for p in pnls_sorted[:5])
            top10 = sum(p["pnl"] for p in pnls_sorted[:10])

            print("\nPROFIT CONCENTRATION:")
            print("  Top 1 trade: $%.2f (%.1f%% of net)" % (pnls_sorted[0]["pnl"], pnls_sorted[0]["pnl"]/net*100))
            print("  Top 2 trades: $%.2f (%.1f%% of net)" % (top2, top2/net*100))
            print("  Top 5 trades: $%.2f (%.1f%% of net)" % (top5, top5/net*100))
            print("  Top 10 trades: $%.2f (%.1f%% of net)" % (top10, top10/net*100))

            # Without top 2 - what would PF be?
            remaining_profit = total_profit - max(0, pnls_sorted[0]["pnl"]) - max(0, pnls_sorted[1]["pnl"])
            remaining_loss = total_loss  # losses don't change
            remaining_pf = remaining_profit / abs(remaining_loss) if remaining_loss != 0 else 0
            print("  PF without top 2 winning trades: %.3f" % remaining_pf)

        # Time distribution
        if dates:
            # Group by year-month
            months = {}
            for d in dates:
                ym = str(d)[:7]  # YYYY-MM
                months[ym] = months.get(ym, 0) + 1

            print("\nTIME DISTRIBUTION:")
            for ym in sorted(months.keys()):
                bar = "#" * months[ym]
                print("  %s: %3d trades %s" % (ym, months[ym], bar))

        # Regime distribution
        regimes = {}
        regime_pnls = {}
        for p in pnls:
            r = p["regime"]
            regimes[r] = regimes.get(r, 0) + 1
            if r not in regime_pnls:
                regime_pnls[r] = 0
            regime_pnls[r] += p["pnl"]

        print("\nREGIME DISTRIBUTION:")
        for r, c in sorted(regimes.items(), key=lambda x: x[1], reverse=True):
            pct = c / len(pnls) * 100
            rpnl = regime_pnls.get(r, 0)
            print("  %s: %d trades (%.1f%%), PnL=$%.2f" % (r, c, pct, rpnl))

        # Top 5 and bottom 5 trades
        print("\nTOP 5 WINNING TRADES:")
        for p in pnls_sorted[:5]:
            print("  $%.2f | %s -> %s | %s" % (p["pnl"], p["entry"], p["exit"], p["regime"]))

        print("\nBOTTOM 5 LOSING TRADES:")
        for p in pnls_sorted[-5:]:
            print("  $%.2f | %s -> %s | %s" % (p["pnl"], p["entry"], p["exit"], p["regime"]))

    except Exception as e:
        print("ERROR: %s: %s" % (tlf, e))
        import traceback
        traceback.print_exc()
