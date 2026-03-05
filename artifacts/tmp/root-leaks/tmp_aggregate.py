import json, glob, os, sys, math
from collections import Counter, defaultdict

# Gather all backtest result files
pattern = os.path.join('C:/Users/Clamps/.openclaw/workspace', 'artifacts/backtests/20260306/*.backtest_result.json')
files = glob.glob(pattern)
print(f'Total backtest result files found: {len(files)}')

# Parse all
results = []
parse_errors = []
for f in files:
    try:
        with open(f, 'r') as fh:
            d = json.load(fh)

        # Extract asset and timeframe from dataset_meta path
        meta = d.get('inputs', {}).get('dataset_meta', '')
        parts = meta.replace('\\', '/').split('/')
        # Find hyperliquid/<asset>/<tf>/
        asset = 'UNKNOWN'
        tf = 'UNKNOWN'
        for i, p in enumerate(parts):
            if p == 'hyperliquid' and i+2 < len(parts):
                asset = parts[i+1]
                tf = parts[i+2]
                break

        r = d.get('results', {})
        cov = d.get('coverage', {})
        ppr_data = d.get('ppr', {})
        spec_path = d.get('inputs', {}).get('strategy_spec', '')
        spec_id = os.path.basename(spec_path).replace('.strategy_spec.json', '')
        variant = d.get('inputs', {}).get('variant', '')

        regime_pf = r.get('regime_pf', {})
        regime_wr = r.get('regime_wr', {})
        regime_bd = r.get('regime_breakdown', {})

        entry_signals = cov.get('entry_signals_seen', {})

        results.append({
            'id': d.get('id', ''),
            'file': os.path.basename(f),
            'spec_id': spec_id,
            'variant': variant,
            'asset': asset,
            'timeframe': tf,
            'total_trades': r.get('total_trades', 0),
            'profit_factor': r.get('profit_factor', 0.0),
            'max_drawdown_pct': r.get('max_drawdown_pct', 0.0),
            'win_rate': r.get('win_rate', 0.0),
            'net_profit_pct': r.get('net_profit_pct', 0.0),
            'total_return_pct': r.get('total_return_pct', 0.0),
            'final_equity': r.get('final_equity', 0.0),
            'regime_pf_trending': regime_pf.get('trending', 0.0),
            'regime_pf_ranging': regime_pf.get('ranging', 0.0),
            'regime_pf_transitional': regime_pf.get('transitional', 0.0),
            'regime_trades_trending': regime_bd.get('trending_trades', 0),
            'regime_trades_ranging': regime_bd.get('ranging_trades', 0),
            'regime_trades_transitional': regime_bd.get('transitional_trades', 0),
            'dominant_regime': r.get('dominant_regime', ''),
            'ppr_score': ppr_data.get('score', 0.0),
            'ppr_decision': ppr_data.get('decision', ''),
            'ppr_flags': ppr_data.get('flags', []),
            'entry_signals_long': entry_signals.get('long', 0),
            'entry_signals_short': entry_signals.get('short', 0),
            'entry_signals_total': entry_signals.get('total', 0),
            'bars_tested': cov.get('bars_tested', 0),
            'time_in_market_pct': cov.get('time_in_market_pct', 0.0),
            'fees_paid': r.get('total_fees_paid', 0.0),
        })
    except Exception as e:
        parse_errors.append((f, str(e)))

if parse_errors:
    print(f'\n=== PARSE ERRORS ({len(parse_errors)}) ===')
    for f, e in parse_errors:
        print(f'  {os.path.basename(f)}: {e}')

# Sort by profit factor descending
results.sort(key=lambda x: (-x['total_trades'], -x['profit_factor']))

# ============================================================
# OVERVIEW STATS
# ============================================================
total = len(results)
zero_trade = [r for r in results if r['total_trades'] == 0]
has_trades = [r for r in results if r['total_trades'] > 0]

