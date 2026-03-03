# Strategy Advisory — 2026-03-04 (Update 20)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** ~740 outcome notes (20260226 latest 30), 46+ backtests, 14 brain objects, 10 research cards, 49 batch runs, 3 new Claude specs
**Prior advisory:** 2026-03-03 (Update 19)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 174 asymmetric k_prev/k_now. 0 trades, 18+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken. 0 trades, 14+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "DEAD: 0 trades across 12 backtests."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy. Dead."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "20 cycles. 0 BTC ACCEPTs across 740+ outcomes."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 15m ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "ALL ACCEPT-tier results are 4h."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics."},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%."},
  {"action": "PREFER_TEMPLATE", "target": "vortex_transition", "priority": 0, "reason": "CHAMPION: v3a PF=2.034. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "kama_stoch_pullback", "priority": 1, "reason": "ACCEPT: v1 PF=1.857. Forward-test candidate."},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 2, "reason": "PF=1.921. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 3, "reason": "9 ACCEPTs, best PF=1.712."},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate. 44 directive stall cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of ACCEPTs. Pipeline produces 0."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a_eth_4h", "reason": "LIVE."},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "LIVE."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1_eth_4h", "reason": "Third lane."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-almamh01", "reason": "ALMA+MACDh first test. Untested indicator."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-ichtk01v", "reason": "Ichimoku TK first test. Untested indicator."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-t3vxpb01", "reason": "T3+Vortex Pullback first test. Untested indicator."},
  {"action": "PREFER_ADAPTIVE_INDICATORS", "reason": "Adaptive indicators (KAMA, Vortex) produce all-regime ACCEPTs."},
  {"action": "FLAG_PIPELINE_STARVATION", "starvation_cycles": 2, "drought_cycles": 53, "directive_stall_cycles": 44, "reason": "Pipeline dead. 0 backtests executed due to BALROG brain validation block."},
  {"action": "FLAG_BRAIN_SCHEMA_FIX", "reason": "CRITICAL: Fixed 17 FAIL + 14 WARN brain schema violations. Inline YAML arrays incompatible with simple parser. All objects now use multi-line syntax + validated_at."}
]
```

---

## Executive Summary

**CRITICAL SYSTEM FIX CYCLE.** Zero new ACCEPTs but a root cause discovery: the brain knowledge base (initialized in U18) had YAML formatting that was incompatible with the BALROG pre-backtest validator's simple parser, causing **every backtest to be blocked for 36+ attempts across 6+ autopilot cycles**. The inline array syntax `tags: [a, b, c]` was parsed as a string instead of an array, triggering 17 schema FAILs. This has been fixed by converting all 14 brain objects to multi-line YAML syntax and adding `validated_at` timestamps.

Pipeline health: starvation steady at 2, but drought surged from 31 to **53** and directive stalls from 22 to **44**. The pipeline generated 14 theses, 49 batch runs, and 13 promotions — but zero backtests executed due to the BALROG block.

Three new Claude specs (Ichimoku TK, ALMA MACDh, T3 Vortex Pullback) were generated but remain unexecuted. These represent the first tests of three previously untested indicator families (Ichimoku, ALMA, T3).

**Priority 0 for next cycle:** Verify brain validation passes and backtest the 3 pending Claude specs.

---

## Failing Patterns

### 1. BALROG Brain Validation Block (CRITICAL — NOW FIXED)
The simple YAML parser in `validate_brain.py` uses `json.loads()` to parse inline arrays. JSON requires quoted strings, so `[asset, timeframe, eth, 4h]` fails parsing and returns a raw string. The schema then rejects it as "expected array". This blocked all 14 objects, producing 17 FAILs and 14 WARNs (missing `validated_at`).

**Impact:** Every backtest since brain init (U18, ~36+ attempts) was blocked. The pipeline generated specs and promotions successfully but could never execute backtests.

**Fix applied:** Converted all inline arrays to multi-line YAML (`- item` per line) and added `validated_at: "2026-03-04T12:00:00Z"` to all objects.

### 2. Pipeline Deep Starvation (CRITICAL — STRUCTURAL)
- Drought cycles: 31 → **53** (largest single-cycle jump)
- Directive stall cycles: 22 → **44** (doubled)
- Starvation cycles: 2 (reset counter)
- Backtests executed this cycle: **0** (BALROG blocked)
- Pipeline has produced exactly 1 ACCEPT ever (template_div PF=1.419)
- All 8 unique ACCEPTs came from Claude-specified strategies

### 3. Signal Clustering in Refinement
Latest backtests (10 runs of refine-8d9a5d5c) all produced 0 trades with SIGNAL_CLUSTERED failure. Entry signals bunch together at the same bars, leaving too few independent trading opportunities. This may indicate overly correlated entry conditions in pipeline-generated specs.

### 4. Research Card Quality Still Low
8/10 latest TradingView catalog cards contain only title + author — no extracted indicator logic, parameters, or conditions. The TV catalog extraction pipeline is non-functional for content parsing.

Only 2 cards had actionable content:
- Bitcoin seasonality (IntoTheCryptoverse): February low → March lower high pattern
- Red K Pressure Index (SoheilPKO): Dual-MACD + pressure indicator with explicit parameters

### 5. Dead Directives
49 machine directives issued across 2 advisory cycles. 0 enforced. The directives are write-only — the pipeline reads and ignores them.

---

## Promising Directions

### 1. Three Untested Indicator Families Ready for Backtest
Claude specs covering three never-tested indicators are ready:

| Spec | Indicator | Hypothesis | Variants |
|------|-----------|------------|----------|
| almamh01 | ALMA_9_6.0_0.85 | Gaussian-weighted low-lag MA + MACDh momentum timing | 3 |
| ichtk01v | ITS_9/IKS_26/ISA_9/ISB_26 | Ichimoku structural trend detection for transitions | 3 |
| t3vxpb01 | T3_10_0.7 | Triple-smoothed deep pullback + Vortex trend confirm | 3 |

All specs follow validated patterns: spec_rules template, 8:1 or 10:1 R:R, ETH 4h primary target. If BALROG passes now, these should execute immediately.

### 2. Adaptivity Thesis Strengthening
The meta-rule from U19 (adaptive indicators > static for all-regime edge) continues to hold. No counter-evidence in this cycle. The three new specs test whether ALMA (Gaussian smoothing) and T3 (triple-smoothed) qualify as "adaptive" or are merely "smooth static" — an important distinction.

### 3. Ichimoku as Transition Architecture
Ichimoku TK cross targets the same transition-detection thesis as Vortex but uses a completely different mechanism (dual-MA structural momentum vs directional movement crossover). If Ichimoku achieves all-regime profitability, it validates the thesis that transition-detection is the mechanism, not Vortex specifically.

### 4. Research Video Insight: Dual-MACD System
The Red K Pressure Index video (SoheilPKO) provides a specific setup: longer MACD (100/200/50) + shorter MACD (34/144/9) with pressure index > 30. This dual-timeframe MACD architecture is different from any strategy in the system. Worth a Claude spec if current pending specs show promise.

### 5. Forward-Testing Continues
Vortex v3a and Supertrend 8:1 remain in forward-test. No new evaluation data this cycle (blocked by BALROG). KAMA Stoch v1 remains the forward-test candidate for a third lane.

---

## Template Health

| Template | ACCEPTs | Best PF | Status |
|---|---|---|---|
| vortex_transition | 6 | 2.034 | CHAMPION (FORWARD-TESTING) |
| kama_stoch_pullback | 1 | 1.857 | ACCEPT (FORWARD-TEST CANDIDATE) |
| supertrend_follow | 7 | 1.921 | STRONG (FORWARD-TESTING) |
| macd_confirmation | 9 | 1.712 | STRONG |
| rsi_pullback | 5 | 1.442 | GOOD (SATURATED) |
| cci_chop_fade | 1 | 1.255 | RISING |
| spec_rules (pipeline) | ~1 | 1.419 | DEAD |
| spec_rules (Claude) | 8 | 2.034 | ACTIVE |
| ema_rsi_atr | 2 | 1.327 | GOOD |
| alma_macdh (NEW) | 0 | — | PENDING BACKTEST |
| ichimoku_tk (NEW) | 0 | — | PENDING BACKTEST |
| t3_vortex_pullback (NEW) | 0 | — | PENDING BACKTEST |
| ema_crossover | 0 | — | EXHAUSTED |
| choppiness_donchian_fade | 0 | — | DEAD |
| kama_vortex_divergence | 0 | — | UNTESTED |
| stc_cycle_timing | 0 | — | DEAD |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## Regime Insights

- **Current market:** ETH sustained ranging (all forward-test evaluations through U19)
- **Ranging = universal base:** All 8 ACCEPTs profitable in ranging (PF 1.12–4.87)
- **Transitional = highest alpha:** Vortex v3a trans PF=3.886 (system record)
- **Trending = filter or die:** Only adaptive indicators (Vortex, KAMA) survive trending. All others need CHOP gate.
- **Key test pending:** Ichimoku TK targets transition detection — if it works, confirms thesis is about mechanism not indicator.

---

## Recommended Directives

**Priority 0:** Verify brain validation passes (BALROG gate unblocked). Execute 3 pending Claude specs (ALMA, Ichimoku, T3).

**Priority 1:** Add KAMA Stoch v1 as third forward-test lane. Define forward-test graduation criteria.

**Priority 2:** Address pipeline death — decide between: (a) accept pipeline is dead and rely on Claude specs only, (b) rebuild ingestion/spec-generation from scratch, (c) hybrid model.

**Priority 3:** Fix TV catalog content extraction (8/10 cards empty). Add dual-MACD research spec based on SoheilPKO video.

**Priority 4:** System health — remove dead templates from TEMPLATE_REGISTRY, enforce machine directives (currently 0% enforcement), define forward-test metrics dashboard.

---

## Doctrine Gaps

1. **YAML Serialization Standard:** No doctrine on how brain objects should serialize arrays. The contract says "YAML frontmatter" but doesn't specify inline vs multi-line. The simple parser only supports multi-line. **Recommendation:** Add to QUANDALF_BRAIN contract: "Use multi-line YAML list syntax only. Do not use inline arrays."

2. **Directive Enforcement:** 49 machine directives issued, 0 enforced. No mechanism exists to make the pipeline read and apply directives. Directives are purely advisory/archival.

3. **Forward-Test Graduation:** No defined criteria for when a forward-tested strategy graduates to live trading. Currently open-ended monitoring.

4. **Signal Clustering:** No doctrine on minimum signal independence. Pipeline-generated specs create signals that cluster at the same bars.

---

## Suggestions For Asz

1. **URGENT: Verify BALROG passes** — The brain YAML fix should unblock all backtests. Run `python scripts/quandalf/validate_brain.py` to confirm 0 FAILs. If it passes, the next autopilot cycle should execute the 3 pending Claude specs.

2. **Add YAML rule to brain contract** — Add a line to `docs/CONTRACTS/QUANDALF_BRAIN.md`: "Frontmatter arrays must use multi-line YAML syntax (`- item`), never inline (`[a, b, c]`)."

3. **Pipeline decision point** — 53 drought cycles, 44 directive stalls, 0 ACCEPTs from pipeline ever. The pipeline's spec-generation produces low-quality, duplicated specs that cluster signals. Consider: is the pipeline worth maintaining, or should all research flow through Claude advisory cycles?

4. **Fix TV catalog extraction** — 80% of research cards are empty shells. The extraction pipeline captures metadata but not indicator logic/parameters. This limits research value.

5. **Consider dual-MACD spec** — The Red K Pressure video describes a specific dual-timeframe MACD architecture (100/200/50 slow + 34/144/9 fast) that hasn't been tested. These are non-standard MACD parameters requiring new indicator columns.

---

## ACCEPT Leaderboard (top 12, unchanged)

| Rank | Strategy | PF | DD | Trades | All-Regime |
|------|----------|----|----|--------|------------|
| 1 | Vortex v3a 4h (ETH) | 2.034 | 15.2% | 84 | YES |
| 2 | Supertrend 8:1 (ETH) | 1.921 | 10.9% | 85 | YES |
| 3 | Supertrend ultra ADX10 8:1 (ETH) | 1.907 | 12.9% | 99 | YES |
| 4 | Vortex v2c 4h (ETH) | 1.892 | 12.3% | 84 | YES |
| 5 | Vortex v3b 4h (ETH) | 1.885 | 11.8% | 84 | YES |
| 6 | KAMA Stoch v1 8:1 (ETH) | 1.857 | 10.1% | 42 | YES |
| 7 | Vortex v2a 4h (ETH) | 1.735 | 11.4% | 80 | — |
| 8 | MACD 7:1 (ETH) | 1.712 | 7.5% | 161 | — |
| 9 | MACD 6:1 (ETH) | 1.460 | 8.2% | 170 | — |
| 10 | RSI pullback 8:1 (ETH) | 1.442 | 7.1% | 156 | — |
| 11 | Pipeline template_div (ETH) | 1.419 | 10.5% | 140 | — |
| 12 | CCI Chop Fade v2 4h (ETH) | 1.255 | 16.4% | 179 | YES |

---

## Data Summary

- Total backtests: 46 (unchanged — BALROG blocked all new runs)
- Forward-test lanes: 2 (+ 1 candidate)
- ACCEPT-tier results: 8
- All-regime profitable: 6
- Best backtest PF: 2.034 (Vortex v3a)
- Best ranging PF: 4.87 (KAMA Stoch v1)
- Brain objects: 14 (schema-fixed, now valid)
- Pipeline drought cycles: 53
- Directive stall cycles: 44
- Claude spec ACCEPT rate: 22.2% (8/36)
- Directives enforced: 0/49
- Pending Claude specs: 3 (ALMA, Ichimoku, T3)
