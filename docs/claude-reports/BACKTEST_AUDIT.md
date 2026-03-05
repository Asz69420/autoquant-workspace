# Backtest Quality Audit — 2026-03-06 (Update 7)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** 2,242 backtests across 20260305 (2,122) and 20260306 (120)
**Prior audit:** 2026-03-05 Update 6 (931 backtests, 788 zero-trade, 6 CRITICALs)

---

## Summary

**2,242 backtests reviewed. 2,221 zero-trade (99.06%). 0 new ACCEPTs. 3 overfit suspects. 7 CRITICALs.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 3 suspects (all MODERATE — structural to R:R design) | MODERATE |
| Data Quality | 2,221 zero-trade (99.06%), 2 duplicate pairs, 120 gate bypasses | CRITICAL |
| Regime Bias | 0 new flags — all profitable strategies are all-regime | CLEAN |
| Pipeline Health | 2,221/2,242 pipeline+directive backtests = 0 trades (99.06%) | CRITICAL |

**Key numbers:**
- Zero-trade results: **2,221 of 2,242** (99.06%)
- Mar 6 zero-trade: **120/120 (100%)** — all BTC 1h directive specs
- Mar 5 zero-trade: **2,101/2,122 (99.01%)** — SOL 100%, BTC 98.7%, ETH 98.4%
- Pipeline zero-trade streak: **2,221+** (138 prior + 2,083 new pipeline runs)
- Non-zero-trade results: **21** (all Claude-designed specs, all Mar 5)
- Accept-worthy candidates: **3** (all Vortex Transition re-runs on updated data)
- New ACCEPT strategies discovered: **0**
- Prior audit CRITICALs fixed: **0 of 6** (now 7th consecutive audit)

---

## Overfit Suspects

### A. Profit Concentration (Top-5 Trade Dominance)

Full trade-list analysis was performed on all 3 strategies with PF > 1.5:

| Strategy | Asset/TF | PF | Trades | Win Rate | Top 1 % Gross | Top 5 % Gross | PF w/o Top 2 (est.) | Flag |
|---|---|---|---|---|---|---|---|---|
| Vortex v3a | ETH 4h | 1.959 | 85 | 20.0% | 22.7% | **68.1%** | ~1.15 | MODERATE |
| Vortex v2c | ETH 4h | 1.868 | 84 | 25.0% | 22.4% | **70.6%** | ~1.10 | MODERATE |
| Vortex v3b | ETH 4h | 1.861 | 84 | 25.0% | ~20% | **~68%** | ~1.12 | MODERATE |

**Assessment:** All 3 are the same Vortex Transition mechanism with different stop/TP parameters — they should be treated as 1 strategy family, not 3 independent validations. The top 5 winning trades are shared across all variants:

| Date | Side | Regime | Approx PnL (v3a) |
|---|---|---|---|
| 2026-01-29 | Short | Transitional | $3,604 (22.7%) |
| 2025-11-03 | Short | Trending | $2,176 (13.7%) |
| 2025-08-07 | Long | Ranging | $1,944 (12.3%) |
| 2024-11-06 | Long | Trending | $1,763 (11.1%) |
| 2024-11-21 | Long | Ranging | $1,304 (8.2%) |

These correspond to major ETH moves (Trump rally Nov 2024, Aug 2025 surge, Nov 2025 crash, Jan 2026 crash). The strategy captures genuine macro reversals, not noise. Removing the top 2 trades still leaves all variants profitable (PF ~1.10-1.15). **Verdict: structural to 8:1+ R:R design, not curve-fitting. Forward-test essential.**

### B. PF > 2.0 with < 30 Trades

**None found.** Highest PF (1.959) has 85 trades.

### C. Win Rate > 70% on Trend-Following

**None found.** All strategies have win rates 10-27%, consistent with high-R:R tail-harvesting design.

---

## Data Quality Issues

### 1. CRITICAL: 2,221 Zero-Trade Backtests (99.06%)

| Date | Total | Zero-Trade | Rate | Root Cause |
|---|---|---|---|---|
| 20260305 | 2,122 | 2,101 | 99.01% | Pipeline natural-language specs (ALL assets) |
| 20260306 | 120 | **120** | **100%** | Pipeline directive specs (ALL BTC 1h) |
| **Total** | **2,242** | **2,221** | **99.06%** | |

**Breakdown by asset (Mar 5):**

