import { readFileSync } from 'fs';

function parseDate(s) {
  return new Date(s.replace(' ', 'T') + 'Z');
}

function analyze(filepath, label) {
  const data = JSON.parse(readFileSync(filepath, 'utf8'));
  const trades = data.trades;
  const n = trades.length;

  console.log(`\n${'='.repeat(80)}`);
  console.log(`  ${label}`);
  console.log(`  ID: ${data.id}  |  ${n} trades`);
  console.log(`${'='.repeat(80)}`);

  const winners = trades.filter(t => t.pnl > 0);
  const losers = trades.filter(t => t.pnl <= 0);
  const grossProfit = winners.reduce((s, t) => s + t.pnl, 0);
  const grossLoss = Math.abs(losers.reduce((s, t) => s + t.pnl, 0));
  const netPnl = trades.reduce((s, t) => s + t.pnl, 0);

  console.log(`\n  BASIC STATS:`);
  console.log(`    Winners: ${winners.length}/${n} (${(100*winners.length/n).toFixed(1)}%)`);
  console.log(`    Gross Profit: $${grossProfit.toFixed(2)}  |  Gross Loss: $${grossLoss.toFixed(2)}`);
  console.log(`    Net PnL: $${netPnl.toFixed(2)}`);
  if (grossLoss > 0) console.log(`    Profit Factor: ${(grossProfit/grossLoss).toFixed(3)}`);

  // 1. PROFIT CONCENTRATION
  const sortedWinners = [...winners].sort((a, b) => b.pnl - a.pnl);
  console.log(`\n  1. PROFIT CONCENTRATION:`);
  if (grossProfit > 0) {
    for (const k of [1, 3, 5]) {
      const topK = sortedWinners.slice(0, Math.min(k, sortedWinners.length));
      const topKSum = topK.reduce((s, t) => s + t.pnl, 0);
      console.log(`    Top ${k} trade(s): $${topKSum.toFixed(2)} = ${(100*topKSum/grossProfit).toFixed(1)}% of gross profit`);
    }
    console.log(`\n    Top 5 winning trades:`);
    sortedWinners.slice(0, 5).forEach((t, i) => {
      console.log(`      #${i+1}: $${t.pnl.toFixed(2)} (${t.pnl_pct.toFixed(1)}%) | ${t.entry_time} -> ${t.exit_time} | ${t.side} | ${t.entry_regime} | ${t.reason}`);
    });
  }

  const sortedAll = [...trades].sort((a, b) => b.pnl - a.pnl);
  const top3Pnl = sortedAll.slice(0, 3).reduce((s, t) => s + t.pnl, 0);
  if (netPnl > 0) {
    console.log(`\n    Top 3 trades as % of NET profit: ${(100*top3Pnl/netPnl).toFixed(1)}%`);
  } else if (netPnl < 0) {
    console.log(`\n    Net PnL is NEGATIVE. Top 3 best trades sum: $${top3Pnl.toFixed(2)}`);
  }

  // 2. TIME CLUSTERING
  console.log(`\n  2. TIME CLUSTERING / DISTRIBUTION:`);
  const entryDates = trades.map(t => parseDate(t.entry_time));
  const minDate = new Date(Math.min(...entryDates));
  const maxDate = new Date(Math.max(...entryDates));
  const spanDays = Math.round((maxDate - minDate) / (1000*60*60*24));
  console.log(`    Backtest span: ${minDate.toISOString().slice(0,10)} to ${maxDate.toISOString().slice(0,10)} (${spanDays} days)`);

  // Quarterly
  const quarterTrades = {};
  trades.forEach(t => {
    const d = parseDate(t.entry_time);
    const q = `${d.getUTCFullYear()}-Q${Math.floor(d.getUTCMonth()/3)+1}`;
    if (!quarterTrades[q]) quarterTrades[q] = [];
    quarterTrades[q].push(t);
  });
  console.log(`\n    Quarterly distribution:`);
  Object.keys(quarterTrades).sort().forEach(q => {
    const qt = quarterTrades[q];
    const qPnl = qt.reduce((s, t) => s + t.pnl, 0);
    const qWins = qt.filter(t => t.pnl > 0).length;
    console.log(`      ${q}: ${qt.length} trades, ${qWins} wins, PnL=$${qPnl.toFixed(2)}`);
  });

  // Month gaps
  const monthSet = new Set();
  entryDates.forEach(d => monthSet.add(`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}`));
  const allMonths = new Set();
  let cur = new Date(minDate);
  cur.setUTCDate(1);
  while (cur <= maxDate) {
    allMonths.add(`${cur.getUTCFullYear()}-${String(cur.getUTCMonth()+1).padStart(2,'0')}`);
    cur.setUTCMonth(cur.getUTCMonth() + 1);
  }
  const gaps = [...allMonths].filter(m => !monthSet.has(m)).sort();
  if (gaps.length) console.log(`\n    Months with ZERO trades: ${gaps.join(', ')}`);

  // 3. STREAK ANALYSIS
  console.log(`\n  3. STREAK ANALYSIS:`);
  let maxWinStreak = 0, maxLoseStreak = 0, curWin = 0, curLose = 0;
  trades.forEach(t => {
    if (t.pnl > 0) { curWin++; curLose = 0; }
    else { curLose++; curWin = 0; }
    maxWinStreak = Math.max(maxWinStreak, curWin);
    maxLoseStreak = Math.max(maxLoseStreak, curLose);
  });
  console.log(`    Max winning streak: ${maxWinStreak}`);
  console.log(`    Max losing streak: ${maxLoseStreak}`);

  const lossRuns = [];
  let runLen = 0, runPnl = 0;
  trades.forEach(t => {
    if (t.pnl <= 0) { runLen++; runPnl += t.pnl; }
    else { if (runLen > 0) lossRuns.push([runLen, runPnl]); runLen = 0; runPnl = 0; }
  });
  if (runLen > 0) lossRuns.push([runLen, runPnl]);
  lossRuns.sort((a, b) => a[1] - b[1]);
  console.log(`    Worst loss runs:`);
  lossRuns.slice(0, 3).forEach(([len, pnl]) => {
    console.log(`      ${len} consecutive losses, total PnL=$${pnl.toFixed(2)}`);
  });

  // 4. REGIME BREAKDOWN
  console.log(`\n  4. REGIME BREAKDOWN:`);
  const regimeTrades = {};
  trades.forEach(t => {
    if (!regimeTrades[t.entry_regime]) regimeTrades[t.entry_regime] = [];
    regimeTrades[t.entry_regime].push(t);
  });

  Object.keys(regimeTrades).sort().forEach(regime => {
    const rt = regimeTrades[regime];
    const rWins = rt.filter(t => t.pnl > 0);
    const rGp = rWins.reduce((s, t) => s + t.pnl, 0);
    const rGl = Math.abs(rt.filter(t => t.pnl <= 0).reduce((s, t) => s + t.pnl, 0));
    const rNet = rt.reduce((s, t) => s + t.pnl, 0);
    const rPf = rGl > 0 ? rGp / rGl : Infinity;
    console.log(`    ${regime}: ${rt.length} trades, ${rWins.length} wins, GP=$${rGp.toFixed(2)}, GL=$${rGl.toFixed(2)}, PF=${rPf.toFixed(3)}, Net=$${rNet.toFixed(2)}`);
    if (regime === 'transitional' && rPf > 5) {
      console.log(`      *** ANOMALY: Transitional PF=${rPf.toFixed(2)} flagged ***`);
      rWins.forEach(t => console.log(`          WIN: $${t.pnl.toFixed(2)} (${t.pnl_pct.toFixed(1)}%) ${t.entry_time} ${t.side} bars=${t.bars_held} reason=${t.reason}`));
      rt.filter(t => t.pnl <= 0).forEach(t => console.log(`          LOSS: $${t.pnl.toFixed(2)} (${t.pnl_pct.toFixed(1)}%) ${t.entry_time} ${t.side} bars=${t.bars_held} reason=${t.reason}`));
    }
  });

  // 5. FLAGS
  console.log(`\n  5. OVERFITTING FLAGS:`);
  const flags = [];

  if (grossProfit > 0) {
    const top3GpPct = 100 * sortedWinners.slice(0,Math.min(3,sortedWinners.length)).reduce((s,t)=>s+t.pnl,0) / grossProfit;
    if (top3GpPct > 50) flags.push(`HIGH CONCENTRATION: Top 3 trades = ${top3GpPct.toFixed(1)}% of gross profit`);
  }
  if (netPnl > 0 && top3Pnl/netPnl > 0.8) flags.push(`EXTREME NET DEPENDENCY: Top 3 trades = ${(100*top3Pnl/netPnl).toFixed(1)}% of net profit`);

  const winRate = winners.length / n;
  if (grossLoss > 0 && winRate < 0.3 && grossProfit/grossLoss > 1.5) flags.push(`TAIL DEPENDENCY: Win rate ${(100*winRate).toFixed(1)}% but PF=${(grossProfit/grossLoss).toFixed(2)}`);
  if (maxLoseStreak >= 8) flags.push(`LONG LOSING STREAK: ${maxLoseStreak} consecutive losses`);

  Object.entries(regimeTrades).forEach(([regime, rt]) => {
    const rWins = rt.filter(t => t.pnl > 0);
    const rGp = rWins.reduce((s,t) => s+t.pnl, 0);
    const rGl = Math.abs(rt.filter(t => t.pnl <= 0).reduce((s,t) => s+t.pnl, 0));
    if (rGl > 0) {
      const rpf = rGp / rGl;
      if (rpf > 10 && rt.length < 10) flags.push(`REGIME ANOMALY: ${regime} PF=${rpf.toFixed(2)} on only ${rt.length} trades`);
    }
  });

  const sortedDates = [...entryDates].sort((a,b) => a-b);
  for (let i = 1; i < sortedDates.length; i++) {
    const gap = Math.round((sortedDates[i] - sortedDates[i-1]) / (1000*60*60*24));
    if (gap > 60) flags.push(`TIME GAP: ${gap} days (${sortedDates[i-1].toISOString().slice(0,10)} to ${sortedDates[i].toISOString().slice(0,10)})`);
  }

  if (sortedWinners.length >= 3) {
    const top3Dates = sortedWinners.slice(0,3).map(t => parseDate(t.entry_time));
    const top3Span = Math.round((Math.max(...top3Dates) - Math.min(...top3Dates)) / (1000*60*60*24));
    if (top3Span < 90 && spanDays > 365) flags.push(`TEMPORAL CLUSTERING: Top 3 winners all within ${top3Span} days (backtest=${spanDays} days)`);
  }

  if (grossProfit > 0) {
    const maxTrade = sortedWinners[0].pnl;
    if (maxTrade/grossProfit > 0.25) flags.push(`SINGLE TRADE DOMINANCE: Best trade = ${(100*maxTrade/grossProfit).toFixed(1)}% of gross profit ($${maxTrade.toFixed(2)})`);
  }

  const tpWins = winners.filter(t => t.reason === 'tp');
  const tpProfit = tpWins.reduce((s,t) => s+t.pnl, 0);
  const nonTpProfit = grossProfit - tpProfit;
  if (grossProfit > 0) {
    console.log(`\n    TP-sourced profit: $${tpProfit.toFixed(2)} (${(100*tpProfit/grossProfit).toFixed(1)}%)`);
    console.log(`    Non-TP profit: $${nonTpProfit.toFixed(2)} (${(100*nonTpProfit/grossProfit).toFixed(1)}%)`);
    if (tpProfit > 0 && 100*tpProfit/grossProfit > 80) flags.push(`TP DEPENDENCY: ${(100*tpProfit/grossProfit).toFixed(1)}% of gross profit from TP exits only`);
  }

  if (flags.length === 0) flags.push('No major overfitting flags detected.');
  flags.forEach(f => console.log(`    *** ${f}`));
  return flags;
}

const files = [
  ['C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_db2af052.trade_list.json', '1. Vortex v3a ETH 4h | PF=2.034 | 84 trades | TOP RESULT'],
  ['C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_be4177e1.trade_list.json', '2. KAMA Stoch v1 ETH 1h | PF=1.857 | 42 trades'],
  ['C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_4409e998.trade_list.json', '3. Vortex v2c ETH 4h | PF=1.892 | 84 trades'],
  ['C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_880e9fc2.trade_list.json', '4. KAMA Stoch v1 ETH 4h | PF=0.399 | 43 trades | TRANSITIONAL CHECK'],
  ['C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260303/hl_20260303_1147a757.trade_list.json', '5. KAMA Stoch v2 ETH 1h | PF=1.709 | 42 trades'],
];

const allFlags = {};
for (const [fp, label] of files) {
  allFlags[label] = analyze(fp, label);
}

console.log(`\n${'='.repeat(80)}`);
console.log(`  CROSS-STRATEGY OVERFITTING SUMMARY`);
console.log(`${'='.repeat(80)}`);
for (const [label, flags] of Object.entries(allFlags)) {
  console.log(`\n  ${label}:`);
  flags.forEach(f => console.log(`    - ${f}`));
}
