# Backtest Quality Audit — 2026-03-05 (Update 6)

**Author:** claude-auditor | **Mode:** BACKTEST_AUDITOR
**Scope:** 931 backtests across 20260303 (55), 20260304 (840), 20260305 (36)
**Prior audit:** 2026-03-04 Update 5 (78 backtests, 48 issues flagged, 0 CRITICALs fixed)

---

## Summary

**931 backtests reviewed. 788 zero-trade (84.6%). 0 new ACCEPTs. 5 overfit suspects. 6 CRITICALs.**

| Category | Flagged Items | Severity |
|---|---|---|
| Overfitting | 5 suspects (2 HIGH, 2 MODERATE, 1 noise artifact) | HIGH |
| Data Quality | 788 zero-trade (84.6%), ~54 duplicates, 22+ gate bypasses, 3 tiny-dataset runs | CRITICAL |
| Regime Bias | 5 strategies with single-regime dependency, transitional small-sample inflation | HIGH |
| Pipeline Health | 778/876 pipeline backtests = 0 trades (88.8%), 36/36 on 20260305 = 100% failure | CRITICAL |

**Key numbers:**
- Zero-trade results: **788 of 931** (84.6%) — 10/55 on Mar 3, 742/840 on Mar 4, **36/36 on Mar 5**
- Pipeline zero-trade streak: **138+** consecutive (102 prior + 36 new today)
- Duplicate triplicates on Mar 4: **~18 groups = 54 wasted runs**
- Unique non-zero results (Mar 4): **~40 of 840** (4.8%)
- Gate bug (min_trades=0): **22+ instances** across 3 days — **6th audit flagging**
- Prior audit CRITICALs fixed: **0 of 5** (now 6th consecutive audit)
- Best PF in window: **2.034** (Vortex v3a — re-run of known champion, NOT new)
- New ACCEPT strategies discovered: **0**

---

## Overfit Suspects

### A. Profit Concentration (Structural to 8:1+ R:R Design)

| Strategy | Asset/TF | PF | Trades | Top 3 as % of Net | PF w/o Top 3 (est.) | Flag |
|---|---|---|---|---|---|---|
| KAMA Stoch v1 | ETH 1h | 1.857 | 42 | ~88% | ~1.05 | **HIGH** — low trade count + concentrated |
| KAMA Stoch v2 | ETH 1h | 1.709 | 42 | ~85% | ~1.08 | **HIGH** — same fragility as v1 |
| EMA200 Vortex v2 | ETH 4h | 1.969 | 52 | ~80% | ~1.10 | **MODERATE** — 52 trades borderline |
| Vortex v3a | ETH 4h | 2.034 | 84 | ~82% | ~1.15 | MODERATE — 84 trades provides cushion |
| Vortex v2c | ETH 4h | 1.892 | 84 | ~85% | ~1.12 | MODERATE |

**Structural note:** All 8:1+ R:R strategies inherently concentrate profit in a few tail-harvesting wins. Win rates of 17-27% mean 7-12 consecutive losses are expected. This is the design, not curve-fitting. However, removing any single top-3 trade degrades all strategies to PF ~1.1. Forward-test validation is essential.

**Trade clustering check on Vortex v3a (PF=2.034):** 84 trades well-distributed across 24 months (Feb 2024 – Feb 2026). No month with zero trades. Top 5 winners spread across Nov 2024, Aug 2025, Nov 2025, Jan 2026 — different regimes, different seasons. **NOT clustered. Structurally sound.**

### B. Regime-Level Noise Artifacts

| Strategy | Asset/TF | Overall PF | Regime | Regime PF | Regime Trades | Verdict |
|---|---|---|---|---|---|---|
| EMA200 Vortex v2 | ETH 4h | 1.969 | Transitional | **4.321** | ~8-10 | Small-sample inflation. Record PF from <10 trades. |
| KAMA Stoch v1 | ETH 4h | 0.399 | Transitional | **21.97** | 3 | Pure noise — strategy is a loser (overall PF=0.40) |
| KAMA Stoch v2 | ETH 4h | 0.369 | Transitional | **18.95** | 3 | Same artifact. Strike from all reporting. |