| Asset | Total | Zero-Trade | Rate |
|---|---|---|---|
| ETH | 911 | 896 | 98.4% |
| SOL | 904 | **904** | **100%** |
| BTC | 307 | 303 | 98.7% |

**Breakdown by timeframe:**

| Timeframe | Total (both days) | Zero-Trade | Rate |
|---|---|---|---|
| 1h | 1,222 | 1,216 | 99.5% |
| 4h | 1,020 | 1,005 | 98.5% |

**Mar 6 root cause:** All 120 backtests are pipeline-generated directive specs running against BTC 1h exclusively. Entry rules contain natural-language: `"Require candidate signal confidence >= 0.60"`, `"Use signal: alignment_entry"`. These are not valid dataframe column references. 60 `directive_baseline_retest` + 60 `directive_variant_1_template_switch` variants, all producing identical zero results.

### 2. CRITICAL: SOL Complete Failure — 904 Backtests, 0 Trades

SOL has never produced a single trade across 904 backtest runs on Mar 5. Whatever conditions the pipeline specs use, they are structurally incompatible with SOL price action. This asset should be pipeline-excluded.

### 3. CRITICAL: Pipeline Zero-Trade Streak = 2,221+

The directive loop has now produced **2,221+ consecutive zero-trade backtests** across 2 days (Mar 5-6) with no circuit-breaker. Combined with the 138 from the prior audit window, the total streak exceeds **2,300+**.

### 4. CRITICAL: Claude Specs Not Backtested (Mar 6)

6 Claude-authored specs exist in `artifacts/strategy_specs/20260306/` (`claude-almcci01`, `claude-t3vtx01`, `claude-mchtrn01`, `claude-st7m4h2c`, `claude-rc8p5k3w`, `claude-sa6c9n1e`) with **zero corresponding backtest results**. All 120 Mar 6 backtest slots were consumed by directive pipeline specs producing 0 trades. The Claude specs — with 22% historical ACCEPT rate vs pipeline 0% — remain blocked.

### 5. CRITICAL: Gate Bypass (min_trades=0) — 7th Audit

All 120 Mar 6 backtests have `gate_pass: true` with 0 trades. The 1h pathway consistently sets `min_trades=0`, allowing zero-trade results to pass the quality gate. **7th consecutive audit flagging this. Never fixed.**

### 6. HIGH: Duplicate Result Pairs

Two identical-result pairs detected on Mar 5:

| Pair | Specs | Asset/TF | PF | Trades | DD% |
|---|---|---|---|---|---|
| 1 | ema200_vortex_v3_8to1 ↔ v3b_8to1 | ETH 4h | 1.046 | 130 | 25.56% |
| 2 | kama_vortex_div_v1 ↔ v1_10to1 | ETH 4h | 0.000 | 9 | 9.51% |

Pair 1: v3 and v3b naming difference produces no actual logic change at 8:1 R:R. Pair 2: 10:1 R:R variant is identical because all 9 trades hit stop loss (TP never reached).

### 7. LOW: Max Drawdown = 0% with 0 Trades

All 2,221 zero-trade backtests report DD=0.0%. This is correct behavior (no trades = no drawdown), not a bug. No instances of DD=0% with trades > 0.

### 8. LOW: No NaN or Negative Values

All trade counts are valid non-negative integers. No NaN or Inf values in any PF fields.

---

## Regime Analysis

### All Non-Zero Results — Regime Breakdown

| Strategy | Asset/TF | PF | Trending PF | Ranging PF | Transitional PF | Trans Trades | All-Regime? |
|---|---|---|---|---|---|---|---|
| Vortex v3a | ETH 4h | **1.959** | 1.49 | 2.02 | **3.50** | 10 | YES |
| Vortex v2c | ETH 4h | **1.868** | 1.55 | 1.98 | **2.67** | 10 | YES |
| Vortex v3b | ETH 4h | **1.861** | 1.64 | 2.09 | **2.01** | 10 | YES |
| EMA200 Vortex v3 tight | ETH 4h | 1.365 | 1.29 | 1.45 | 1.23 | — | YES (but DD=40%) |
| Supertrend CCI v4 8:1 | ETH 4h | 1.358 | 0.74 | 1.55 | **3.29** | — | NO (trending loss) |
| EMA200 Vortex v3b 10:1 | ETH 4h | 1.358 | 0.57 | 1.75 | **2.30** | — | NO (trending loss) |
| Supertrend CCI v4 default | ETH 4h | 1.290 | 0.56 | 1.99 | **2.78** | — | NO (trending loss) |
| Supertrend CCI v4 tight | ETH 4h | 1.179 | 0.78 | 1.43 | 1.76 | — | NO (trending loss) |
| EMA200 Vortex v3 8:1 | ETH 4h | 1.046 | 0.42 | 1.50 | 1.48 | — | NO (trending loss) |
| EMA200 Vortex v3b 8:1 | ETH 4h | 1.046 | 0.42 | 1.50 | 1.48 | — | DUPLICATE |

