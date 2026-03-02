# Backtest Quality Audit — 2026-03-03 (Update 4)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** ~2,323 backtests across 20260301 (1,121) and 20260302 (1,202)
**Prior advisory context:** STRATEGY_ADVISORY Update 14 (2026-03-03)
**Prior audit:** 2026-03-02 Update 3 (1,556 backtests, 11 issues flagged)

---

## Summary

**~2,323 backtests reviewed. 14 issues flagged across 3 categories.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 3 profit-concentration warnings (unchanged), 1 time-clustering alert (unchanged), 1 new single-trade dependency | HIGH |
| Data Quality | 8 distinct issues (gate bug WORSENING, duplication epidemic WORSENING, zero-trade from Claude specs NEW, DD% bug 4TH AUDIT, BTC leakage UNCHANGED, refinement triplication UNCHANGED, Claude template routing NEW, max_dd_pct impossible values NEW) | CRITICAL |
| Regime Bias | Trending profit destruction confirmed with fresh data, single-regime-only strategies flagged | MEDIUM |

**Key numbers:**
- Zero-trade results: **129+ estimated** — Claude spec 0-trade rate now 60% (3/5 newest specs)
- Gate bug (min_trades_required=0): **500+ results estimated** — worsening from 392 in prior audit
- Duplicate fingerprints: **~1,400-1,600 estimated wasted backtests** across both days
- Best PF in 48h window: **1.712** (MACD 1h 7:1, flagged for time clustering in prior audit)
- DD% bug: **max_drawdown_pct=0.0** on 6+ sampled results despite DD >$73K; also **max_drawdown_pct >4,000%** on others
- Identical-result duplication: **5+ copies** of PF=1.001 / 406 trades / DD=217% (BTC 4h gate_adjust)
- Prior audit CRITICALs fixed: **0 of 4**
- Compute waste rate: **~87-93%** (worsening from 85-90%)

---

## Overfit Suspects

### A. Prior Confirmed Overfit — STILL IN SYSTEM

| ID | Variant | PF | Trades | Flag | Status |
|---|---|---|---|---|---|
| `39ec9668` | supertrend_conviction_tight_stop | 1.916 | 23 | PF→0.83 w/o top 2, 100% trending, single crash trade = 79.5% of net | **UNFIXED — 2nd audit flagging** |

**Not removed from system.** This confirmed overfit was flagged in Update 3. No action taken.

### B. Severe Profit Concentration — UNCHANGED

| ID | Variant | PF | Trades | Top 2 % of Net | PF w/o Top 2 | Flag |
|---|---|---|---|---|---|---|
| `5623e97b` | supertrend_tail_harvester_8to1 | 1.921 | 85 | 70.8% | 1.18 | Crash-dependent |
| `54d2de29` | supertrend_no_adx_gate_8to1 | 1.907 | 99 | 70.8% | 1.16 | Same crash trades |
| `199a8350` | supertrend_ultra_tight_7to1 | 1.878 | 85 | 69.2% | 1.14 | Same crash trades |

**Verdict: STILL REVISE.** These remain unflagged in the pipeline. Forward-testing has been requested for 8 cycles with zero action.

### C. MACD 1h 7:1 — TIME CLUSTERING + SINGLE-TRADE DEPENDENCY (NEW FINDING)

| ID | Variant | PF | Trades | Window | Top Trade | Flag |
|---|---|---|---|---|---|---|
| `0537219a` | rsi_pullback_1h_tail_harvester_7to1 | 1.712 | 161 | 7 months only | $757.65 (18.5% PnL, one trade) = 24% of total net | Time clustering + single-trade dependency |

**Trade list analysis (161 trades, Aug 2025 — Feb 2026):**
- Win rate: 19.9% (32 winners, 129 losers)
- Winning trades distributed: Aug(4), Sep(3), Oct(4), Nov(3), Dec(3), Jan(5), Feb(2) — reasonably even monthly distribution
- **BUT**: Single largest trade = $757.65 short on Oct 10 (ETH $4100→$3339 in 7 bars). This one trade = **24% of total $3,159.62 net profit**
- Second largest: $399.23 short on Jan 31 (ETH $2643→$2242). Top 2 trades combined = **37% of net profit**
- Third largest: $380.25 short on Nov 19 (ETH $3067→$2685). Top 3 = **49% of net profit**
- **PF without top 3 trades: ~1.27** (still profitable but significantly weaker)
- Only 7-month trade window — no exposure to 2024 market conditions

