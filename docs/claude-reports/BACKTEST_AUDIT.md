# Backtest Quality Audit — 2026-03-02 (Update 3)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** 1,556 backtests across 20260301 (1,121) and 20260302 (435)
**Prior advisory context:** STRATEGY_ADVISORY Update 8 (2026-03-02)
**Prior audit:** 2026-03-01 Update 2 (2,621 backtests, 8 issues flagged)

---

## Summary

**1,556 backtests reviewed. 11 issues flagged across 3 categories.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 5 overfit suspects (1 confirmed unprofitable), 3 profit-concentration warnings, 1 time-clustering alert | HIGH |
| Data Quality | 6 distinct issues (gate bug worsening, duplication epidemic, zero-trade acceleration, DD% bug unfixed, BTC leakage, refinement triplication) | CRITICAL |
| Regime Bias | Trending-only overfit cluster, universal Supertrend crash-dependency | MEDIUM |

**Key numbers:**
- Zero-trade results: **129** (8.3%) — 105 on Mar 1, 24 on Mar 2
- Gate bug (min_trades_required=0): **392 results** (25.2%) — worsening from 279 in prior audit
- Duplicate fingerprints: **~600-700 estimated wasted backtests** across both days
- Mar 2 best PF: **1.236** — dramatic collapse from Mar 1 best of 1.921
- Confirmed overfit: `39ec9668` (PF=1.916, 23 trades) — PF drops to **0.83 without top 2 trades**
- Prior audit CRITICALs fixed: **0 of 3**
- Compute waste rate: **~85-90%** (unchanged)

---

## Overfit Suspects

### A. Confirmed Overfit — REJECT

| ID | Date | Variant | PF | Trades | WR% | DD% | Flag | PF w/o Top 2 |
|---|---|---|---|---|---|---|---|---|
| `39ec9668` | 0301 | supertrend_conviction_tight_stop | **1.916** | **23** | 21.7 | 30.4 | PF~2, trades<30, 100% trending, top 1 = 79.5% of net | **0.829** |

**Verdict: REJECT.** This is the clearest overfit in the system. 23 trades over 2 years, all in trending regime, single crash trade ($1,030.73) provides 79.5% of net profit. Without the top 2 winners, the strategy is a net loser (PF=0.83). This should never have passed the gate — it did because of the min_trades_required=0 bug.

### B. Severe Profit Concentration — REVISE WITH CAUTION

| ID | Date | Variant | PF | Trades | Top 2 % of Net | PF w/o Top 2 | Flag |
|---|---|---|---|---|---|---|---|
| `5623e97b` | 0301 | supertrend_tail_harvester_8to1 | **1.921** | 85 | **70.8%** | **1.18** | Crash-dependent, ranging PF=2.91 |
| `54d2de29` | 0301 | supertrend_no_adx_gate_8to1 | **1.907** | 99 | **70.8%** | **1.16** | Same crash trades as above |
| `199a8350` | 0301 | supertrend_ultra_tight_7to1 | **1.878** | 85 | **69.2%** | **1.14** | Same crash trades as above |

**Verdict: REVISE.** These three Supertrend variants share the same two monster crash trades (Oct 2025 $1,178 and Jul 2024 $910). They are not independent strategies — they are the same signal with minor parameter tweaks. The "normal operating" PF (excluding rare crash captures) is only 1.14-1.18. Reported PFs of 1.88-1.92 are misleading. Forward testing is mandatory before promotion.

### C. MACD 1h 7:1 Duplicate Cluster — TIME CLUSTERING ALERT (NEW)

| ID | Date | Variant | PF | Trades | Top 2 % of Net | PF w/o Top 2 | Flag |
|---|---|---|---|---|---|---|---|
| `85409ce4` | 0301 | macd_tight_stop_1h_7to1 | **1.712** | 161 | **44.5%** | **1.21** | 5 identical copies, 7-month trade window |

**Critical finding: All 161 trades occur between Aug 2025 and Feb 2026 — only 7 months.** This means the strategy has ZERO exposure to pre-Aug-2025 market conditions (including the 2024 bull run, early-2025 consolidation, and multiple regime changes). A 7-month window is not a valid multi-cycle test. The PF=1.712 may reflect a regime-specific edge that disappears in different market conditions.

Additionally, this result appears in **5 identical copies** from 4 different strategy specs (macd and rsi_pullback templates producing byte-identical results). 4 of 5 are pure waste.

### D. Template Cross-Contamination — CONFIRMED AND WORSENING

**Mar 1 duplicate clusters:**
- **5-file identical group** (PF=1.712, 161 trades, net=$3,159.62): macd_tight_stop_1h_7to1, macd_tight_stop_4h_7to1, rsi_pullback_1h_tail_harvester_7to1, macd_1h_tail_harvester_7to1, macd_tail_harvester_7to1_4h — from 4 different specs
- **2-file identical pairs**: supertrend_no_adx_gate vs supertrend_ultra_relaxed (PF=1.907), supertrend_tail_harvester vs supertrend_ultra_tight (PF=1.878)

