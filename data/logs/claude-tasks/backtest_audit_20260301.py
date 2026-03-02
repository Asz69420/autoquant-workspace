import json, glob, os, re

BASE = "C:/Users/Clamps/.openclaw/workspace"
files = sorted(glob.glob(os.path.join(BASE, "artifacts/backtests/20260301/*.backtest_result.json")))
print(f"Total files: {len(files)}")

high_pf_low_trade = []
zero_trade = []
high_winrate = []
zero_dd = []
identical_results = {}
btc_results = []
negative_or_nan = []
all_results = []

for f in files:
    try:
        with open(f) as fh:
            data = json.load(fh)

        r = data.get("results", data)
        fid = os.path.basename(f).replace(".backtest_result.json", "")

        pf = r.get("profit_factor", 0) or 0
        trades = r.get("total_trades", 0) or 0
        wr = r.get("win_rate", 0) or 0
        dd_pct = r.get("max_drawdown_pct", 0) or 0
        dd_abs = r.get("max_drawdown", 0) or 0
        net = r.get("net_profit", 0) or 0

        # Extract asset/tf from inputs.dataset_meta path
        inputs = data.get("inputs", {})
        ds_meta = inputs.get("dataset_meta", "")
        variant = inputs.get("variant", data.get("variant_name", r.get("variant_name", "")))

        # Parse asset/tf from path like .../hyperliquid/BTC/4h/...
        asset = ""
        tf = ""
        m = re.search(r"hyperliquid[/\\](\w+)[/\\](\w+)[/\\]", ds_meta)
        if m:
            asset = m.group(1)
            tf = m.group(2)
        else:
            asset = r.get("asset", data.get("asset", ""))
            tf = r.get("timeframe", data.get("timeframe", ""))

        template = r.get("template_name", data.get("template_name", ""))

        # Gate info
        gate_info = data.get("gate", {})
        gate = gate_info.get("gate_pass", data.get("gate_pass", None))
        min_trades = gate_info.get("min_trades_required", data.get("min_trades_required", None))

        # Regime
        rb = r.get("regime_breakdown", data.get("regime_breakdown", {}))
        t_trades = rb.get("trending_trades", "N/A")
        r_trades = rb.get("ranging_trades", "N/A")
        tr_trades = rb.get("transitional_trades", "N/A")

        rpf = r.get("regime_pf", data.get("regime_pf", {}))
        t_pf = rpf.get("trending", "N/A")
        r_pf = rpf.get("ranging", "N/A")
        tr_pf = rpf.get("transitional", "N/A")

        rec = {
            "id": fid, "variant": variant, "template": template,
            "pf": pf, "trades": trades, "wr": wr,
            "dd_pct": dd_pct, "dd_abs": dd_abs, "net": net,
            "asset": asset, "tf": tf, "gate": gate, "min_trades": min_trades,
            "t_trades": t_trades, "r_trades": r_trades, "tr_trades": tr_trades,
            "t_pf": t_pf, "r_pf": r_pf, "tr_pf": tr_pf
        }
        all_results.append(rec)

        fp = f"{pf:.6f}|{trades}|{net:.2f}"
        if fp not in identical_results:
            identical_results[fp] = []
        identical_results[fp].append(fid)

        if trades == 0:
            zero_trade.append(rec)
        if pf > 2.0 and trades < 30 and trades > 0:
            high_pf_low_trade.append(rec)
        if wr and wr > 0.70 and trades > 0:
            high_winrate.append(rec)
        if dd_pct == 0 and trades > 0:
            zero_dd.append(rec)
        if "BTC" in str(asset).upper():
            btc_results.append(rec)
        if trades < 0 or (isinstance(pf, float) and pf != pf):
            negative_or_nan.append(rec)
    except Exception as e:
        print(f"ERROR reading {f}: {e}")

print(f"\n=== SUMMARY ===")
print(f"Total results: {len(all_results)}")
print(f"Zero-trade results: {len(zero_trade)}")
print(f"BTC results: {len(btc_results)}")
print(f"High PF (>2.0) / Low trades (<30): {len(high_pf_low_trade)}")
print(f"High win rate (>70%): {len(high_winrate)}")
print(f"Zero DD% with trades: {len(zero_dd)}")
print(f"Negative trades/NaN: {len(negative_or_nan)}")

