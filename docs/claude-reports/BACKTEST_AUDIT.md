# Backtest Quality Audit — 2026-03-04 (Update 5)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** 78 backtests across 20260303 (55) and 20260304 (23) + 30 batch files sampled
**Prior audit:** 2026-03-03 Update 4 (~2,323 backtests, 14 issues flagged, 0 CRITICALs fixed)

---

## Summary

**78 backtests reviewed. 48 issues flagged across 4 categories.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 3 profit-concentration warnings, 2 regime-level noise artifacts | MEDIUM |
| Data Quality | 34 zero-trade results (44%), 4 gate bypass bugs, 2 duplicate pairs, 3 tiny-dataset runs | CRITICAL |
| Regime Bias | 5 strategies with single-regime dependency, trending weakness universal | HIGH |
| Pipeline Health | 100% of 20260304 = zero trades, 73% of batches dedup-skipped, effective execution matrix = 2 cells | CRITICAL |

**Key numbers:**
- Zero-trade results: **34 of 78** (44%) — 23/23 on 20260304 (100%), 11/55 on 20260303
- 20260304 total loss: **23 backtests, 0 trades, 0 usable results**
- Gate bug (min_trades=0): **4 new instances** — still unfixed (5th audit flagging)
- Duplicate results: **2 pairs** from mislabeled v2c_btc spec
- Batch dedup-skip rate: **22 of 30** batches (73%) are 100% dedup-skipped
- Best PF in window: **2.034** (Vortex v3a ETH 4h — re-run of known champion)
- Profit concentration: Top 3 trades = 82-88% of net profit across all profitable strategies
- Pipeline effective execution matrix: **2 of 9 cells** (ETH 4h + SOL 4h only)
- Prior audit CRITICALs fixed: **0 of 4** (now 5th consecutive audit)

---

## Overfit Suspects

### A. Profit Concentration — Structural to 8:1 R:R Design

| Strategy | Asset/TF | PF | Trades | Top 3 as % of Net | PF w/o Top 3 (est.) | Flag |
|---|---|---|---|---|---|---|
| Vortex v3a | ETH 4h | 2.034 | 84 | ~82% | ~1.15 | Moderate — 84 trades provides cushion |
| KAMA Stoch v1 | ETH 1h | 1.857 | 42 | ~88% | ~1.05 | **HIGH** — low trade count + concentrated |
| Vortex v2c | ETH 4h | 1.892 | 84 | ~85% | ~1.12 | Moderate |
| KAMA Stoch v2 | ETH 1h | 1.709 | 42 | ~85% | ~1.08 | **HIGH** — same fragility as v1 |

**Structural note:** All profitable strategies use 8:1 or 10:1 R:R. Win rates of 20-27% mean 7-12 consecutive losses are expected. Removing any single top-3 trade significantly degrades PF. This is inherent to tail-harvesting, not curve-fitting, but it makes forward-test validation essential before capital allocation.

### B. Regime-Level Noise Artifacts

| Strategy | Asset/TF | Overall PF | Regime | Regime PF | Regime Trades | Verdict |
|---|---|---|---|---|---|---|
| KAMA Stoch v1 | ETH 4h | 0.399 | Transitional | **21.97** | 3 | Small-sample noise. Strategy is a loser. |
| KAMA Stoch v2 | ETH 4h | 0.369 | Transitional | **18.95** | 3 | Same artifact. Strike from all reporting. |

**Action:** These PF values must never appear in performance claims. The 4h KAMA variants are confirmed failures (overall PF < 0.4). The inflated transitional PF comes from 3 winning trades out of 3 — pure sample noise.

---

## Data Quality Issues

### 1. CRITICAL: 23/23 Zero-Trade Backtests on 20260304

**Every single backtest on 20260304 produced 0 trades.** Two pipeline-generated specs are responsible:

| Spec ID | Variants Run | Root Cause |
|---|---|---|
| `refine-8d9a5d5c` | baseline + exploit_1 through exploit_7 (15 runs) | Natural language entry rules not parseable by backtester |
| `19b3e1c752d2` | remove_component + threshold_mutation (8 runs) | Same: text descriptions, not indicator expressions |

**Example non-executable rule:** `"Require trend/confirmation alignment on bar close."` vs working format: `"VTXP_14 crosses_above VTXM_14"`

The pipeline emits specs with human-readable descriptions instead of dataframe-column references. The backtester correctly finds zero matching signals. All 23 runs = wasted compute.

