const fs = require('fs');
const path = require('path');

const base = 'C:/Users/Clamps/.openclaw/workspace/artifacts/backtests';
const days = ['20260226', '20260227', '20260228'];
const results = [];

for (const day of days) {
  const dir = path.join(base, day);
  let files = [];
  try {
    files = fs.readdirSync(dir).filter(f => f.endsWith('.backtest_result.json'));
  } catch(e) { continue; }
  for (const fname of files) {
    const fp = path.join(dir, fname);
    try {
      const data = JSON.parse(fs.readFileSync(fp, 'utf8'));
      const r = data.results || {};
      const inp = data.inputs || {};
      const gate = data.gate || {};
      results.push({
        day, id: data.id || '', variant: (inp.variant || 'unknown'),
        spec: path.basename(inp.strategy_spec || ''),
        pf: r.profit_factor != null ? r.profit_factor : null,
        trades: r.total_trades != null ? r.total_trades : (r.trades || 0),
        win_rate: r.win_rate != null ? r.win_rate : null,
        max_dd: r.max_drawdown != null ? r.max_drawdown : (r.max_drawdown_proxy != null ? r.max_drawdown_proxy : null),
        net_profit: r.net_profit != null ? r.net_profit : (r.net_return != null ? r.net_return : null),
        net_profit_pct: r.net_profit_pct != null ? r.net_profit_pct : (r.net_return != null ? r.net_return : null),
        regime_breakdown: r.regime_breakdown || null,
        regime_pf: r.regime_pf || null,
        regime_wr: r.regime_wr || null,
        dominant_regime: r.dominant_regime || null,
        gate_pass: gate.gate_pass != null ? gate.gate_pass : null,
        gate_reason: gate.gate_reason || '',
        file: fname
      });
    } catch(e) { process.stderr.write('ERROR parsing '+fp+': '+e.message+'\n'); }
  }
}

results.sort((a,b) => {
  if (a.day !== b.day) return a.day < b.day ? -1 : 1;
  return (b.pf || 0) - (a.pf || 0);
});

const total = results.length;
const d26 = results.filter(r => r.day==='20260226').length;
const d27 = results.filter(r => r.day==='20260227').length;
const d28 = results.filter(r => r.day==='20260228').length;
console.log('=== TOTAL BACKTESTS: '+total+' ===');
console.log('  20260226: '+d26);
console.log('  20260227: '+d27);
console.log('  20260228: '+d28);

console.log();
console.log('=== OVERFITTING CHECK: PF > 2.0 with < 30 trades ===');
const of1 = results.filter(r => r.pf && r.pf > 2.0 && r.trades < 30);
if (of1.length) of1.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | PF='+r.pf.toFixed(3)+' | trades='+r.trades+' | WR='+r.win_rate));
else console.log('  None found');

console.log();
console.log('=== OVERFITTING CHECK: PF > 1.5 with < 50 trades ===');
const of2 = results.filter(r => r.pf && r.pf > 1.5 && r.trades && r.trades < 50);
if (of2.length) of2.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | PF='+r.pf.toFixed(3)+' | trades='+r.trades+' | WR='+r.win_rate));
else console.log('  None found');

console.log();
console.log('=== OVERFITTING CHECK: Win rate > 70% ===');
const hwr = results.filter(r => r.win_rate && r.win_rate > 0.70);
if (hwr.length) hwr.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | PF='+r.pf.toFixed(3)+' | trades='+r.trades+' | WR='+(r.win_rate*100).toFixed(2)+'%'));
else console.log('  None found');

console.log();
console.log('=== DATA QUALITY: Zero trades ===');
const zt = results.filter(r => r.trades === 0);
if (zt.length) zt.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | spec='+r.spec));
else console.log('  None found');

console.log();
console.log('=== DATA QUALITY: Max drawdown = 0 ===');
const zdd = results.filter(r => r.max_dd !== null && r.max_dd === 0);
if (zdd.length) zdd.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | trades='+r.trades+' | PF='+r.pf));
else console.log('  None found');

console.log();
console.log('=== DATA QUALITY: Negative trade counts ===');
const bt = results.filter(r => r.trades !== null && r.trades < 0);
if (bt.length) bt.forEach(r => console.log('  '+r.id+' | trades='+r.trades));
else console.log('  None found');

