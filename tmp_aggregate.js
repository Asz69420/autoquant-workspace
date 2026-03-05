const fs = require('fs');
const path = require('path');
const dir = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests/20260306';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.backtest_result.json'));
console.log('Total files:', files.length);

const results = [];
for (const f of files) {
  try {
    const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const meta = (d.inputs && d.inputs.dataset_meta || '').replace(/\\/g, '/');
    const parts = meta.split('/');
    let asset = 'UNK', tf = 'UNK';
    for (let i = 0; i < parts.length; i++) {
      if (parts[i] === 'hyperliquid' && i+2 < parts.length) {
        asset = parts[i+1]; tf = parts[i+2]; break;
      }
    }
    const r = d.results || {};
    const cov = d.coverage || {};
    const ppr = d.ppr || {};
    const rpf = r.regime_pf || {};
    const rbd = r.regime_breakdown || {};
    const sig = cov.entry_signals_seen || {};
    const specPath = (d.inputs && d.inputs.strategy_spec) || '';
    const specId = path.basename(specPath).replace('.strategy_spec.json', '');
    results.push({
      id: d.id || '', file: f, specId, variant: (d.inputs && d.inputs.variant) || '',
      asset, tf,
      trades: r.total_trades || 0, pf: r.profit_factor || 0, dd: r.max_drawdown_pct || 0,
      wr: r.win_rate || 0, ret: r.total_return_pct || 0, netPnl: r.net_profit_pct || 0,
      eq: r.final_equity || 0,
      rpfTrend: rpf.trending || 0, rpfRange: rpf.ranging || 0, rpfTrans: rpf.transitional || 0,
      rtTrend: rbd.trending_trades || 0, rtRange: rbd.ranging_trades || 0, rtTrans: rbd.transitional_trades || 0,
      dom: r.dominant_regime || '',
      pprScore: ppr.score || 0, pprDec: ppr.decision || '', pprFlags: ppr.flags || [],
      sigTotal: sig.total || 0, sigLong: sig.long || 0, sigShort: sig.short || 0,
      bars: cov.bars_tested || 0, tim: cov.time_in_market_pct || 0,
    });
  } catch(e) { console.log('PARSE ERROR:', f, e.message); }
}

const total = results.length;
const zeroTrade = results.filter(r => r.trades === 0);
const hasTrades = results.filter(r => r.trades > 0);

console.log('');
console.log('====================================================================================================');
console.log('BACKTEST RESULTS SUMMARY -- 2026-03-06 (' + total + ' files)');
console.log('====================================================================================================');
console.log('');
console.log('Total backtests:     ' + total);
console.log('With trades:         ' + hasTrades.length);
console.log('Zero-trade:          ' + zeroTrade.length + '  (' + (100*zeroTrade.length/total).toFixed(1) + '%)');

// Asset breakdown
const assetMap = {};
results.forEach(r => { if (!assetMap[r.asset]) assetMap[r.asset] = {total: 0, wt: 0, zt: 0}; assetMap[r.asset].total++; if (r.trades > 0) assetMap[r.asset].wt++; else assetMap[r.asset].zt++; });
console.log('');
console.log('Asset breakdown:');
Object.keys(assetMap).sort().forEach(a => { const v = assetMap[a]; console.log('  ' + a.padEnd(6) + ': ' + String(v.total).padStart(4) + ' total  |  ' + String(v.wt).padStart(3) + ' with trades  |  ' + String(v.zt).padStart(3) + ' zero-trade'); });

// TF breakdown
const tfMap = {};
results.forEach(r => { if (!tfMap[r.tf]) tfMap[r.tf] = {total: 0, wt: 0, zt: 0}; tfMap[r.tf].total++; if (r.trades > 0) tfMap[r.tf].wt++; else tfMap[r.tf].zt++; });
console.log('');
console.log('Timeframe breakdown:');
Object.keys(tfMap).sort().forEach(t => { const v = tfMap[t]; console.log('  ' + t.padEnd(6) + ': ' + String(v.total).padStart(4) + ' total  |  ' + String(v.wt).padStart(3) + ' with trades  |  ' + String(v.zt).padStart(3) + ' zero-trade'); });

// PPR breakdown
const pprMap = {};
results.forEach(r => { pprMap[r.pprDec] = (pprMap[r.pprDec] || 0) + 1; });
console.log('');
console.log('PPR decisions:');
Object.keys(pprMap).sort().forEach(d => console.log('  ' + d.padEnd(20) + ': ' + pprMap[d]));

// Variant breakdown
const varMap = {};
results.forEach(r => { if (!varMap[r.variant]) varMap[r.variant] = {total: 0, zt: 0}; varMap[r.variant].total++; if (r.trades === 0) varMap[r.variant].zt++; });
console.log('');
console.log('Variant breakdown:');
Object.keys(varMap).sort().forEach(v => { const val = varMap[v]; console.log('  ' + v.padEnd(55) + ': ' + String(val.total).padStart(4) + ' total  |  ' + String(val.zt).padStart(3) + ' zero-trade'); });