### 2. CRITICAL: WILLR+STIFFNESS — 21 Cumulative Zero-Trade Runs

| Strategy | Runs (this audit) | Runs (all-time) | Assets | Timeframes | Trades |
|---|---|---|---|---|---|
| willr_stiffness_fade_v1 | 3 | — | ETH | 15m, 1h, 4h | 0 |
| willr_stiffness_fade_1h_8to1 | 7 | — | ETH, BTC, SOL | 1h, 4h | 0 |
| **Total this audit** | **10** | **21+** | all | all | **0** |

STIFFNESS_20_3_100 never meets entry conditions. Already blacklisted in advisory. Still executing. Still producing 0 trades.

### 3. HIGH: Gate Bypass Bug — 5th Audit, Still Unfixed

| ID | Spec | Asset/TF | Trades | Gate Result | Issue |
|---|---|---|---|---|---|
| `c3a02629` | 19b3e1c752d2 | ETH 1h | 0 | **PASS** | min_trades_required=0 |
| `b9c2abae` | 19b3e1c752d2 | SOL 1h | 0 | **PASS** | min_trades_required=0 |
| `a8fa32d4` | 19b3e1c752d2 | ETH 1h | 0 | **PASS** | min_trades_required=0 |
| `15d4115b` | 19b3e1c752d2 | SOL 1h | 0 | **PASS** | min_trades_required=0 |

The 4h variants of the same spec correctly require min_trades=10 and fail. The 1h pathway still sets min_trades=0. **This bug has been flagged for 5 consecutive audits with zero remediation.**

### 4. MEDIUM: Duplicate Results — Mislabeled Spec

| Pair | IDs | Metrics | Cause |
|---|---|---|---|
| v2c ETH 4h | `4409e998` = `b4b1757e` | PF=1.892, 84 trades, identical equity | `vortex_transition_v2c_btc` label ran against ETH data |
| v2c ETH 1h | `44c615b6` = `74daae0c` | PF=0.856, 120 trades, identical | Same mislabeling |

### 5. LOW: Tiny Dataset Runs (48 bars = 2 days)

| ID | Strategy | Asset/TF | Bars | Trades | Issue |
|---|---|---|---|---|---|
| `578a3e2a` | Vortex v3a | BTC 1h | 48 | 1 | Statistically meaningless |
| `5692a143` | Vortex v3b | BTC 1h | 48 | 1 | Same |
| `bbacab69` | Vortex v2c | BTC 1h | 48 | 1 | Same |

BTC 1h dataset is 20260223–20260225 (2 days). Any result from this data is noise.

---

## Regime Analysis

### Regime Breakdown of Profitable Strategies

| Strategy | Asset/TF | PF | Trending | Ranging | Transitional | All-Regime? |
|---|---|---|---|---|---|---|
| Vortex v3a | ETH 4h | **2.034** | 1.57 | 2.02 | **3.89** | YES |
| Vortex v2c | ETH 4h | **1.892** | 1.64 | 1.86 | **2.99** | YES |
| Vortex v3b | ETH 4h | **1.885** | 1.73 | 1.95 | 2.25 | YES |
| KAMA Stoch v1 | ETH 1h | **1.857** | 1.25 | **4.87** | 1.36 | YES |
| Vortex v2a | ETH 4h | **1.735** | 1.77 | 1.54 | 2.22 | YES |
| KAMA Stoch v2 | ETH 1h | **1.709** | 1.15 | **3.65** | 1.67 | YES |
| KAMA Stoch v2 | SOL 1h | **1.480** | 2.10 | 1.12 | 0.50 | NO |
| Vortex v2b | ETH 4h | **1.436** | 1.58 | 1.34 | 1.29 | YES |
| Vortex v1 | ETH 4h | **1.385** | 1.45 | 1.22 | 1.61 | YES |
| CCI Chop Fade v1 | ETH 4h | **1.255** | 1.13 | 1.43 | 1.52 | YES |
| Vortex v3a | SOL 4h | **1.202** | 0.22 | **2.83** | 1.10 | NO |

### Regime Bias Flags

