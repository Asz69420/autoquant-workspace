import json, os, glob, sys
from collections import defaultdict

dir_path = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260301'
files = glob.glob(os.path.join(dir_path, '*.backtest_result.json'))
files.sort()
print(f'Total files: {len(files)}')

rows = []
for f in files:
    try:
        with open(f, 'r') as fh:
            d = json.load(fh)
    except Exception as e:
        rows.append({'file': os.path.basename(f), 'error': str(e)})
        continue

    bid = d.get('id', os.path.basename(f).replace('.backtest_result.json',''))
    variant = d.get('inputs', {}).get('variant', 'UNKNOWN')
    r = d.get('results', {})
    pf = r.get('profit_factor', None)
    dd = r.get('max_drawdown', None)
    dd_pct = r.get('max_drawdown_pct', None)
    trades = r.get('total_trades', None)
    wr = r.get('win_rate', None)
    net_pnl = r.get('net_profit', r.get('net_pnl', r.get('total_pnl', None)))
    regime = r.get('regime_breakdown', None)
    regime_pf = r.get('regime_pf', None)

    flags = []
    # Overfit: PF > 2.0 with < 30 trades
    pf_threshold = 2.0
    extreme_pf_threshold = 5.0
    low_trade_threshold = 30
    if pf is not None and trades is not None:
        if pf > pf_threshold and trades < low_trade_threshold:
            flags.append('OVERFIT_SUSPECT')
    if trades is not None and trades == 0:
        flags.append('ZERO_TRADES')
    if dd is not None and dd == 0:
        flags.append('DD_ZERO_BUG')
    if trades is not None and trades < 0:
        flags.append('NEG_TRADES')
    if trades is None:
        flags.append('MISSING_TRADES')
    if pf is None:
        flags.append('MISSING_PF')
    elif isinstance(pf, float) and (pf != pf):
        flags.append('NAN_PF')
    if pf is not None and trades is not None:
        if pf > extreme_pf_threshold and trades >= low_trade_threshold:
            flags.append('EXTREME_PF')

    rows.append({
        'hash': bid, 'variant': variant, 'pf': pf, 'trades': trades,
        'dd': dd, 'dd_pct': dd_pct, 'wr': wr, 'net_pnl': net_pnl,
        'regime': regime, 'regime_pf': regime_pf, 'flags': flags
    })

# Duplicate detection: identical (pf, trades, dd, net_pnl)
sig_map = defaultdict(list)
for r in rows:
    if 'error' not in r:
        sig = (r['pf'], r['trades'], r['dd'], r['net_pnl'])
        sig_map[sig].append(r['hash'])

dup_hashes = set()
dup_groups = []
for sig, hashes in sig_map.items():
    if len(hashes) > 1:
        dup_groups.append(hashes)
        for h in hashes:
            dup_hashes.add(h)

for r in rows:
    if 'error' not in r and r['hash'] in dup_hashes:
        r['flags'].append('DUPLICATE')

# Summary stats
print(f'Parsed: {len(rows)} rows')
errs = sum(1 for r in rows if 'error' in r)
print(f'Parse errors: {errs}')
flagged = sum(1 for r in rows if 'error' not in r and len(r['flags']) > 0)
print(f'Flagged total: {flagged}')
print(f'Duplicate hashes: {len(dup_hashes)}')
print(f'Duplicate groups: {len(dup_groups)}')
zt = sum(1 for r in rows if 'error' not in r and r.get('trades') == 0)
print(f'Zero trades: {zt}')
ov = sum(1 for r in rows if 'error' not in r and 'OVERFIT_SUSPECT' in r.get('flags',[]))
print(f'Overfit suspect (PF>2, trades<30): {ov}')
dz = sum(1 for r in rows if 'error' not in r and 'DD_ZERO_BUG' in r.get('flags',[]))
print(f'DD zero bug: {dz}')
ep = sum(1 for r in rows if 'error' not in r and 'EXTREME_PF' in r.get('flags',[]))
print(f'Extreme PF (>5, trades>=30): {ep}')