print(f'\n{"="*100}')
print(f'BACKTEST RESULTS SUMMARY -- 2026-03-06 ({len(results)} files)')
print('='*100)

print(f'\nTotal backtests:     {total}')
print(f'With trades:         {len(has_trades)}')
print(f'Zero-trade:          {len(zero_trade)}  ({100*len(zero_trade)/total:.1f}%)')

# Asset breakdown
asset_counts = Counter(r['asset'] for r in results)
print(f'\nAsset breakdown:')
for a, c in sorted(asset_counts.items()):
    zt = sum(1 for r in results if r['asset'] == a and r['total_trades'] == 0)
    wt = sum(1 for r in results if r['asset'] == a and r['total_trades'] > 0)
    print(f'  {a:6s}: {c:4d} total  |  {wt:3d} with trades  |  {zt:3d} zero-trade')

# Timeframe breakdown
tf_counts = Counter(r['timeframe'] for r in results)
print(f'\nTimeframe breakdown:')
for t, c in sorted(tf_counts.items()):
    zt = sum(1 for r in results if r['timeframe'] == t and r['total_trades'] == 0)
    wt = sum(1 for r in results if r['timeframe'] == t and r['total_trades'] > 0)
    print(f'  {t:6s}: {c:4d} total  |  {wt:3d} with trades  |  {zt:3d} zero-trade')

# PPR decisions
ppr_counts = Counter(r['ppr_decision'] for r in results)
print(f'\nPPR decisions:')
for d, c in sorted(ppr_counts.items()):
    print(f'  {d:20s}: {c}')

# Variant breakdown
var_counts = Counter(r['variant'] for r in results)
print(f'\nVariant breakdown:')
for v, c in sorted(var_counts.items()):
    zt = sum(1 for r in results if r['variant'] == v and r['total_trades'] == 0)
    print(f'  {v:50s}: {c:4d} total  |  {zt:3d} zero-trade')

# ============================================================
# RESULTS WITH TRADES (sorted by PF)
# ============================================================
print(f'\n{"="*100}')
print(f'RESULTS WITH TRADES ({len(has_trades)} backtests) -- sorted by Profit Factor')
print('='*100)

if has_trades:
    has_trades_sorted = sorted(has_trades, key=lambda x: -x['profit_factor'])
    hdr = f'{"No":>3} {"ID":>22} {"Spec (last 20 chars)":>20} {"Var":>12} {"Ast":>4} {"TF":>4} {"Trd":>5} {"PF":>7} {"WR%":>6} {"DD%":>7} {"Ret%":>8} {"PPR":>5} {"TrPF":>7} {"RgPF":>7} {"TrsPF":>7}'
    print(hdr)
    print('-'*140)
    for i, r in enumerate(has_trades_sorted, 1):
        spec_short = r['spec_id'][-20:] if len(r['spec_id']) > 20 else r['spec_id']
        var_short = r['variant'][:12]
        print(f'{i:3d} {r["id"]:>22} {spec_short:>20} {var_short:>12} {r["asset"]:>4} {r["timeframe"]:>4} {r["total_trades"]:>5} {r["profit_factor"]:>7.3f} {r["win_rate"]*100:>5.1f}% {r["max_drawdown_pct"]:>6.2f}% {r["total_return_pct"]:>7.2f}% {r["ppr_score"]:>5.2f} {r["regime_pf_trending"]:>7.3f} {r["regime_pf_ranging"]:>7.3f} {r["regime_pf_transitional"]:>7.3f}')
else:
    print('  ** NO RESULTS WITH TRADES **')

# ============================================================
# FLAG 1: Zero-trade summary
# ============================================================
print(f'\n{"="*100}')
print(f'FLAG 1: ZERO-TRADE RESULTS ({len(zero_trade)} of {total})')
print('='*100)

# Group by spec
zt_by_spec = defaultdict(list)
for r in zero_trade:
    zt_by_spec[r['spec_id']].append(r)

