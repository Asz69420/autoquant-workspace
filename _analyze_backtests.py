"""Analyze backtest results from 2026-03-04."""
import os
import json
from collections import Counter

DIR = "C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260304"

# Get all result files
result_files = sorted([f for f in os.listdir(DIR) if f.endswith('.backtest_result.json')])
trade_files = sorted([f for f in os.listdir(DIR) if f.endswith('.trade_list.json')])

print(f"=== FILE COUNTS ===")
print(f"backtest_result.json files: {len(result_files)}")
print(f"trade_list.json files: {len(trade_files)}")

# Analyze trade_list sizes
trade_sizes = {}
for f in trade_files:
    sz = os.path.getsize(os.path.join(DIR, f))
    trade_sizes[f] = sz

size_dist = Counter(trade_sizes.values())
print(f"\n=== TRADE_LIST FILE SIZE DISTRIBUTION ===")
for sz, cnt in sorted(size_dist.items())[:15]:
    print(f"  {sz} bytes: {cnt} files")
if len(size_dist) > 15:
    print(f"  ... ({len(size_dist)} unique sizes total)")
    for sz, cnt in sorted(size_dist.items())[-5:]:
        print(f"  {sz} bytes: {cnt} files")

# Zero-trade threshold
zero_trade_ids = set()
has_trade_ids = set()
for f, sz in trade_sizes.items():
    fid = f.replace('.trade_list.json', '')
    if sz < 150:
        zero_trade_ids.add(fid)
    else:
        has_trade_ids.add(fid)

print(f"\n=== ZERO-TRADE ANALYSIS ===")
print(f"Zero-trade (trade_list < 150 bytes): {len(zero_trade_ids)}")
print(f"Has trades (trade_list >= 150 bytes): {len(has_trade_ids)}")
print(f"Zero-trade percentage: {len(zero_trade_ids)/len(trade_files)*100:.1f}%")

# Now read all backtest_result files for key metrics
print(f"\n=== READING ALL RESULT FILES ===")
all_results = []
errors = 0
for f in result_files:
    try:
        with open(os.path.join(DIR, f), 'r') as fh:
            data = json.load(fh)
        r = data.get('results', {})
        inp = data.get('inputs', {})
        cov = data.get('coverage', {})
        gate = data.get('gate', {})

        # Extract asset and timeframe from dataset_meta path
        meta_path = inp.get('dataset_meta', '')
        parts = meta_path.replace('\\', '/').split('/')
        asset = ''
        timeframe = ''
        for i, p in enumerate(parts):
            if p == 'hyperliquid' and i + 2 < len(parts):
                asset = parts[i+1]
                timeframe = parts[i+2]
                break

        # Extract spec name from strategy_spec path
        spec_path = inp.get('strategy_spec', '')
        spec_name = os.path.basename(spec_path).replace('.strategy_spec.json', '') if spec_path else ''
        variant = inp.get('variant', '')

        rec = {
            'id': data.get('id', ''),
            'asset': asset,
            'timeframe': timeframe,
            'spec_name': spec_name,
            'variant': variant,
            'total_trades': r.get('total_trades', 0),
            'profit_factor': r.get('profit_factor', 0.0),
            'win_rate': r.get('win_rate', 0.0),
            'max_drawdown_pct': r.get('max_drawdown_pct', 0.0),
            'net_profit_pct': r.get('net_profit_pct', 0.0),
            'total_return_pct': r.get('total_return_pct', 0.0),
            'final_equity': r.get('final_equity', 0.0),
            'gate_pass': gate.get('gate_pass', False),
            'gate_reason': gate.get('gate_reason', ''),
            'regime_pf': r.get('regime_pf', {}),
            'regime_trades': r.get('regime_breakdown', {}),
            'entry_signals': cov.get('entry_signals_seen', {}),
            'time_in_market_pct': cov.get('time_in_market_pct', 0.0),
        }
        all_results.append(rec)
    except Exception as e:
        errors += 1

print(f"Successfully parsed: {len(all_results)}")
print(f"Errors: {errors}")

# Gate pass analysis
gate_pass = [r for r in all_results if r['gate_pass']]
gate_fail = [r for r in all_results if not r['gate_pass']]
print(f"\n=== GATE RESULTS ===")
print(f"Gate PASS: {len(gate_pass)}")
print(f"Gate FAIL: {len(gate_fail)}")

# Gate reasons
reasons = Counter(r['gate_reason'] for r in all_results)
print(f"\nGate reasons:")
for reason, cnt in reasons.most_common():
    print(f"  {reason}: {cnt}")

# Zero-trade confirmation from results
zero_from_results = sum(1 for r in all_results if r['total_trades'] == 0)
print(f"\nZero trades (from results JSON): {zero_from_results}")