| Strategy | Asset/TF | PF | Flag | Severity |
|---|---|---|---|---|
| Vortex v3a | SOL 4h | 1.202 | Trending PF=**0.22** — severe loss. Ranging-dependent. | HIGH |
| CCI ADX Chop Fade v1 | ETH 4h | 1.053 | Trending PF=**0.00** — zero profit in trends. | HIGH |
| QQE Chop Fade v1 | ETH 4h | 0.116 | Ranging PF=0.00, Transitional PF=0.00 — dead in all regimes. | LOW (already dead) |
| KAMA Stoch v1 | ETH 4h | 0.399 | Ranging PF=0.24 vs 1h ranging PF=4.87. Extreme timeframe sensitivity. | MEDIUM |
| STC Cycle Fade v1 | ETH 1h | 0.809 | Trending PF=0.63. Transitional-only viability (PF=1.25). | MEDIUM |

### Key Regime Findings

1. **Trending remains the universal weakness.** Even the Vortex family — the system champion — has trending PF of 1.45-1.77 (weaker than ranging or transitional). Trending is ~43% of trades by count, producing the largest drag.

2. **Transitional is highest alpha.** Vortex v3a transitional PF=3.89 remains the system record. All Vortex variants produce their best returns in transitions.

3. **Ranging is the universal base.** Every ACCEPT-tier strategy is profitable in ranging (PF 1.12–4.87). No strategy has been accepted without ranging profitability.

4. **KAMA is timeframe-fragile.** KAMA Stoch v1: PF=1.857 on 1h vs PF=0.399 on 4h. Same strategy, same asset, 20x performance divergence. The 4h version has ranging PF=0.24 (catastrophic) while 1h has ranging PF=4.87 (best in system). This fragility is a significant risk for deployment.

5. **SOL Vortex v3a is ranging-only.** Trending PF=0.22 means this strategy would destroy capital in trending markets. Not viable for forward-testing without a regime filter.

---

## Pipeline Health Assessment

### Batch Summary (30 files sampled)

| Metric | 20260303 | 20260304 | Combined |
|---|---|---|---|
| Batches sampled | 8 | 22 | 30 |
| Batches with any trades | 3 | **0** | 3 |
| 100% dedup-skipped | 3 | **19** | 22 (73%) |
| Total trades produced | 1,786 | **0** | 1,786 |
| Profitable runs (PF > 1.0) | 3 | **0** | 3 |

### Effective Execution Matrix (20260304)

Cumulative blocking from EXCLUDE_ASSET:BTC, EXCLUDE_TIMEFRAME:15m, and SIGNAL_CLUSTERED on 1h:

| | ETH | BTC | SOL |
|---|---|---|---|
| **15m** | BLOCKED | BLOCKED | BLOCKED |
| **1h** | FEASIBILITY_FAIL | BLOCKED | FEASIBILITY_FAIL |
| **4h** | EXECUTED (0 trades) | BLOCKED | EXECUTED (0 trades) |

**Only 2 of 9 cells execute. Both produce 0 trades.** The pipeline has no viable path to generate results.

### Dedup Saturation

22 of 30 batches (73%) are 100% dedup-skipped. The pipeline re-submits the same specs repeatedly and the dedup layer correctly blocks re-execution. But this means the pipeline is churning cycles with zero research output.

### Refinement Engine: Still Dead

The refine-8d9a5d5c spec spawned 7 variant batches (baseline + 6 exploits). All 7 produced identical 0-trade results. The refinement engine is generating exploit variants that are equally unable to produce signals. This confirms the engine is non-functional (flagged for 5+ audit cycles).

---

## Comparison With Prior Audit

| Metric | Update 4 (Mar 3) | Update 5 (Mar 4) | Trend |
|---|---|---|---|
| Backtests reviewed | ~2,323 | 78 | Smaller window (48h rolling) |
| Zero-trade results | 129+ (5.5%) | **34 (44%)** | **Dramatically worse ratio** |
| 20260304 trade rate | — | **0/23 (0%)** | **Total pipeline failure** |
| Gate bug (min_trades=0) | 500+ est. | 4 new | **Still present — 5th audit** |
| Duplicate rate (batches) | ~87-93% | 73% dedup-skipped | Pipeline saturated |
| Best PF (new data) | 1.712 | 2.034 (re-run of known champion) | No new discoveries |
| Prior CRITICALs fixed | **0 of 4** | **0 of 4** | **5th consecutive zero-fix** |
| Pipeline backtests with trades (20260304) | — | **0** | Dead |
| Refinement improvements | 0% | 0% (7 variant batches = 0 trades) | Dead |
| New ACCEPT strategies | 0 | 0 | Drought continues |