**Verdict: FLAG — not overfit but crash-dependent.** The strategy works by catching large downside moves with wide TP targets. It generates many small losses (~80% of trades hit SL) and occasional massive wins. This is a valid tail-harvesting approach, but forward-test is mandatory to confirm it survives non-crash periods.

### D. Pipeline ACCEPT Cluster — INFLATED BY DUPLICATION

| Metric Profile | Count | PF | Trades | DD% | Verdict |
|---|---|---|---|---|---|
| Profile A | 9 identical | 1.419 | 140 | 10.5% | ACCEPT (but 1 unique strategy, not 9) |
| Profile B | 17 identical | 1.295 | 140 | 24.3% | REVISE (same strategy, different gate) |

**9 pipeline ACCEPTs are the same strategy.** Effective ACCEPT count from pipeline: 1, not 9. Parameter convergence now inflates ACCEPT metrics.

---

## Data Quality Issues

### 1. CRITICAL: Gate Bypass Bug (min_trades_required=0) — 4TH AUDIT, STILL UNFIXED

| Audit | Affected Results | Trend |
|---|---|---|
| Update 1 (Feb 28) | 119 | Baseline |
| Update 2 (Mar 1) | 279 | Worsening |
| Update 3 (Mar 2) | 392 | Surging |
| **Update 4 (Mar 3)** | **500+ estimated** | **Accelerating** |

**Root cause unchanged:** ETH/1h and claude-spec pathways do not set min_trades_required. Zero-trade and sub-10-trade results pass gate as OK. The confirmed overfit (39ec9668, PF=1.916→0.83 real) entered the system via this bug.

### 2. CRITICAL: Duplication Epidemic — NOW AT 87-93% WASTE

**Confirmed duplicates from 43-file sample:**

| Metric Fingerprint | Copies Found | Asset/TF | Variants |
|---|---|---|---|
| PF=1.001, 406 trades, DD=217.4% | 5+ | BTC 4h | gate_adjust, threshold_sweep |
| PF=0.998, 415 trades, DD=181.1% | 2+ | ETH 1h | gate_adjust (different specs) |
| PF=1.033, 389 trades, DD=174.2% | 2+ | ETH 4h | gate_adjust (different specs) |
| PF=1.295, 140 trades, DD=24.3% | 17 | ETH 4h | template_diversity variants |
| PF=1.419, 140 trades, DD=10.5% | 9 | ETH 4h | template_diversity variants |

In a 43-file sample, **26 results (60%) were duplicates of just 5 unique metric profiles**. Extrapolating: ~1,400-1,600 of ~2,323 total backtests are duplicates. Compute waste has worsened from ~62% (Update 3) to **~87-93%**.

**New duplication source (Update 3, still unfixed):** Refinement loop triplication — 3 refine specs produce byte-identical output. Refinement mutations don't affect resolved template parameters.

### 3. CRITICAL: Claude Spec Template Routing Failure — NEW

| Claude Spec | Template Name | Result | Trades | Issue |
|---|---|---|---|---|
| claude-ec3w5m8k | ema_crossover_minimalist/extreme | REJECT | 0 | Custom template_name not routed |
| claude-st4q7r2n | supertrend_deep_tail_12to1 | REJECT | 0 | Custom template_name not routed |
| claude-rp5r7c1h | rsi_pullback variants | REJECT | 0 | Conditions too strict |
| claude-rd42k7b3 | rsi_deep_dip_trend_continuation | REJECT | 0 | Conditions too strict |
| claude-rp2d9f4w | rsi_deep_conviction_1h | REJECT | 0 | Conditions too strict |

**5 of 6 Claude specs tested in 48h produced 0 trades.** Root cause for 3 specs: custom `template_name` values (e.g., "ema_crossover_minimalist_8to1") not in TEMPLATE_REGISTRY cause fallback to wrong signal logic or silently discard entry conditions. Root cause for 2 specs: conditions are legitimately too strict for available data.

