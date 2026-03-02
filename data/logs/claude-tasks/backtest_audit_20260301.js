const fs = require('fs');
const path = require('path');

const BASE = "C:/Users/Clamps/.openclaw/workspace";
const dir = path.join(BASE, "artifacts/backtests/20260301");
const allFiles = fs.readdirSync(dir).filter(f => f.endsWith('.backtest_result.json')).sort();

console.log(`Total files: ${allFiles.length}`);

const highPfLowTrade = [];
const zeroTrade = [];
const highWinrate = [];
const zeroDd = [];
const identicalResults = {};
const btcResults = [];
const negativeOrNan = [];
const allResults = [];

for (const fname of allFiles) {
    try {
        const raw = fs.readFileSync(path.join(dir, fname), 'utf8');
        const data = JSON.parse(raw);
        const r = data.results || data;
        const fid = fname.replace('.backtest_result.json', '');

        const pf = r.profit_factor || 0;
        const trades = r.total_trades || 0;
        const wr = r.win_rate || 0;
        const ddPct = r.max_drawdown_pct || 0;
        const ddAbs = r.max_drawdown || 0;
        const net = r.net_profit || 0;

        const inputs = data.inputs || {};
        const dsMeta = inputs.dataset_meta || '';
        let variant = inputs.variant || data.variant_name || r.variant_name || '';

        let asset = '', tf = '';
        const m = dsMeta.match(/hyperliquid[/\\](\w+)[/\\](\w+)[/\\]/);
        if (m) { asset = m[1]; tf = m[2]; }
        else { asset = r.asset || data.asset || ''; tf = r.timeframe || data.timeframe || ''; }

        const template = r.template_name || data.template_name || '';
        const gateInfo = data.gate || {};
        const gate = gateInfo.gate_pass != null ? gateInfo.gate_pass : (data.gate_pass != null ? data.gate_pass : null);
        const minTrades = gateInfo.min_trades_required != null ? gateInfo.min_trades_required : (data.min_trades_required != null ? data.min_trades_required : null);

        const rb = r.regime_breakdown || data.regime_breakdown || {};
        const tTrades = rb.trending_trades != null ? rb.trending_trades : 'N/A';
        const rTrades = rb.ranging_trades != null ? rb.ranging_trades : 'N/A';
        const trTrades = rb.transitional_trades != null ? rb.transitional_trades : 'N/A';

        const rpf = r.regime_pf || data.regime_pf || {};
        const tPf = rpf.trending != null ? rpf.trending : 'N/A';
        const rPf = rpf.ranging != null ? rpf.ranging : 'N/A';
        const trPf = rpf.transitional != null ? rpf.transitional : 'N/A';

        const rec = {
            id: fid, variant, template, pf, trades, wr,
            dd_pct: ddPct, dd_abs: ddAbs, net,
            asset, tf, gate, min_trades: minTrades,
            t_trades: tTrades, r_trades: rTrades, tr_trades: trTrades,
            t_pf: tPf, r_pf: rPf, tr_pf: trPf
        };
        allResults.push(rec);

        const fp = `${pf.toFixed(6)}|${trades}|${net.toFixed(2)}`;
        if (!identicalResults[fp]) identicalResults[fp] = [];
        identicalResults[fp].push(fid);

        if (trades === 0) zeroTrade.push(rec);
        if (pf > 2.0 && trades < 30 && trades > 0) highPfLowTrade.push(rec);
        if (wr && wr > 0.70 && trades > 0) highWinrate.push(rec);
        if (ddPct === 0 && trades > 0) zeroDd.push(rec);
        if (asset.toUpperCase().includes('BTC')) btcResults.push(rec);
        if (trades < 0 || isNaN(pf)) negativeOrNan.push(rec);
    } catch (e) {
        console.log(`ERROR reading ${fname}: ${e.message}`);
    }
}

console.log(`\n=== SUMMARY ===`);
console.log(`Total results: ${allResults.length}`);
console.log(`Zero-trade results: ${zeroTrade.length}`);
console.log(`BTC results: ${btcResults.length}`);
console.log(`High PF (>2.0) / Low trades (<30): ${highPfLowTrade.length}`);
console.log(`High win rate (>70%): ${highWinrate.length}`);
console.log(`Zero DD% with trades: ${zeroDd.length}`);
console.log(`Negative trades/NaN: ${negativeOrNan.length}`);