**Action:** Transitional regime PFs above 3.0 should carry a "small-sample" warning in all reporting. The EMA200 Vortex v2 trans PF=4.321 "record" is based on ~8-10 trades — statistically unreliable. The KAMA 4h transitional PFs are from 3 trades and must never appear in performance claims.

---

## Data Quality Issues

### 1. CRITICAL: 788 Zero-Trade Backtests (84.6% of All)

| Date | Total | Zero-Trade | Rate | Root Cause |
|---|---|---|---|---|
| 20260303 | 55 | 10 | 18.2% | WILLR+STIFFNESS entry conditions impossible |
| 20260304 | 840 | 742 | 88.3% | Pipeline natural-language specs + WILLR+STIFFNESS |
| 20260305 | 36 | **36** | **100%** | Pipeline natural-language specs (confirmed) |
| **Total** | **931** | **788** | **84.6%** | |

**Root cause confirmed (Mar 5):** All 36 Mar 5 specs use non-executable natural-language rules like `"Require trend/confirmation alignment on bar close."` and `"Require candidate signal confidence >= 0.60."` These are NOT valid dataframe expressions. The backtester correctly generates 0 signals. The "entry_relax" variant merely changes confidence from 0.60 to 0.55 — equally non-functional. All 3 variants (gate_adjust, entry_relax, exploration) of all 3 specs are structurally identical despite claiming different templates.

### 2. CRITICAL: Pipeline Zero-Trade Streak = 138+

The directive loop has produced **138+ consecutive zero-trade backtests** crossing the day boundary (Mar 4 → Mar 5) with no circuit-breaker intervention. The loop recycles 5 remediation directives (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE) on specs that fundamentally cannot generate signals.

### 3. CRITICAL: Massive Duplication on Mar 4

**~54 of 98 non-zero Mar 4 results are exact duplicates** — same spec+asset+timeframe run 3 times at ~14:30, ~15:00, and ~15:30 producing byte-for-byte identical results.

| Triplicate Group | Spec | Asset/TF | PF | Trades | Wasted Runs |
|---|---|---|---|---|---|
| supertrend_obv_confirm_v1 | .auto.json | ETH 1h | 1.003 | 324 | 2 |
| supertrend_obv_confirm_v1 | .auto.json | BTC 4h | 0.878 | 281 | 2 |
| supertrend_obv_confirm_v1 | .auto.json | ETH 4h | 1.094 | 284 | 2 |
| vortex_transition_v3b | .auto.json | ETH 1h | 0.803 | 124 | 2 |
| vortex_transition_v2c_btc | .auto.json | BTC 4h | 0.733 | 120 | 2 |
| + ~13 more groups | various | various | various | various | 26 |
| **Total wasted** | | | | | **~36** |

Additionally, mislabeled `v2c_btc` spec continues to run against ETH data, producing duplicate results identical to `v2c`:
- Mar 3: `4409e998` = `b4b1757e` (PF=1.892, ETH 4h)
- Mar 3: `44c615b6` = `74daae0c` (PF=0.856, ETH 1h)
- Mar 3: `b0ac1096` = `d64eef4a` (CCI Chop Fade v1=v2, identical PF=1.255)

### 4. CRITICAL: Gate Bypass Bug — 6th Audit, Still Unfixed

| Date | Instances | Pattern |
|---|---|---|
| 20260303 | 4+ | 1h specs with min_trades_required=0 |
| 20260304 | Multiple (sampled) | Same pattern |
| 20260305 | **18** | All 1h runs PASS with 0 trades (min_trades=0), all 4h runs correctly FAIL (min_trades=10) |

**The 1h pathway consistently sets min_trades=0, allowing zero-trade results to pass the quality gate.** This has been flagged for **6 consecutive audits with zero remediation.**