### Regime Bias Flags

| Flag | Strategies Affected | Severity |
|---|---|---|
| Trending PF < 0.5 | EMA200 Vortex 8:1 variants (0.42), EMA200 v3b 10:1 (0.57), STCCI default (0.56) | HIGH |
| Transitional small-sample | All trans PF > 2.0 based on 10 or fewer trades | MODERATE |

### Key Regime Findings

1. **Only Vortex Transition family is truly all-regime.** v3a/v2c/v3b are profitable in all 3 regimes (trending 1.49-1.64, ranging 1.98-2.09, transitional 2.01-3.50).

2. **All other profitable strategies bleed in trending.** EMA200 Vortex (trending 0.42-0.57), Supertrend CCI (trending 0.56-0.78). These are ranging/transitional specialists only.

3. **Transitional PF remains small-sample.** Highest trans PF (3.50 for v3a) is based on ~10 trades. Statistically suggestive but not robust.

4. **Winner temporal distribution is clean.** Vortex v3a profits are spread across all 8 quarters of the backtest period (2024-Q2 through 2026-Q1). No quarter exceeds 29% of gross profit. No clustering detected.

5. **BTC is universally unprofitable.** BTC 4h: PF 0.72-0.82 across all Vortex variants. BTC 1h: 1 trade each (meaningless). BTC on Mar 6: 120 backtests, 0 trades.

6. **1h degrades all strategies.** ETH 1h: PF 0.72-0.82 for Vortex family (vs 1.86-1.96 on 4h). Transition-detection signals produce too many false positives at higher frequency.

---

## Pipeline Health Assessment

### Volume Explosion

| Metric | Prior Audit (U6) | This Audit (U7) | Change |
|---|---|---|---|
| Backtests reviewed | 931 | **2,242** | **+141%** |
| Zero-trade results | 788 (84.6%) | **2,221 (99.06%)** | **+182%, rate +14.5pp** |
| Pipeline zero-trade streak | 138+ | **2,300+** | **+17x** |
| Non-zero unique results | ~35 | **21** | **-40%** |
| New ACCEPTs | 0 | 0 | Unchanged |
| Claude specs backtested | ~30 combos | **21** (all re-runs) | **-30%** |
| Claude specs blocked | 6 specs | **6 specs (Mar 6)** | Still blocked |
| Prior CRITICALs fixed | 0 of 5 | **0 of 6** | **7th audit with 0 fixes** |

### Compute Waste

| Source | Backtests | Trades Produced | Unique Non-Zero | ACCEPTs |
|---|---|---|---|---|
| Pipeline/directive specs | ~2,221 | **0** | **0** | 0 |
| Claude specs | 21 | ~1,800+ | 21 | 0 (re-runs of known) |
| **Total** | 2,242 | ~1,800+ | 21 | **0** |

**Pipeline consumed 99.06% of backtest capacity to produce 0% of research output.**

### Mar 6 Monoculture

All 120 Mar 6 backtests: BTC 1h only. No ETH. No 4h. No SOL.
- Worst asset choice: 0 BTC ACCEPTs in 1,000+ outcomes across 33+ cycles
- Worst timeframe choice: All 11 ACCEPTs are 4h; 1h produces universally worse results
- 60 `directive_baseline_retest` + 60 `directive_variant_1_template_switch`
- All produce identical zero results

---

## Recommendations

### CRITICAL (Act Immediately)