**Mar 2 duplicate clusters:**
- **3x triplication**: Every result from refine-da59d822, refine-ee162da7, refine-2f949828 produces identical output per variant name. The top 9 results are 3 unique sets tripled. The entire Mar 2 refinement batch produces ~3x redundant compute.
- **Estimated unique results in Mar 2: ~145 of 435 (33%)** — 67% waste from duplication alone.

### E. Mar 2 Best Performers — MARGINAL AT BEST

| ID | Date | Variant | PF | Trades | WR% | DD% | Net | Flag |
|---|---|---|---|---|---|---|---|---|
| `058c0178` | 0302 | directive_variant_1_exit_change_exploit_6 | **1.236** | 117 | 37.6 | **95.4** | $1,677 | Triplicate, DD near-total |
| `0d3b8a53` | 0302 | directive_variant_1_exit_change_exploit_3 | **1.209** | 121 | 38.0 | **94.1** | $1,470 | Triplicate, DD near-total |
| `4f6e8aaa` | 0302 | directive_variant_1_exit_change_exploit_5 | **1.185** | 126 | 39.7 | **134.9** | $1,228 | Triplicate, DD exceeds account |

**Verdict: REJECT ALL.** Despite being the best PFs in the Mar 2 batch, these strategies have drawdowns of 94-135% — meaning the account would be liquidated before reaching profitability. Even the "best" Mar 2 result ($1,677 over 2 years with 95% DD) is not deployable. All three results are tripled across 3 refine specs.

---

## Data Quality Issues

### 1. CRITICAL: Gate Bypass Bug (min_trades_required=0) — 3RD AUDIT, STILL UNFIXED

| Date | Affected | % of Daily Total | Trend |
|---|---|---|---|
| 20260228 | 119 | ~6% | Baseline |
| 20260301 (prior audit) | 160 | ~8% | Worsening |
| 20260301 (this audit) | **267** | **23.8%** | Surging |
| 20260302 | **125** | **28.7%** | Worst rate ever |
| **Cumulative** | **392** | **25.2%** | **Accelerating** |

**Impact:** Zero-trade results pass gate. Overfit results with 10-23 trades promoted. The confirmed overfit `39ec9668` (PF=1.916, 23 trades, 100% trending, PF→0.83 without top 2) passed gate specifically because of this bug.

**Root cause:** ETH/1h and claude-spec backtest pathways do not set min_trades_required. The BTC/4h pathway correctly sets it to 10.

### 2. CRITICAL: Duplication Epidemic — WORST EVER

| Date | Estimated Unique | Total | Waste Rate |
|---|---|---|---|
| 20260228 (prior audit) | ~13% unique | ~450 | ~87% |
| 20260301 | ~40% unique (~450) | 1,121 | ~60% |
| 20260302 | ~33% unique (~145) | 435 | ~67% |
| **Combined** | ~595 unique | 1,556 | **~62%** |

**New finding (Mar 2):** The refinement loop produces exact triplicates — 3 refine specs generate identical variant results. This is a NEW duplication source beyond the known template-resolution convergence. The refinement specs themselves are insufficiently diverse.

### 3. HIGH: Zero-Trade Results Accelerating

| Date | Zero-Trade Count | % of Daily Total |
|---|---|---|
| 20260227 | 3 | ~0.2% |
| 20260228 | 54 | ~6% |
| 20260301 | **105** | **9.4%** |
| 20260302 | 24 | 5.5% |

Mar 1 shows the highest absolute count (105). Mar 2 is lower in percentage but still present. All zero-trade results on Mar 1 pass the gate due to the min_trades_required=0 bug.

### 4. MEDIUM: DD% Calculation Bug — 3RD AUDIT, STILL UNFIXED

**317 results** on Mar 1 report `max_drawdown_pct: 0.0` despite real drawdowns up to $73,427 in absolute terms. Any DD%-based gating is completely broken. This has been flagged for 3 consecutive audits.

### 5. MEDIUM: BTC Leakage Continues — 9TH ADVISORY + 3RD AUDIT

| Date | BTC Results | % of Total | Best BTC PF |
|---|---|---|---|
| 20260301 | ~267 | 23.8% | PF < 1.1 (all) |
| 20260302 | ~125 | 28.7% | PF = 1.001 (noise) |

BTC consumes 24-29% of compute with zero viable results. Advisory has recommended hard-excluding BTC for 8+ cycles. BTC's best result on Mar 2 is PF=1.001 (breakeven) with DD=217%.

### 6. NEW: Refinement Loop Triplication