### 5. CRITICAL: Claude Specs Not Backtested (Mar 5)

On Mar 5, 6 Claude-authored specs exist in the spec directory but **none were backtested**. All 36 backtest slots were consumed by 3 pipeline specs that produced 0 trades. The Claude specs — which have a 22% historical ACCEPT rate vs pipeline ~0% — have been blocked for 3+ cycles.

### 6. LOW: Tiny Dataset Runs (48 bars)

| ID | Strategy | Asset/TF | Bars | Trades | Issue |
|---|---|---|---|---|---|
| `578a3e2a` | Vortex v3a | BTC 1h | 48 | 1 | Statistically meaningless |
| `5692a143` | Vortex v3b | BTC 1h | 48 | 1 | Same |
| `bbacab69` | Vortex v2c | BTC 1h | 48 | 1 | Same |
| `2f2ba9a1` | Vortex v3a | BTC 1h | 48 | 1 | Forward-test window |
| `70d40de8` | Supertrend OBV | BTC 1h | 48 | 3 | Forward-test window |

---

## Regime Analysis

### Regime Breakdown of Profitable Strategies (from non-zero results)

| Strategy | Asset/TF | PF | Trending | Ranging | Transitional | Trans Trades | All-Regime? |
|---|---|---|---|---|---|---|---|
| Vortex v3a | ETH 4h | **2.034** | 1.57 | 2.02 | **3.89** | 9 | YES |
| EMA200 Vortex v2 | ETH 4h | **1.969** | 1.87 | 1.62 | **4.32** | ~8 | YES* |
| Vortex v2c | ETH 4h | **1.892** | 1.64 | 1.86 | **2.99** | ~12 | YES |
| Vortex v3b | ETH 4h | **1.885** | 1.73 | 1.95 | 2.25 | ~12 | YES |
| KAMA Stoch v1 | ETH 1h | **1.857** | 1.25 | **4.87** | 1.36 | ~6 | YES |
| Vortex v2a | ETH 4h | **1.735** | 1.77 | 1.54 | 2.22 | ~10 | YES |
| Ichimoku TK v1 | ETH 4h | **1.604** | 0.69 | **2.01** | **2.78** | ~15 | BORDERLINE |
| Supertrend CCI v3 wide | ETH 4h | **1.541** | 1.01 | **1.97** | **2.29** | ~10 | YES |
| EMA200 Vortex v2 | SOL 4h | **1.519** | 1.42 | 1.34 | **1.99** | ~6 | YES |
| Supertrend CCI v3 wide | ETH 1h | **1.480** | 1.64 | 1.47 | 1.28 | — | YES |

*EMA200 Vortex v2 trans PF=4.321 flagged as small-sample artifact (see Overfit section)

### Regime Bias Flags

| Strategy | Asset/TF | PF | Flag | Severity |
|---|---|---|---|---|
| Vortex v3a | SOL 4h | 1.202 | Trending PF=**0.22** — catastrophic in trends | HIGH |
| CCI ADX Chop Fade | ETH 4h | 1.053 | Trending PF=**0.00** — zero trending trades | HIGH |
| Ichimoku TK v1 | ETH 4h | 1.604 | Trending PF=**0.69** — loses in trends | MEDIUM |
| KAMA Stoch v1 | ETH 4h | 0.399 | PF=1.857 on 1h vs 0.399 on 4h = extreme timeframe fragility | MEDIUM |
| STC Cycle Fade | ETH 1h | 0.809 | Trending PF=0.63, transitional-only viability | LOW (dead strategy) |

### Key Regime Findings

1. **Transitional = highest alpha but smallest samples.** Every "record" transitional PF (3.89, 4.32, 2.99) is based on 8-15 trades. Statistically suggestive but not robust. The 4.321 "record" comes from ~8 trades.

2. **Ranging = universal base.** Every ACCEPT is profitable in ranging (PF 1.12-4.87). This is the one regime where all sample sizes are adequate (30-40+ trades per strategy).

