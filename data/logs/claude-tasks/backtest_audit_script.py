import json, glob, os, sys
from collections import defaultdict

results = []
days = ["20260226", "20260227", "20260228"]

for day in days:
    pattern = os.path.join("artifacts", "backtests", day, "*.backtest_result.json")
    files = glob.glob(pattern)
    for f in files:
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            r = data.get("results", {})
            inp = data.get("inputs", {})
            gate = data.get("gate", {})

            entry = {
                "day": day,
                "id": data.get("id", ""),
                "variant": inp.get("variant", "unknown"),
                "spec": os.path.basename(inp.get("strategy_spec", "")),
                "pf": r.get("profit_factor", None),
                "trades": r.get("total_trades", r.get("trades", 0)),
                "win_rate": r.get("win_rate", None),
                "max_dd": r.get("max_drawdown", r.get("max_drawdown_proxy", None)),
                "net_profit": r.get("net_profit", r.get("net_return", None)),
                "net_profit_pct": r.get("net_profit_pct", r.get("net_return", None)),
                "regime_breakdown": r.get("regime_breakdown", None),
                "regime_pf": r.get("regime_pf", None),
                "regime_wr": r.get("regime_wr", None),
                "dominant_regime": r.get("dominant_regime", None),
                "gate_pass": gate.get("gate_pass", None),
                "gate_reason": gate.get("gate_reason", ""),
                "file": os.path.basename(f),
            }
            results.append(entry)
        except Exception as e:
            print("ERROR parsing %s: %s" % (f, e), file=sys.stderr)

results.sort(key=lambda x: (x["day"], -(x["pf"] or 0)))

total = len(results)
d26 = sum(1 for r in results if r["day"] == "20260226")
d27 = sum(1 for r in results if r["day"] == "20260227")
d28 = sum(1 for r in results if r["day"] == "20260228")
print("=== TOTAL BACKTESTS: %d ===" % total)
print("  20260226: %d" % d26)
print("  20260227: %d" % d27)
print("  20260228: %d" % d28)

print()
print("=== OVERFITTING CHECK: PF > 2.0 with < 30 trades ===")
overfit_high_pf = [r for r in results if r["pf"] and r["pf"] > 2.0 and r["trades"] < 30]
if overfit_high_pf:
    for r in overfit_high_pf:
        print("  %s | variant=%s | PF=%.3f | trades=%d | WR=%s" % (r["id"], r["variant"], r["pf"], r["trades"], r["win_rate"]))
else:
    print("  None found")

print()
print("=== OVERFITTING CHECK: PF > 1.5 with < 50 trades ===")
overfit_med = [r for r in results if r["pf"] and r["pf"] > 1.5 and r["trades"] and r["trades"] < 50]
if overfit_med:
    for r in overfit_med:
        print("  %s | variant=%s | PF=%.3f | trades=%d | WR=%s" % (r["id"], r["variant"], r["pf"], r["trades"], r["win_rate"]))
else:
    print("  None found")

print()
print("=== OVERFITTING CHECK: Win rate > 70%% ===")
high_wr = [r for r in results if r["win_rate"] and r["win_rate"] > 0.70]
if high_wr:
    for r in high_wr:
        print("  %s | variant=%s | PF=%.3f | trades=%d | WR=%.2f%%" % (r["id"], r["variant"], r["pf"], r["trades"], r["win_rate"]*100))
else:
    print("  None found")

print()
print("=== DATA QUALITY: Zero trades ===")
zero_trades = [r for r in results if r["trades"] == 0]
if zero_trades:
    for r in zero_trades:
        print("  %s | variant=%s | spec=%s" % (r["id"], r["variant"], r["spec"]))
else:
    print("  None found")

print()
print("=== DATA QUALITY: Max drawdown = 0 ===")
zero_dd = [r for r in results if r["max_dd"] is not None and r["max_dd"] == 0]
if zero_dd:
    for r in zero_dd:
        print("  %s | variant=%s | trades=%s | PF=%s" % (r["id"], r["variant"], r["trades"], r["pf"]))
else:
    print("  None found")

print()
print("=== DATA QUALITY: Negative trade counts ===")
bad_trades = [r for r in results if r["trades"] is not None and r["trades"] < 0]
if bad_trades:
    for r in bad_trades:
        print("  %s | trades=%s" % (r["id"], r["trades"]))
else:
    print("  None found")

print()
print("=== DATA QUALITY: Gate failures ===")
gate_fails = [r for r in results if r["gate_pass"] == False]
if gate_fails:
    for r in gate_fails:
        print("  %s | variant=%s | reason=%s | trades=%d" % (r["id"], r["variant"], r["gate_reason"], r["trades"]))
else:
    print("  None found")

print()
print("=== DUPLICATE CHECK: Identical PF+trades+DD combos ===")
fingerprints = defaultdict(list)
for r in results:
    if r["id"] == "bt-fixture":
        continue
    fp = (round(r["pf"] or 0, 6), r["trades"], round(r["max_dd"] or 0, 2))
    fingerprints[fp].append(r)
dupes = {k: v for k, v in fingerprints.items() if len(v) > 1}
if dupes:
    for fp, entries in sorted(dupes.items(), key=lambda x: -len(x[1])):
        pf, trades, dd = fp
        print("  PF=%.4f | trades=%d | DD=%.2f -- %d duplicates:" % (pf, trades, dd, len(entries)))
        for e in entries[:6]:
            print("    %s | variant=%s | day=%s | spec=%s" % (e["id"], e["variant"], e["day"], e["spec"]))
        if len(entries) > 6:
            print("    ... and %d more" % (len(entries) - 6))
else:
    print("  None found")

