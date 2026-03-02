const fs = require('fs');
const path = require('path');

const dir = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.backtest_result.json')).sort();
process.stderr.write('Total files: ' + files.length + '\n');

const rows = [];
for (const f of files) {
    try {
        const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
        const r = d.results || {};
        const inp = d.inputs || {};
        rows.push({
            hash: d.id || '',
            variant: inp.variant || '',
            pf: r.profit_factor,
            trades: r.total_trades,
            dd: r.max_drawdown,
            win_rate: r.win_rate,
            net_pnl: r.net_profit,
            regime_breakdown: r.regime_breakdown || null,
            regime_pf: r.regime_pf || null,
        });
    } catch (e) {
        process.stderr.write('ERROR reading ' + f + ': ' + e.message + '\n');
    }
}

console.log(JSON.stringify(rows, null, 0));