const dupes = {};
for (const [fp, ids] of Object.entries(identicalResults)) {
    if (ids.length > 1) dupes[fp] = ids;
}
const dupCount = Object.values(dupes).reduce((s, v) => s + v.length - 1, 0);
console.log(`Duplicate fingerprint groups: ${Object.keys(dupes).length}`);
console.log(`Total duplicate results (wasted): ${dupCount}`);

console.log(`\n=== HIGH PF / LOW TRADES (PF>2, trades<30) ===`);
highPfLowTrade.sort((a, b) => b.pf - a.pf).slice(0, 20).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} WR=${r.wr.toFixed(4)} DD=${r.dd_pct.toFixed(1)}% asset=${r.asset} tf=${r.tf}`);
});

console.log(`\n=== ZERO TRADE RESULTS (first 20) ===`);
zeroTrade.slice(0, 20).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} template=${r.template} asset=${r.asset} tf=${r.tf} gate=${r.gate} min_trades=${r.min_trades}`);
});

console.log(`\n=== BTC RESULTS (top 30 by PF) ===`);
btcResults.sort((a, b) => b.pf - a.pf).slice(0, 30).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} DD%=${r.dd_pct.toFixed(1)} net=${r.net.toFixed(2)}`);
});

console.log(`\n=== HIGH WIN RATE (>70%, top 20) ===`);
highWinrate.sort((a, b) => b.wr - a.wr).slice(0, 20).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} WR=${r.wr.toFixed(4)}`);
});

console.log(`\n=== ZERO DD% WITH TRADES (first 20) ===`);
zeroDd.slice(0, 20).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} DD%=${r.dd_pct} DD_abs=${r.dd_abs}`);
});

console.log(`\n=== DUPLICATE FINGERPRINTS (top 10 groups) ===`);
Object.entries(dupes).sort((a, b) => b[1].length - a[1].length).slice(0, 10).forEach(([fp, ids]) => {
    const parts = fp.split('|');
    const shown = ids.slice(0, 5).join(', ');
    console.log(`  PF=${parts[0]} trades=${parts[1]}: ${ids.length} copies -> [${shown}]${ids.length > 5 ? '...' : ''}`);
});

const legit = allResults.filter(r => r.trades >= 30);
console.log(`\n=== TOP 15 PF RESULTS (trades >= 30) ===`);
legit.sort((a, b) => b.pf - a.pf).slice(0, 15).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} WR=${r.wr.toFixed(4)} DD=${r.dd_pct.toFixed(1)}% net=${r.net.toFixed(2)} asset=${r.asset} tf=${r.tf}`);
    console.log(`    Regime: trending=${r.t_trades}(PF=${typeof r.t_pf === 'number' ? r.t_pf.toFixed(3) : r.t_pf}) ranging=${r.r_trades}(PF=${typeof r.r_pf === 'number' ? r.r_pf.toFixed(3) : r.r_pf}) trans=${r.tr_trades}(PF=${typeof r.tr_pf === 'number' ? r.tr_pf.toFixed(3) : r.tr_pf})`);
});

const gateZero = allResults.filter(r => r.min_trades === 0);
console.log(`\n=== GATE BUG (min_trades_required=0) ===`);
console.log(`  Affected results: ${gateZero.length}`);
gateZero.slice(0, 10).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} trades=${r.trades} gate_pass=${r.gate}`);
});

const worst = allResults.filter(r => r.trades > 0);
console.log(`\n=== WORST 10 PF RESULTS ===`);
worst.sort((a, b) => a.pf - b.pf).slice(0, 10).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} DD=${r.dd_pct.toFixed(1)}% net=${r.net.toFixed(2)} asset=${r.asset}`);
});

const dirExp = allResults.filter(r => (r.variant || '').toLowerCase().includes('directive'));
console.log(`\n=== DIRECTIVE VARIANTS ===`);
console.log(`  Total directive variants: ${dirExp.length}`);
dirExp.slice(0, 15).forEach(r => {
    console.log(`  ${r.id}: ${r.variant} PF=${r.pf.toFixed(3)} trades=${r.trades} DD=${r.dd_pct.toFixed(1)}%`);
});

const assets = {};
allResults.forEach(r => {
    const a = r.asset || 'UNKNOWN';
    if (!assets[a]) assets[a] = { count: 0, pf_sum: 0, total_trades: 0, net_sum: 0 };
    assets[a].count++;
    assets[a].pf_sum += r.pf;
    assets[a].total_trades += r.trades;
    assets[a].net_sum += r.net;
});

