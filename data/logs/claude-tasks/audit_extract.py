import json, os, glob

dates = ['20260228', '20260301']
results = []
for d in dates:
    pattern = f'artifacts/backtests/{d}/*.backtest_result.json'
    files = glob.glob(pattern)
    for f in files:
        with open(f, 'r') as fh:
            data = json.load(fh)
        r = data.get('results', {})
        inp = data.get('inputs', {})
        gate = data.get('gate', {})
        cov = data.get('coverage', {})
        regime_pf = r.get('regime_pf', {})
        regime_trades = r.get('regime_breakdown', {})
        results.append({
            'id': data.get('id', ''),
            'date': d,
            'spec': os.path.basename(inp.get('strategy_spec', '')),
            'variant': inp.get('variant', 'unknown'),
            'pf': r.get('profit_factor', 0),
            'trades': r.get('total_trades', 0),
            'win_rate': r.get('win_rate', 0),
            'max_dd': r.get('max_drawdown', 0),
            'max_dd_pct': r.get('max_drawdown_pct', 0),
            'net_profit': r.get('net_profit', 0),
            'gate_pass': gate.get('gate_pass', None),
            'min_trades_req': gate.get('min_trades_required', 0),
            'trending_pf': regime_pf.get('trending', None),
            'ranging_pf': regime_pf.get('ranging', None),
            'transitional_pf': regime_pf.get('transitional', None),
            'trending_trades': regime_trades.get('trending_trades', 0),
            'ranging_trades': regime_trades.get('ranging_trades', 0),
            'transitional_trades': regime_trades.get('transitional_trades', 0),
        })
with open('data/logs/claude-tasks/audit_data.json', 'w') as out:
    json.dump(results, out)
print(f'Total: {len(results)}')