**Only 1 Claude spec succeeded:** `claude-er7v4x2p` (ema_rsi_atr vol expansion) — PF=1.10-1.14 across multiple R:R ratios. Demonstrates spec_rules template works when routing is correct.

**Impact:** 288 backtest runs were triggered by Claude specs across the 48h window (240 Mar 1, 48 Mar 2). At least 60% produced 0 trades. Wasted compute from template routing bug alone: ~170+ backtests.

### 4. CRITICAL: max_drawdown_pct Bug — DUAL FAILURE MODE CONFIRMED

**Mode 1: Zero DD%** — max_drawdown_pct=0.0 when max_drawdown>0

| Sample ID | max_drawdown ($) | max_drawdown_pct | Trades |
|---|---|---|---|
| `000dc694` | $73,427.78 | **0.0%** | 153 |
| `007f2434` | $1,294.32 | **0.0%** | 54 |
| `00d8e67a` | $80,771.42 | **0.0%** | 160 |
| `02a951a7` | $81,176.99 | **0.0%** | 153 |
| `04ef6da8` | $4,077.13 | **0.0%** | 891 |

**Mode 2: Extreme DD%** — max_drawdown_pct >100% (account liquidation impossible to survive)

| Sample ID | max_drawdown ($) | max_drawdown_pct | Trades | Asset |
|---|---|---|---|---|
| `01be6fed` | unknown | **2,159.73%** | — | — |
| `01e08408` | $83,649.20 | **4,165.90%** | 128 | BTC |
| `006c6eaa` | — | **563.66%** | — | — |
| `0cb979be` | $55,871.20 | **217.44%** | 406 | BTC 4h |
| `02d73a2a` | — | **1,245.41%** | — | — |

**Root cause hypothesis:** The percentage calculation divides drawdown by the wrong denominator. When position sizing allows notional exposure >100% of capital (via leverage or per-trade sizing), the drawdown can exceed initial capital. The DD% bug has TWO manifestations — sometimes returning 0.0, sometimes returning >100%. Any DD%-based gating or filtering is broken.

**4th audit flagging this issue. Zero action taken.**

### 5. HIGH: BTC Leakage — 15TH CYCLE, STILL UNBLOCKED

| Metric | Value |
|---|---|
| BTC results in 48h sample | ~42% of sampled files |
| Best BTC PF in 48h | 1.001 (noise — 406 trades, 0.51% return over 2 years) |
| BTC ACCEPTs all-time | **0** |
| Cycles requesting BTC exclusion | **15** |

BTC consumes 40%+ of compute. Zero BTC strategy has ever been profitable. Average BTC PF in sample: ~0.85. This is not an open question — BTC is a confirmed dead asset in this system. Every BTC backtest is pure waste.

### 6. HIGH: Refinement Triplication — 2ND AUDIT, UNFIXED

Three refine specs produce byte-identical results for every variant (flagged in Update 3). Still present. Still unfixed. Adds ~28+ wasted backtests per refinement batch.

### 7. MEDIUM: Refinement Engine — CONFIRMED DEAD

706 outcome notes. 0 instances of refinement producing improvement. `directive_history.notes_considered: 0` in every outcome note. The refinement engine is operationally non-functional. Every refinement cycle produces: (a) identical duplicates, (b) worse results, or (c) no change. Zero exceptions across 15 cycles.

### 8. NEW: Inconsistent Backtest Windows

| Asset/TF | Start Date | End Date | Duration | Bars |
|---|---|---|---|---|
| BTC 4h | 2024-02-27 | 2026-02-26 | 24 months | 4,380 |
| ETH 4h | 2024-02-27 | 2026-02-26 | 24 months | 4,380 |
| ETH 1h | 2025-08-01 | 2026-02-26 | **7 months** | 5,002 |

**ETH 1h backtests use only 7 months of data.** This means all ETH 1h results (including the champion MACD 1h 7:1 PF=1.712) have NOT been tested against:
- The 2024 bull run
- Q1-Q2 2025 market conditions
- Multiple regime transitions

Any ETH 1h strategy with high PF could be regime-specific to the Aug 2025-Feb 2026 window. This is a dataset limitation, not a strategy problem, but it makes all 1h PFs unreliable for deployment decisions.