print()
print("=== TOP 15 BY PF (highest) ===")
top = sorted([r for r in results if r["id"] != "bt-fixture"], key=lambda x: -(x["pf"] or 0))
for r in top[:15]:
    regime_info = ""
    if r["regime_pf"]:
        rpf = r["regime_pf"]
        regime_info = " | regime_pf: tr=%.3f ra=%.3f trans=%.3f" % (rpf.get("trending", 0), rpf.get("ranging", 0), rpf.get("transitional", 0))
    wr_str = "%.2f%%" % (r["win_rate"]*100) if r["win_rate"] else "N/A"
    print("  %s | variant=%s | PF=%.4f | trades=%d | WR=%s | DD=%.2f | net=%.2f%%%s" % (r["id"], r["variant"], r["pf"], r["trades"], wr_str, r["max_dd"] or 0, r["net_profit_pct"] or 0, regime_info))

print()
print("=== BOTTOM 15 BY PF (lowest non-fixture) ===")
non_fixture = [r for r in results if r["id"] != "bt-fixture" and r["pf"] is not None]
non_fixture.sort(key=lambda x: x["pf"])
for r in non_fixture[:15]:
    regime_info = ""
    if r["regime_pf"]:
        rpf = r["regime_pf"]
        regime_info = " | regime_pf: tr=%.3f ra=%.3f trans=%.3f" % (rpf.get("trending", 0), rpf.get("ranging", 0), rpf.get("transitional", 0))
    wr_str = "%.2f%%" % (r["win_rate"]*100) if r["win_rate"] else "N/A"
    print("  %s | variant=%s | PF=%.4f | trades=%d | WR=%s | DD=%.2f%s" % (r["id"], r["variant"], r["pf"], r["trades"], wr_str, r["max_dd"] or 0, regime_info))

print()
print("=== REGIME ANALYSIS (files with regime data) ===")
regime_results = [r for r in results if r["regime_pf"] is not None]
print("  Files with regime data: %d of %d" % (len(regime_results), len(results)))
for r in regime_results:
    rpf = r["regime_pf"]
    rb = r["regime_breakdown"]
    rwr = r["regime_wr"]
    tr_pf = rpf.get("trending", 0)
    ra_pf = rpf.get("ranging", 0)
    trans_pf = rpf.get("transitional", 0)

    profitable_regimes = sum(1 for v in [tr_pf, ra_pf, trans_pf] if v > 1.0)
    flag = ""
    if profitable_regimes == 1:
        flag = " ** SINGLE-REGIME PROFIT **"
    elif profitable_regimes == 0:
        flag = " ** UNPROFITABLE ALL REGIMES **"

    print("  %s | variant=%s | PF=%.4f" % (r["id"], r["variant"], r["pf"]))
    print("    trending:  PF=%.3f trades=%s WR=%.2f%%" % (tr_pf, rb.get("trending_trades", "?"), rwr.get("trending", 0)*100))
    print("    ranging:   PF=%.3f trades=%s WR=%.2f%%" % (ra_pf, rb.get("ranging_trades", "?"), rwr.get("ranging", 0)*100))
    print("    transit:   PF=%.3f trades=%s WR=%.2f%%%s" % (trans_pf, rb.get("transitional_trades", "?"), rwr.get("transitional", 0)*100, flag))
    print()

print()
print("=== AGGREGATE STATS ===")
pfs = [r["pf"] for r in results if r["pf"] and r["id"] != "bt-fixture"]
trades_all = [r["trades"] for r in results if r["trades"] and r["id"] != "bt-fixture"]
profitable = sum(1 for r in results if r["pf"] and r["pf"] > 1.0 and r["id"] != "bt-fixture")
print("  Avg PF: %.4f" % (sum(pfs)/len(pfs)))
print("  Median PF: %.4f" % sorted(pfs)[len(pfs)//2])
print("  PF > 1.0: %d of %d (%.1f%%)" % (profitable, len(pfs), 100*profitable/len(pfs)))
print("  Avg trades: %.1f" % (sum(trades_all)/len(trades_all)))
print("  Min trades: %d" % min(trades_all))
print("  Max trades: %d" % max(trades_all))

print()
print("=== VARIANT SUMMARY ===")
variant_stats = defaultdict(list)
for r in results:
    if r["id"] == "bt-fixture":
        continue
    variant_stats[r["variant"]].append(r["pf"])
for v, pfs_list in sorted(variant_stats.items(), key=lambda x: -sum(x[1])/len(x[1])):
    avg = sum(pfs_list)/len(pfs_list)
    best = max(pfs_list)
    worst = min(pfs_list)
    print("  %s: count=%d avg_pf=%.4f best=%.4f worst=%.4f" % (v, len(pfs_list), avg, best, worst))

print()
print("=== SPEC-LEVEL DEDUP CHECK ===")
spec_results = defaultdict(list)
for r in results:
    if r["id"] == "bt-fixture":
        continue
    spec_results[r["spec"]].append(r)
for spec, entries in sorted(spec_results.items()):
    if len(entries) > 1:
        pf_set = set(round(e["pf"] or 0, 6) for e in entries)
        if len(pf_set) == 1 and len(entries) > 2:
            print("  SUSPECT: %s has %d variants ALL with identical PF=%.4f" % (spec, len(entries), list(pf_set)[0]))

print()
print("=== DAY-OVER-DAY PF TREND ===")
for day in days:
    day_pfs = [r["pf"] for r in results if r["day"] == day and r["pf"] and r["id"] != "bt-fixture"]
    if day_pfs:
        print("  %s: avg_pf=%.4f median=%.4f min=%.4f max=%.4f n=%d" % (day, sum(day_pfs)/len(day_pfs), sorted(day_pfs)[len(day_pfs)//2], min(day_pfs), max(day_pfs), len(day_pfs)))
