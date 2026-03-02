const fs = require('fs');
const path = require('path');

const dir = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.backtest_result.json')).sort();

const rows = [];
for (const f of files) {
    try {
        const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
        const r = d.results || {};
        const inp = d.inputs || {};
        const rb = r.regime_breakdown || {};
        const rpf = r.regime_pf || {};
        rows.push([
            d.id || '',
            inp.variant || '',
            r.profit_factor || 0,
            r.total_trades || 0,
            r.max_drawdown || 0,
            r.win_rate || 0,
            r.net_profit || 0,
            rb.trending_trades || 0,
            rb.ranging_trades || 0,
            rb.transitional_trades || 0,
            rpf.trending || 0,
            rpf.ranging || 0,
            rpf.transitional || 0,
            r.dominant_regime || ''
        ].join('|'));
    } catch (e) {
        process.stderr.write('ERR:' + f + ':' + e.message + '\n');
    }
}

// header
console.log('hash|variant|pf|trades|dd|win_rate|net_pnl|trend_trades|range_trades|trans_trades|trend_pf|range_pf|trans_pf|dom_regime');
rows.forEach(r => console.log(r));