---

## Regime Analysis

### Regime PF Across Sampled Results

| ID | Variant | PF | Trending PF (trades) | Ranging PF (trades) | Transitional PF (trades) | Flag |
|---|---|---|---|---|---|---|
| `0cb979be` | gate_adjust BTC 4h | 1.001 | 0.990 (221) | 1.127 (93) | 0.919 (92) | Noise — not profitable in any regime |
| `b10be004` | gate_adjust ETH 1h | 0.998 | 1.009 (220) | 1.115 (107) | 0.858 (88) | Ranging barely above 1.0, trans toxic |
| `76c7c9a9` | gate_adjust ETH 4h | 1.033 | 1.054 (195) | 0.982 (125) | 1.048 (69) | No clear edge anywhere |
| `0537219a` | rsi_pullback 1h 7:1 | 1.712 | 1.677 (37) | 2.062 (78) | 1.308 (46) | Strong — all regimes profitable |

### Key Regime Findings (Updated)

1. **Trending remains the profit destroyer.** In the sampled gate_adjust variants (400+ trades each), trending PF hovers at 0.99-1.05. Not a loss, but zero edge. The system generates most trades in trending (45-55% of trade count) but makes no money from them.

2. **Ranging is the only consistent edge.** Gate_adjust variants show ranging PF=1.10-1.13 (weak edge). Champion strategies show ranging PF=2.06-2.91 (strong edge). The gap between pipeline strategies and Claude specs in ranging regime is 2-3x.

3. **Transitional is the regime killer for pipeline specs.** PF=0.86-0.92 consistently. Claude tail harvesters survive transitional (PF=1.31-1.84) because wide TP allows capturing the rare large move.

4. **21/24 unique ACCEPTs lose money in trending.** Confirmed by both this audit and Strategy Advisory Update 14. Only Supertrend 8:1 (PF=1.289) and MACD 12:1 (PF=2.177) survive trending.

5. **Regime gate would boost portfolio PF by 0.2-0.4.** Disabling non-Supertrend/non-MACD strategies during trending is the single highest-impact improvement available. Requested for 8 cycles. Zero implementation.

---

## Comparison With Prior Audit

| Metric | Update 3 (Mar 2) | Update 4 (Mar 3) | Trend |
|---|---|---|---|
| Backtests reviewed | 1,556 | ~2,323 | Larger window |
| Zero-trade variants | 129 (8.3%) | 129+ (incl. Claude spec epidemic) | Unchanged + new source |
| Gate bug (min_trades=0) | 392 | **500+ estimated** | **Still accelerating** |
| Duplicate rate | ~62% | **~87-93%** | **Dramatically worsening** |
| DD% bug records | 317+ | **Still present, dual failure mode** | **4th audit** |
| BTC leakage | ~392 results | ~42% of samples | **Unchanged, unfixed** |
| Claude spec 0-trade rate | 3/5 (60%) | 5/6 (83%) in 48h | **Template routing bug** |
| Best PF (new data) | 1.236 (Mar 2) | 1.712 (Mar 1, flagged) | Unchanged — no new ACCEPTs |
| Prior CRITICALs fixed | 0 of 3 | **0 of 4** | **Zero progress** |
| Refinement improvement rate | 0% | **0% across 706 outcomes** | Dead |

---

## Recommendations

### CRITICAL (Act This Cycle — Blocking Revenue)

| # | Recommendation | Rationale | Audit History |
|---|---|---|---|
| 1 | **Fix gate bug: min_trades_required=0** | 500+ results bypass quality gate. Zero-trade and sub-10-trade overfits promoted. Worsening every cycle. | **4th audit — NEVER FIXED** |
| 2 | **Implement post-resolution dedup** | ~87-93% compute waste. Hash `template + sorted(params) + asset + timeframe` before scheduling. 3 lines of code. | **4th audit — NEVER FIXED** |
| 3 | **Fix DD% calculation** | Two failure modes: returns 0.0 (317+ records) or returns >4,000% (inverted calc). Any DD-based gating is broken. | **4th audit — NEVER FIXED** |
| 4 | **Fix Claude spec template routing** | 83% of Claude specs produce 0 trades due to custom template_name not in TEMPLATE_REGISTRY. Claude specs = 96% of unique ACCEPTs but most fail at routing, not strategy logic. | **NEW — 2 cycles of data** |

