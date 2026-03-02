import json, os, glob, sys
from collections import defaultdict, Counter

# Step 1: Extract all backtest results
dates = ['20260228', '20260301']
base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
results = []

for d in dates:
    pattern = os.path.join(base, f'artifacts/backtests/{d}/*.backtest_result.json')
    files = glob.glob(pattern)
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"ERROR reading {f}: {e}")
            continue
        r = data.get('results', {})
        inp = data.get('inputs', {})
        gate = data.get('gate', {})
        regime_pf = r.get('regime_pf', {})
        regime_bd = r.get('regime_breakdown', {})
        results.append({
            'id': data.get('id', ''),
            'date': d,
            'file': os.path.basename(f),
            'spec': os.path.basename(inp.get('strategy_spec', '')),
            'variant': inp.get('variant', 'unknown'),
            'pf': r.get('profit_factor'),
            'trades': r.get('total_trades'),
            'win_rate': r.get('win_rate'),
            'max_dd': r.get('max_drawdown'),
            'max_dd_pct': r.get('max_drawdown_pct'),
            'net_profit': r.get('net_profit'),
            'gate_pass': gate.get('gate_pass'),
            'min_trades_req': gate.get('min_trades_required'),
            'trending_pf': regime_pf.get('trending'),
            'ranging_pf': regime_pf.get('ranging'),
            'transitional_pf': regime_pf.get('transitional'),
            'trending_trades': regime_bd.get('trending_trades'),
            'ranging_trades': regime_bd.get('ranging_trades'),
            'transitional_trades': regime_bd.get('transitional_trades'),
        })

# Save extracted data
out_path = os.path.join(base, 'data/logs/claude-tasks/audit_data.json')
with open(out_path, 'w') as out:
    json.dump(results, out, indent=2)

print(f"=== AUDIT EXTRACTION COMPLETE ===")
print(f"Total records extracted: {len(results)}")
print()

# Step 2: Analysis
print("=" * 80)
print("BACKTEST AUDIT REPORT — 2026-03-01")
print("=" * 80)

# --- Total count by date ---
print("\n--- TOTAL COUNT BY DATE ---")
date_counts = Counter(r['date'] for r in results)
for d, c in sorted(date_counts.items()):
    print(f"  {d}: {c} backtests")
print(f"  TOTAL: {len(results)}")

# --- Zero-trade results ---
print("\n--- ZERO-TRADE RESULTS (trades == 0) ---")
zero_trades = [r for r in results if r['trades'] is not None and r['trades'] == 0]
print(f"  Count: {len(zero_trades)}")
for r in zero_trades:
    print(f"    {r['id']} | variant={r['variant']} | spec={r['spec']}")

# --- Null/None trade counts ---
null_trades = [r for r in results if r['trades'] is None]
if null_trades:
    print(f"\n--- NULL TRADE COUNTS ---")
    print(f"  Count: {len(null_trades)}")
    for r in null_trades:
        print(f"    {r['id']} | variant={r['variant']}")

# --- Negative trade counts ---
neg_trades = [r for r in results if r['trades'] is not None and r['trades'] < 0]
if neg_trades:
    print(f"\n--- NEGATIVE TRADE COUNTS ---")
    print(f"  Count: {len(neg_trades)}")
    for r in neg_trades:
        print(f"    {r['id']} | trades={r['trades']} | variant={r['variant']}")
else:
    print("\n--- NEGATIVE TRADE COUNTS ---")
    print("  None found.")

# --- Null/NaN PF values ---
null_pf = [r for r in results if r['pf'] is None]
print(f"\n--- NULL PF VALUES ---")
print(f"  Count: {len(null_pf)}")
for r in null_pf[:20]:
    print(f"    {r['id']} | trades={r['trades']} | variant={r['variant']}")
if len(null_pf) > 20:
    print(f"    ... and {len(null_pf)-20} more")

# --- Overfit suspects: PF > 2.0 AND trades < 30 ---
print("\n--- OVERFIT SUSPECTS (PF > 2.0 AND trades < 30) ---")
overfit = [r for r in results if r['pf'] is not None and r['pf'] > 2.0 and r['trades'] is not None and r['trades'] < 30 and r['trades'] > 0]
print(f"  Count: {len(overfit)}")
for r in sorted(overfit, key=lambda x: x['pf'], reverse=True):
    print(f"    {r['id']} | PF={r['pf']:.4f} | trades={r['trades']} | wr={r['win_rate']:.4f} | variant={r['variant']}")

