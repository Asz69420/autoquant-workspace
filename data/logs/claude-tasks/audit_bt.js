const fs = require('fs');
const path = require('path');
const base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228';

// Read all backtest results
const files = fs.readdirSync(base).filter(f => f.endsWith('.backtest_result.json'));
const results = [];
for (const f of files) {
  try {
    const d = JSON.parse(fs.readFileSync(path.join(base, f), 'utf8'));
    const r = d.results || d;
    results.push({
      hash: f.replace('.backtest_result.json', ''),
      pf: r.profit_factor || 0,
      trades: r.total_trades || 0,
      net: r.net_profit || 0,
      wr: r.win_rate || 0,
      variant: d.inputs ? d.inputs.variant : 'unknown'
    });
  } catch(e) {}
}

results.sort((a, b) => b.pf - a.pf);
console.log('TOP 30 BY PF:');
results.slice(0, 30).forEach(r => console.log('  ' + r.hash + '  PF=' + r.pf.toFixed(5) + '  T=' + r.trades + '  WR=' + r.wr.toFixed(3) + '  Net=' + r.net.toFixed(2) + '  V=' + r.variant));

console.log('\nTotal files: ' + results.length);
const zeros = results.filter(r => r.trades === 0);
console.log('Zero-trade: ' + zeros.length);
zeros.forEach(r => console.log('  ZERO: ' + r.hash + '  V=' + r.variant));

const low = results.filter(r => r.trades > 0 && r.trades <= 5);
console.log('\nVery low (1-5): ' + low.length);
low.forEach(r => console.log('  LOW: ' + r.hash + '  PF=' + r.pf.toFixed(5) + '  T=' + r.trades));

// Unique PF values to check for duplicates
const pfCounts = {};
results.forEach(r => {
  const k = r.pf.toFixed(8);
  pfCounts[k] = (pfCounts[k] || 0) + 1;
});
console.log('\nPF VALUE DISTRIBUTION (showing duplicates):');
Object.entries(pfCounts).sort((a,b) => b[1] - a[1]).slice(0, 15).forEach(([pf, c]) => console.log('  PF=' + pf + ' appears ' + c + ' times'));

// Unique trade counts
const tradeCounts = {};
results.forEach(r => {
  tradeCounts[r.trades] = (tradeCounts[r.trades] || 0) + 1;
});
console.log('\nTRADE COUNT DISTRIBUTION:');
Object.entries(tradeCounts).sort((a,b) => parseInt(b[0]) - parseInt(a[0])).forEach(([t, c]) => console.log('  Trades=' + t + ' appears ' + c + ' times'));
