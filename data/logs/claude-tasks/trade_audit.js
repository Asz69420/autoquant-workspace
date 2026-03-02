const fs = require('fs');
const path = require('path');
const base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260228';

// Analyze specific trade list files
const targets = [
  'hl_20260228_5be501f9',  // PF=1.033, 389 trades, ETH 4h
  'hl_20260228_24b7e3c6',  // PF=1.001, 406 trades, BTC 4h
  'hl_20260228_3615cc19',  // PF=0.998, 415 trades, ETH 1h
  'hl_20260228_a0699436',  // PF=0.818, 843 trades, BTC 4h exploration
  'hl_20260228_691da115',  // PF=0.624, 153 trades, BTC 4h refine
  'hl_20260228_761792a1',  // PF=0.966, 139 trades, ETH 4h refine
  'hl_20260228_64783559',  // PF=0.587, 160 trades, BTC 4h exploit_1
  'hl_20260228_042263dd',  // PF=0.804, 143 trades, ETH 4h exploit_1
  'hl_20260228_6f13f79f',  // PF=0.965, 137 trades, ETH 4h exploit_2
  'hl_20260228_ae567daa',  // PF=0.907, 140 trades, BTC 4h exploit_3
  'hl_20260228_0334c909',  // PF=0, 0 trades, template_diversity
  'hl_20260228_a01d914e',  // PF=0, 0 trades, template_diversity
  'hl_20260228_78edcf00',  // PF=0.754, 891 trades, ETH 1h exploration
  'hl_20260228_a5466507',  // PF=0.884, 766 trades, ETH 4h exploration
  'hl_20260228_d4b88fec',  // PF=1.033, 389 trades, ETH 4h library_augmented (duplicate?)
];