print(f'\nUnique specs with zero trades: {len(zt_by_spec)}')
print(f'\n{"Spec ID (last 35)":>35} {"Cnt":>4} {"Assets":>15} {"TFs":>12} {"Sigs":>6}')
print('-'*80)
for spec, runs in sorted(zt_by_spec.items(), key=lambda x: -len(x[1])):
    assets = ', '.join(sorted(set(r['asset'] for r in runs)))
    tfs = ', '.join(sorted(set(r['timeframe'] for r in runs)))
    signals = set(r['entry_signals_total'] for r in runs)
    sig_str = ', '.join(str(s) for s in sorted(signals))
    spec_short = spec[-35:] if len(spec) > 35 else spec
    print(f'{spec_short:>35} {len(runs):>4} {assets:>15} {tfs:>12} {sig_str:>6}')

# ============================================================
# FLAG 2: PF > 2.0 with trades < 30
# ============================================================
print(f'\n{"="*100}')
print('FLAG 2: HIGH PF (>2.0) WITH LOW TRADES (<30)')
print('='*100)
flag2 = [r for r in has_trades if r['profit_factor'] > 2.0 and r['total_trades'] < 30]
if flag2:
    for r in flag2:
        print(f'  {r["id"]} | {r["spec_id"][-35:]} | {r["asset"]} {r["timeframe"]} | PF={r["profit_factor"]:.3f} | Trades={r["total_trades"]} | DD={r["max_drawdown_pct"]:.2f}%')
else:
    print('  None found.')

# ============================================================
# FLAG 3: Max drawdown == 0 with trades > 0 (bug indicator)
# ============================================================
print(f'\n{"="*100}')
print('FLAG 3: MAX DRAWDOWN == 0 WITH TRADES > 0 (BUG INDICATOR)')
print('='*100)
flag3 = [r for r in has_trades if r['max_drawdown_pct'] == 0.0]
if flag3:
    for r in flag3:
        print(f'  {r["id"]} | {r["spec_id"][-35:]} | {r["asset"]} {r["timeframe"]} | PF={r["profit_factor"]:.3f} | Trades={r["total_trades"]} | DD=0.00%')
else:
    print('  None found.')

# ============================================================
# FLAG 4: NaN or negative trade counts
# ============================================================
print(f'\n{"="*100}')
print('FLAG 4: NaN OR NEGATIVE TRADE COUNTS')
print('='*100)
flag4 = [r for r in results if r['total_trades'] is None or (isinstance(r['total_trades'], (int, float)) and r['total_trades'] < 0)]
if flag4:
    for r in flag4:
        print(f'  {r["id"]} | {r["spec_id"][-35:]} | trades={r["total_trades"]}')
else:
    print('  None found.')

# Also check for NaN in PF
flag4b = [r for r in results if isinstance(r['profit_factor'], float) and (math.isnan(r['profit_factor']) or math.isinf(r['profit_factor']))]
if flag4b:
    print(f'\n  NaN/Inf profit factors:')
    for r in flag4b:
        print(f'  {r["id"]} | {r["spec_id"][-35:]} | PF={r["profit_factor"]}')
else:
    print('  No NaN/Inf profit factors found.')

# ============================================================
# FLAG 5: Identical results across different specs
# ============================================================
print(f'\n{"="*100}')
print('FLAG 5: IDENTICAL RESULTS ACROSS DIFFERENT SPECS')
print('='*100)

# Create a fingerprint for each result (using key performance metrics)
fingerprints = defaultdict(list)
for r in results:
    fp = (
        r['total_trades'],
        round(r['profit_factor'], 6),
        round(r['max_drawdown_pct'], 6),
        round(r['win_rate'], 6),
        round(r['total_return_pct'], 6),
        r['asset'],
        r['timeframe'],
    )
    fingerprints[fp].append(r)

# Find groups with different specs but same results
dup_groups_nontrivial = []
dup_groups_zero = []
for fp, group in fingerprints.items():
    spec_ids = set(r['spec_id'] for r in group)
    if len(spec_ids) > 1:
        if fp[0] == 0:
            dup_groups_zero.append((fp, group))
        else:
            dup_groups_nontrivial.append((fp, group))

