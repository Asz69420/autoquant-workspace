import json, os, glob
from collections import Counter

base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests'
dirs = ['20260226', '20260227', '20260228']

files_by_dir = {}
for d in dirs:
    pattern = os.path.join(base, d, '*.backtest_result.json')
    files = sorted(glob.glob(pattern))
    files = [f for f in files if 'fixture' not in os.path.basename(f)]
    files_by_dir[d] = files

samples = []
for d in ['20260226', '20260227']:
    flist = files_by_dir[d]
    n = len(flist)
    step = max(1, n // 14)
    picked = [flist[i] for i in range(0, n, step)][:14]
    samples.extend(picked)

flist_28 = files_by_dir['20260228']
n28 = len(flist_28)
step28 = max(1, n28 // 12)
picked28 = [flist_28[i] for i in range(0, n28, step28)][:12]
samples.extend(picked28)

print("Total sample: %d" % len(samples))
for d in dirs:
    count = sum(1 for s in samples if d in s)
    print("  %s: %d" % (d, count))

rows = []
for fpath in samples:
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
        rid = data.get('id', 'N/A')
        variant = data.get('inputs', {}).get('variant', 'N/A')
        results = data.get('results', {})
        pf = results.get('profit_factor', None)
        trades = results.get('total_trades', None)
        wr = results.get('win_rate', None)
        dd = results.get('max_drawdown', None)
        regime_pf = None
        if 'regime_breakdown' in results:
            regime_pf = 'Yes'
        elif 'regime_pf' in results:
            regime_pf = 'Yes'
        gate = data.get('gate', {})
        gate_pass = gate.get('gate_pass', None)
        spec = data.get('inputs', {}).get('strategy_spec', 'N/A')
        spec_base = os.path.basename(spec) if spec != 'N/A' else 'N/A'
        rows.append([rid, variant, pf, trades, wr, dd, regime_pf, gate_pass, spec_base])
    except Exception as e:
        rows.append([os.path.basename(fpath), 'ERROR', None, None, None, None, None, None, str(e)])

print()
hdr = "%-30s %-22s %6s %6s %6s %10s %6s %5s %s" % ("ID", "Variant", "PF", "Trades", "WR%", "MaxDD", "Regime", "Gate", "Spec")
print(hdr)
print("-" * 160)
for r in rows:
    rid, variant, pf, trades, wr, dd, regime_pf, gate_pass, spec = r
    pf_s = "%.2f" % pf if pf is not None else "N/A"
    tr_s = str(trades) if trades is not None else "N/A"
    wr_s = "%.1f" % (wr*100) if wr is not None else "N/A"
    dd_s = "%.1f" % dd if dd is not None else "N/A"
    rg_s = "Yes" if regime_pf else "No"
    gp_s = "Y" if gate_pass == True else ("N" if gate_pass == False else "?")
    spec_short = spec[:48] if spec else "N/A"
    print("%-30s %-22s %6s %6s %6s %10s %6s %5s %s" % (rid, variant, pf_s, tr_s, wr_s, dd_s, rg_s, gp_s, spec_short))

# Summary
pfs = [r[2] for r in rows if r[2] is not None]
trades_list = [r[3] for r in rows if r[3] is not None]
wr_list = [r[4] for r in rows if r[4] is not None]
dd_list = [r[5] for r in rows if r[5] is not None]

print()
print("=== SUMMARY STATS ===")
print("Total files sampled:  %d" % len(rows))
print("Files with valid PF:  %d" % len(pfs))
if pfs:
    print("Avg PF:               %.4f" % (sum(pfs)/len(pfs)))
    print("Min PF:               %.4f" % min(pfs))
    print("Max PF:               %.4f" % max(pfs))
    sorted_pfs = sorted(pfs)
    print("Median PF:            %.4f" % sorted_pfs[len(pfs)//2])
    gt1 = sum(1 for p in pfs if p > 1.0)
    gt12 = sum(1 for p in pfs if p > 1.2)
    gt15 = sum(1 for p in pfs if p > 1.5)
    lt08 = sum(1 for p in pfs if p < 0.8)
    print("PF > 1.0:             %d / %d (%.1f%%)" % (gt1, len(pfs), gt1/len(pfs)*100))
    print("PF > 1.2:             %d / %d (%.1f%%)" % (gt12, len(pfs), gt12/len(pfs)*100))
    print("PF > 1.5:             %d / %d (%.1f%%)" % (gt15, len(pfs), gt15/len(pfs)*100))
    print("PF < 0.8:             %d / %d (%.1f%%)" % (lt08, len(pfs), lt08/len(pfs)*100))
if trades_list:
    print("Avg Trades:           %.1f" % (sum(trades_list)/len(trades_list)))
    print("Min/Max Trades:       %d / %d" % (min(trades_list), max(trades_list)))
if wr_list:
    print("Avg Win Rate:         %.1f%%" % (sum(wr_list)/len(wr_list)*100))
if dd_list:
    print("Avg Max DD:           %.1f" % (sum(dd_list)/len(dd_list)))
    print("Min/Max DD:           %.1f / %.1f" % (min(dd_list), max(dd_list)))

regime_count = sum(1 for r in rows if r[6] is not None)
print("Has Regime Data:      %d / %d" % (regime_count, len(rows)))
gate_pass_count = sum(1 for r in rows if r[7] == True)
gate_fail_count = sum(1 for r in rows if r[7] == False)
print("Gate Pass:            %d / %d" % (gate_pass_count, len(rows)))
print("Gate Fail:            %d / %d" % (gate_fail_count, len(rows)))

# Variant breakdown
var_counts = Counter(r[1] for r in rows)
print()
print("=== VARIANT BREAKDOWN ===")
for v, c in var_counts.most_common():
    vpfs = [r[2] for r in rows if r[1] == v and r[2] is not None]
    avg_pf = sum(vpfs)/len(vpfs) if vpfs else 0
    gt1 = sum(1 for p in vpfs if p > 1.0)
    print("  %-22s count=%3d  avg_pf=%.3f  PF>1.0=%d/%d" % (v, c, avg_pf, gt1, len(vpfs)))

# Spec breakdown
spec_counts = Counter(r[8] for r in rows)
print()
print("=== SPEC BREAKDOWN (top 15) ===")
for s, c in spec_counts.most_common(15):
    spfs = [r[2] for r in rows if r[8] == s and r[2] is not None]
    avg_pf = sum(spfs)/len(spfs) if spfs else 0
    print("  %-55s count=%2d  avg_pf=%.3f" % (s[:55], c, avg_pf))

# Date breakdown
print()
print("=== DATE BREAKDOWN ===")
for d in dirs:
    drows = [r for r in rows if d in r[0]]
    dpfs = [r[2] for r in drows if r[2] is not None]
    if dpfs:
        avg = sum(dpfs)/len(dpfs)
        gt1 = sum(1 for p in dpfs if p > 1.0)
        print("  %s: n=%3d  avg_pf=%.3f  PF>1.0=%d/%d (%.0f%%)" % (d, len(drows), avg, gt1, len(dpfs), gt1/len(dpfs)*100))
