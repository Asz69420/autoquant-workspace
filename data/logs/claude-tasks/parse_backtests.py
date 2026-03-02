import json, os, glob

files = sorted(glob.glob('C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260301/*.backtest_result.json'))
print(f'Total files: {len(files)}')

rows = []
for f in files:
    with open(f, 'r') as fh:
        d = json.load(fh)

    r = d.get('results', {})
    g = d.get('gate', {})
    inp = d.get('inputs', {})
    regime_pf = r.get('regime_pf', {})

    spec_file = inp.get('strategy_spec', '')
    spec_name = os.path.basename(spec_file) if spec_file else ''

    row = {
        'id': d.get('id', ''),
        'variant': inp.get('variant', ''),
        'spec_file': spec_name,
        'pf': r.get('profit_factor', 0),
        'trades': r.get('total_trades', 0),
        'win_rate': r.get('win_rate', 0),
        'max_dd_pct': r.get('max_drawdown_pct', 0),
        'net_profit': r.get('net_profit', 0),
        'regime_pf_trending': regime_pf.get('trending', None),
        'regime_pf_ranging': regime_pf.get('ranging', None),
        'regime_pf_transitional': regime_pf.get('transitional', None),
        'gate_pass': g.get('gate_pass', None),
        'min_trades_req': g.get('min_trades_required', None),
    }
    rows.append(row)

# Sort by PF descending
rows.sort(key=lambda x: x['pf'] if x['pf'] is not None else 0, reverse=True)

# Print as JSON for reliable parsing
for i, row in enumerate(rows):
    print(json.dumps(row))