// Results with trades sorted by PF
console.log('');
console.log('====================================================================================================');
console.log('RESULTS WITH TRADES (' + hasTrades.length + ' backtests) -- sorted by Profit Factor');
console.log('====================================================================================================');
if (hasTrades.length > 0) {
  hasTrades.sort((a, b) => b.pf - a.pf);
  console.log('No  ID                     Spec(last25)              Ast  TF   Trd     PF    WR%    DD%    Ret%  PPR  TrPF   RgPF  TrsPF');
  console.log('----------------------------------------------------------------------------------------------------------------------------------');
  hasTrades.forEach((r, i) => {
    const sp = r.specId.slice(-25);
    console.log(
      String(i+1).padStart(2) + '  ' + r.id.padEnd(22) + ' ' + sp.padStart(25) + ' ' +
      r.asset.padStart(4) + ' ' + r.tf.padStart(4) + ' ' +
      String(r.trades).padStart(5) + ' ' + r.pf.toFixed(3).padStart(7) + ' ' +
      (r.wr*100).toFixed(1).padStart(5) + '% ' +
      r.dd.toFixed(2).padStart(6) + '% ' +
      r.ret.toFixed(2).padStart(7) + '% ' +
      r.pprScore.toFixed(2).padStart(5) + ' ' +
      r.rpfTrend.toFixed(3).padStart(6) + ' ' +
      r.rpfRange.toFixed(3).padStart(6) + ' ' +
      r.rpfTrans.toFixed(3).padStart(6)
    );
  });
} else {
  console.log('  ** NO RESULTS WITH TRADES **');
}

// FLAG 1: Zero-trade
console.log('');
console.log('====================================================================================================');
console.log('FLAG 1: ZERO-TRADE RESULTS (' + zeroTrade.length + ' of ' + total + ')');
console.log('====================================================================================================');
const ztSpecs = {};
zeroTrade.forEach(r => { if (!ztSpecs[r.specId]) ztSpecs[r.specId] = []; ztSpecs[r.specId].push(r); });
console.log('');
console.log('Unique specs with zero trades: ' + Object.keys(ztSpecs).length);
console.log('');
console.log('                          Spec ID (last 40)  Cnt  Assets          TFs         Signals');
console.log('----------------------------------------------------------------------------------------------------');
Object.entries(ztSpecs).sort((a,b) => b[1].length - a[1].length).forEach(([spec, runs]) => {
  const assets = [...new Set(runs.map(r => r.asset))].sort().join(', ');
  const tfs = [...new Set(runs.map(r => r.tf))].sort().join(', ');
  const sigs = [...new Set(runs.map(r => String(r.sigTotal)))].sort().join(', ');
  console.log(spec.slice(-40).padStart(40) + '  ' + String(runs.length).padStart(3) + '  ' + assets.padEnd(14) + '  ' + tfs.padEnd(10) + '  ' + sigs);
});

// FLAG 2: PF > 2.0 with trades < 30
console.log('');
console.log('====================================================================================================');
console.log('FLAG 2: HIGH PF (>2.0) WITH LOW TRADES (<30)');
console.log('====================================================================================================');
const f2 = hasTrades.filter(r => r.pf > 2.0 && r.trades < 30);
if (f2.length > 0) f2.forEach(r => console.log('  ' + r.id + ' | ' + r.specId.slice(-35) + ' | ' + r.asset + ' ' + r.tf + ' | PF=' + r.pf.toFixed(3) + ' | Trades=' + r.trades + ' | DD=' + r.dd.toFixed(2) + '%'));
else console.log('  None found.');

// FLAG 3: DD == 0 with trades > 0
console.log('');
console.log('====================================================================================================');
console.log('FLAG 3: MAX DRAWDOWN == 0 WITH TRADES > 0 (BUG INDICATOR)');
console.log('====================================================================================================');
const f3 = hasTrades.filter(r => r.dd === 0.0);
if (f3.length > 0) f3.forEach(r => console.log('  ' + r.id + ' | ' + r.specId.slice(-35) + ' | ' + r.asset + ' ' + r.tf + ' | PF=' + r.pf.toFixed(3) + ' | Trades=' + r.trades));
else console.log('  None found.');

// FLAG 4: NaN or negative
console.log('');
console.log('====================================================================================================');
console.log('FLAG 4: NaN OR NEGATIVE TRADE COUNTS');
console.log('====================================================================================================');
const f4 = results.filter(r => r.trades === null || r.trades === undefined || isNaN(r.trades) || r.trades < 0);
if (f4.length > 0) f4.forEach(r => console.log('  ' + r.id + ' | trades=' + r.trades));
else console.log('  None found.');
const f4b = results.filter(r => isNaN(r.pf) || !isFinite(r.pf));
if (f4b.length > 0) { console.log('  NaN/Inf profit factors:'); f4b.forEach(r => console.log('  ' + r.id + ' | PF=' + r.pf)); }
else console.log('  No NaN/Inf profit factors found.');