Three refine specs (refine-da59d822, refine-ee162da7, refine-2f949828) produce **byte-identical results** for every variant. This means:
- 42 refinement results on Mar 2 → only 14 unique
- ~28 wasted backtests from refinement triplication alone
- The refinement loop's mutation mechanism is non-functional — it generates spec metadata changes that don't affect resolved template parameters

---

## Regime Analysis

### Regime Distribution in Top Performers

| ID | Variant | PF | Trades | Trending | Ranging | Trans. | Regime Flag |
|---|---|---|---|---|---|---|---|
| `39ec9668` | supertrend_conviction_tight | 1.92 | 23 | **23 (100%)** | 0 | 0 | **EXTREME BIAS — OVERFIT** |
| `5623e97b` | supertrend_tail_harvester_8to1 | 1.92 | 85 | 33 (39%) | 31 (36%) | 21 (25%) | Balanced |
| `54d2de29` | supertrend_no_adx_gate_8to1 | 1.91 | 99 | 33 (33%) | 45 (45%) | 21 (21%) | Balanced |
| `199a8350` | supertrend_ultra_tight_7to1 | 1.88 | 85 | 33 (39%) | 31 (36%) | 21 (25%) | Balanced |
| `85409ce4` | macd_tight_stop_1h_7to1 | 1.71 | 161 | 37 (23%) | 78 (48%) | 46 (29%) | Balanced |
| `058c0178` | exit_change_exploit_6 | 1.24 | 117 | ~40% | ~35% | ~25% | Balanced but trans PF=0.64 |

### Regime PF Breakdown

| Variant | Trending PF | Ranging PF | Transitional PF | Edge Source |
|---|---|---|---|---|
| supertrend_conviction_tight | 1.92 | N/A | N/A | Trending-only overfit |
| supertrend_tail_harvester_8to1 | 1.29 | **2.91** | 1.84 | Ranging crash captures |
| supertrend_no_adx_gate_8to1 | 1.29 | **2.56** | 1.84 | Ranging crash captures |
| supertrend_ultra_tight_7to1 | 1.29 | **2.95** | 1.61 | Ranging crash captures |
| macd_tight_stop_1h_7to1 | 1.68 | **2.06** | 1.31 | Ranging dominance |
| exit_change_exploit_6 | 1.38 | 1.33 | **0.64** | Trending only |

### Key Regime Findings

1. **The Supertrend "tail harvester" family is a crash-capture strategy, not a trend-follower.** Despite using a trend-following signal (Supertrend), the highest PF comes from ranging regime (2.56-2.95). The strategy profits by catching range breakdowns — sharp drops within established ranges — not from trend continuations. This is a valid edge but must be understood as crash insurance, not continuous alpha.

2. **All Supertrend variants share the same crash events.** The Oct 2025 and Jul 2024 crashes produce $910-$1,178 winning trades across ALL Supertrend variants. These are the same 2 market events captured with slightly different parameters. Running 3-5 variants of the same crash-capture strategy does not provide diversification.

3. **Transitional regime toxicity is R:R-dependent (confirmed).** Exit_change_exploit_6 (low R:R) shows transitional PF=0.64 (toxic). Supertrend 8:1 (high R:R) shows transitional PF=1.84 (profitable). This confirms the prior audit finding: wide R:R strategies survive transitional regimes that destroy narrow R:R strategies.

4. **Mar 2 results show NO regime differentiation.** Pipeline results cluster at PF~1.03 across all regimes. Parameter convergence eliminates regime-specific edge.

---

## Comparison With Prior Audit

| Metric | Update 2 (2026-03-01) | Update 3 (2026-03-02) | Trend |
|---|---|---|---|
| Backtests reviewed | 2,621 | 1,556 | Smaller window (48h vs 72h) |
| Zero-trade variants | 138 (5.3%) | 129 (8.3%) | Rate worsening |
| Gate bug (min_trades=0) | 279 | **392** | **+40% — accelerating** |
| Duplicate rate | ~50-60% | ~62% | **Worsening** |
| Overfit suspects | 6 | 5 (1 confirmed) | 1 confirmed unprofitable |
| DD% bug | 60+ records | **317+ records** | **5x more records affected** |
| stochastic/bollinger templates | Removed | Removed | Fixed (stable) |
| directive_exploration | 45 (0301) | Still present | Unfixed |
| BTC leakage | 5+ results | **~392 results** | **Massively worsening** |
| Best PF (new data) | 1.921 (0301) | **1.236** (0302) | **Collapsed on Mar 2** |
| Prior CRITICALs fixed | 0 of 2 | **0 of 3** | **Zero progress** |

**Net assessment:** All three prior-audit CRITICAL findings remain unaddressed (gate bug, DD% bug, dedup). A new CRITICAL has emerged (refinement triplication). The Mar 2 batch shows dramatic quality degradation — best PF fell from 1.921 to 1.236, and 67% of results are duplicates. The only positive signal is the continued absence of dead templates (stochastic/bollinger).