# --- Suspicious high win rate: > 0.70 ---
print("\n--- SUSPICIOUS HIGH WIN RATE (> 0.70) ---")
high_wr = [r for r in results if r['win_rate'] is not None and r['win_rate'] > 0.70 and r['trades'] is not None and r['trades'] > 0]
print(f"  Count: {len(high_wr)}")
for r in sorted(high_wr, key=lambda x: x['win_rate'], reverse=True):
    print(f"    {r['id']} | WR={r['win_rate']:.4f} | PF={r['pf']} | trades={r['trades']} | variant={r['variant']}")

# --- Impossible: max_dd == 0 but trades > 0 ---
print("\n--- IMPOSSIBLE: max_dd == 0 BUT trades > 0 ---")
impossible_dd = [r for r in results if r['max_dd'] is not None and r['max_dd'] == 0 and r['trades'] is not None and r['trades'] > 0]
print(f"  Count: {len(impossible_dd)}")
for r in impossible_dd:
    print(f"    {r['id']} | trades={r['trades']} | PF={r['pf']} | net_profit={r['net_profit']} | variant={r['variant']}")

# --- Duplicate detection: same (spec, variant) with identical PF ---
print("\n--- DUPLICATE DETECTION: same (spec, variant) with identical PF ---")
sv_pf = defaultdict(list)
for r in results:
    key = (r['spec'], r['variant'])
    sv_pf[key].append(r)

dup_count = 0
for key, recs in sorted(sv_pf.items()):
    if len(recs) > 1:
        pf_vals = [r['pf'] for r in recs]
        # Check if any PF values are identical (not None)
        pf_counter = Counter(v for v in pf_vals if v is not None)
        for pf_val, cnt in pf_counter.items():
            if cnt > 1:
                dup_count += 1
                print(f"  spec={key[0]} | variant={key[1]} | PF={pf_val} | appears {cnt}x")
                for r in recs:
                    if r['pf'] == pf_val:
                        print(f"    -> {r['id']} (date={r['date']}, trades={r['trades']})")
if dup_count == 0:
    print("  No exact PF duplicates found.")

# --- All regime PFs null/zero but trades > 0 ---
print("\n--- REGIME PFs ALL NULL/ZERO BUT trades > 0 ---")
regime_null = []
for r in results:
    if r['trades'] is not None and r['trades'] > 0:
        tpf = r['trending_pf']
        rpf = r['ranging_pf']
        xpf = r['transitional_pf']
        all_null_zero = all(
            v is None or v == 0 for v in [tpf, rpf, xpf]
        )
        if all_null_zero:
            regime_null.append(r)
print(f"  Count: {len(regime_null)}")
for r in regime_null[:30]:
    print(f"    {r['id']} | trades={r['trades']} | PF={r['pf']} | variant={r['variant']} | trending_pf={r['trending_pf']} ranging_pf={r['ranging_pf']} trans_pf={r['transitional_pf']}")
if len(regime_null) > 30:
    print(f"    ... and {len(regime_null)-30} more")

# --- Profitable in ONLY ONE regime ---
print("\n--- PROFITABLE IN ONLY ONE REGIME (one PF > 1.0, others < 1.0) ---")
one_regime = []
for r in results:
    if r['trades'] is not None and r['trades'] > 0:
        regime_vals = {
            'trending': r['trending_pf'],
            'ranging': r['ranging_pf'],
            'transitional': r['transitional_pf']
        }
        # Filter to non-None values
        valid = {k: v for k, v in regime_vals.items() if v is not None}
        if len(valid) >= 2:  # need at least 2 regimes to judge
            profitable = [k for k, v in valid.items() if v > 1.0]
            unprofitable = [k for k, v in valid.items() if v < 1.0]
            if len(profitable) == 1 and len(unprofitable) >= 1:
                one_regime.append((r, profitable[0], valid))

print(f"  Count: {len(one_regime)}")
for r, regime, vals in sorted(one_regime, key=lambda x: x[2][x[1]], reverse=True)[:40]:
    print(f"    {r['id']} | ONLY profitable in '{regime}' | trending={vals.get('trending', 'N/A'):.4f} ranging={vals.get('ranging', 'N/A'):.4f} trans={vals.get('transitional', 'N/A'):.4f} | trades={r['trades']} | variant={r['variant']}")
if len(one_regime) > 40:
    print(f"    ... and {len(one_regime)-40} more")

