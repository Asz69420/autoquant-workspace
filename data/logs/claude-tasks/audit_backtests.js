#!/usr/bin/env node
/**
 * Comprehensive backtest result auditor.
 * Parses all *.backtest_result.json files from 20260228 and 20260301,
 * extracts key fields, and produces aggregated audit output.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const BASE = path.resolve(__dirname, '..', '..', '..', 'artifacts', 'backtests');
const DAYS = ['20260228', '20260301'];

function safeGet(obj, ...keys) {
  let cur = obj;
  for (const k of keys) {
    if (cur && typeof cur === 'object' && k in cur) {
      cur = cur[k];
    } else {
      return null;
    }
  }
  return cur;
}

function isNanOrNull(v) {
  if (v === null || v === undefined) return true;
  if (typeof v === 'number' && isNaN(v)) return true;
  return false;
}

function extractSymbolTimeframe(data) {
  for (const key of ['dataset_meta', 'dataset_csv']) {
    const p = safeGet(data, 'inputs', key);
    if (!p) continue;
    const m = p.match(/hyperliquid[/\\]([A-Za-z0-9]+)[/\\](\w+)[/\\]/);
    if (m) return { symbol: m[1], timeframe: m[2] };
  }
  return { symbol: null, timeframe: null };
}

function parseFile(filepath) {
  const raw = fs.readFileSync(filepath, 'utf-8');
  const data = JSON.parse(raw);

  const results = safeGet(data, 'results') || {};
  const inputs = safeGet(data, 'inputs') || {};
  const gate = safeGet(data, 'gate') || {};
  const regimeBreakdown = safeGet(results, 'regime_breakdown') || {};
  const regimePf = safeGet(results, 'regime_pf') || {};

  const { symbol, timeframe } = extractSymbolTimeframe(data);

  return {
    id: safeGet(data, 'id'),
    variant: safeGet(inputs, 'variant'),
    strategy_spec: safeGet(inputs, 'strategy_spec'),
    symbol,
    timeframe,
    total_trades: safeGet(results, 'total_trades'),
    profit_factor: safeGet(results, 'profit_factor'),
    win_rate: safeGet(results, 'win_rate'),
    max_drawdown: safeGet(results, 'max_drawdown'),
    max_drawdown_pct: safeGet(results, 'max_drawdown_pct'),
    net_profit: safeGet(results, 'net_profit'),
    regime_breakdown: {
      trending_trades: safeGet(regimeBreakdown, 'trending_trades'),
      ranging_trades: safeGet(regimeBreakdown, 'ranging_trades'),
      transitional_trades: safeGet(regimeBreakdown, 'transitional_trades'),
    },
    regime_pf: {
      trending: safeGet(regimePf, 'trending'),
      ranging: safeGet(regimePf, 'ranging'),
      transitional: safeGet(regimePf, 'transitional'),
    },
    gate_pass: safeGet(gate, 'gate_pass'),
    source_file: path.basename(filepath),
    day: null,
  };
}

function main() {
  const allResults = [];
  const dayCounts = {};

  for (const day of DAYS) {
    const dayDir = path.join(BASE, day);
    let files = [];
    try {
      files = fs.readdirSync(dayDir)
        .filter(f => f.endsWith('.backtest_result.json'))
        .sort()
        .map(f => path.join(dayDir, f));
    } catch (e) {
      console.log(`  WARNING: could not read ${dayDir}: ${e.message}`);
    }
    dayCounts[day] = files.length;
    for (const fp of files) {
      try {
        const rec = parseFile(fp);
        rec.day = day;
        allResults.push(rec);
      } catch (e) {
        console.log(`  ERROR parsing ${fp}: ${e.message}`);
      }
    }
  }

  console.log(`Total files parsed: ${allResults.length}`);
  for (const day of DAYS) {
    console.log(`  ${day}: ${dayCounts[day] || 0} backtests`);
  }

  // 3. overfit_suspects
  const overfitSuspects = [];
  for (const r of allResults) {
    const pf = r.profit_factor;
    const tt = r.total_trades;
    const wr = r.win_rate;
    const variant = (r.variant || '').toLowerCase();
    if (pf === null || tt === null) continue;
    const reasons = [];
    if (pf > 2.0 && tt < 30) reasons.push('PF>2.0 AND trades<30');
    if (wr !== null && wr > 0.70 && variant.includes('trend')) reasons.push('win_rate>0.70 for trend variant');
    if (pf > 3.0) reasons.push('PF>3.0');
    if (reasons.length > 0) {
      overfitSuspects.push({
        id: r.id, variant: r.variant, profit_factor: pf,
        total_trades: tt, win_rate: wr, reasons, day: r.day,
      });
    }
  }

  // 4. zero_trade
  const zeroTrade = allResults
    .filter(r => r.total_trades === 0)
    .map(r => ({ id: r.id, variant: r.variant, day: r.day, strategy_spec: r.strategy_spec }));

  // 5. data_quality_issues
  const dataQualityIssues = [];
  for (const r of allResults) {
    const issues = [];
    if (r.max_drawdown === 0) issues.push('max_drawdown==0');
    if (r.max_drawdown_pct === 0) issues.push('max_drawdown_pct==0');
    if (r.total_trades !== null && r.total_trades < 0) issues.push('total_trades<0');
    if (isNanOrNull(r.net_profit)) issues.push('net_profit is null/NaN');
    if (issues.length > 0) {
      dataQualityIssues.push({ id: r.id, variant: r.variant, day: r.day, issues });
    }
  }

  // 6. duplicate_fingerprints
  const fpGroups = {};
  for (const r of allResults) {
    const pf = r.profit_factor;
    const tt = r.total_trades;
    const wr = r.win_rate;
    if (pf === null || tt === null || wr === null) continue;
    const key = `${Math.round(pf * 100000) / 100000}_${tt}_${Math.round(wr * 100000) / 100000}`;
    if (!fpGroups[key]) fpGroups[key] = [];
    fpGroups[key].push({
      id: r.id, variant: r.variant, day: r.day,
      profit_factor: pf, total_trades: tt, win_rate: wr,
    });
  }
  const duplicateFingerprints = [];
  for (const [key, members] of Object.entries(fpGroups)) {
    if (members.length >= 2) {
      const parts = key.split('_');
      duplicateFingerprints.push({
        fingerprint: {
          profit_factor: parseFloat(parts[0]),
          total_trades: parseInt(parts[1]),
          win_rate: parseFloat(parts[2]),
        },
        count: members.length,
        members,
      });
    }
  }
  duplicateFingerprints.sort((a, b) => b.count - a.count);

  // 7. high_pf_low_trades
  const highPfLowTrades = allResults
    .filter(r => r.profit_factor !== null && r.total_trades !== null && r.profit_factor > 1.5 && r.total_trades < 30)
    .map(r => ({
      id: r.id, variant: r.variant, profit_factor: r.profit_factor,
      total_trades: r.total_trades, day: r.day,
    }));

  // 8. regime_single_regime_profitable
  const regimeSingleRegimeProfitable = [];
  for (const r of allResults) {
    const rpf = r.regime_pf || {};
    const vals = { trending: rpf.trending, ranging: rpf.ranging, transitional: rpf.transitional };
    const nonNull = {};
    for (const [k, v] of Object.entries(vals)) {
      if (v !== null && v !== undefined) nonNull[k] = v;
    }
    if (Object.keys(nonNull).length < 2) continue;
    for (const [regimeName, regimeVal] of Object.entries(nonNull)) {
      if (regimeVal > 1.0) {
        const others = {};
        for (const [k, v] of Object.entries(nonNull)) {
          if (k !== regimeName) others[k] = v;
        }
        if (Object.keys(others).length > 0 && Object.values(others).every(v => v < 0.9)) {
          regimeSingleRegimeProfitable.push({
            id: r.id, variant: r.variant, day: r.day,
            profitable_regime: regimeName,
            profitable_regime_pf: regimeVal,
            other_regime_pfs: others,
          });
          break;
        }
      }
    }
  }

  // 9. extreme_dd
  const extremeDd = allResults
    .filter(r => r.max_drawdown_pct !== null && r.max_drawdown_pct > 100)
    .map(r => ({
      id: r.id, variant: r.variant, max_drawdown_pct: r.max_drawdown_pct, day: r.day,
    }));

  // Build output
  const output = {
    total_count: dayCounts,
    all_results: allResults,
    overfit_suspects: overfitSuspects,
    zero_trade: zeroTrade,
    data_quality_issues: dataQualityIssues,
    duplicate_fingerprints: duplicateFingerprints,
    high_pf_low_trades: highPfLowTrades,
    regime_single_regime_profitable: regimeSingleRegimeProfitable,
    extreme_dd: extremeDd,
  };

  const outPath = path.join(os.tmpdir(), 'audit_results.json');
  fs.writeFileSync(outPath, JSON.stringify(output, null, 2), 'utf-8');

  console.log(`\nOutput written to: ${outPath}`);
  console.log(`\n--- SUMMARY ---`);
  console.log(`Total backtests:                    ${allResults.length}`);
  for (const day of DAYS) {
    console.log(`  ${day}:                           ${dayCounts[day] || 0}`);
  }
  console.log(`Overfit suspects:                   ${overfitSuspects.length}`);
  console.log(`Zero-trade results:                 ${zeroTrade.length}`);
  console.log(`Data quality issues:                ${dataQualityIssues.length}`);
  console.log(`Duplicate fingerprint groups:       ${duplicateFingerprints.length}`);
  const dupMemberTotal = duplicateFingerprints.reduce((s, g) => s + g.count, 0);
  console.log(`  (total members in dup groups):    ${dupMemberTotal}`);
  console.log(`High PF + low trades (PF>1.5,<30):  ${highPfLowTrades.length}`);
  console.log(`Single-regime profitable:           ${regimeSingleRegimeProfitable.length}`);
  console.log(`Extreme drawdown (>100%):           ${extremeDd.length}`);

  // Top overfit suspects
  if (overfitSuspects.length > 0) {
    console.log(`\n--- TOP 10 OVERFIT SUSPECTS (by PF) ---`);
    const top = [...overfitSuspects].sort((a, b) => b.profit_factor - a.profit_factor).slice(0, 10);
    top.forEach((s, i) => {
      console.log(`  ${i + 1}. ${s.id} | PF=${s.profit_factor.toFixed(4)} | trades=${s.total_trades} | WR=${s.win_rate.toFixed(4)} | reasons=${JSON.stringify(s.reasons)}`);
    });
  }

  // Top duplicate fingerprint groups
  if (duplicateFingerprints.length > 0) {
    console.log(`\n--- TOP 5 DUPLICATE FINGERPRINT GROUPS ---`);
    duplicateFingerprints.slice(0, 5).forEach((g, i) => {
      const fp = g.fingerprint;
      console.log(`  ${i + 1}. PF=${fp.profit_factor} trades=${fp.total_trades} WR=${fp.win_rate} -> ${g.count} members`);
      g.members.slice(0, 3).forEach(m => {
        console.log(`       - ${m.id} (${m.variant}) [${m.day}]`);
      });
      if (g.count > 3) {
        console.log(`       ... and ${g.count - 3} more`);
      }
    });
  }

  // Extreme DD
  if (extremeDd.length > 0) {
    console.log(`\n--- EXTREME DRAWDOWN (>100%) ---`);
    const topDd = [...extremeDd].sort((a, b) => b.max_drawdown_pct - a.max_drawdown_pct).slice(0, 10);
    topDd.forEach((d, i) => {
      console.log(`  ${i + 1}. ${d.id} | DD%=${d.max_drawdown_pct.toFixed(2)}% | variant=${d.variant}`);
    });
  }

  // Single-regime profitable
  if (regimeSingleRegimeProfitable.length > 0) {
    console.log(`\n--- TOP 10 SINGLE-REGIME PROFITABLE ---`);
    regimeSingleRegimeProfitable.slice(0, 10).forEach((r, i) => {
      console.log(`  ${i + 1}. ${r.id} | ${r.profitable_regime} PF=${r.profitable_regime_pf.toFixed(4)} | others=${JSON.stringify(r.other_regime_pfs)}`);
    });
  }
}

main();
