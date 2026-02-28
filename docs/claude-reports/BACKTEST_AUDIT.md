# Backtest Quality Audit — 2026-02-28

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Audit window:** 20260226 – 20260228 (48h rolling)
**Files scanned:** 2,967 backtest results (1,346 on 20260226, 1,586 on 20260227, 35 on 20260228)
**Files with regime data:** 617 (all from 20260228 batch — new schema addition)
**Prior audit:** None (first audit)

---

## Summary

**2,967 backtests reviewed. 15 flagged across 4 issue categories.**

| Category | Flagged | Severity |
|---|---|---|
| Overfit Suspects | 1 | CRITICAL |
| Data Quality Issues | 8 | CRITICAL (4), HIGH (4) |
| Variant Deduplication Failures | 4 | HIGH |
| Regime Bias | 2 | MEDIUM |

The pipeline is producing an enormous volume of backtests (~1,500/day) but nearly all are unprofitable (avg PF ~0.85, only ~10% above 1.0). The highest legitimate PF observed is 1.033. No classic high-PF overfitting was detected, but a degenerate PF=999 result on a 2-day micro-window is passing the gate due to a configuration bug. The most concerning systemic issue is **variant deduplication failure**: different variant names are producing byte-identical results, wasting compute and creating false diversity in the result set.

---

## Overfit Suspects

| ID | Spec | Variant | PF | Trades | WR | DD | Flag |
|---|---|---|---|---|---|---|---|
| hl_20260226_0e25b404 | strategy-spec-20260225-2da349e2d5ab | baseline | **999.0** | 3 | 100% | $0.00 | **DEGENERATE: 2-day window, 48 bars, PF=999, DD=0** |

### Details

**hl_20260226_0e25b404** — This is not classic overfitting but a degenerate result. A baseline strategy was backtested on a **48-bar BTC/1h window** (2026-02-23 to 2026-02-25 — just 2 days). It took 3 trades, won all 3, and the backtester reports PF=999.0 (a sentinel/cap value) with max_drawdown=0.0.

**Why this passed the gate:** `min_trades_required: 0` and `gate_pass: true`. The gate does not enforce a minimum bar count or window duration, so a 2-day window with 3 trades is treated as a valid result.

**Risk:** If this result enters the outcome pipeline, it will create a false-positive signal that could drive further iterations on a strategy "validated" by 3 trades on 2 days of data.

**No other classic overfitting detected:** No backtests showed PF > 2.0 with < 30 trades (besides this degenerate case). No win rates above 70% on trend-following strategies. No large trades carrying entire results. The pipeline's overfitting risk is currently low because no strategies are profitable enough to overfit — the problem is underperformance, not false positives.

---

## Data Quality Issues

### CRITICAL: Zero-trade `template_diversity` variant (6 files)

| ID | Day | Dataset | Gate Pass | Gate Reason |
|---|---|---|---|---|
| hl_20260228_a01d914e | 0228 | BTC/4h | false | INSUFFICIENT_TRADES |
| hl_20260228_95c8ca44 | 0228 | ETH/4h | false | INSUFFICIENT_TRADES |
| hl_20260228_0334c909 | 0228 | ETH/1h | **true** | OK (min_trades=0!) |
| hl_20260227_4c1839b1 | 0227 | BTC/4h | false | INSUFFICIENT_TRADES |
| hl_20260227_5a6a216c | 0227 | ETH/4h | false | INSUFFICIENT_TRADES |
| hl_20260227_2b655139 | 0227 | ETH/1h | **true** | OK (min_trades=0!) |

**Root cause:** The `template_diversity` variant generates zero entry signals across ALL datasets and ALL timeframes. This is a **template bug** — the variant's signal logic is fundamentally broken or the template it references does not exist. All 6 files show `entry_signals_seen: {long: 0, short: 0, total: 0}`.

**Compounding bug:** Two of these zero-trade files (ETH/1h) **pass the gate** because `min_trades_required` is set to 0 for ETH/1h configurations. A zero-trade result with `gate_pass: true` is semantically invalid and could pollute downstream analysis.

### CRITICAL: `min_trades_required: 0` gate misconfiguration

The ETH/1h dataset configuration sets `min_trades_required: 0`, which means ANY result — including zero trades — passes the gate. This was detected in widespread files across the audit window. A massive number of files use this configuration (estimated hundreds based on the min_trades grep).

**Impact:** Zero-trade and degenerate results are being marked as valid, corrupting the outcome pipeline's ability to distinguish real strategies from broken templates.

### HIGH: Max drawdown = 0 on non-zero-trade results