# --- Top 10 highest PF ---
print("\n--- TOP 10 HIGHEST PF RESULTS ---")
valid_pf = [r for r in results if r['pf'] is not None and r['trades'] is not None and r['trades'] > 0]
top10 = sorted(valid_pf, key=lambda x: x['pf'], reverse=True)[:10]
for i, r in enumerate(top10, 1):
    print(f"  #{i}: PF={r['pf']:.4f} | trades={r['trades']} | WR={r['win_rate']:.4f} | net_profit={r['net_profit']:.2f} | max_dd_pct={r['max_dd_pct']:.2f} | variant={r['variant']} | id={r['id']}")

# --- PF Distribution ---
print("\n--- PF DISTRIBUTION ---")
pf_gt1 = len([r for r in results if r['pf'] is not None and r['pf'] > 1.0])
pf_05_1 = len([r for r in results if r['pf'] is not None and 0.5 <= r['pf'] <= 1.0])
pf_lt05 = len([r for r in results if r['pf'] is not None and 0 < r['pf'] < 0.5])
pf_eq0 = len([r for r in results if r['pf'] is not None and r['pf'] == 0])
pf_none = len([r for r in results if r['pf'] is None])
print(f"  PF > 1.0:       {pf_gt1}")
print(f"  PF 0.5 - 1.0:   {pf_05_1}")
print(f"  PF 0.0 < 0.5:   {pf_lt05}")
print(f"  PF == 0:         {pf_eq0}")
print(f"  PF is null:      {pf_none}")
print(f"  TOTAL:           {pf_gt1 + pf_05_1 + pf_lt05 + pf_eq0 + pf_none}")

# Additional distribution detail
if valid_pf:
    pf_vals_sorted = sorted([r['pf'] for r in valid_pf])
    print(f"\n  PF statistics (non-null, trades>0):")
    print(f"    Min:    {pf_vals_sorted[0]:.4f}")
    print(f"    Max:    {pf_vals_sorted[-1]:.4f}")
    print(f"    Median: {pf_vals_sorted[len(pf_vals_sorted)//2]:.4f}")
    avg_pf = sum(pf_vals_sorted) / len(pf_vals_sorted)
    print(f"    Mean:   {avg_pf:.4f}")

# --- Gate pass stats ---
print("\n--- GATE PASS STATS ---")
gate_pass_count = len([r for r in results if r['gate_pass'] == True])
gate_fail_count = len([r for r in results if r['gate_pass'] == False])
gate_none_count = len([r for r in results if r['gate_pass'] is None])
print(f"  Gate PASS:  {gate_pass_count}")
print(f"  Gate FAIL:  {gate_fail_count}")
print(f"  Gate null:  {gate_none_count}")

# Gate pass with min_trades_required == 0
gate_pass_mintrades0 = [r for r in results if r['gate_pass'] == True and r['min_trades_req'] is not None and r['min_trades_req'] == 0]
print(f"\n  Gate PASS with min_trades_required == 0: {len(gate_pass_mintrades0)}")
for r in gate_pass_mintrades0[:15]:
    print(f"    {r['id']} | trades={r['trades']} | PF={r['pf']} | variant={r['variant']}")
if len(gate_pass_mintrades0) > 15:
    print(f"    ... and {len(gate_pass_mintrades0)-15} more")

# Min trades distribution
print(f"\n  min_trades_required distribution:")
min_trades_dist = Counter(r['min_trades_req'] for r in results)
for k, v in sorted(min_trades_dist.items(), key=lambda x: (x[0] is None, x[0] if x[0] is not None else 0)):
    print(f"    min_trades={k}: {v} backtests")

# --- Summary flags ---
print("\n" + "=" * 80)
print("SUMMARY FLAGS")
print("=" * 80)
print(f"  Total backtests:          {len(results)}")
print(f"  Zero-trade results:       {len(zero_trades)}")
print(f"  Overfit suspects:         {len(overfit)}")
print(f"  High win-rate (>70%):     {len(high_wr)}")
print(f"  Impossible max_dd==0:     {len(impossible_dd)}")
print(f"  Single-regime profitable: {len(one_regime)}")
print(f"  Regime PFs all null/0:    {len(regime_null)}")
print(f"  Gate pass rate:           {gate_pass_count}/{len(results)} ({100*gate_pass_count/len(results) if results else 0:.1f}%)")
print(f"  PF > 1.0 rate:            {pf_gt1}/{len(results)} ({100*pf_gt1/len(results) if results else 0:.1f}%)")