// FLAG 5: Identical results from different specs
console.log('');
console.log('====================================================================================================');
console.log('FLAG 5: IDENTICAL RESULTS ACROSS DIFFERENT SPECS');
console.log('====================================================================================================');
const fps = {};
results.forEach(r => {
  const key = [r.trades, r.pf.toFixed(6), r.dd.toFixed(6), r.wr.toFixed(6), r.ret.toFixed(6), r.asset, r.tf].join('|');
  if (!fps[key]) fps[key] = [];
  fps[key].push(r);
});
let dupCount = 0;
Object.entries(fps).forEach(([key, group]) => {
  const specs = new Set(group.map(r => r.specId));
  if (specs.size > 1 && group[0].trades > 0) {
    dupCount++;
    console.log('');
    console.log('  Fingerprint: ' + key);
    group.forEach(r => console.log('    - ' + r.specId.slice(-40) + ' (variant: ' + r.variant + ')'));
  }
});
if (dupCount === 0) console.log('  No identical non-zero-trade results from different specs.');

// Zero-trade groups
const ztAtf = {};
zeroTrade.forEach(r => { const k = r.asset + ' ' + r.tf; if (!ztAtf[k]) ztAtf[k] = []; ztAtf[k].push(r); });
console.log('');
console.log('  Zero-trade identical groups by asset/timeframe:');
Object.keys(ztAtf).sort().forEach(k => {
  const g = ztAtf[k];
  const specs = new Set(g.map(r => r.specId));
  console.log('    ' + k + ': ' + g.length + ' backtests, ' + specs.size + ' unique specs -- ALL identical zero-trade');
});

// Performance stats
if (hasTrades.length > 0) {
  console.log('');
  console.log('====================================================================================================');
  console.log('PERFORMANCE STATISTICS (trades > 0 only)');
  console.log('====================================================================================================');
  const pfs = hasTrades.map(r => r.pf).sort((a,b) => a-b);
  const dds = hasTrades.map(r => r.dd).sort((a,b) => a-b);
  const tcs = hasTrades.map(r => r.trades).sort((a,b) => a-b);
  const wrs = hasTrades.map(r => r.wr*100).sort((a,b) => a-b);
  const rets = hasTrades.map(r => r.ret).sort((a,b) => a-b);
  const avg = arr => arr.reduce((s,v) => s+v, 0) / arr.length;
  const med = arr => arr[Math.floor(arr.length/2)];
  console.log('  Profit Factor:   min=' + Math.min(...pfs).toFixed(3) + '  max=' + Math.max(...pfs).toFixed(3) + '  avg=' + avg(pfs).toFixed(3) + '  median=' + med(pfs).toFixed(3));
  console.log('  Max Drawdown%:   min=' + Math.min(...dds).toFixed(2) + '  max=' + Math.max(...dds).toFixed(2) + '  avg=' + avg(dds).toFixed(2));
  console.log('  Trade Count:     min=' + Math.min(...tcs) + '  max=' + Math.max(...tcs) + '  avg=' + avg(tcs).toFixed(1));
  console.log('  Win Rate%:       min=' + Math.min(...wrs).toFixed(1) + '  max=' + Math.max(...wrs).toFixed(1) + '  avg=' + avg(wrs).toFixed(1));
  console.log('  Total Return%:   min=' + Math.min(...rets).toFixed(2) + '  max=' + Math.max(...rets).toFixed(2) + '  avg=' + avg(rets).toFixed(2));

  const accept = hasTrades.filter(r => r.pf > 1.2 && r.dd < 20 && r.trades >= 30).sort((a,b) => b.pf - a.pf);
  console.log('');
  console.log('  ACCEPT candidates (PF>1.2, DD<20%, trades>=30): ' + accept.length);
  accept.forEach(r => {
    console.log('    ' + r.id + ' | ' + r.specId.slice(-40) + ' | ' + r.asset + ' ' + r.tf);
    console.log('      PF=' + r.pf.toFixed(3) + ' | Trades=' + r.trades + ' | DD=' + r.dd.toFixed(2) + '% | Ret=' + r.ret.toFixed(2) + '%');
    console.log('      Regime PF: trend=' + r.rpfTrend.toFixed(3) + ' range=' + r.rpfRange.toFixed(3) + ' trans=' + r.rpfTrans.toFixed(3));
    console.log('      PPR=' + r.pprScore.toFixed(2) + ' (' + r.pprDec + ')');
  });
}

console.log('');
console.log('====================================================================================================');
console.log('END OF SUMMARY');
console.log('====================================================================================================');