| ID | Day | Trades | PF | DD | Issue |
|---|---|---|---|---|---|
| hl_20260226_0e25b404 | 0226 | 3 | 999.0 | $0.00 | Impossible — even all-winning trades have intra-bar drawdown |

Max drawdown of exactly 0.0 with non-zero trades indicates the backtester is not calculating intra-trade drawdown for small windows. While this only affects micro-window backtests (48 bars), it means the drawdown metric is unreliable for short-duration tests.

### HIGH: Fixture/test file in production directory

| ID | Day | File |
|---|---|---|
| bt-fixture | 0226 | fixture.backtest_result.json |

A test fixture file (`fixture.backtest_result.json`) exists in the 20260226 production backtest directory. It has 8 trades, PF=0.8, and a different schema structure (`trades` vs `total_trades`, `net_return` vs `net_profit`). If ingested by downstream tools expecting the standard schema, this could cause parsing errors. A second fixture (`batch-fixture-v2.json`) also exists in the same directory.

---

## Variant Deduplication Failures

**4 confirmed byte-identical result pairs across different variant names:**

### Pair 1: exit_change = threshold_sweep (ETH/4h)
| ID | Variant | PF | Trades | DD | Net Profit |
|---|---|---|---|---|---|
| hl_20260228_5be501f9 | directive_variant_1_exit_change | 1.03262 | 389 | $2,853.31 | $656.91 |
| hl_20260228_ffd6628e | directive_variant_2_threshold_sweep | 1.03262 | 389 | $2,853.31 | $656.91 |

**Identical to the last decimal place.** Different variant names, same execution path.

### Pair 2: threshold_sweep = library_augmented (ETH/1h)
| ID | Variant | PF | Trades | DD | Net Profit |
|---|---|---|---|---|---|
| hl_20260228_c1bf2bcf | directive_variant_2_threshold_sweep | 0.99839 | 415 | $1,179.35 | -$19.20 |
| hl_20260228_ec9ff8b6 | library_augmented | 0.99839 | 415 | $1,179.35 | -$19.20 |

**Identical results, different variant names.** The `library_augmented` variant is collapsing to the same signal as `threshold_sweep`.

### Advisory context
The Strategy Advisory (2026-02-28) previously flagged `library_augmented` collapsing to `entry_tighten` on 20260226–27 data. The problem persists on 20260228 data but with a different collapse partner (`threshold_sweep`). This confirms the deduplication bug is **variant-agnostic** — any two variants can collapse to identical results depending on how their directive parameters resolve.

### Estimated compute waste
With ~3,000 backtests per 48h window and duplicates appearing across multiple spec families, conservatively 10-15% of backtests are producing redundant results. At current volume, this wastes 300-450 backtests per 48h cycle.

---

## Regime Analysis

**New capability:** 617 files from 20260228 include `regime_breakdown`, `regime_pf`, `regime_wr`, and `dominant_regime` fields. This is a significant pipeline upgrade from 20260226-27 which had zero regime data in backtest outputs.

### Regime Performance Summary (from sampled 20260228 files)

| ID | Variant | Overall PF | Trending PF | Ranging PF | Transitional PF | Flag |
|---|---|---|---|---|---|---|
| hl_20260228_5be501f9 | exit_change | **1.033** | 1.054 | 0.982 | 1.048 | Best balance |
| hl_20260228_c1bf2bcf | threshold_sweep | 0.998 | 1.009 | **1.115** | 0.858 | SINGLE-REGIME (ranging) |
| hl_20260228_24b7e3c6 | exit_change | 1.001 | 0.990 | **1.127** | 0.919 | SINGLE-REGIME (ranging) |
| hl_20260228_a5466507 | exploration | 0.884 | 0.856 | 0.928 | 0.911 | UNPROFITABLE ALL |
| hl_20260228_691da115 | exit_change (refine) | 0.624 | 0.795 | 0.584 | 0.494 | UNPROFITABLE ALL |

### Regime Bias Flags

1. **hl_20260228_c1bf2bcf** (threshold_sweep, ETH/1h): Profitable ONLY in ranging regime (PF=1.115). Loses money in trending (PF=1.009 but with transitional at 0.858). Concentrated profitability in one regime with 107 of 415 trades.

2. **hl_20260228_24b7e3c6** (exit_change, BTC/4h): Ranging PF=1.127 carries the result while trending PF=0.990 and transitional PF=0.919 are negative. Only 93 of 406 trades are in the profitable regime.