dupes = {k: v for k, v in identical_results.items() if len(v) > 1}
dup_count = sum(len(v) - 1 for v in dupes.values())
print(f"Duplicate fingerprint groups: {len(dupes)}")
print(f"Total duplicate results (wasted): {dup_count}")

print(f"\n=== HIGH PF / LOW TRADES (PF>2, trades<30) ===")
for r in sorted(high_pf_low_trade, key=lambda x: x["pf"], reverse=True)[:20]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} WR={r['wr']:.4f} DD={r['dd_pct']:.1f}% asset={r['asset']} tf={r['tf']}")

print(f"\n=== ZERO TRADE RESULTS (first 20) ===")
for r in zero_trade[:20]:
    print(f"  {r['id']}: {r['variant']} template={r['template']} asset={r['asset']} tf={r['tf']} gate={r['gate']} min_trades={r['min_trades']}")

print(f"\n=== BTC RESULTS (first 30) ===")
for r in sorted(btc_results, key=lambda x: x["pf"], reverse=True)[:30]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} DD%={r['dd_pct']:.1f} net={r['net']:.2f}")

print(f"\n=== HIGH WIN RATE (>70%, first 20) ===")
for r in sorted(high_winrate, key=lambda x: x["wr"], reverse=True)[:20]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} WR={r['wr']:.4f}")

print(f"\n=== ZERO DD% WITH TRADES (first 20) ===")
for r in zero_dd[:20]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} DD%={r['dd_pct']} DD_abs={r['dd_abs']}")

print(f"\n=== DUPLICATE FINGERPRINTS (top 10 groups) ===")
for fp, ids in sorted(dupes.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    parts = fp.split("|")
    print(f"  PF={parts[0]} trades={parts[1]}: {len(ids)} copies -> {ids[:5]}{'...' if len(ids) > 5 else ''}")

legit = [r for r in all_results if r["trades"] >= 30]
print(f"\n=== TOP 15 PF RESULTS (trades >= 30) ===")
for r in sorted(legit, key=lambda x: x["pf"], reverse=True)[:15]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} WR={r['wr']:.4f} DD={r['dd_pct']:.1f}% net={r['net']:.2f} asset={r['asset']} tf={r['tf']}")
    print(f"    Regime: trending={r['t_trades']}(PF={r['t_pf']}) ranging={r['r_trades']}(PF={r['r_pf']}) trans={r['tr_trades']}(PF={r['tr_pf']})")

gate_zero = [r for r in all_results if r.get("min_trades") == 0]
print(f"\n=== GATE BUG (min_trades_required=0) ===")
print(f"  Affected results: {len(gate_zero)}")
for r in gate_zero[:10]:
    print(f"  {r['id']}: {r['variant']} trades={r['trades']} gate_pass={r['gate']}")

worst = [r for r in all_results if r["trades"] > 0]
print(f"\n=== WORST 10 PF RESULTS ===")
for r in sorted(worst, key=lambda x: x["pf"])[:10]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} DD={r['dd_pct']:.1f}% net={r['net']:.2f} asset={r['asset']}")

dir_exp = [r for r in all_results if "directive" in str(r.get("variant", "")).lower()]
print(f"\n=== DIRECTIVE VARIANTS ===")
print(f"  Total directive variants: {len(dir_exp)}")
for r in dir_exp[:15]:
    print(f"  {r['id']}: {r['variant']} PF={r['pf']:.3f} trades={r['trades']} DD={r['dd_pct']:.1f}%")

assets = {}
for r in all_results:
    a = r["asset"] or "UNKNOWN"
    if a not in assets:
        assets[a] = {"count": 0, "pf_sum": 0, "total_trades": 0, "net_sum": 0}
    assets[a]["count"] += 1
    assets[a]["pf_sum"] += r["pf"]
    assets[a]["total_trades"] += r["trades"]
    assets[a]["net_sum"] += r["net"]

