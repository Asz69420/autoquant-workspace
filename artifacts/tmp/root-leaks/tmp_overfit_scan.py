import json, glob, os, sys

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

results = []

for folder in ['artifacts/backtests/20260306', 'artifacts/backtests/20260305']:
    full_folder = os.path.join(WORKSPACE, folder)
    for f in glob.glob(os.path.join(full_folder, '*.backtest_result.json')):
        try:
            with open(f) as fp:
                d = json.load(fp)
            r = d.get('results', {})
            pf = r.get('profit_factor', 0)
            trades = r.get('total_trades', 0)
            if trades > 0:
                hid = os.path.basename(f).replace('.backtest_result.json', '')
                results.append({
                    'id': hid,
                    'pf': pf,
                    'trades': trades,
                    'dd': r.get('max_drawdown_pct', 0),
                    'net_pnl_pct': r.get('net_profit_pct', 0),
                    'file': f,
                    'spec': d.get('inputs', {}).get('strategy_spec', ''),
                    'variant': d.get('inputs', {}).get('variant', ''),
                    'dataset': d.get('inputs', {}).get('dataset_meta', ''),
                    'regime_pf': r.get('regime_pf', {}),
                    'regime_breakdown': r.get('regime_breakdown', {}),
                })
        except Exception as e:
            pass

results.sort(key=lambda x: x['pf'], reverse=True)

print('Total backtests with >0 trades:', len(results))
print('Backtests with PF > 1.5:', len([r for r in results if r['pf'] > 1.5]))
print()
print('=== ALL NON-ZERO TRADE BACKTESTS (sorted by PF desc) ===')
for r in results:
    dm = r['dataset']
    asset_tf = ''
    for a in ['ETH','BTC','SOL']:
        if a in dm:
            asset_tf = a
            break
    for t in ['4h','1h','15m']:
        if t in dm:
            asset_tf += ' ' + t
            break
    spec_short = os.path.basename(r['spec']) if r['spec'] else 'unknown'
    regime = r['regime_breakdown']
    rpf = r['regime_pf']
    print('PF={:.3f} Trades={:3d} DD={:.1f}% {:8s} {} {}'.format(
        r['pf'], r['trades'], r['dd'], asset_tf, r['id'], spec_short[:60]))
    print('  RegimeTrades: trend={} rang={} trans={}'.format(
        regime.get('trending_trades',0), regime.get('ranging_trades',0), regime.get('transitional_trades',0)))
    print('  RegimePF: trend={:.2f} rang={:.2f} trans={:.2f}'.format(
        rpf.get('trending',0), rpf.get('ranging',0), rpf.get('transitional',0)))
    print('  Variant:', r['variant'])
    print()