# Asset/timeframe distribution
asset_tf = Counter(f"{r['asset']}/{r['timeframe']}" for r in all_results)
print(f"\n=== ASSET/TIMEFRAME DISTRIBUTION ===")
for at, cnt in asset_tf.most_common():
    print(f"  {at}: {cnt}")

# Variant distribution
variants = Counter(r['variant'] for r in all_results)
print(f"\n=== VARIANT DISTRIBUTION ===")
for v, cnt in variants.most_common():
    print(f"  {v}: {cnt}")

# Spec name distribution
specs = Counter(r['spec_name'] for r in all_results)
print(f"\n=== UNIQUE SPEC NAMES: {len(specs)} ===")
for sp, cnt in specs.most_common(20):
    print(f"  {sp}: {cnt}")

# PF > 1.0 results
profitable = [r for r in all_results if r['profit_factor'] > 1.0 and r['total_trades'] > 0]
print(f"\n=== PROFITABLE RESULTS (PF > 1.0, trades > 0) ===")
print(f"Count: {len(profitable)}")

# PF > 2.0 results
high_pf = [r for r in all_results if r['profit_factor'] > 2.0 and r['total_trades'] > 0]
print(f"\n=== HIGH PF RESULTS (PF > 2.0, trades > 0) ===")
print(f"Count: {len(high_pf)}")
for r in sorted(high_pf, key=lambda x: -x['profit_factor']):
    print(f"  PF={r['profit_factor']:.3f} | {r['asset']}/{r['timeframe']} | trades={r['total_trades']} | WR={r['win_rate']:.1f}% | DD={r['max_drawdown_pct']:.1f}% | ret={r['total_return_pct']:.1f}% | spec={r['spec_name']} | var={r['variant']}")
    print(f"    regime_pf={r['regime_pf']} | regime_trades={r['regime_trades']}")

# All non-zero results sorted by PF
has_trades_results = [r for r in all_results if r['total_trades'] > 0]
print(f"\n=== ALL RESULTS WITH TRADES (sorted by PF desc) ===")
print(f"Count: {len(has_trades_results)}")
for r in sorted(has_trades_results, key=lambda x: -x['profit_factor'])[:30]:
    print(f"  PF={r['profit_factor']:.3f} | {r['asset']}/{r['timeframe']} | trades={r['total_trades']} | WR={r['win_rate']:.1f}% | DD={r['max_drawdown_pct']:.1f}% | ret={r['total_return_pct']:.1f}% | gate={r['gate_pass']} | spec={r['spec_name'][:50]} | var={r['variant']}")

# Bottom results
print(f"\n=== WORST RESULTS WITH TRADES (sorted by PF asc) ===")
for r in sorted(has_trades_results, key=lambda x: x['profit_factor'])[:15]:
    print(f"  PF={r['profit_factor']:.3f} | {r['asset']}/{r['timeframe']} | trades={r['total_trades']} | WR={r['win_rate']:.1f}% | DD={r['max_drawdown_pct']:.1f}% | ret={r['total_return_pct']:.1f}% | spec={r['spec_name'][:50]} | var={r['variant']}")

# Check for duplicate results (same PF, same trades, same return)
print(f"\n=== DUPLICATE CHECK ===")
fingerprints = Counter()
fp_details = {}
for r in has_trades_results:
    fp = f"pf={r['profit_factor']:.6f}_trades={r['total_trades']}_ret={r['total_return_pct']:.6f}_wr={r['win_rate']:.4f}"
    fingerprints[fp] += 1
    if fp not in fp_details:
        fp_details[fp] = []
    fp_details[fp].append(r)

dupes = {fp: cnt for fp, cnt in fingerprints.items() if cnt > 1}
print(f"Unique fingerprints: {len(fingerprints)}")
print(f"Duplicate groups: {len(dupes)}")
for fp, cnt in sorted(dupes.items(), key=lambda x: -x[1])[:10]:
    print(f"\n  Fingerprint ({cnt}x): {fp}")
    for r in fp_details[fp][:3]:
        print(f"    {r['id']} | {r['asset']}/{r['timeframe']} | spec={r['spec_name'][:50]} | var={r['variant']}")

# Entry signal analysis for zero-trade results
print(f"\n=== ENTRY SIGNAL ANALYSIS (zero-trade results) ===")
zero_results = [r for r in all_results if r['total_trades'] == 0]
signal_counts = Counter()
for r in zero_results:
    total_signals = r['entry_signals'].get('total', 0)
    signal_counts[total_signals] += 1
print(f"Entry signals seen in zero-trade results:")
for sig, cnt in sorted(signal_counts.items())[:10]:
    print(f"  {sig} signals: {cnt} backtests")