print(f"\n=== ASSET DISTRIBUTION ===")
for a, v in sorted(assets.items(), key=lambda x: x[1]["count"], reverse=True):
    avg_pf = v["pf_sum"] / v["count"] if v["count"] > 0 else 0
    print(f"  {a}: {v['count']} results, avg_pf={avg_pf:.3f}, total_trades={v['total_trades']}, net_sum={v['net_sum']:.2f}")

tfs = {}
for r in all_results:
    t = r["tf"] or "UNKNOWN"
    if t not in tfs:
        tfs[t] = {"count": 0, "pf_sum": 0}
    tfs[t]["count"] += 1
    tfs[t]["pf_sum"] += r["pf"]

print(f"\n=== TIMEFRAME DISTRIBUTION ===")
for t, v in sorted(tfs.items(), key=lambda x: x[1]["count"], reverse=True):
    avg_pf = v["pf_sum"] / v["count"] if v["count"] > 0 else 0
    print(f"  {t}: {v['count']} results, avg_pf={avg_pf:.3f}")

templates = {}
for r in all_results:
    t = r["template"] or "UNKNOWN"
    if t not in templates:
        templates[t] = {"count": 0, "pf_sum": 0, "trades_sum": 0, "gate_pass": 0}
    templates[t]["count"] += 1
    templates[t]["pf_sum"] += r["pf"]
    templates[t]["trades_sum"] += r["trades"]
    if r.get("gate") == True:
        templates[t]["gate_pass"] += 1

print(f"\n=== TEMPLATE DISTRIBUTION ===")
for t, v in sorted(templates.items(), key=lambda x: x[1]["count"], reverse=True):
    avg_pf = v["pf_sum"] / v["count"] if v["count"] > 0 else 0
    print(f"  {t}: {v['count']} results, avg_pf={avg_pf:.3f}, total_trades={v['trades_sum']}, gate_pass={v['gate_pass']}")

gate_pass_count = sum(1 for r in all_results if r.get("gate") == True)
gate_fail_count = sum(1 for r in all_results if r.get("gate") == False)
gate_none_count = sum(1 for r in all_results if r.get("gate") is None)
print(f"\n=== GATE PASS SUMMARY ===")
print(f"  gate_pass=True: {gate_pass_count}")
print(f"  gate_pass=False: {gate_fail_count}")
print(f"  gate_pass=None/missing: {gate_none_count}")

# PF distribution histogram
pf_buckets = {"<0.5": 0, "0.5-0.8": 0, "0.8-1.0": 0, "1.0-1.2": 0, "1.2-1.5": 0, "1.5-2.0": 0, "2.0-3.0": 0, "3.0+": 0}
for r in all_results:
    p = r["pf"]
    if r["trades"] == 0:
        continue
    if p < 0.5: pf_buckets["<0.5"] += 1
    elif p < 0.8: pf_buckets["0.5-0.8"] += 1
    elif p < 1.0: pf_buckets["0.8-1.0"] += 1
    elif p < 1.2: pf_buckets["1.0-1.2"] += 1
    elif p < 1.5: pf_buckets["1.2-1.5"] += 1
    elif p < 2.0: pf_buckets["1.5-2.0"] += 1
    elif p < 3.0: pf_buckets["2.0-3.0"] += 1
    else: pf_buckets["3.0+"] += 1

print(f"\n=== PF DISTRIBUTION (excl zero-trade) ===")
for bucket, count in pf_buckets.items():
    bar = "#" * min(count, 80)
    print(f"  {bucket:>8}: {count:>4} {bar}")

# Profitable vs unprofitable
profitable = sum(1 for r in all_results if r["trades"] > 0 and r["pf"] > 1.0)
unprofitable = sum(1 for r in all_results if r["trades"] > 0 and r["pf"] <= 1.0)
print(f"\n=== PROFITABILITY ===")
print(f"  Profitable (PF>1): {profitable}")
print(f"  Unprofitable (PF<=1): {unprofitable}")
if profitable + unprofitable > 0:
    print(f"  Win rate: {profitable/(profitable+unprofitable)*100:.1f}%")