| # | Recommendation | Audit History |
|---|---|---|
| 1 | **HALT PIPELINE COMPLETELY.** 2,300+ consecutive zero-trade backtests. Pipeline is architecturally incapable of producing signals. Every backtest slot it consumes is a Claude spec not run. | **7th audit — NEVER FIXED** |
| 2 | **Block natural-language specs at ingestion.** Pre-backtest validator: entry rules must reference valid dataframe columns. Would prevent 2,221+ wasted runs. | **7th audit — NEVER FIXED** |
| 3 | **Fix gate bug: enforce min_trades >= 10 on 1h.** 120+ zero-trade results pass quality gate on Mar 6 alone. | **7th audit — NEVER FIXED** |
| 4 | **Execute 6 blocked Claude specs (Mar 6).** `claude-almcci01`, `claude-t3vtx01`, `claude-mchtrn01`, `claude-st7m4h2c`, `claude-rc8p5k3w`, `claude-sa6c9n1e`. 22% ACCEPT rate vs pipeline 0%. | Escalated from U5 |
| 5 | **Exclude SOL from pipeline.** 904 backtests, 100% zero-trade on Mar 5. No evidence SOL can produce trades with any pipeline spec. | NEW |
| 6 | **Implement pipeline circuit-breaker.** Auto-halt any spec family after 5 consecutive zero-trade results. Would have saved 2,200+ wasted runs. | Escalated from U6 |
| 7 | **Implement post-resolution dedup.** Hash `template + params + asset + timeframe` before scheduling. 2 duplicate pairs found this audit, ~54 triplicates in prior. | **7th audit — NEVER FIXED** |

### HIGH (This Week)

| # | Recommendation | Rationale |
|---|---|---|
| 8 | **Report "PF without top 5 trades" in backtester.** All Vortex family strategies: PF 1.86-1.96 → ~1.10-1.15 without top 2 trades. Auto-expose tail-harvesting fragility. | Carried 4 audits |
| 9 | **Add trending-regime robustness gate.** Block strategies with trending PF < 0.5. EMA200 8:1 (0.42) and Supertrend CCI default (0.56) would be caught. | Carried from U5 |
| 10 | **Report transitional-regime sample sizes.** Flag any regime PF based on < 15 trades. All "record" transitional PFs (3.50, 3.29, 2.78) are from < 12 trades. | Carried from U6 |

### MEDIUM (Next Sprint)

| # | Recommendation | Rationale |
|---|---|---|
| 11 | **Kill refinement engine.** 0% improvement rate across 7 audits. All variant batches produce 0 trades or identical results. | Carried 4 audits |
| 12 | **Remove v2c_btc mislabeled spec.** Still producing duplicate results. | Carried 3 audits |
| 13 | **Tune kama_vortex_div parameters.** 9 trades (1 short of min gate). Template works but signals too rare. | From Advisory U33 |

---

## Escalation Note

**Seven consecutive audits. Six CRITICAL issues. Zero fixed.**

The pipeline has now produced **2,300+ consecutive zero-trade backtests** spanning 3+ days. On March 6, **100% of backtests (120/120) produced zero trades** — all targeting BTC 1h (the worst possible asset/timeframe combination) — while 6 Claude specs sat unexecuted for the second consecutive day.

The scale of waste has increased by an order of magnitude since the prior audit: from 788 zero-trade (U6) to 2,221 zero-trade (U7). The pipeline is consuming **99% of compute capacity to produce 0% of research output**. Meanwhile, the 21 Claude spec runs that did execute on Mar 5 re-confirmed existing strategies (Vortex v3a PF=1.959, v2c PF=1.868, v3b PF=1.861) with no new discoveries because no new Claude specs were tested.

**Every hour the pipeline remains active, ~50+ backtest slots are wasted on specs that cannot produce trades, while novel Claude specs with a 22% ACCEPT rate sit in queue.**

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-06 |
| Audit version | Update 7 |
| Backtests reviewed | 2,242 (2,122 Mar 5 + 120 Mar 6) |
| Trade lists analyzed | 3 (full analysis: v3a 85 trades, v2c 84 trades, v3b 84 trades) |
| Overfit suspects | 3 (all MODERATE — structural to 8:1 R:R, not curve-fitting) |
| Data quality issues | 2,221 zero-trade, 2 duplicate pairs, 120+ gate bypasses, 904 SOL dead |
| Regime bias flags | 0 new (Vortex family confirmed all-regime clean) |
| Pipeline health | DEAD (2,300+ zero-trade streak, 99.06% failure, 99% capacity consumed for 0% output) |
| Critical issues (cumulative) | 7 (halt pipeline, spec validation, gate bug, Claude spec execution, SOL exclude, circuit-breaker, dedup) |
| Prior-audit CRITICALs fixed | **0 of 6** |

*Next audit recommended after any CRITICAL fix is deployed, or in 48 hours, whichever comes first.*