3. **Trending weakness is universal.** Even the champion (Vortex v3a trending PF=1.57) underperforms its ranging/transitional returns. CCI ADX has literally zero trending trades. Ichimoku TK loses in trending (PF=0.69).

4. **No new regime data.** 788 zero-trade backtests produced zero trades and thus zero regime analysis. The regime picture is identical to Update 5.

---

## Pipeline Health Assessment

### Day-by-Day Pipeline Output

| Metric | Mar 3 | Mar 4 | Mar 5 | Trend |
|---|---|---|---|---|
| Total backtests | 55 | 840 | 36 | |
| Zero-trade | 10 (18%) | 742 (88%) | **36 (100%)** | **Accelerating failure** |
| Unique non-zero | 43 | ~40 | **0** | **Collapse** |
| New ACCEPTs | 0 | 0 | 0 | Drought: 3+ days |
| Claude specs run | ~8 | ~30 combos | **0** | **BLOCKED** |
| Pipeline specs run | ~47 | ~810 | **36** | All zero-trade |
| Duplicates | 3 pairs | ~54 triplicates | 0 | Waste |

### Mar 5 Root Cause Breakdown

3 pipeline specs tested, each with 3 variants x 4 asset/TF combos = 36 runs:

| Spec ID | Template Claimed | Actual Entry Rules | Result |
|---|---|---|---|
| `5df8f61c0c71` | supertrend_follow | `"Require trend/confirmation alignment"` | 0 trades x 12 |
| `13a80050d94c` | ema_rsi_atr | `"Require candidate signal confidence >= 0.60"` | 0 trades x 12 |
| `12c5d8d913ad` | rsi_pullback | `"Use signal: alignment_entry"` | 0 trades x 12 |

All 3 specs are **structurally identical** despite claiming different templates. None reference actual dataframe columns (RSI_14, EMA_9, SUPERT_7_3.0, etc.). The directive loop generates 3 variants per spec that are equally non-functional.

### Effective Research Output (48h)

| Source | Backtests | Trades Produced | Unique Results | ACCEPTs |
|---|---|---|---|---|
| Claude specs | ~38 | ~4,000+ | ~35 | 0 (all re-runs of known strategies) |
| Pipeline specs | ~893 | **0** | **0** | 0 |
| **Total** | 931 | ~4,000+ | ~35 | **0** |

**The pipeline consumed 96% of backtest capacity to produce 0% of research output.**

---

## Comparison With Prior Audit

| Metric | Update 5 (Mar 4) | Update 6 (Mar 5) | Trend |
|---|---|---|---|
| Backtests reviewed | 78 | **931** | Full-scope audit |
| Zero-trade results | 34 (44%) | **788 (84.6%)** | **2x worse ratio** |
| Mar 5 trade rate | — | **0/36 (0%)** | Pipeline dead |
| Zero-trade streak | 66+ | **138+** | No circuit-breaker |
| Duplicate waste | 4 results | **~60 results** | Pipeline triplicating |
| Gate bug instances | 4 | **22+** | **6th audit unfixed** |
| New ACCEPTs | 0 | 0 | Drought: 3+ days |
| Claude specs blocked | 2 cycles | **3+ cycles** | Escalating |
| Prior CRITICALs fixed | **0 of 4** | **0 of 5** | **6th consecutive zero-fix** |

---

## Recommendations

### CRITICAL (Act Immediately)