console.log(`\n=== ASSET DISTRIBUTION ===`);
Object.entries(assets).sort((a, b) => b[1].count - a[1].count).forEach(([a, v]) => {
    const avgPf = v.count > 0 ? v.pf_sum / v.count : 0;
    console.log(`  ${a}: ${v.count} results, avg_pf=${avgPf.toFixed(3)}, total_trades=${v.total_trades}, net_sum=${v.net_sum.toFixed(2)}`);
});

const tfs = {};
allResults.forEach(r => {
    const t = r.tf || 'UNKNOWN';
    if (!tfs[t]) tfs[t] = { count: 0, pf_sum: 0 };
    tfs[t].count++;
    tfs[t].pf_sum += r.pf;
});

console.log(`\n=== TIMEFRAME DISTRIBUTION ===`);
Object.entries(tfs).sort((a, b) => b[1].count - a[1].count).forEach(([t, v]) => {
    const avgPf = v.count > 0 ? v.pf_sum / v.count : 0;
    console.log(`  ${t}: ${v.count} results, avg_pf=${avgPf.toFixed(3)}`);
});

const templates = {};
allResults.forEach(r => {
    const t = r.template || 'UNKNOWN';
    if (!templates[t]) templates[t] = { count: 0, pf_sum: 0, trades_sum: 0, gate_pass: 0 };
    templates[t].count++;
    templates[t].pf_sum += r.pf;
    templates[t].trades_sum += r.trades;
    if (r.gate === true) templates[t].gate_pass++;
});

console.log(`\n=== TEMPLATE DISTRIBUTION ===`);
Object.entries(templates).sort((a, b) => b[1].count - a[1].count).forEach(([t, v]) => {
    const avgPf = v.count > 0 ? v.pf_sum / v.count : 0;
    console.log(`  ${t}: ${v.count} results, avg_pf=${avgPf.toFixed(3)}, total_trades=${v.trades_sum}, gate_pass=${v.gate_pass}`);
});

const gatePassCount = allResults.filter(r => r.gate === true).length;
const gateFailCount = allResults.filter(r => r.gate === false).length;
const gateNoneCount = allResults.filter(r => r.gate === null).length;
console.log(`\n=== GATE PASS SUMMARY ===`);
console.log(`  gate_pass=True: ${gatePassCount}`);
console.log(`  gate_pass=False: ${gateFailCount}`);
console.log(`  gate_pass=None/missing: ${gateNoneCount}`);

const pfBuckets = { '<0.5': 0, '0.5-0.8': 0, '0.8-1.0': 0, '1.0-1.2': 0, '1.2-1.5': 0, '1.5-2.0': 0, '2.0-3.0': 0, '3.0+': 0 };
allResults.forEach(r => {
    if (r.trades === 0) return;
    const p = r.pf;
    if (p < 0.5) pfBuckets['<0.5']++;
    else if (p < 0.8) pfBuckets['0.5-0.8']++;
    else if (p < 1.0) pfBuckets['0.8-1.0']++;
    else if (p < 1.2) pfBuckets['1.0-1.2']++;
    else if (p < 1.5) pfBuckets['1.2-1.5']++;
    else if (p < 2.0) pfBuckets['1.5-2.0']++;
    else if (p < 3.0) pfBuckets['2.0-3.0']++;
    else pfBuckets['3.0+']++;
});

console.log(`\n=== PF DISTRIBUTION (excl zero-trade) ===`);
for (const [bucket, count] of Object.entries(pfBuckets)) {
    const bar = '#'.repeat(Math.min(count, 80));
    console.log(`  ${bucket.padStart(8)}: ${String(count).padStart(4)} ${bar}`);
}

const profitable = allResults.filter(r => r.trades > 0 && r.pf > 1.0).length;
const unprofitable = allResults.filter(r => r.trades > 0 && r.pf <= 1.0).length;
console.log(`\n=== PROFITABILITY ===`);
console.log(`  Profitable (PF>1): ${profitable}`);
console.log(`  Unprofitable (PF<=1): ${unprofitable}`);
if (profitable + unprofitable > 0) {
    console.log(`  Win rate: ${(profitable / (profitable + unprofitable) * 100).toFixed(1)}%`);
}