# Distribution stats
valid = [r for r in rows if 'error' not in r and r['pf'] is not None]
if valid:
    pfs = [r['pf'] for r in valid]
    trds = [r['trades'] for r in valid if r['trades'] is not None]
    pnls = [r['net_pnl'] for r in valid if r['net_pnl'] is not None]
    print(f'\n=== DISTRIBUTION ===')
    print(f'PF: min={min(pfs):.4f} max={max(pfs):.4f} mean={sum(pfs)/len(pfs):.4f} median={sorted(pfs)[len(pfs)//2]:.4f}')
    print(f'Trades: min={min(trds)} max={max(trds)} mean={sum(trds)/len(trds):.1f}')
    print(f'PnL: min={min(pnls):.2f} max={max(pnls):.2f} mean={sum(pnls)/len(pnls):.2f}')

# Print full table
print('\n=== FULL TABLE ===')
print('HASH|VARIANT|PF|TRADES|DD|DD_PCT|WR|NET_PNL|FLAGS')
for r in rows:
    if 'error' in r:
        print(f'{r["file"]}|ERROR|{r["error"]}|||||')
        continue
    flag_str = ','.join(r['flags']) if r['flags'] else 'CLEAN'
    pf_s = f"{r['pf']:.4f}" if r['pf'] is not None else 'N/A'
    dd_s = f"{r['dd']:.2f}" if r['dd'] is not None else 'N/A'
    ddp_s = f"{r['dd_pct']:.2f}" if r['dd_pct'] is not None else 'N/A'
    wr_s = f"{r['wr']:.4f}" if r['wr'] is not None else 'N/A'
    pnl_s = f"{r['net_pnl']:.2f}" if r['net_pnl'] is not None else 'N/A'
    print(f"{r['hash']}|{r['variant']}|{pf_s}|{r['trades']}|{dd_s}|{ddp_s}|{wr_s}|{pnl_s}|{flag_str}")

# Print flagged items separately
flagged_rows = [r for r in rows if 'error' not in r and len(r['flags']) > 0]
if flagged_rows:
    print(f'\n=== FLAGGED ITEMS ({len(flagged_rows)}) ===')
    print('HASH|VARIANT|PF|TRADES|DD|WR|NET_PNL|FLAGS')
    for r in flagged_rows:
        flag_str = ','.join(r['flags'])
        pf_s = f"{r['pf']:.4f}" if r['pf'] is not None else 'N/A'
        dd_s = f"{r['dd']:.2f}" if r['dd'] is not None else 'N/A'
        wr_s = f"{r['wr']:.4f}" if r['wr'] is not None else 'N/A'
        pnl_s = f"{r['net_pnl']:.2f}" if r['net_pnl'] is not None else 'N/A'
        print(f"{r['hash']}|{r['variant']}|{pf_s}|{r['trades']}|{dd_s}|{wr_s}|{pnl_s}|{flag_str}")

# Print duplicate groups
if dup_groups:
    print(f'\n=== DUPLICATE GROUPS ({len(dup_groups)}) ===')
    for i, group in enumerate(dup_groups):
        print(f'Group {i+1}: {", ".join(group)}')

# Regime analysis summary
print('\n=== REGIME COVERAGE ===')
has_regime = sum(1 for r in rows if 'error' not in r and r.get('regime') is not None)
no_regime = sum(1 for r in rows if 'error' not in r and r.get('regime') is None)
print(f'Has regime breakdown: {has_regime}')
print(f'Missing regime breakdown: {no_regime}')

# Top 10 by PF (clean only)
clean = [r for r in rows if 'error' not in r and len(r['flags']) == 0 and r['pf'] is not None]
clean.sort(key=lambda x: x['pf'], reverse=True)
print('\n=== TOP 10 CLEAN BY PF ===')
print('HASH|VARIANT|PF|TRADES|DD_PCT|WR|NET_PNL')
for r in clean[:10]:
    print(f"{r['hash']}|{r['variant']}|{r['pf']:.4f}|{r['trades']}|{r['dd_pct']:.2f}|{r['wr']:.4f}|{r['net_pnl']:.2f}")

# Bottom 10 by PF (clean only)
print('\n=== BOTTOM 10 CLEAN BY PF ===')
print('HASH|VARIANT|PF|TRADES|DD_PCT|WR|NET_PNL')
for r in clean[-10:]:
    print(f"{r['hash']}|{r['variant']}|{r['pf']:.4f}|{r['trades']}|{r['dd_pct']:.2f}|{r['wr']:.4f}|{r['net_pnl']:.2f}")