---

## Recommendations

### CRITICAL (Act Immediately)

| # | Recommendation | Audit History |
|---|---|---|
| 1 | **Block natural language specs at ingestion.** Add pre-backtest validator: entry rules must contain valid dataframe column names. Would have prevented 23 wasted backtests on 20260304. | NEW |
| 2 | **Fix gate bug: enforce min_trades >= 10 on all timeframes.** 1h pathway still sets min_trades=0. Zero-trade results pass gate. | **5th audit — NEVER FIXED** |
| 3 | **Implement post-resolution dedup.** 73% of batches are dedup-skipped. Hash `template + params + asset + timeframe` before scheduling. | **5th audit — NEVER FIXED** |
| 4 | **Fix DD% calculation.** Dual failure mode (returns 0.0 or >4000%). Any DD-based gating is broken. | **5th audit — NEVER FIXED** |

### HIGH (This Week)

| # | Recommendation | Rationale |
|---|---|---|
| 5 | **Extend KAMA Stoch v1 backtest to 2+ years.** 42 trades in 6.6 months is below confidence threshold. Q1 2026 already net negative. Must validate before forward-test promotion. | NEW — trade list analysis |
| 6 | **Add trending-regime robustness gate.** Vortex v3a SOL (trending PF=0.22), CCI ADX (trending PF=0.00) would be caught. Trending is 43% of trades. | Enhanced from prior audit |
| 7 | **Remove WILLR+STIFFNESS from pipeline.** 21+ zero-trade runs across all assets/timeframes. Blacklisted in advisory but still executing. | Escalated from prior audit |
| 8 | **Fix v2c_btc spec mislabeling.** Producing duplicate results (runs against ETH despite BTC label). | NEW |

### MEDIUM (Next Sprint)

| # | Recommendation | Rationale |
|---|---|---|
| 9 | **Report "PF without top 3 trades" in backtester.** Would auto-expose fragility. All profitable strategies drop to PF 1.05-1.15 without top 3 trades. | Carried from prior audit |
| 10 | **Kill refinement engine.** 0% improvement rate across 5+ audits. 7 variant batches on 20260304 all = 0 trades. Pure compute waste. | Escalated — now with 20260304 evidence |
| 11 | **Pipeline triage decision.** With 0/23 trade-producing backtests on 20260304, 73% dedup rate, and 2/9 effective execution cells — decide whether to fix or abandon the pipeline. Claude specs are the only ACCEPT source. | NEW — structural assessment |

---

## Escalation Note

**Five consecutive audits. Four CRITICAL issues. Zero fixed.** The pipeline is now producing literal zero results — 23/23 backtests on 20260304 generated 0 trades. The prior audit recommended halting pipeline execution. That recommendation is now **urgent**: the pipeline is consuming compute to produce verified zero output.

The system has two functioning components:
1. **Claude-specified strategies** (100% of ACCEPTs, 22.2% success rate)
2. **Forward-testing infrastructure** (Vortex v3a + Supertrend 8:1 running)

Everything else — the refinement engine, the pipeline spec generator, the batch scheduler — is producing zero value at nonzero cost. The path forward is to either fix the pipeline (4 CRITICALs) or accept it's dead and reallocate to Claude-only research cycles.

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-04 |
| Audit version | Update 5 |
| Backtests reviewed | 78 (55 from 20260303, 23 from 20260304) |
| Batch files sampled | 30 (8 from 20260303, 22 from 20260304) |
| Trade lists analyzed | 5 (Vortex v3a, v2c; KAMA Stoch v1, v2 ETH 1h/4h) |
| Agent-assisted analysis | 3 agents (20260303 results, 20260304 results, batch analysis) + 1 agent (trade list overfit) |
| Overfit suspects | 5 (2 high-concentration KAMA, 2 moderate Vortex, 2 noise artifacts) |
| Data quality issues | 43 (34 zero-trade, 4 gate bug, 2 duplicate pairs, 3 tiny dataset) |
| Regime bias flags | 5 strategies flagged |
| Pipeline health | DEAD (0/23 trades on 20260304, 73% dedup, 2/9 execution matrix) |
| Critical issues (cumulative) | 4 (spec validation NEW, gate bug 5th, dedup 5th, DD% 5th) |
| Prior-audit CRITICALs fixed | **0 of 4** |

*Next audit recommended after any CRITICAL fix is deployed, or in 48 hours, whichever comes first.*