| # | Recommendation | Audit History |
|---|---|---|
| 1 | **HALT PIPELINE.** 138+ consecutive zero-trade backtests across 2+ days. Pipeline consumes 96% of capacity for 0% output. Full halt, not pause. | Escalated from U5 |
| 2 | **Block natural-language specs at ingestion.** Pre-backtest validator: entry rules must contain valid dataframe column names. Would prevent 778+ wasted runs. | U5 NEW → U6 CRITICAL |
| 3 | **Fix gate bug: enforce min_trades >= 10 on all timeframes.** 1h pathway sets min_trades=0. 22+ zero-trade results pass quality gate. | **6th audit — NEVER FIXED** |
| 4 | **Implement post-resolution dedup.** Hash `template + params + asset + timeframe` before scheduling. ~54 duplicate runs on Mar 4 alone. | **6th audit — NEVER FIXED** |
| 5 | **Execute blocked Claude specs.** ALMA Vortex, T3 EMA200, CCI KAMA — 9 variants ready. 22% ACCEPT rate vs pipeline 0%. Only path to progress. | Escalated U5→U6 |
| 6 | **Fix DD% calculation.** Still returning 0.0% or >4000% in edge cases. Any DD-based gating is unreliable. | **6th audit — NEVER FIXED** |

### HIGH (This Week)

| # | Recommendation | Rationale |
|---|---|---|
| 7 | **Extend KAMA Stoch v1 backtest to 2+ years.** 42 trades in ~6 months is below confidence threshold. PF drops to ~1.05 without top 3 trades. | Carried from U5 |
| 8 | **Add trending-regime robustness gate.** Block strategies with trending PF < 0.5. Vortex SOL (0.22), CCI ADX (0.00), Ichimoku TK (0.69) would be caught. | Carried from U5 |
| 9 | **Report transitional-regime sample sizes.** Flag any regime PF based on <15 trades. Current "records" (trans PF=4.321) are statistically weak. | NEW |
| 10 | **Remove v2c_btc mislabeled spec.** Produces duplicate results identical to v2c (runs ETH data despite BTC label). | Carried from U5 |

### MEDIUM (Next Sprint)

| # | Recommendation | Rationale |
|---|---|---|
| 11 | **Report "PF without top 3 trades" in backtester.** All profitable strategies drop to PF ~1.05-1.15 without top 3 trades. Auto-expose tail-harvesting fragility. | Carried 3 audits |
| 12 | **Kill refinement engine.** 0% improvement rate across 6 audits. All variant batches produce 0 trades or identical results. | Escalated from U5 |
| 13 | **Add pipeline circuit-breaker.** Halt any spec family after 5 consecutive zero-trade results. Would have saved 133+ wasted runs. | NEW |

---

## Escalation Note

**Six consecutive audits. Five CRITICAL issues. Zero fixed.** The pipeline has now produced **138+ consecutive zero-trade backtests** spanning 2+ days. On March 5, **100% of backtests (36/36) produced zero trades** while 6 Claude specs sat unexecuted.

The pipeline is not broken — it is **architecturally incapable of producing results**. It generates natural-language pseudo-conditions that the backtester cannot evaluate. The directive loop "fixes" them by adjusting confidence thresholds on non-existent columns. Each cycle wastes 12-36 backtest slots that could run Claude specs with a demonstrated 22% ACCEPT rate.

**The entire research program is blocked by a pipeline that has a 0% success rate consuming 96% of compute.**

---

## Audit Metadata

| Metric | Value |
|---|---|
| Audit date | 2026-03-05 |
| Audit version | Update 6 |
| Backtests reviewed | 931 (55 Mar 3 + 840 Mar 4 + 36 Mar 5) |
| Trade lists analyzed | 12+ (including full Vortex v3a 84-trade review) |
| Overfit suspects | 5 (2 HIGH KAMA concentration, 1 MODERATE EMA200 low-count, 2 noise artifacts) |
| Data quality issues | 788 zero-trade, ~60 duplicates, 22+ gate bypasses, 5 tiny-dataset runs |
| Regime bias flags | 5 strategies flagged |
| Pipeline health | DEAD (138+ zero-trade streak, 100% failure on Mar 5, 96% capacity consumed for 0% output) |
| Critical issues (cumulative) | 6 (halt pipeline, spec validation, gate bug, dedup, Claude spec execution, DD calculation) |
| Prior-audit CRITICALs fixed | **0 of 5** |

*Next audit recommended after any CRITICAL fix is deployed, or in 48 hours, whichever comes first.*
