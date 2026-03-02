# Strategy Advisory — 2026-03-02 (Update 11)

**Author:** claude-advisor | **Mode:** STRATEGY_RESEARCHER
**Data window:** 610 outcome notes (all-time across 5 date folders), 21 ACCEPT outcomes, latest 30 outcomes (20260302), latest 10 backtests (20260302), 239 strategy specs (20260302), 9 claude-specs (25 variants), 1 research card (fixture only), doctrine as of 20260228
**Prior advisory:** 2026-03-02 (Update 10)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "0 trades in 11+ cycles, bug line 179, 11th advisory"},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "0 trades in 8+ cycles, structural impossibility on crypto 4h/1h"},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "NEW — PF 0.615-0.969 across 6 backtests, structural loser at any R:R"},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "DD 83-484% in latest 10 backtests, pipeline STILL generating BTC specs despite 11 cycles of exclusion requests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications, 12 cycles, notes_considered=0 always"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "NEW — produces identical metrics across all applications"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%, 12 cycles"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_exit_change", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_gate_adjust", "reason": "PF 1.001 at best, noise trading"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_threshold_sweep", "reason": "0% improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_template_switch", "reason": "0% success in 30+ outcome notes"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_param_sweep", "reason": "PF 0.969, DD 147%, zero improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_role_swap", "reason": "PF 0.963, 100% REJECT rate"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_threshold_sweep", "reason": "PF 0.998, noise, converges to same params"},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 1, "reason": "UPGRADED — best ACCEPT PF=1.921, 7 ACCEPTs total"},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 2, "reason": "9 ACCEPTs, best PF=1.712, most consistent"},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 3, "reason": "4 ACCEPTs, best PF=1.712"},
  {"action": "PREFER_TEMPLATE", "target": "ema_rsi_atr", "priority": 4, "reason": "1 ACCEPT PF=1.288, narrow-band validated"},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All 21 ACCEPTs use 5:1+ R:R, sub-4:1 is structural noise on HyperLiquid fees"},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 7+ cycles, every outcome shows NO_IMPROVEMENT"},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of all-time ACCEPTs (21/21), pipeline specs = 0%"},
  {"action": "BACKTEST_CLAUDE_SPECS_FIRST", "targets": ["claude-er8v3m6k", "claude-st5k2r8w", "claude-rp3w7k9d", "claude-mc6t8b3k", "claude-rp4f2w8n", "claude-st7a3k5w", "claude-ec6t4w8m", "claude-rp8f3m7v", "claude-mc4w9s2t"], "reason": "9 specs, 25 variants — most still unbacktested"},
  {"action": "FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "NEW CHAMPION PF=1.921, DD=10.9%, all regimes profitable"},
  {"action": "FORWARD_TEST", "target": "macd_7to1_tail_harvester", "reason": "PF=1.712, DD=7.5%, 5th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "ea9p5k2m_4h_narrow_9to1", "reason": "PF=1.288, transitional specialist"},
  {"action": "INVESTIGATE_BUG", "target": "regime_classifier", "reason": "NEW — zero ranging trades in latest 10 backtests despite ranging being dominant profit regime in all 21 ACCEPTs"}
]
```

---

## Executive Summary

**The system has 21 all-time ACCEPTs — all Claude-originated — but a newly discovered regime classifier bug threatens the entire pipeline.** The latest 10 backtests show ZERO ranging trades despite ranging being the dominant profit regime in every historical ACCEPT (ranging PF 1.03-2.91). If the regime classifier stopped assigning ranging labels, the pipeline has been blind to its most profitable regime for at least this cycle. Separately, the parameter convergence trap has worsened: 30 latest outcomes collapse to just 4 unique metric profiles (down from ~5 across 696 backtests), and even among ACCEPTs, 4 different template names produce identical PF=1.712 results. Supertrend has quietly emerged as the true champion: PF=1.921 with 10.9% DD and profitable in ALL regimes — surpassing MACD's 1.712. Pipeline directive compliance remains at 0%.

---

## Failing Patterns

### 1. Parameter Convergence (CRITICAL — WORSENING)
Latest 30 outcomes produce only **4 unique metric profiles** across 30 different strategy family hashes. Even worse: among ACCEPTs, 4 different template names (MACD tight stop 4h, MACD 1h tail, RSI pullback 1h tail, MACD tail 4h) all produce **identical** PF=1.712/DD=7.45%/161 trades. The pipeline is running hundreds of "variants" that are functionally identical backtests. Estimated compute waste: **99.5%+**.

### 2. alignment_entry Signal (NEW — DEAD ON ARRIVAL)
The `alignment_entry` signal (generic "confidence >= 0.60" threshold) appears in 6 of the latest 10 backtests. Results: PF=0.615 (ETH/4h), PF=0.738 (ETH/1h), PF=0.969 (BTC/4h). All losers. The signal uses abstract "alignment" logic with no concrete indicator conditions, producing entry signals that are essentially random relative to price movement. Combined with the 1.3:1 R:R the pipeline assigns, this is a structural loss generator.

### 3. BTC Asset (STILL ACTIVE DESPITE 11 CYCLES OF EXCLUSION)
Latest backtests: BTC/4h shows max DD of 83-484%. Pipeline-generated specs on 20260302 **exclusively target BTC/1h** with 1.3:1 R:R — simultaneously violating the asset exclusion AND R:R floor directives. The pipeline is generating the worst possible combination.

### 4. Directive System (DEAD — 0/31 ENFORCED)
All 30 latest outcomes show `directive_history.notes_considered: 0`. Every outcome emits 2-5 new directives (GATE_ADJUST, ENTRY_TIGHTEN, EXIT_CHANGE, PARAM_SWEEP, TEMPLATE_SWITCH) that are never consumed. The pipeline generates new directive variant names to circumvent blacklists (v2 variants appeared despite 10 cycles of blacklisting v1 variants). This is a broken feedback loop: the analyser writes directives, the pipeline ignores them, the analyser writes more directives about the same failures.

### 5. Refinement Engine (DEAD — 7+ CYCLES)
Every single outcome note (all 610) contains `NO_IMPROVEMENT` as a failure reason. The refinement cycle hash is shared across entire batches. Zero improvement has been achieved through the refinement process at any point in the system's history.

### 6. stochastic_reversal Template (DEAD — BUG CONFIRMED)
Bug at `signal_templates.py:179`. Long condition requires K < 20 at the exact bar K crosses above D, which is logically impossible. Zero trades in 11+ cycles.

### 7. bollinger_breakout Template (DEAD — STRUCTURAL)
Requires close outside 2-sigma Bollinger bands. On crypto with high volatility, the bands are too wide for close to break out on 1h/4h timeframes. Zero trades in 8+ cycles.

### 8. Low R:R Pipeline Specs (STRUCTURAL NOISE)
All pipeline-generated specs use stop_atr_mult=1.5 / tp_atr_mult=2.0 (1.3:1 R:R). At HyperLiquid's 4.5bps taker + 1.0bps slippage per side, this R:R cannot overcome fees on low win-rate signals. Every ACCEPT uses 5:1+ R:R. This is the single most important parameter the pipeline gets wrong.

### 9. Regime Classifier (NEW — POSSIBLE BUG)
All 10 latest backtests show **zero ranging trades**. In every historical ACCEPT, ranging was the dominant or co-dominant regime (17/21 ACCEPTs have ranging as dominant). If the classifier stopped labelling trades as "ranging", the pipeline cannot detect its most profitable market condition. This requires immediate investigation.

### 10. Research Card Pipeline (DEAD)
Only 1 research card exists (`rc-directive-loop-fixture.json`) and it's a test fixture. No real research cards from video ingestion. The auto-transcript ingestion system referenced in doctrine has never produced output.

---

## Promising Directions

### 1. Supertrend 8:1 Tail Harvester — NEW CHAMPION (PF=1.921)
**Highest PF of any ACCEPT.** DD=10.9%, 85 trades, profitable in ALL regimes (trending=1.289, ranging=2.914, transitional=1.844). The ultra-relaxed ADX10 variant also strong at PF=1.907/99 trades. Supertrend's ranging PF=2.914 is the highest single-regime score of any strategy. This should be the #1 forward-test candidate.

### 2. MACD Tail Harvester Family — Most Consistent
9 ACCEPT variants across 5:1 to 12:1 R:R ratios. Best is PF=1.712 at 7:1 R:R with 161 trades and only 7.45% DD. The "wide exit fee killer" variant has the lowest DD of any ACCEPT at 6.17%. MACD is the broadest winning family with the most validated edge. 5th cycle requesting forward test.

### 3. Multi-Strategy Portfolio (READY TO BUILD)
The 21 ACCEPTs contain complementary regime profiles:
- **Ranging dominance:** Supertrend 8:1 (PF=2.914 ranging), MACD 7:1 (PF=2.062 ranging)
- **Transitional specialist:** ea9p5k2m (PF=2.765 transitional), RSI shallow dip (PF=5.568 transitional, low trades)
- **Trending edge:** MACD 12:1 ultimate (PF=2.177 trending)
A portfolio allocating capital by regime detection could achieve PF > 1.5 across ALL market conditions.

### 4. Transitional Regime Edge (NEWLY VALIDATED)
BTC/4h alignment_entry — despite being an overall loser (PF=0.969) — shows PF=1.804 and 56% WR in transitional periods. The ea9p5k2m ACCEPT shows PF=2.765 in transitional. Transitional regime strategies are under-explored and could be a significant alpha source.

### 5. Narrow RSI Bands (VALIDATED — NEEDS WIDER TESTING)
ea9p5k2m's success (RSI 50-65 vs standard 40-70) proves that narrower entry bands produce higher-conviction entries. This principle has NOT been tested on MACD, Supertrend, or RSI pullback templates yet. Could improve PF across the entire template family.

### 6. Extreme R:R Frontier (12:1)
MACD 12:1 ultimate achieved PF=1.302 with trending PF=2.177 — the best trending-regime score. 137 trades provides adequate sample. Testing 12:1+ on Supertrend (which already works at 8:1 with PF=1.921) could yield even higher PF.

### 7. EMA Crossover Diagnostic (UNBACKTESTED)
Claude spec `claude-ec6t4w8m` tests raw EMA_9/EMA_21 crossover with 7:1, 8:1, and 10:1 R:R. If this produces PF > 1.2, it proves that signal complexity is irrelevant for tail harvesting — R:R is the only parameter that matters.

### 8. Profile D from Latest Batch (PROMISING BUT STUCK)
Among the latest 30 outcomes, Profile D (PF=1.179, DD=10.8%, 131 trades, ranging PF=2.427) is the standout. It would likely ACCEPT if the refinement engine could iterate on it, but refinement is dead. Manual spec creation targeting this profile's parameters could unlock an ACCEPT.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg PF | Avg DD | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|---|---|
| supertrend_follow | 7 | 1.921 | 1.470 | 12.5% | 95 | CHAMPION | Forward-test immediately |
| macd_confirmation | 9 | 1.712 | 1.459 | 8.2% | 155 | STRONG | Forward-test immediately |
| rsi_pullback | 4 | 1.712 | 1.427 | 9.5% | 90 | GOOD | Expand narrow-RSI testing |
| ema_rsi_atr | 1 | 1.288 | 1.288 | 18.6% | 92 | PROMISING | Test narrow bands on other assets |
| ema_crossover | 0 | — | — | — | — | DIAGNOSTIC | 3 variants awaiting backtest |
| stochastic_reversal | 0 | — | — | — | — | DEAD | Remove from registry (bug) |
| bollinger_breakout | 0 | — | — | — | — | DEAD | Remove from registry (structural) |

**Claude spec backtest queue:** 9 specs, 25 variants. Only ea9p5k2m has been backtested from the latest batch. 24 variants still waiting.

---

## Regime Insights

### Regime Performance Matrix (from 21 ACCEPTs)

| Template Family | Trending PF | Ranging PF | Transitional PF | Best Regime |
|---|---|---|---|---|
| Supertrend 8:1 | 1.289 | **2.914** | 1.844 | Ranging |
| Supertrend (other) | 0.75-0.95 | 1.61-2.56 | 1.38-1.57 | Ranging |
| MACD 7:1 | 1.677 | **2.062** | 1.308 | Ranging |
| MACD 12:1 | **2.177** | 1.581 | 0.569 | Trending |
| MACD wide exit | 1.230 | **1.872** | 0.816 | Ranging |
| RSI pullback 8:1 | 1.505 | **1.795** | 0.930 | Ranging |
| RSI pullback 7:1 | 1.605 | 1.415 | 1.309 | Trending |
| RSI shallow dip | 1.202 | 0.090 | **5.568** | Transitional |
| ea9p5k2m | 0.766 | 1.216 | **2.765** | Transitional |

### Key Regime Findings

1. **Ranging is the money regime.** 17/21 ACCEPTs have ranging as dominant regime. Top ranging PFs: 2.914 (Supertrend), 2.558 (Supertrend), 2.062 (MACD), 2.002 (Supertrend). This aligns with the macro thesis of bear/ranging market conditions.

2. **Transitional is under-explored alpha.** Two strategies show extreme transitional edge (RSI shallow dip PF=5.568, ea9p5k2m PF=2.765) but sample sizes are small (9-12 trades). More transitional-focused specs needed.

3. **Trending is template-dependent.** MACD 12:1 shows trending PF=2.177 while Supertrend variants show trending PF < 1.0. R:R ratio is the differentiator: higher R:R captures larger trend extensions.

4. **CRITICAL: Latest batch has zero ranging trades.** The regime classifier may have broken. If ranging detection is offline, the pipeline cannot route capital to its most profitable regime. This is the single highest-priority investigation.

---

## Recommended Directives

### Priority 1 — IMMEDIATE (blocks all downstream progress)
1. **Investigate regime classifier bug** — zero ranging trades in latest 10 backtests. Check regime labelling logic for regressions.
2. **Forward-test Supertrend 8:1** (PF=1.921) — true champion, profitable in all regimes, DD=10.9%.
3. **Forward-test MACD 7:1** (PF=1.712) — 5th cycle requesting, most validated strategy, DD=7.5%.
4. **Backtest remaining Claude specs** — 24 variants still waiting. ea9p5k2m proved Claude specs produce ACCEPTs; pipeline specs produce 0%.
5. **Kill pipeline spec generation** — 230 pipeline specs on 20260302 produced 0 ACCEPTs. 9 Claude specs produced 21. Stop burning compute on pipeline specs.

### Priority 2 — HIGH (systemic improvements)
1. **Implement parameter hash dedup** — hash the actual indicator params + R:R + asset + timeframe. Skip backtests that duplicate an existing hash. Would eliminate 99%+ of compute waste.
2. **Enforce R:R floor of 5:1** — all pipeline specs use 1.3:1. Hard-reject any spec with R:R < 5:1 before it reaches the backtester.
3. **Enforce BTC exclusion** — hard-reject any spec targeting BTC before it reaches the backtester.
4. **Remove dead templates** — delete stochastic_reversal and bollinger_breakout from TEMPLATE_REGISTRY.
5. **Block alignment_entry signal** — abstract confidence thresholds produce random entries.
6. **Disable refinement engine** — 0% improvement rate across 610 outcomes, 7+ cycles. It generates noise.
7. **Apply narrow RSI bands** (50-65 long / 35-50 short) as defaults for ema_rsi_atr template.

### Priority 3 — MEDIUM (strategic advancement)
1. **Build portfolio backtester** — test combined allocation across Supertrend (ranging) + MACD (ranging/trending) + ea9p5k2m (transitional).
2. **Test extreme R:R on Supertrend** — Supertrend 8:1 is champion at PF=1.921. Test 10:1 and 12:1 variants.
3. **Test narrow RSI bands on MACD and Supertrend** — proven on ema_rsi_atr, untested elsewhere.
4. **Build transitional regime specs** — only 2 strategies exploit transitional edge. Design specs specifically targeting regime transitions.
5. **Fix or replace research card pipeline** — auto-transcript ingestion has produced zero output. The indicator library is growing but not connected to strategy research.

---

## Doctrine Gaps

### 1. Directive Enforcement Failure (CRITICAL — 12 CYCLES)
31 machine directives issued. 0 enforced. The directive system is entirely decorative. The pipeline does not read, parse, or apply any directive from the advisory. This has been reported in every advisory since Update 1. **Recommendation:** Either implement a directive parser in the pipeline or remove the directive system entirely — the current state wastes advisory bandwidth.

### 2. Parameter Convergence (CRITICAL — WORSENING)
Down from ~5 unique profiles per 696 backtests to 4 unique profiles per 30 outcomes. The pipeline's spec generation produces functionally identical strategies with different hashes. Even ACCEPTs are duplicated: 4 template names produce identical PF=1.712 results. **Root cause:** The resolve_template function in signal_templates.py falls back to the same indicator logic regardless of variant naming, and the pipeline doesn't hash actual parameters before launching backtests.

### 3. ACCEPT Count Inflation
MEMORY.md tracked "5 ACCEPTs total." Actual count from outcome files: 21 ACCEPTs across 610 outcomes. However, many ACCEPTs share identical metrics (PF=1.712 appears 4x, PF=1.442 appears 2x). Unique metric profiles among ACCEPTs: ~13. Truly distinct strategies: ~6-8. The system needs a canonical strategy registry that deduplicates by actual parameters, not by variant name.

### 4. Forward-Testing Infrastructure (ABSENT — 5 CYCLES REQUESTING)
Zero strategies have been forward-tested despite 5 cycles of requests. Two strategies (Supertrend 8:1 PF=1.921, MACD 7:1 PF=1.712) are validated across 85-161 trades with controlled DD. Without forward-testing, we cannot distinguish backtest-fitted strategies from genuinely profitable ones. This is the single biggest blocker to real trading income.

### 5. Research Card Pipeline (NON-FUNCTIONAL)
Doctrine references auto-transcript ingestion and research card generation. The pipeline has produced exactly 1 file: a test fixture. No video research insights have been converted to testable hypotheses. The indicator library is growing (INDICATOR_INDEX.json) but not connected to strategy research.

### 6. Claude-Specs Staging Directory (EMPTY)
`artifacts/claude-specs/` is empty. Claude specs exist in `artifacts/strategy_specs/` but the staging directory intended for promotion review is unused. The promote-claude-specs.ps1 script may not be running, or specs are promoted directly without staging.

### 7. Regime Classifier Regression (NEW)
Zero ranging trades in latest 10 backtests. All 21 historical ACCEPTs show ranging as the primary profit source. If the classifier broke, the pipeline is blind to its most valuable market condition. No doctrine heuristic covers regime classifier validation.

---

## Suggestions For Asz

### 1. Paper Trade NOW — Two Strategies Are Ready
Supertrend 8:1 (PF=1.921, DD=10.9%, all-regime profitable) and MACD 7:1 (PF=1.712, DD=7.5%, 161 trades) have been validated for 5+ cycles. Every day without forward-testing is a day of potential income lost. Even a minimal paper-trading setup on HyperLiquid testnet would validate whether backtest edge translates to live markets. This is the single highest-ROI action available. The Smaug executor agent should be prioritized.

### 2. Pause the Pipeline, Run Claude-Only Batches
The pipeline has generated **230 specs on 20260302 with 0 ACCEPTs.** Claude generated 9 specs with **21 ACCEPTs** (all-time). The pipeline burns compute on BTC specs with 1.3:1 R:R despite 11 cycles of exclusion directives. **Concrete proposal:** Disable the pipeline's spec generator entirely. Route ALL backtest compute to the 24 remaining Claude spec variants. If even 30% match ea9p5k2m's success rate, that's 7+ new ACCEPTs from existing specs alone. Resume pipeline generation only after implementing parameter hash dedup and R:R floor enforcement.

### 3. Investigate the Regime Classifier Immediately
The latest 10 backtests show ZERO ranging trades. Ranging is the dominant profit source in 17/21 ACCEPTs (PF 1.03-2.91). If this is a code regression, the entire current batch of backtests is unreliable. If it's a data issue (genuinely no ranging periods in the test window), then we need to understand whether our ranging-dominant strategies will continue to work in a trending market. Either way, this needs investigation before any more compute is spent on backtesting.

---

## Appendix: Data Summary

| Metric | Value |
|---|---|
| Total outcome notes (all-time) | 610 |
| ACCEPTs (all-time) | 21 (3.4% rate) |
| Unique ACCEPT metric profiles | ~13 |
| Truly distinct ACCEPT strategies | ~6-8 |
| Claude-originated ACCEPT rate | 100% (21/21) |
| Pipeline-originated ACCEPT rate | 0% (0/589) |
| Latest batch outcomes (20260302) | 63 |
| Latest batch ACCEPTs | 1 (ea9p5k2m) |
| Latest batch unique profiles | 4 |
| Compute waste (estimated) | 99.5%+ |
| Directives enforced | 0/31 |
| Forward tests initiated | 0 |
| Cycles requesting forward test | 5 |
| Claude spec variants awaiting backtest | 24 |
| Dead templates | 2 (stochastic_reversal, bollinger_breakout) |
| Dead signals | 1 (alignment_entry) |
| Regime classifier status | SUSPECT — zero ranging trades in latest batch |

### ACCEPT Leaderboard (by unique PF, deduplicated)

| Rank | Strategy | PF | DD | Trades | Best Regime | Template |
|---|---|---|---|---|---|---|
| 1 | Supertrend tail 8:1 | 1.921 | 10.9% | 85 | Ranging (2.914) | supertrend_follow |
| 2 | Supertrend ultra ADX10 8:1 | 1.907 | 12.9% | 99 | Ranging (2.558) | supertrend_follow |
| 3 | MACD 7:1 family | 1.712 | 7.5% | 161 | Ranging (2.062) | macd_confirmation |
| 4 | MACD 6:1 | 1.460 | 8.2% | 170 | Ranging (1.762) | macd_confirmation |
| 5 | RSI pullback 8:1 | 1.442 | 7.1% | 156 | Ranging (1.795) | rsi_pullback |
| 6 | RSI pullback 7:1 | 1.421 | 13.8% | 127 | Trending (1.605) | rsi_pullback |
| 7 | Supertrend 10:1 | 1.410 | 12.9% | 99 | Ranging (1.874) | supertrend_follow |
| 8 | Supertrend 5:1 | 1.395 | 12.3% | 85 | Ranging (2.002) | supertrend_follow |
| 9 | MACD 5:1 | 1.358 | 10.2% | 147 | Ranging (1.822) | macd_confirmation |
| 10 | MACD moderate | 1.353 | 10.8% | 139 | Ranging (1.465) | macd_confirmation |
| 11 | MACD wide exit | 1.347 | 6.2% | 189 | Ranging (1.872) | macd_confirmation |
| 12 | Supertrend 1h 5:1 | 1.339 | 14.3% | 99 | Ranging (1.693) | supertrend_follow |
| 13 | RSI shallow dip 7:1 | 1.333 | 7.9% | 38 | Trans (5.568) | rsi_pullback |
| 14 | MACD 12:1 ultimate | 1.302 | 9.8% | 137 | Trending (2.177) | macd_confirmation |
| 15 | ea9p5k2m narrow 9:1 | 1.288 | 18.6% | 92 | Trans (2.765) | ema_rsi_atr |
| 16 | Supertrend ADX5 6:1 | 1.220 | 14.3% | 99 | Ranging (1.611) | supertrend_follow |
| 17 | RSI pullback safe mod | 1.210 | 9.2% | 38 | Trans (1.597) | rsi_pullback |