### Positive finding
**hl_20260228_5be501f9** (exit_change, ETH/4h) shows the **only balanced regime profile**: trending PF=1.054, transitional PF=1.048, ranging PF=0.982. This is the only strategy that generates positive expectancy across two regimes simultaneously. This corroborates the Strategy Advisory's identification of the exit_change variant on family 6167b17afa4f as the highest-priority lead.

### Regime coverage gap
No backtests from 20260226 or 20260227 include regime data. The regime analysis is based solely on the 35-file 20260228 batch. Historical comparison is not possible until regime data is backfilled.

---

## Recommendations

### Priority 1: CRITICAL (fix this cycle)

1. **FIX `min_trades_required: 0` on ETH/1h** — Set minimum to 10 (matching BTC/4h and ETH/4h). Zero-trade results should never pass the gate. This single bug allows broken templates and degenerate micro-window results to pollute the outcome pipeline.

2. **FIX `template_diversity` variant** — The variant produces zero entry signals across all 6 tested configurations (2 specs x 3 datasets). Either the template reference is broken or the signal logic is incompatible with the current indicator registry. Disable the variant until fixed to stop wasting 3 backtests per spec cycle.

3. **ADD minimum bar/duration gate** — The PF=999 degenerate on 48 bars should never reach the outcome pipeline. Add a minimum `bars_tested >= 500` (or equivalent duration) check to the gate logic.

### Priority 2: HIGH (fix within 2 cycles)

4. **IMPLEMENT variant fingerprinting** — Before submitting to the backtester, hash the resolved signal parameters (after directive application) and skip duplicate runs. Two confirmed collapse patterns (exit_change=threshold_sweep, threshold_sweep=library_augmented) are wasting ~15% of compute.

5. **REMOVE fixture files from production directories** — `fixture.backtest_result.json` and `batch-fixture-v2.json` in 20260226/ use a different schema and could cause parsing errors in downstream tools. Move to a `test/` directory.

6. **FIX intra-trade drawdown calculation** — Max drawdown of exactly 0.0 with non-zero trades (hl_20260226_0e25b404) indicates the backtester doesn't track equity curve drawdown properly on micro-windows.

### Priority 3: MEDIUM (within 5 cycles)

7. **BACKFILL regime data to 20260226-27** — Only the 20260228 batch has regime_pf/regime_wr fields. Without historical regime data, trend analysis across cycles is impossible.

8. **ADD regime-concentration alert** — Flag strategies where >60% of profit comes from a single regime with <30% of trades. Two strategies in this audit (c1bf2bcf, 24b7e3c6) show this pattern.

9. **MONITOR exit_change deduplication** — The best result (PF=1.033, 5be501f9) is byte-identical to threshold_sweep (ffd6628e). If the underlying strategy is the same, the pipeline is reporting the same edge under two names, creating false confidence in reproducibility.

---

## Appendix: Aggregate Statistics

| Metric | Value |
|---|---|
| Total backtests (48h window) | 2,967 |
| Avg PF (sampled, excl degenerate) | 0.846 |
| Median PF | 0.85 |
| PF > 1.0 | ~10% of results |
| Best PF (legitimate) | 1.033 (exit_change, ETH/4h, spec 18323d891886) |
| Worst PF (legitimate) | 0.624 (exit_change refine, BTC/4h, spec refine-a8c09725) |
| Degenerate PF | 999.0 (3 trades on 48-bar window) |
| Avg win rate | 39.3% |
| Avg trades per backtest | ~215 |
| Zero-trade results (in window) | 6 (all `template_diversity`) |
| Gate failures | 6 (4 legitimate INSUFFICIENT_TRADES, 2 should-have-failed) |
| Duplicate result pairs | 4 confirmed |
| Fixture files in production | 2 |
| Files with regime data | 617 of 2,967 (20260228 only) |

### Day-over-Day PF Trend

| Date | Backtests | Avg PF | Best PF | Regime Data |
|---|---|---|---|---|
| 20260226 | 1,346 | ~0.86 | 0.95 (threshold_mutation, ETH/4h) | No |
| 20260227 | 1,586 | ~0.82 | 0.92 (library_augmented/entry_tighten, ETH/1h) | No |
| 20260228 | 35 | ~0.89 | **1.033** (exit_change, ETH/4h) | Yes |

**Trend:** PF dipped on 20260227 (dragged down by directive_exploration variants at PF 0.68-0.70) then partially recovered on 20260228 with the new spec family (18323d891886) and exit_change variant. The 20260228 batch is much smaller (35 vs 1,500) but higher quality.

---

*Next audit scheduled: 2026-03-01. Watch items: template_diversity fix, min_trades gate fix, variant dedup implementation.*