for (const t of targets) {
  const f = path.join(base, t + '.trade_list.json');
  if (!fs.existsSync(f)) {
    console.log('\n=== ' + t + ' === FILE MISSING');
    continue;
  }

  try {
    const data = JSON.parse(fs.readFileSync(f, 'utf8'));
    const trades = data.trades || data;

    if (!Array.isArray(trades) || trades.length === 0) {
      console.log('\n=== ' + t + ' === EMPTY (0 trades)');
      continue;
    }

    // Get PnL field name
    const sample = trades[0];
    const pnlKey = 'pnl' in sample ? 'pnl' : ('profit' in sample ? 'profit' : 'net_pnl');
    const tsKey = 'entry_time' in sample ? 'entry_time' : ('entry_ts' in sample ? 'entry_ts' : 'open_time');

    const pnls = trades.map(t => t[pnlKey] || 0);
    const totalPnl = pnls.reduce((a, b) => a + b, 0);
    const winners = pnls.filter(p => p > 0);
    const losers = pnls.filter(p => p < 0);
    const grossProfit = winners.reduce((a, b) => a + b, 0);
    const grossLoss = Math.abs(losers.reduce((a, b) => a + b, 0));

    // Top 2 concentration
    const sortedPnls = [...pnls].sort((a, b) => b - a);
    const top2 = sortedPnls.slice(0, 2).reduce((a, b) => a + b, 0);
    const top2PctNet = totalPnl > 0 ? (top2 / totalPnl * 100).toFixed(1) : 'N/A (net<=0)';
    const top2PctGross = grossProfit > 0 ? (top2 / grossProfit * 100).toFixed(1) : 'N/A';

    // Top 5 concentration
    const top5 = sortedPnls.slice(0, 5).reduce((a, b) => a + b, 0);
    const top5PctGross = grossProfit > 0 ? (top5 / grossProfit * 100).toFixed(1) : 'N/A';

    // Time analysis
    const timestamps = trades.map(t => t[tsKey]).filter(Boolean);
    let timeInfo = '';
    const monthlyDist = {};
    const monthlyPnl = {};

    if (timestamps.length > 0) {
      const dates = timestamps.map(ts => new Date(ts));
      const minDate = new Date(Math.min(...dates));
      const maxDate = new Date(Math.max(...dates));
      const spanDays = Math.round((maxDate - minDate) / (1000 * 60 * 60 * 24));

      // Monthly distribution
      for (let i = 0; i < dates.length; i++) {
        const d = dates[i];
        const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
        monthlyDist[key] = (monthlyDist[key] || 0) + 1;
        monthlyPnl[key] = (monthlyPnl[key] || 0) + pnls[i];
      }

      timeInfo = spanDays + ' days (' + minDate.toISOString().slice(0, 10) + ' to ' + maxDate.toISOString().slice(0, 10) + ')';

      // Find max concentration in any 25% window
      const sortedDates = [...dates].sort((a, b) => a - b);
      const quarterSpan = spanDays * 0.25 * 24 * 60 * 60 * 1000;
      let maxInQuarter = 0;
      for (let i = 0; i < sortedDates.length; i++) {
        const windowEnd = sortedDates[i].getTime() + quarterSpan;
        let count = 0;
        for (let j = i; j < sortedDates.length; j++) {
          if (sortedDates[j].getTime() <= windowEnd) count++;
          else break;
        }
        if (count > maxInQuarter) maxInQuarter = count;
      }
      const clusterPct = (maxInQuarter / sortedDates.length * 100).toFixed(1);

      timeInfo += ' | max25%window=' + clusterPct + '%';
    }

    console.log('\n=== ' + t + ' ===');
    console.log('  Trades: ' + trades.length + ' (W:' + winners.length + ' L:' + losers.length + ')');
    console.log('  TotalPnL: ' + totalPnl.toFixed(2) + '  GrossP: ' + grossProfit.toFixed(2) + '  GrossL: -' + grossLoss.toFixed(2));
    console.log('  Top2 PnL: ' + top2.toFixed(2) + '  as%Net: ' + top2PctNet + '  as%Gross: ' + top2PctGross + '%');
    console.log('  Top5 as%Gross: ' + top5PctGross + '%');
    console.log('  TopTrade: ' + sortedPnls[0].toFixed(2) + '  WorstTrade: ' + sortedPnls[sortedPnls.length - 1].toFixed(2));
    console.log('  TimeSpan: ' + timeInfo);

    // Monthly breakdown
    const months = Object.keys(monthlyDist).sort();
    console.log('  Monthly trades: ' + months.map(m => m + ':' + monthlyDist[m]).join('  '));
    console.log('  Monthly PnL:    ' + months.map(m => m + ':' + (monthlyPnl[m] || 0).toFixed(0)).join('  '));

    // Flag issues
    if (totalPnl > 0 && top2 / totalPnl > 0.5) {
      console.log('  ** FLAG: Top 2 trades carry ' + top2PctNet + '% of net profit');
    }
    if (grossProfit > 0 && top2 / grossProfit > 0.15) {
      console.log('  ** FLAG: Top 2 trades are ' + top2PctGross + '% of gross profit');
    }

    // Check if best month PnL > 50% of gross
    if (grossProfit > 0) {
      const bestMonthPnl = Math.max(...Object.values(monthlyPnl));
      const bestMonth = Object.entries(monthlyPnl).find(([k, v]) => v === bestMonthPnl);
      if (bestMonthPnl > 0 && bestMonthPnl / grossProfit > 0.15) {
        console.log('  ** FLAG: Best month ' + (bestMonth ? bestMonth[0] : '?') + ' has ' + (bestMonthPnl / grossProfit * 100).toFixed(1) + '% of gross profit');
      }
    }

  } catch(e) {
    console.log('\n=== ' + t + ' === ERROR: ' + e.message);
  }
}

// Also check for duplicate trade lists
console.log('\n\n=== DUPLICATE CHECK ===');
const checksums = {};
for (const t of ['hl_20260228_5be501f9', 'hl_20260228_d4b88fec', 'hl_20260228_ffd6628e']) {
  const f = path.join(base, t + '.trade_list.json');
  if (fs.existsSync(f)) {
    const size = fs.statSync(f).size;
    const data = JSON.parse(fs.readFileSync(f, 'utf8'));
    const trades = data.trades || data;
    const firstPnl = trades.length > 0 ? trades[0].pnl || trades[0].profit || 0 : 0;
    const lastPnl = trades.length > 0 ? trades[trades.length - 1].pnl || trades[trades.length - 1].profit || 0 : 0;
    console.log(t + ': size=' + size + ' trades=' + trades.length + ' firstPnl=' + firstPnl + ' lastPnl=' + lastPnl);
  }
}
