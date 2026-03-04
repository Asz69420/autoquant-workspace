import json, glob, os
files = sorted(glob.glob('artifacts/backtests/20260305/*.backtest_result.json'))
print('Total files:', len(files))
for f in files:
    with open(f) as fh:
        d = json.load(fh)
    meta = d['inputs']['dataset_meta'].replace('\\', '/')
    parts = meta.split('/')
    asset = 'UNK'
    tf = 'UNK'
    for i, p in enumerate(parts):
        if p == 'hyperliquid' and i+2 < len(parts):
            asset = parts[i+1]
            tf = parts[i+2]
            break
    spec = os.path.basename(d['inputs']['strategy_spec'])
    variant = d['inputs'].get('variant', 'base')
    r = d['results']
    cov = d['coverage']
    gate = d['gate']
    sig_l = cov['entry_signals_seen']['long']
    sig_s = cov['entry_signals_seen']['short']
    rt = r['regime_breakdown']
    gp = 'PASS' if gate['gate_pass'] else 'FAIL'
    print(f"{d['id']}|{spec}|{variant}|{asset}|{tf}|{r['total_trades']}|{r['profit_factor']}|{r['win_rate']}|{r['max_drawdown_pct']}|{r['net_profit']}|{r['total_return_pct']}|{sig_l}|{sig_s}|{rt['trending_trades']}|{rt['ranging_trades']}|{rt['transitional_trades']}|{gp}|{gate['gate_reason']}")