console.log();
console.log('=== DATA QUALITY: Gate failures ===');
const gf = results.filter(r => r.gate_pass === false);
if (gf.length) gf.forEach(r => console.log('  '+r.id+' | variant='+r.variant+' | reason='+r.gate_reason+' | trades='+r.trades));
else console.log('  None found');

console.log();
console.log('=== DUPLICATE CHECK: Identical PF+trades+DD combos ===');
const fingerprints = {};
results.forEach(r => {
  if (r.id === 'bt-fixture') return;
  const fp = [Math.round((r.pf||0)*1e6)/1e6, r.trades, Math.round((r.max_dd||0)*100)/100].join('|');
  if (!fingerprints[fp]) fingerprints[fp] = [];
  fingerprints[fp].push(r);
});
const dupes = Object.entries(fingerprints).filter(([k,v]) => v.length > 1).sort((a,b) => b[1].length - a[1].length);
if (dupes.length) {
  dupes.forEach(([fp, entries]) => {
    const parts = fp.split('|');
    const pf = Number(parts[0]), trades = parts[1], dd = Number(parts[2]);
    console.log('  PF='+pf.toFixed(4)+' | trades='+trades+' | DD='+dd.toFixed(2)+' -- '+entries.length+' duplicates:');
    entries.slice(0,6).forEach(e => console.log('    '+e.id+' | variant='+e.variant+' | day='+e.day+' | spec='+e.spec));
    if (entries.length > 6) console.log('    ... and '+(entries.length-6)+' more');
  });
} else console.log('  None found');

console.log();
console.log('=== TOP 15 BY PF (highest) ===');
const topArr = results.filter(r => r.id !== 'bt-fixture').sort((a,b) => (b.pf||0)-(a.pf||0));
topArr.slice(0,15).forEach(r => {
  let ri = '';
  if (r.regime_pf) {
    ri = ' | regime_pf: tr='+(r.regime_pf.trending||0).toFixed(3)+' ra='+(r.regime_pf.ranging||0).toFixed(3)+' trans='+(r.regime_pf.transitional||0).toFixed(3);
  }
  const wr = r.win_rate ? (r.win_rate*100).toFixed(2)+'%' : 'N/A';
  console.log('  '+r.id+' | variant='+r.variant+' | PF='+(r.pf||0).toFixed(4)+' | trades='+r.trades+' | WR='+wr+' | DD='+(r.max_dd||0).toFixed(2)+' | net='+(r.net_profit_pct||0).toFixed(2)+'%'+ri);
});

console.log();
console.log('=== BOTTOM 15 BY PF (lowest non-fixture) ===');
const nf = results.filter(r => r.id !== 'bt-fixture' && r.pf !== null).sort((a,b) => a.pf - b.pf);
nf.slice(0,15).forEach(r => {
  let ri = '';
  if (r.regime_pf) {
    ri = ' | regime_pf: tr='+(r.regime_pf.trending||0).toFixed(3)+' ra='+(r.regime_pf.ranging||0).toFixed(3)+' trans='+(r.regime_pf.transitional||0).toFixed(3);
  }
  const wr = r.win_rate ? (r.win_rate*100).toFixed(2)+'%' : 'N/A';
  console.log('  '+r.id+' | variant='+r.variant+' | PF='+(r.pf||0).toFixed(4)+' | trades='+r.trades+' | WR='+wr+' | DD='+(r.max_dd||0).toFixed(2)+ri);
});