---

## Recommendations

### CRITICAL (Act This Cycle)

| # | Recommendation | Rationale | Audit History |
|---|---|---|---|
| 1 | **Fix gate bug: min_trades_required=0** | 392 results bypass quality gate across 2 days. Zero-trade and 23-trade overfits pass as OK. Worsening every cycle. | **3rd audit — NEVER FIXED** |
| 2 | **Implement post-resolution dedup** | ~62% of compute is duplicate results. Mar 2 refinement triplication adds a new source. Hash resolved template params, not spec-level strings. | **3rd audit — NEVER FIXED** |
| 3 | **Reject confirmed overfit 39ec9668** | PF=1.916 with 23 trades is a fraud — PF drops to 0.83 without top 2 trades. 100% trending regime. Single crash trade = 79.5% of net. | **NEW — confirmed via trade list** |
| 4 | **Flag MACD 1h 7:1 time clustering** | 161 trades in only 7 months (Aug 2025 - Feb 2026). Not a valid multi-cycle test. PF=1.712 may be regime-specific, not persistent. | **NEW — discovered this audit** |

### HIGH (Act Within 2 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 5 | **Add top-N profit concentration check** | Auto-flag when top 2 trades > 50% of net PnL. Would catch all 4 Supertrend "top performers" and the overfit. Simple addition: compute `sum(sorted_pnl[-2:]) / net_pnl` in backtester. |
| 6 | **Fix DD% calculation bug** | max_drawdown_pct=0.0 for 317+ records with real $10K-$99K drawdowns. 3rd audit cycle flagging. |
| 7 | **Kill directive_exploration and all directive variants** | 653 directive variants on Mar 1 (58% of batch), 345 on Mar 2 (79%). Best ever PF from any directive variant: 1.236 with 95% DD (non-deployable). 10th advisory cycle flagging. |
| 8 | **Hard-exclude BTC** | 267 BTC results on Mar 1, 125 on Mar 2. Zero viable results. Best BTC PF = 1.001. 9th advisory cycle requesting. |
| 9 | **Fix refinement triplication** | 3 refine specs produce identical output. Refinement mutations don't affect resolved parameters. Either fix mutation diversity or dedup at spec emission. |

### MEDIUM (Act Within 5 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 10 | **Require minimum 12-month trade window** | MACD 1h 7:1's 7-month window is insufficient for regime validation. Reject backtests where first-to-last trade span < 12 months. |
| 11 | **Report "PF without top 2" in backtester output** | Trivial computation that instantly exposes crash-dependent results. Would have caught all 5 overfit suspects automatically. |
| 12 | **Cap sentinel regime_pf values** | Replace PF=999.0 with NaN when regime trade count < 3. Still unfixed from prior audit. |
| 13 | **Add regime entropy gate** | Reject variants where 100% of trades in single regime. Catches trending-only overfits automatically. Would have rejected 39ec9668. |
| 14 | **Validate Supertrend crash-dependency thesis** | All Supertrend PF>1.5 results depend on 2 crash events. Forward-test 4+ weeks to verify the strategy survives between crash captures. |

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-02 |
| Audit version | Update 3 |
| Backtests reviewed | 1,556 |
| Date range | 20260301–20260302 |
| Trade lists analyzed | 6 (top performers + Mar 2 best) |
| Overfit suspects | 5 (1 confirmed, 3 severe concentration, 1 time clustering) |
| Data quality issues | 392 (gate) + 129 (zero-trade) + ~960 (dupes) + 317 (DD% bug) + ~392 (BTC leak) + 28 (refine triplication) |
| Regime bias flags | 1 (100% trending overfit) + 3 (crash-dependent concentration) |
| Critical issues | 4 (gate bug, dedup, confirmed overfit, time clustering) |
| High issues | 5 (profit concentration check, DD% bug, directive variants, BTC exclusion, refinement triplication) |
| Medium issues | 5 (trade window minimum, PF-without-top-2, sentinel values, regime entropy, crash-dependency validation) |
| Prior-audit CRITICALs fixed | **0 of 3** |
| Advisory directives actioned (cumulative) | 2 of 20+ (stochastic + bollinger removal only) |

---

## Escalation Note

**Three consecutive audits have flagged the gate bug (min_trades_required=0) as CRITICAL. It has worsened from 24 → 279 → 392 affected results. Zero action taken. This bug directly caused the promotion of a confirmed overfit (39ec9668, PF→0.83 without top 2 trades) and allows zero-trade results to pass quality gates. If this bug is not fixed before the next pipeline cycle, this audit recommends halting pipeline execution until the fix is deployed — running more backtests with a broken gate is worse than running none.**

*Next audit recommended after gate bug fix is deployed, or in 48 hours, whichever comes first.*