if dup_groups_nontrivial:
    print(f'\n  Found {len(dup_groups_nontrivial)} groups of IDENTICAL non-zero-trade results from DIFFERENT specs:')
    for fp, group in dup_groups_nontrivial:
        specs = set(r['spec_id'] for r in group)
        print(f'\n  Fingerprint: trades={fp[0]}, PF={fp[1]}, DD={fp[2]}%, WR={fp[3]}, Ret={fp[4]}%, {fp[5]} {fp[6]}')
        for r in group:
            print(f'    - {r["spec_id"][-40:]} (variant: {r["variant"]})')
else:
    print('\n  No identical non-zero-trade results from different specs.')

# Zero-trade duplicates
zt_by_asset_tf = defaultdict(list)
for r in zero_trade:
    key = (r['asset'], r['timeframe'])
    zt_by_asset_tf[key].append(r)

print(f'\n  Zero-trade identical groups by asset/timeframe:')
for (asset, tf), group in sorted(zt_by_asset_tf.items()):
    specs = set(r['spec_id'] for r in group)
    print(f'    {asset} {tf}: {len(group)} backtests, {len(specs)} unique specs -- ALL identical zero-trade results')

# ============================================================
# SUMMARY STATISTICS FOR TRADES > 0
# ============================================================
if has_trades:
    print(f'\n{"="*100}')
    print('PERFORMANCE STATISTICS (trades > 0 only)')
    print('='*100)
    pfs = [r['profit_factor'] for r in has_trades]
    dds = [r['max_drawdown_pct'] for r in has_trades]
    tcs = [r['total_trades'] for r in has_trades]
    wrs = [r['win_rate']*100 for r in has_trades]
    rets = [r['total_return_pct'] for r in has_trades]

    print(f'  Profit Factor:   min={min(pfs):.3f}  max={max(pfs):.3f}  avg={sum(pfs)/len(pfs):.3f}  median={sorted(pfs)[len(pfs)//2]:.3f}')
    print(f'  Max Drawdown%:   min={min(dds):.2f}  max={max(dds):.2f}  avg={sum(dds)/len(dds):.2f}')
    print(f'  Trade Count:     min={min(tcs)}  max={max(tcs)}  avg={sum(tcs)/len(tcs):.1f}')
    print(f'  Win Rate%:       min={min(wrs):.1f}  max={max(wrs):.1f}  avg={sum(wrs)/len(wrs):.1f}')
    print(f'  Total Return%:   min={min(rets):.2f}  max={max(rets):.2f}  avg={sum(rets)/len(rets):.2f}')

    # ACCEPT candidates (PF > 1.2, DD < 20%, trades >= 30)
    accept_candidates = [r for r in has_trades if r['profit_factor'] > 1.2 and r['max_drawdown_pct'] < 20.0 and r['total_trades'] >= 30]
    print(f'\n  ACCEPT candidates (PF>1.2, DD<20%, trades>=30): {len(accept_candidates)}')
    if accept_candidates:
        accept_candidates.sort(key=lambda x: -x['profit_factor'])
        for r in accept_candidates:
            print(f'    {r["id"]} | {r["spec_id"][-40:]} | {r["asset"]} {r["timeframe"]}')
            print(f'      PF={r["profit_factor"]:.3f} | Trades={r["total_trades"]} | DD={r["max_drawdown_pct"]:.2f}% | Ret={r["total_return_pct"]:.2f}%')
            print(f'      Regime PF: trend={r["regime_pf_trending"]:.3f} range={r["regime_pf_ranging"]:.3f} trans={r["regime_pf_transitional"]:.3f}')
            print(f'      PPR={r["ppr_score"]:.2f} ({r["ppr_decision"]})')

print(f'\n{"="*100}')
print('END OF SUMMARY')
print('='*100)