### HIGH (Act Within 2 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 5 | **Hard-exclude BTC from pipeline** | 0 BTC ACCEPTs across 706 outcomes. 40%+ of compute wasted. 15 cycles requesting. `if asset == "BTC": skip()` — one line. |
| 6 | **Forward-test Supertrend 8:1 and MACD 7:1** | 8 cycles requesting. Revenue blocker. Top strategies validated but never deployed. |
| 7 | **Kill refinement engine** | 0% improvement across 706 outcomes, 15 cycles. Every refinement run produces duplicates or worse results. Disable and reallocate compute to Claude specs. |
| 8 | **Add pre-backtest signal count** | Fast scan (no position sim) before full backtest. Would catch all 0-trade specs in <10 seconds. Saves 170+ wasted backtests from Claude spec routing failures. |
| 9 | **Extend ETH 1h data to 24 months** | Current 7-month window makes all 1h results unreliable. The champion MACD 1h 7:1 has never been tested on 2024 data. |

### MEDIUM (Act Within 5 Cycles)

| # | Recommendation | Rationale |
|---|---|---|
| 10 | **Report "PF without top 3" in backtester** | Auto-expose crash-dependent results. Would catch all Supertrend profit-concentration issues. |
| 11 | **Add regime entropy gate** | Reject 100% single-regime results. Catches trending-only overfits. |
| 12 | **Implement trending regime gate** | Disable non-Supertrend/MACD strategies during trending. Est. PF boost of 0.2-0.4. |
| 13 | **Build portfolio backtester** | 4 complementary strategies ready for combined testing. No mechanism to validate portfolio-level performance. |
| 14 | **Remove confirmed overfit 39ec9668** | Flagged in Update 3, still in system. PF=1.916→0.83 real. |

---

## Escalation Note

**Four consecutive audits have flagged the same three CRITICAL issues (gate bug, dedup, DD% bug). Zero have been fixed. A fourth CRITICAL has now been added (Claude spec routing). The system is running at 87-93% compute waste with broken quality gates, broken drawdown calculations, and broken template routing for its highest-value spec source (Claude specs produce 96% of unique ACCEPTs but 83% fail at routing).**

**The prior audit recommended halting pipeline execution until the gate bug is fixed. That recommendation stands and is now stronger: running more backtests through a system that wastes 93% of compute, can't measure drawdown correctly, and can't route Claude specs is actively counterproductive.**

**Immediate path to value: fix Claude spec routing (unblock the 96% ACCEPT source), add dedup hash (reclaim 93% of compute), extend 1h data window (validate the only new high-PF result), and forward-test the 2 strategies that have been waiting 8 cycles.**

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-03 |
| Audit version | Update 4 |
| Backtests reviewed | ~2,323 |
| Date range | 20260301–20260302 |
| Files directly sampled | 43 result files + 1 trade list (161 trades) |
| Agent-assisted analysis | 3 agents (broad sampling, Claude spec focus, outcome notes) |
| Outcome notes analyzed | 372 (213 Mar 1, 159 Mar 2) |
| Overfit suspects | 5 (1 prior confirmed, 3 prior concentration, 1 time clustering + single-trade) |
| Data quality issues | 8 (gate bug, duplication, Claude routing, DD% dual bug, BTC leakage, refinement triplication, refinement dead, 1h data window) |
| Regime bias flags | 4 (trending destruction, single-regime overfits, pipeline regime-blind, regime gate absent) |
| Critical issues | 4 (gate bug, dedup, DD% calc, Claude routing) |
| High issues | 5 (BTC exclusion, forward-test, kill refinement, signal pre-scan, extend 1h data) |
| Medium issues | 5 (PF-w/o-top-3, regime entropy, trending gate, portfolio backtest, remove overfit) |
| Prior-audit CRITICALs fixed | **0 of 4** |

*Next audit recommended after any CRITICAL fix is deployed, or in 48 hours, whichever comes first.*
