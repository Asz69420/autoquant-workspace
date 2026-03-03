# Strategy Advisory — 2026-03-03 (Update 17)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** ~706 outcome notes (20260302 latest 30), 42 backtests (20260303), 0 Claude specs archived, 1 research card (fixture only), 25 research digest entries, 11 signal templates, doctrine as of 20260226
**Prior advisory:** 2026-03-03 (Update 16)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 174 checks k_prev < os_val but short side checks k_now > ob (asymmetric). 0 trades, 17+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken (line 149-150 skips if i<20). 2-sigma breakout unsuitable for crypto vol. 0 trades, 13+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "CONFIRMED DEAD: 0 trades across 9 backtests — 3 assets (BTC/ETH/SOL) x 3 timeframes (15m/1h/4h). Conditions impossibly restrictive. Abandon permanently."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy that uses it. Dead as regime filter."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116 on 4h (near-total loss). Only fires in trending regime. Structurally wrong for mean-reversion."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "18 cycles of exclusion requests. 0 BTC ACCEPTs across 740+ outcomes. Even champion v3a loses on BTC (PF=0.743). Every BTC computation is waste."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 15m ACCEPTs ever across all strategies. CCI 15m PF=0.617, signal noise too high."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "ALL ACCEPT-tier results are 4h. Every 1h result loses or is marginal. 4h dominance confirmed across 42+ backtests."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications, 17 cycles"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics across all applications"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%, 17 cycles"},
  {"action": "PREFER_TEMPLATE", "target": "vortex_transition", "priority": 0, "reason": "CHAMPION FAMILY: v3a PF=2.034, v2c PF=1.892, v3b PF=1.885. 5/6 variants ALL-REGIME profitable. Now forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 1, "reason": "Former champion — PF=1.921, 7 ACCEPTs, proven all-regime. Now forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 2, "reason": "9 ACCEPTs, best PF=1.712, most consistent"},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 3, "reason": "5 ACCEPTs incl. slingshot_12to1 PF=1.270"},
  {"action": "PREFER_TEMPLATE", "target": "ema_rsi_atr", "priority": 4, "reason": "2 ACCEPTs incl. precision_10to1 PF=1.327"},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All unique ACCEPTs use 5:1+ R:R"},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 11+ cycles, 706+ outcome notes"},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of all new backtests and 100% of new ACCEPTs. Pipeline = 0 backtests."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a_eth_4h", "reason": "LIVE. 2 clean cycles, 0 trades. First trade expected within 3-7 days."},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "LIVE. 2 clean cycles, 0 trades. Weekly scorecard active."},
  {"action": "EVALUATE_ASSET", "target": "SOL", "reason": "NEW: Vortex v3a SOL 4h PF=1.20 (profitable). First SOL test ever. Needs more strategies tested before conclusions."},
  {"action": "ADD_REGIME_GATE", "target": "all_non_vortex_strategies", "gate": "disable_during_trending", "reason": "21/24 legacy ACCEPTs lose money in trending. Vortex family is exception."},
  {"action": "DEDUP_PARAMS", "reason": "87%+ compute waste on identical parameter sets. 9 identical ACCEPTs, 15 identical REVISEs in latest 30 outcomes."},
  {"action": "FIX_RESEARCH_CARDS", "reason": "1 card exists (test fixture). Pipeline not generating real cards from video research."},
  {"action": "FIX_THESIS_GENERATION", "reason": "Thesis LLM not consuming directives. Proposes blacklisted combinations."},
  {"action": "FIX_PROMOTION_PIPELINE", "reason": "Promotion BLOCKED with NO_VARIANTS_COMPILED. Autonomous pipeline produces 0 specs."},
  {"action": "ARCHIVE_CLAUDE_SPECS", "reason": "artifacts/claude-specs/ is empty despite 42+ Claude-designed backtests. Specs not being persisted for analysis."},
  {"action": "TEST_UNTESTED_INDICATORS", "target": "T3_10_0.7, ALMA_9_6.0_0.85", "reason": "T3 mentioned in research digest as trend direction filter. ALMA never tested. Both computed every bar but never used in any strategy."}
]
```

---

## Executive Summary

**The #1 blocker is RESOLVED: forward-testing is live.** Vortex v3a (PF=2.034) and Supertrend 8:1 (PF=1.921) are running paper-trade on ETH 4h with health monitoring and weekly scorecards. Two clean cycles completed, zero trades fired (expected — these strategies average ~1 trade/week). Quandalf has pivoted correctly from exploration to exploitation+diversification, placing orders for Ichimoku, CCI v3, and OBV strategies. SOL was tested for the first time: Vortex v3a SOL 4h PF=1.20 is profitable but below ACCEPT threshold — promising enough to warrant further investigation. Meanwhile, WILLR+STIFFNESS is conclusively dead (0 trades across 9 backtests spanning 3 assets and 3 timeframes), and the autonomous pipeline remains completely stalled.

---

## Failing Patterns

### 1. WILLR + STIFFNESS — Conclusively Dead (EXPANDED)
Previously flagged with 3 zero-trade backtests. Now confirmed with **9 backtests across 3 assets (BTC, ETH, SOL) and 3 timeframes (15m, 1h, 4h)**: zero trades in every single one. The STIFFNESS indicator itself appears to be the bottleneck — it never drops below 50 simultaneously with WILLR at extremes. STIFFNESS should be blacklisted as a regime filter entirely. WILLR alone (without STIFFNESS pairing) has never been tested and may still have value, but needs a different regime gate (e.g., CHOP).

### 2. QQE — Confirmed Structural Misfit (UNCHANGED)
PF=0.116 on 4h (near-total loss). QQE only fires in trending regime, making it structurally unsuitable for mean-reversion. Do not revisit.

### 3. STC — High Churn, No Edge (UNCHANGED)
PF=0.809-1.012, DD=33-45%. Generates too many signals without conviction. The cycle timing hypothesis doesn't produce enough edge to overcome fees.

### 4. ADX as Filter — Destructive for Mean-Reversion (UNCHANGED)
CCI ADX Chop Fade: ADX < 25 filter killed ranging alpha (PF dropped 1.43 → 0.84). ADX doesn't distinguish "ranging" from "quiet/no-signal." CHOP alone is superior.

### 5. Donchian Channel Touches — Discrete Signal Problem (UNCHANGED)
2 trades across 4 backtests. Level-based signals (close <= DCL) are too rare. All ACCEPTs use continuous/zone-based or cross-based signals. Donchian touches need proximity zones (close < DCL * 1.01) not exact matches.

### 6. 1h Timeframe — Consistently Inferior (17TH CYCLE)
Every single strategy tested in this cycle is worse on 1h than 4h:
- Vortex v3a: 1h PF=0.753 vs 4h PF=2.034 (delta: -1.28)
- Vortex v3b: 1h PF=0.841 vs 4h PF=1.885 (delta: -1.04)
- Vortex v2c: 1h PF=0.856 vs 4h PF=1.892 (delta: -1.04)
- Vortex v3a SOL: 1h PF=0.78 vs 4h PF=1.20 (delta: -0.42)
- Average PF degradation: **0.94 points**. 1h is not just worse — it's typically losing.

### 7. BTC — Dead Asset (18TH CYCLE)
Even champion v3a loses on BTC: PF=0.743, DD=19.4%. v2c BTC: PF=0.754, v3b BTC: PF=0.840. BTC 1h: 1 trade each across all variants. The "ETH superiority" thesis is confirmed with the strongest possible evidence — our best signal fails on BTC.

### 8. Pipeline — Still Completely Stalled (UNCHANGED)
- 0 outcome notes generated on 20260303
- Promotion BLOCKED (NO_VARIANTS_COMPILED)
- Research cards: 1 test fixture, 0 real cards
- Latest 30 outcomes (20260302): 87% duplicates
- 3 Claude-designed specs with custom template names were REJECTED with 0 trades (spec routing issue)

---

## Promising Directions

### 1. Forward-Testing LIVE — The Inflection Point (NEW)
The system crossed the most important threshold: **backtested strategies are now running against live data.** Infrastructure includes:
- Forward runner executing at every 4h bar close (+5min buffer)
- Health monitor checking every cycle
- Weekly scorecard (Sunday 7am AEST) with leaderboard, PF drift analysis, and auto-promotion suggestions

Two champions active:
| Strategy | Paper Equity | Cycles | Trades | Status |
|---|---|---|---|---|
| Vortex v3a ETH 4h | $10,000 (flat) | 2 | 0 | Healthy, waiting |
| Supertrend 8:1 ETH 4h | $10,000 (flat) | 2 | 0 | Healthy, waiting |

First trade expected within 3-7 days. This single data point — does live PF match backtest PF? — answers the fundamental question no amount of backtesting can.

### 2. SOL — Potential Third Asset (NEW FINDING)
Vortex v3a was tested on SOL for the first time:
- **SOL 4h: PF=1.20, +18.26%, 94 trades, Win Rate 19.15%** — profitable
- SOL 1h: PF=0.78, -17.50%, 122 trades — loss (confirms 4h-only pattern)
- Regime: Ranging PF=2.83, Transitional PF=1.10, **Trending PF=0.22** (catastrophic)

SOL 4h is profitable overall but extremely regime-dependent — ranging alpha (PF=2.83) masks trending losses (PF=0.22). ETH's v3a is profitable in ALL regimes including trending (PF=1.572). SOL would need a trending regime gate to be viable. Worth testing more strategies on SOL 4h, but with a mandatory trending exclusion gate.

### 3. Portfolio Diversification Orders Placed (NEW)
Quandalf has correctly pivoted to decorrelated signal families:
1. **Ichimoku TK Transition v1** — Tests whether transition detection is a general edge (Ichimoku uses median prices over 9/26 bars) or Vortex-specific. If both work, "regime transition" is a universal alpha source.
2. **CCI Chop Fade v3** — The actual 8:1 R:R test (v2 was accidentally identical to v1). Could push CCI past PF 1.3 to become promotion-eligible.
3. **Supertrend OBV Confirm v1** — First test of volume-based confirmation. Tests whether volume adds signal quality to trend entries.

These are well-designed: each tests a distinct hypothesis, uses decorrelated indicator families, and targets ETH 4h only (following established directives).

### 4. Vortex Family — Still the Core Edge (UNCHANGED)
6 variants tested on ETH 4h, 5 all-regime profitable:

| Variant | PF | DD | Trades | Trans PF | All-Regime? |
|---|---|---|---|---|---|
| **v3a** | **2.034** | 15.2% | 84 | **3.886** | YES |
| v2c | 1.892 | 12.3% | 84 | 2.986 | YES |
| v3b | 1.885 | 11.8% | 84 | 2.250 | YES |
| v2a | 1.735 | 11.4% | 80 | 0.133 | No (trans) |
| v2b | 1.436 | 11.7% | 80 | 1.286 | YES |
| v1 | 1.385 | 10.2% | 79 | 1.613 | YES |

### 5. Research Digest — Untested Concepts Worth Exploring
25 research digest entries (mostly DaviddTech YouTube). Concepts with testable potential that haven't been explored:

| Concept | Source | Available Indicators | Status |
|---|---|---|---|
| **T3 as trend direction filter** | Entry 2 (DaviddTech) | T3_10_0.7 computed | NEVER TESTED |
| **ALMA as smoothed signal** | — | ALMA_9_6.0_0.85 computed | NEVER TESTED |
| **Range Filter concept** | Entries 5, 7, 9 | Not computed | Would need new indicator |
| **Anti-spam filter (min distance between trades)** | Entry 3 | Not implemented | System-level feature |
| **Gaussian Channel (EMA + ATR bands)** | Entry 1 | EMA + ATR computed | Approximation testable |
| **Momentum threshold crossing** | Entry 9 | Various oscillators available | Partially tested via CCI/STC |

**T3_10_0.7 and ALMA_9_6.0_0.85 are computed every bar but have never appeared in any strategy.** T3 is a triple-smoothed EMA designed to reduce lag — it could serve as a superior trend direction filter compared to raw EMA. ALMA (Arnaud Legoux Moving Average) minimizes noise while maintaining responsiveness. Both deserve at least one strategy test.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|
| **vortex_transition** (spec_rules) | **6** | **2.034** | 82 | **CHAMPION (FORWARD-TESTING)** | Monitor forward-test; continue refinement |
| supertrend_follow | 7 | 1.921 | 95 | **STRONG (FORWARD-TESTING)** | Monitor forward-test; proven |
| macd_confirmation | 9 | 1.712 | 155 | STRONG | Test 4h variant; forward-test candidate |
| rsi_pullback | 5 | 1.442 | 105 | GOOD | Saturated; deprioritize new variants |
| ema_rsi_atr | 2 | 1.327 | 127 | GOOD | Needs trending gate; ranging PF=2.864 |
| cci_chop_fade (spec_rules) | 1 | 1.255 | 179 | RISING | v3 (8:1 R:R) ordered; could reach ACCEPT |
| spec_rules (pipeline) | ~1 | 1.419 | 140 | OPERATIONAL | Only produces duplicates; dedup needed |
| ema_crossover | 0 | — | 0 | EXHAUSTED | 0 ACCEPTs ever; remove from fallback |
| choppiness_donchian_fade | 0 | — | 0 | DEAD | 0 trades in 8+ backtests; discrete signal problem |
| kama_vortex_divergence | 0 | — | — | UNTESTED | Never backtested — different hypothesis from KAMA Vortex Trend |
| stc_cycle_timing | 0 | — | — | TESTED-FAILED | PF=0.809-1.012, high DD. Noisy signals. |
| stochastic_reversal | 0 | — | 0 | DEAD (BUG) | Bug line 174; fix or remove |
| bollinger_breakout | 0 | — | 0 | DEAD (BUG) | Volume gate broken; remove |

---

## Regime Insights

### Updated Regime Performance Matrix (All ACCEPT-Tier + SOL)

| Strategy | Asset | Trending PF | Ranging PF | Trans PF | All-Regime? |
|---|---|---|---|---|---|
| **Vortex v3a 4h** | ETH | 1.572 | 2.022 | **3.886** | **YES** |
| Vortex v2c 4h | ETH | 1.636 | 1.855 | **2.986** | **YES** |
| Vortex v3b 4h | ETH | 1.726 | 1.954 | 2.250 | **YES** |
| Supertrend 8:1 | ETH | 1.289 | **2.914** | 1.844 | **YES** |
| Vortex v2b 4h | ETH | 1.582 | 1.338 | 1.286 | **YES** |
| Vortex v1 4h | ETH | 1.453 | 1.222 | 1.613 | **YES** |
| CCI Chop Fade 4h | ETH | 1.132 | 1.430 | 1.521 | **YES** |
| **Vortex v3a 4h** | **SOL** | **0.220** | **2.830** | **1.100** | **No (trending)** |
| MACD 12:1 | ETH | **2.177** | 1.581 | 0.569 | No |
| MACD 7:1 | ETH | 1.677 | **2.062** | 1.308 | YES (marginal) |
| RSI pullback 8:1 | ETH | 1.505 | **1.795** | 0.930 | No |
| ema_rsi_atr precision | ETH | 0.372 | **2.864** | 1.731 | No |

### Key Regime Findings

1. **Vortex = regime-agnostic edge ON ETH.** 5/6 ETH variants profitable in all 3 regimes. SOL shows this is ETH-specific — SOL's trending PF=0.22 proves the Vortex all-regime property doesn't transfer across assets.

2. **SOL's regime profile mirrors legacy strategies.** SOL's Vortex: ranging PF=2.83, trending PF=0.22. This is the SAME profile as non-Vortex ETH strategies (strong ranging, weak trending). ETH's Vortex being all-regime profitable may be an ETH structural property, not a Vortex property.

3. **Transitional regime remains the alpha source.** Vortex v3a ETH transitional PF=3.886 is still the highest single-regime PF ever recorded. Every all-regime strategy has its strongest alpha in transitional.

4. **Ranging is the reliable base.** Every ACCEPT-tier strategy is profitable in ranging. SOL's ranging PF=2.83 is among the highest ever, confirming ranging alpha transfers across assets.

5. **Trending is the discriminator.** Whether a strategy becomes all-regime depends entirely on its trending performance. Vortex on ETH handles trending; everything else and every asset except ETH struggles.

---

## Recommended Directives

### Priority 0 — MONITOR FORWARD-TESTS (ACTIVE)
1. **Watch for first live trade** — Expected within 3-7 days. This is the highest-value data point in the system.
2. **Compare live execution to backtest expectations** — Does the reversal exit fire cleanly on real bars? Does stop/TP geometry hold?
3. **Weekly scorecard review** — First scorecard Sunday 7am AEST. Evaluate PF drift tolerance.

### Priority 1 — PORTFOLIO DIVERSIFICATION (IN PROGRESS)
1. **Execute pending orders** — Ichimoku TK, CCI v3 (8:1), OBV confirm. All designed, awaiting Frodex execution.
2. **Test kama_vortex_divergence template** — Still 0 backtests. Trend exhaustion hypothesis vs. trend confirmation. Different mechanism entirely.
3. **T3 trend filter strategy** — T3_10_0.7 is computed but never tested. Research digest suggests T3 as superior trend direction indicator. Design a spec using T3 crosses or T3 slope as entry signal.
4. **ALMA as smoothed entry signal** — ALMA_9_6.0_0.85 computed, never tested. Could provide lower-lag crossover signals than EMA.

### Priority 2 — SOL INVESTIGATION (NEW)
1. **Test 2-3 more strategies on SOL 4h** — Vortex v3a SOL 4h PF=1.20 is below ACCEPT but profitable. Need more data to determine if SOL is viable.
2. **SOL with trending regime gate** — SOL's trending PF=0.22 is catastrophic. A simple `CHOP > 50` or ADX-based trending gate could push SOL PF above 1.3.
3. **If SOL reaches ACCEPT-tier on 2+ strategies** — Add to forward-test roster for portfolio diversification.

### Priority 3 — SYSTEM FIXES (18TH CYCLE)
1. **Hard-exclude BTC** — 18 cycles requesting. 0 BTC ACCEPTs ever.
2. **Implement parameter hash dedup** — 87% compute waste.
3. **Archive Claude specs** — artifacts/claude-specs/ is empty despite 42+ backtests. Specs aren't being persisted.
4. **Fix research card pipeline** — 1 fixture file, 0 real cards. The research digest has 25 entries but they're not being converted to structured cards.
5. **Remove dead templates from registry** — stochastic_reversal, bollinger_breakout.

---

## Doctrine Gaps

### 1. Forward-Test Validation Framework (NEW — NOW CRITICAL)
Forward-testing is live but there's no documented framework for:
- **PF drift tolerance** — How much can live PF diverge from backtest PF before a strategy is demoted? ±30%? ±50%?
- **Minimum sample size** — How many live trades before making promotion/demotion decisions? 10? 20? 50?
- **Time-weighted vs. trade-weighted scoring** — Does a strategy that trades once in 3 weeks get judged the same as one trading daily?
- **Auto-demotion triggers** — What automatically pulls a strategy from production?

The weekly scorecard is operational but the criteria for success/failure aren't codified in doctrine.

### 2. Multi-Asset Evaluation Framework (NEW)
SOL's first test raises questions the doctrine doesn't address:
- When does an asset merit forward-testing?
- Should strategies run identical parameters across assets, or be re-optimized per asset?
- Is a trending regime gate mandatory for non-ETH assets?
- How many strategies need to ACCEPT before an asset is promoted?

### 3. Directive Enforcement (18 CYCLES, 0 ENFORCED)
35+ directives issued. 0 enforced. BTC still runs. Dead templates still in registry. The directive system remains a write-only log.

### 4. Research Card Quality (4TH CYCLE)
1 fixture file, 0 real cards. Research digest has 25 entries with trading concepts but they aren't being converted to structured, testable research cards. The pipeline from video → card → hypothesis → spec is broken at the card generation step.

### 5. Parameter Convergence (18 CYCLES, WORSENING)
87%+ compute waste. No dedup mechanism. 9 identical ACCEPTs and 15 identical REVISEs in the latest 30 outcome notes.

### 6. Indicator Taxonomy (UNCHANGED)
Doctrine should encode indicator suitability by regime:
- **Directional transition** (Vortex): All-regime on ETH
- **Trend direction** (Supertrend, EMA): Ranging + some trending
- **Momentum oscillator** (MACD, CCI): Ranging/transitional, needs gate for trending
- **Mean-reversion oscillator** (RSI, WILLR): Only ranging, fails in trending
- **Cycle/smoothed oscillator** (STC, QQE): Too noisy, insufficient edge
- **Untested** (T3, ALMA, Ichimoku): Priority test candidates

---

## Quandalf Performance Review

### Intellectual Progression: EXCELLENT
Quandalf's journal (9 entries) shows textbook scientific method:
1. **Entry 001:** Audit → identified 93% compute waste, 11 untested indicator families
2. **Entry 002-003:** Choppiness/Donchian zero-trade → diagnosed "discrete signal problem" → developed signal frequency taxonomy (continuous > cross > discrete)
3. **Entry 004:** CCI confirmed, STIFFNESS dead → pivoted with clear hypothesis resolution
4. **Entry 005:** ADX filter destructive for mean-reversion → dead indicator list growing
5. **Entry 006:** QQE/STC dead → identified transitional regime as untapped alpha → pivoted to Vortex
6. **Entry 007-008:** Vortex v1→v2c optimization → identified reversal exit as the strategy's soul → systematic stop/TP tuning with explicit predictions and post-mortem
7. **Entry 009:** Forward-testing live → strategic shift from exploration to exploitation+diversification

**Notable strength:** Quandalf consistently tests hypotheses, records what was wrong in predictions, and evolves thinking. The pivot from oscillator mean-reversion to transition detection (Entry 006→007) is the highest-quality strategic insight in the system's history.

### Directive Compliance: GOOD
- Following 4h-only ✓, ETH-primary ✓, 5:1+ R:R ✓, CHOP regime gating ✓
- Correctly abandoned dead indicators ✓
- Portfolio diversification orders target decorrelated signals ✓
- SOL exploration within scope (extends test matrix) ✓
- One concern: OBV spec uses `SUPERTd_7_3.0 == 1` with `ADX_14 > 15` — this is supertrend_follow with lower ADX threshold, not an OBV strategy. The spec note acknowledges OBV relative comparison may not be available, but should be flagged.

---

## Suggestions For Asz

### 1. Codify Forward-Test Graduation Criteria
Forward-testing is the single most important system milestone — but there's no documented graduation framework. Before the first trade fires, define:
- **Minimum live trades for verdict:** 15-20 trades (roughly a month at current frequency)
- **PF drift tolerance:** Live PF > 0.7× backtest PF = PASS. Live PF < 0.5× = FAIL.
- **Auto-promotion trigger:** If live PF > 1.5 after 20+ trades, auto-promote to real capital consideration
- **Auto-demotion trigger:** If live DD exceeds 1.5× backtest DD at any point, pause and review

Without these, the weekly scorecard generates data but nobody knows what "passing" looks like.

### 2. Three Compute Savings — 5 Minutes of Work, 90% Waste Eliminated
Still the highest-ROI engineering change available:
```python
if asset == "BTC": skip()        # 18 cycles, 0 BTC ACCEPTs ever
if timeframe == "15m": skip()    # 0 15m ACCEPTs ever
if param_hash in seen: skip()    # 87% of pipeline runs are duplicates
```
Today 42 backtests ran. At least 12 were BTC variants or 1h/15m repetitions of strategies that only work on ETH 4h. That's 28% of compute on experiments we already know will fail.

### 3. SOL as Portfolio Diversification Path
SOL 4h PF=1.20 is the first evidence a third asset could be viable. The regime profile (ranging PF=2.83, trending PF=0.22) mirrors legacy ETH strategies perfectly — meaning a trending gate would likely work. If 2-3 more strategies prove profitable on SOL 4h with trending exclusion, SOL becomes a genuine portfolio diversifier: different asset, same 4h timeframe, same infrastructure. This is cheaper than building new indicator families — we already have the data pipeline for SOL via HyperLiquid.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 16 |
|---|---|---|
| Total backtests (20260303) | 42 | +8 (SOL tests + more WILLR) |
| Forward-test lanes active | **2** | **+2 (BREAKTHROUGH — was 0)** |
| Forward-test cycles completed | 2 | NEW |
| Forward-test trades | 0 | Expected (selective strategies) |
| New ACCEPT-tier results | 7 | — (same as Update 16) |
| New all-regime profitable | 5 | — |
| Best PF ever (backtest) | 2.034 (Vortex v3a) | — |
| SOL backtests (first ever) | 2 | **+2 (NEW ASSET)** |
| SOL best PF | 1.20 (4h) | NEW |
| WILLR+STIFFNESS 0-trade runs | **9** | +6 (now tested on SOL too) |
| BTC ACCEPTs (all-time) | 0 | — (18th cycle) |
| 15m ACCEPTs (all-time) | 0 | — |
| Claude spec ACCEPT rate | 20.6% (7/34 original) | — |
| Pipeline outcomes today | 0 | — (still blocked) |
| Directives enforced | 0/35+ | — (18 cycles) |
| Research cards (real) | 0 | — (only 1 fixture) |
| Research digest entries | 25 | — |
| Pending orders | 3 | NEW (Ichimoku, CCI v3, OBV) |

### ACCEPT Leaderboard (by PF, deduplicated, top 20 + SOL — UPDATED)

| Rank | Strategy | Asset | PF | DD | Trades | Best Regime (PF) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Vortex Transition v3a 4h | ETH | **2.034** | 15.2% | 84 | Trans (3.886) | Claude |
| 2 | Supertrend tail 8:1 | ETH | 1.921 | 10.9% | 85 | Ranging (2.914) | Claude |
| 3 | Supertrend ultra ADX10 8:1 | ETH | 1.907 | 12.9% | 99 | Ranging (2.558) | Claude |
| 4 | Vortex Transition v2c 4h | ETH | 1.892 | 12.3% | 84 | Trans (2.986) | Claude |
| 5 | Vortex Transition v3b 4h | ETH | 1.885 | 11.8% | 84 | Trans (2.250) | Claude |
| 6 | Vortex Transition v2a 4h | ETH | 1.735 | 11.4% | 80 | Trending (1.812) | Claude |
| 7 | MACD 7:1 family | ETH | 1.712 | 7.5% | 161 | Ranging (2.062) | Claude |
| 8 | MACD 6:1 | ETH | 1.460 | 8.2% | 170 | Ranging (1.762) | Claude |
| 9 | RSI pullback 8:1 | ETH | 1.442 | 7.1% | 156 | Ranging (1.795) | Claude |
| 10 | Vortex Transition v2b 4h | ETH | 1.436 | 11.7% | 80 | Trending (1.582) | Claude |
| 11 | RSI pullback 7:1 | ETH | 1.421 | 13.8% | 127 | Trending (1.605) | Claude |
| 12 | Pipeline template_div | ETH | 1.419 | 10.5% | 140 | Trending (2.145*) | Pipeline |
| 13 | Supertrend 10:1 | ETH | 1.410 | 12.9% | 99 | Ranging (1.874) | Claude |
| 14 | Supertrend 5:1 | ETH | 1.395 | 12.3% | 85 | Ranging (2.002) | Claude |
| 15 | Vortex Transition v1 4h | ETH | 1.385 | 10.2% | 79 | Trans (1.613) | Claude |
| 16 | MACD 5:1 | ETH | 1.358 | 10.2% | 147 | Ranging (1.822) | Claude |
| 17 | MACD moderate | ETH | 1.353 | 10.8% | 139 | Ranging (1.465) | Claude |
| 18 | MACD wide exit | ETH | 1.347 | 6.2% | 189 | Ranging (1.872) | Claude |
| 19 | Supertrend 1h 5:1 | ETH | 1.339 | 14.3% | 99 | Ranging (1.693) | Claude |
| 20 | ema_rsi_atr precision 10:1 | ETH | 1.327 | 16.6% | 162 | Ranging (2.864) | Claude |
| — | CCI Chop Fade v2 4h | ETH | 1.255 | 16.4% | 179 | Trans (1.521) | Claude |
| — | **Vortex v3a 4h** | **SOL** | **1.200** | — | 94 | Ranging (2.830) | **Claude NEW** |

*SOL enters the leaderboard for the first time — below ACCEPT threshold but profitable.*