console.log();
console.log('=== REGIME ANALYSIS (files with regime data) ===');
const rr = results.filter(r => r.regime_pf !== null);
console.log('  Files with regime data: '+rr.length+' of '+results.length);
rr.forEach(r => {
  const rpf = r.regime_pf;
  const rb = r.regime_breakdown;
  const rwr = r.regime_wr;
  const tr_pf = rpf.trending||0, ra_pf = rpf.ranging||0, trans_pf = rpf.transitional||0;
  let profitableCount = [tr_pf, ra_pf, trans_pf].filter(v => v > 1.0).length;
  let flag = '';
  if (profitableCount === 1) flag = ' ** SINGLE-REGIME PROFIT **';
  else if (profitableCount === 0) flag = ' ** UNPROFITABLE ALL REGIMES **';
  console.log('  '+r.id+' | variant='+r.variant+' | PF='+(r.pf||0).toFixed(4));
  console.log('    trending:  PF='+tr_pf.toFixed(3)+' trades='+(rb.trending_trades||'?')+' WR='+((rwr.trending||0)*100).toFixed(2)+'%');
  console.log('    ranging:   PF='+ra_pf.toFixed(3)+' trades='+(rb.ranging_trades||'?')+' WR='+((rwr.ranging||0)*100).toFixed(2)+'%');
  console.log('    transit:   PF='+trans_pf.toFixed(3)+' trades='+(rb.transitional_trades||'?')+' WR='+((rwr.transitional||0)*100).toFixed(2)+'%'+flag);
  console.log();
});

console.log();
console.log('=== AGGREGATE STATS ===');
const pfs = results.filter(r => r.pf && r.id !== 'bt-fixture').map(r => r.pf);
const trades_all = results.filter(r => r.trades && r.id !== 'bt-fixture').map(r => r.trades);
const profitableAll = pfs.filter(p => p > 1.0).length;
const avg_pf = pfs.reduce((a,b)=>a+b,0)/pfs.length;
const sorted_pfs = [...pfs].sort((a,b)=>a-b);
const median_pf = sorted_pfs[Math.floor(sorted_pfs.length/2)];
console.log('  Avg PF: '+avg_pf.toFixed(4));
console.log('  Median PF: '+median_pf.toFixed(4));
console.log('  PF > 1.0: '+profitableAll+' of '+pfs.length+' ('+(100*profitableAll/pfs.length).toFixed(1)+'%)');
const avg_trades = trades_all.reduce((a,b)=>a+b,0)/trades_all.length;
console.log('  Avg trades: '+avg_trades.toFixed(1));
console.log('  Min trades: '+Math.min(...trades_all));
console.log('  Max trades: '+Math.max(...trades_all));

console.log();
console.log('=== VARIANT SUMMARY ===');
const vs = {};
results.forEach(r => {
  if (r.id === 'bt-fixture') return;
  if (!vs[r.variant]) vs[r.variant] = [];
  vs[r.variant].push(r.pf);
});
Object.entries(vs).sort((a,b) => {
  const avgA = a[1].reduce((x,y)=>x+y,0)/a[1].length;
  const avgB = b[1].reduce((x,y)=>x+y,0)/b[1].length;
  return avgB - avgA;
}).forEach(([v, plist]) => {
  const avg = plist.reduce((a,b)=>a+b,0)/plist.length;
  const best = Math.max(...plist);
  const worst = Math.min(...plist);
  console.log('  '+v+': count='+plist.length+' avg_pf='+avg.toFixed(4)+' best='+best.toFixed(4)+' worst='+worst.toFixed(4));
});

console.log();
console.log('=== SPEC-LEVEL DEDUP CHECK ===');
const sr = {};
results.forEach(r => {
  if (r.id === 'bt-fixture') return;
  if (!sr[r.spec]) sr[r.spec] = [];
  sr[r.spec].push(r);
});
Object.entries(sr).sort().forEach(([spec, entries]) => {
  if (entries.length > 1) {
    const pfset = new Set(entries.map(e => Math.round((e.pf||0)*1e6)/1e6));
    if (pfset.size === 1 && entries.length > 2) {
      console.log('  SUSPECT: '+spec+' has '+entries.length+' variants ALL with identical PF='+[...pfset][0].toFixed(4));
    }
  }
});

console.log();
console.log('=== DAY-OVER-DAY PF TREND ===');
days.forEach(day => {
  const dp = results.filter(r => r.day === day && r.pf && r.id !== 'bt-fixture').map(r => r.pf);
  if (dp.length) {
    const sdp = [...dp].sort((a,b)=>a-b);
    console.log('  '+day+': avg_pf='+(dp.reduce((a,b)=>a+b,0)/dp.length).toFixed(4)+' median='+sdp[Math.floor(sdp.length/2)].toFixed(4)+' min='+Math.min(...dp).toFixed(4)+' max='+Math.max(...dp).toFixed(4)+' n='+dp.length);
  }
});
