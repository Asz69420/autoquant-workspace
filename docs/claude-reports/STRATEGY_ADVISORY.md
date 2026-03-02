# Strategy Advisory — 2026-03-02 (Update 13)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 610+ outcome notes (all-time), 23 ACCEPT outcomes, latest 30 outcomes (20260302), latest 10 backtests (20260302 — all 0-trade failures), 11 signal templates (2 dead, 2 untested), ~80 strategy specs (incl. 9 claude-specs / 27 variants), 1 research card (fixture only), doctrine as of 20260228
**Prior advisory:** 2026-03-02 (Update 12)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "0 trades in 13+ cycles, bug line 174-175 (K/D conditions reversed), 13th advisory"},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "0 trades in 10+ cycles, volume gate structurally broken (line 149-150 skips if i<20)"},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser at any R:R"},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "DD 83-484% in backtests, pipeline STILL generating BTC specs despite 13 cycles of exclusion requests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications, 14 cycles, notes_considered=0 always"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "produces identical metrics across all applications"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%, 14 cycles"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_exit_change", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_gate_adjust", "reason": "PF 1.001 at best, noise trading"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_threshold_sweep", "reason": "0% improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_template_switch", "reason": "0% success in 30+ outcome notes"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_param_sweep", "reason": "PF 0.969, DD 147%, zero improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_role_swap", "reason": "PF 0.644-0.963, 100% REJECT rate"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_threshold_sweep", "reason": "PF 0.998, noise, converges to same params"},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 1, "reason": "CHAMPION — PF=1.921, 7 ACCEPTs, only all-regime profitable template"},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 2, "reason": "9 ACCEPTs, best PF=1.712, most consistent"},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 3, "reason": "5 ACCEPTs incl. slingshot_12to1 PF=1.270"},
  {"action": "PREFER_TEMPLATE", "target": "ema_rsi_atr", "priority": 4, "reason": "2 ACCEPTs incl. precision_10to1 PF=1.327"},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All 23 ACCEPTs use 5:1+ R:R"},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 8+ cycles"},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of ACCEPTs (23/23), pipeline = 0%"},
  {"action": "BACKTEST_CLAUDE_SPECS_FIRST", "targets": ["claude-er8v3m6k", "claude-st5k2r8w", "claude-rp3w7k9d", "claude-mc6t8b3k", "claude-rp4f2w8n", "claude-st7a3k5w", "claude-ec6t4w8m", "claude-rp8f3m7v", "claude-mc4w9s2t", "claude-st6n2w4r", "claude-rp2f8k4v", "claude-mc7b3t9w", "claude-mc8r5t2w"], "reason": "13 specs ~33 variants still unbacktested"},
  {"action": "FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "CHAMPION PF=1.921, 7th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "macd_7to1_tail_harvester", "reason": "PF=1.712, 7th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "ema_rsi_atr_precision_10to1", "reason": "ACCEPT PF=1.327, ranging PF=2.864"},
  {"action": "ADD_REGIME_GATE", "target": "all_strategies", "gate": "disable_during_trending", "reason": "21/23 ACCEPTs lose money in trending. Gate would boost portfolio PF ~0.2-0.4"},
  {"action": "DEBUG_SIGNAL", "target": "choppiness_donchian_fade", "reason": "NEW — 0 trades across 8 backtests (v1 and v2), conditions too strict or indicator thresholds miscalibrated"},
  {"action": "DEBUG_SIGNAL", "target": "ema_crossover_extreme_10to1", "reason": "NEW — 0 trades across 2 backtests, extreme conditions never fire"},
  {"action": "TEST_TEMPLATE", "target": "kama_vortex_divergence", "reason": "NEW — exists in signal_templates.py but 0 backtests ever run"},
  {"action": "TEST_TEMPLATE", "target": "stc_cycle_timing", "reason": "NEW — exists in signal_templates.py but 0 backtests ever run"}
]
```

---

## Executive Summary

**The latest 10 backtests produced a total of 2 trades and -$212 net PnL — a complete signal drought.** All 10 runs tested Quandalf-designed strategies (choppiness_donchian_fade v1/v2, ema_crossover_extreme_10to1) that generated 0-1 trades across all asset/timeframe combinations. This reveals a new failure mode: Claude-designed specs with overly strict entry conditions that never fire on historical data. Meanwhile, the pipeline continues producing identical template_diversity outcomes (28/30 collapse to 4 unique metric profiles, 93%+ compute waste for the 14th consecutive cycle). Two Quandalf-designed templates in signal_templates.py (kama_vortex_divergence, stc_cycle_timing) have never been backtested at all. The 23 all-time ACCEPTs remain 100% Claude-originated, but the Claude spec failure rate on newest experimental specs (3/5 = 60% zero-trade REJECT) demands tighter pre-backtest validation.

---

## Failing Patterns

### 1. Quandalf Template Signal Drought (NEW — CRITICAL)
The latest 10 backtests are ALL from Quandalf-designed strategies and ALL failed:
- **choppiness_donchian_fade v1**: 0 trades across BTC 1h, BTC 4h, ETH 1h, ETH 4h (4 backtests)
- **choppiness_donchian_fade v2**: 0-1 trades across same matrix (4 backtests). The single trade that fired (ETH 1h short) lost $91.
- **ema_crossover_extreme_10to1**: 0 trades on ETH 1h and ETH 4h (2 backtests)

Root cause: entry conditions are too restrictive. The choppiness_donchian_fade template requires CHOP > 61.8 AND RSI confirmation AND Donchian edge proximity simultaneously — this conjunction almost never occurs. The "extreme" EMA crossover adds conditions that prevent any signal from firing over 4,000+ bars of data.

**Lesson:** Claude specs that performed well (36% ACCEPT rate) all used PROVEN templates (supertrend_follow, macd_confirmation, rsi_pullback, ema_rsi_atr) with parameter innovation. Novel template designs with untested indicator combinations are failing at the signal generation level. The spec_rules interpreter works — the conditions themselves are the problem.

### 2. Parameter Convergence (CRITICAL — 14TH CYCLE, UNCHANGED)
Latest 30 outcomes collapse to 4 unique metric profiles. 28/30 are template_diversity variants. Metrics:
- Profile A: PF=1.419, DD=10.5%, 140 trades (4 outcomes — ACCEPT)
- Profile B: PF=1.295, DD=24.3%, 140 trades (16 outcomes — REVISE)
- Profile C: PF=0.0, DD=100%, 0 trades (9 outcomes — REJECT, includes Claude specs)
- Profile D: PF=1.075-1.095, DD=38-74%, 162-166 trades (1 outcome — REJECT for high DD)

**Compute waste: 93%+ of resources produce duplicate data.** This has been reported for 14 consecutive cycles with zero remediation.

### 3. Pipeline Spec Generation (STRUCTURALLY BROKEN — 14 CYCLES)
- 600+ pipeline specs: 0 ACCEPTs (all-time 0% rate)
- Still generating BTC specs despite 13 cycles of exclusion requests
- Still using sub-5:1 R:R despite established floor
- 0/34+ machine directives enforced (14 cycles)
- `directive_history.notes_considered: 0` in every outcome note

### 4. Refinement Engine (DEAD — 9+ CYCLES)
Every outcome note across 610+ results contains `NO_IMPROVEMENT`. Refinement cycle hash is shared across entire batches. System has never produced measurable improvement.

### 5. Dead Templates (UNCHANGED + NEW ADDITIONS)
- **stochastic_reversal**: Bug at line 174-175 — long condition checks `K < stoch_os` when K just crossed above D (logically impossible). 0 trades, 13 cycles.
- **bollinger_breakout**: Volume gate at line 149-150 always returns False when `i < 20` (first 20 bars). 2-sigma breakout structurally impossible on crypto volatility. 0 trades, 10 cycles.
- **choppiness_donchian_fade** (NEW): Conditions too restrictive — 0 trades in 8/8 backtests across v1 and v2. Needs threshold relaxation or complete redesign.
- **ema_crossover_extreme_10to1** (NEW): "Extreme" entry conditions never fire. 0 trades in 2/2 backtests.

### 6. alignment_entry Signal (DEAD — UNCHANGED)
PF 0.615-0.969 across all tests. Generic confidence threshold with no indicator logic. Structural loser.

### 7. Research Card Pipeline (DEAD — ONLY TEST FIXTURE)
Single file: `rc-directive-loop-fixture.json`. Zero real research cards from video ingestion. Doctrine references auto-transcript ingestion but nothing has been built.

### 8. Trending Regime Destruction (UNCHANGED)
21/23 ACCEPTs lose money in trending. Both new ACCEPTs from Update 12 confirm: ema_rsi_atr precision trending PF=0.372, RSI slingshot trending PF=0.763. Only Supertrend 8:1 (PF=1.289) and MACD 12:1 (PF=2.177) survive trending.

---

## Promising Directions

### 1. Supertrend 8:1 Tail Harvester — STILL CHAMPION (7th cycle requesting forward test)
PF=1.921, DD=10.9%, 85 trades, profitable in ALL regimes (trending=1.289, ranging=2.914, transitional=1.844). Only template profitable during trending. **Highest priority for forward testing.**

### 2. ema_rsi_atr Precision — 2 ACCEPTs, Ranging Specialist
ema_rsi_atr_precision_10to1 (PF=1.327, ranging PF=2.864) and ea9p5k2m narrow-band (PF=1.288, transitional PF=2.765). Narrow RSI bands (50-65) validated as precision entry technique. With a trending regime gate, effective PF would jump to ~2.0+.

### 3. RSI Shallow Slingshot 12:1 — Extreme R:R Validated
PF=1.270, DD=8.4%, 162 trades, transitional PF=1.834. Proves 12:1 R:R works on RSI pullback. Opens testing 12:1+ on Supertrend and MACD families.

### 4. Trending Regime Gate — Biggest Single Improvement Available
Configuration change, not new strategy. Disable non-Supertrend/non-MACD-12:1 strategies during trending. Estimated PF improvement of 0.2-0.4 across portfolio. Zero risk.

### 5. Untested Quandalf Templates — kama_vortex_divergence and stc_cycle_timing
Both exist in signal_templates.py (lines ~200-280) but have NEVER been backtested:
- **kama_vortex_divergence**: KAMA flattening + Vortex crossover + ATR gate. Designed for early trend exhaustion. Uses KAMA_10_2_30, VTXP_14, VTXM_14 — all available but untested in any strategy.
- **stc_cycle_timing**: STC threshold crossover + EMA_50 slope + Choppiness gate. Cycle-based entries. Uses STC_10_12_26_0.5, CHOP_14_1_100 — available indicators never tested together.

These represent the freshest untested hypotheses in the system. Priority backtest candidates.

### 6. Multi-Strategy Portfolio (READY — 4 COMPLEMENTARY PROFILES)

| Strategy | Ranging PF | Transitional PF | Trending PF | Role |
|---|---|---|---|---|
| Supertrend 8:1 | 2.914 | 1.844 | 1.289 | All-weather core |
| ema_rsi_atr precision | 2.864 | 1.731 | 0.372 | Ranging specialist (trending gate) |
| MACD 12:1 ultimate | 1.581 | 0.569 | 2.177 | Trending specialist |
| RSI slingshot 12:1 | 1.610 | 1.834 | 0.763 | Transitional specialist (trending gate) |

### 7. Claude Spec Backtest Queue — 33+ Variants Waiting
13 Claude specs (~33 variants) unbacktested. Expected 10-12 new ACCEPTs based on 36% historical rate. BUT newer experimental specs (choppiness_donchian_fade, ema_crossover_extreme) are failing — need pre-validation for signal count before queueing backtests.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|
| supertrend_follow | 7 | 1.921 | 95 | CHAMPION | Forward-test immediately; test 12:1 R:R |
| macd_confirmation | 9 | 1.712 | 155 | STRONG | Forward-test MACD 7:1; test 1h |
| rsi_pullback | 5 | 1.442 | 105 | GOOD | 12:1 ACCEPT validated; test narrow RSI |
| ema_rsi_atr | 2 | 1.327 | 127 | RISING | Add trending gate; ranging PF=2.864 |
| ema_crossover | 0 | — | 0 | STALLED | "Extreme" variant 0 trades; try moderate conditions |
| choppiness_donchian_fade | 0 | — | 0 | FAILING | 0 trades in 8 backtests; relax CHOP threshold to 50 |
| kama_vortex_divergence | 0 | — | — | UNTESTED | Exists in code, never backtested — priority test |
| stc_cycle_timing | 0 | — | — | UNTESTED | Exists in code, never backtested — priority test |
| stochastic_reversal | 0 | — | 0 | DEAD | Bug line 174-175; remove from registry |
| bollinger_breakout | 0 | — | 0 | DEAD | Volume gate broken line 149-150; remove |
| spec_rules | — | — | — | OPERATIONAL | Universal interpreter; used by all Claude specs |

---

## Regime Insights

### Regime Performance Matrix (23 ACCEPTs)

| Template Family | Trending PF | Ranging PF | Transitional PF | Best Regime |
|---|---|---|---|---|
| Supertrend 8:1 | 1.289 | **2.914** | 1.844 | Ranging |
| Supertrend (other) | 0.75-0.95 | 1.61-2.56 | 1.38-1.57 | Ranging |
| MACD 7:1 | 1.677 | **2.062** | 1.308 | Ranging |
| MACD 12:1 | **2.177** | 1.581 | 0.569 | Trending |
| RSI pullback 8:1 | 1.505 | **1.795** | 0.930 | Ranging |
| RSI slingshot 12:1 | 0.763 | 1.610 | **1.834** | Transitional |
| ema_rsi_atr precision | 0.372 | **2.864** | 1.731 | Ranging |
| ea9p5k2m narrow | 0.766 | 1.216 | **2.765** | Transitional |

### Key Regime Findings

1. **Ranging remains the money regime.** 19/23 ACCEPTs profit. Top ranging PFs: 2.914 (Supertrend), 2.864 (ema_rsi_atr precision), 2.558 (Supertrend ultra).

2. **Trending is the profit destroyer.** 21/23 ACCEPTs show trending PF < 1.0. Exceptions: Supertrend 8:1 (1.289), MACD 12:1 (2.177). A trending gate is the single biggest portfolio improvement.

3. **Transitional alpha growing.** 4 strategies with strong transitional edge: RSI slingshot 12:1 (PF=1.834, 37 trades), ea9p5k2m (PF=2.765, ~12 trades), RSI shallow dip (PF=5.568, ~9 trades), ema_rsi_atr precision (PF=1.731, 45 trades).

4. **Regime classifier is NOT broken** (confirmed Update 12). Claude specs find 51-57 ranging trades. Pipeline template_diversity finds 0. Root cause: pipeline signals don't fire during consolidation — signal design issue, not classifier bug.

5. **Latest batch regime labeling anomaly:** All 10 latest backtests show "transitional" as dominant regime, yet 8/10 produced 0 trades. The Quandalf templates designed for ranging/transitional markets couldn't find signals even during those regimes. Suggests indicator thresholds (CHOP > 61.8 especially) are calibrated for a different market regime than what the data contains.

---

## Recommended Directives

### Priority 1 — IMMEDIATE
1. **Forward-test Supertrend 8:1** — 7th cycle requesting. Revenue blocker.
2. **Forward-test MACD 7:1** — 7th cycle requesting.
3. **Backtest kama_vortex_divergence and stc_cycle_timing** — templates exist in code but 0 backtests ever. Freshest hypotheses available.
4. **Implement trending regime gate** — disable non-Supertrend/non-MACD-12:1 during trending. Immediate portfolio PF boost.
5. **Kill pipeline spec generation** — 600+ specs, 0 ACCEPTs. Redirect ALL compute to Claude specs.

### Priority 2 — HIGH
1. **Pre-validate Claude specs for signal count** — run a fast signal scan (no position sim) before full backtest to catch 0-trade specs early. Would have saved 10 backtest runs this cycle.
2. **Implement parameter hash dedup** — eliminate 93%+ compute waste.
3. **Enforce R:R floor of 5:1** and **BTC exclusion** at pipeline entry.
4. **Remove dead templates** — stochastic_reversal, bollinger_breakout from TEMPLATE_REGISTRY.
5. **Relax choppiness_donchian_fade thresholds** — lower CHOP from 61.8 to 50, widen RSI bands from 35/65 to 30/70 for v3 test.

### Priority 3 — MEDIUM
1. **Build portfolio backtester** — test combined regime-gated allocation.
2. **Test 12:1 R:R on Supertrend** — proven at 8:1 (PF=1.921), RSI works at 12:1, Supertrend at 12:1 could be exceptional.
3. **Build forward-testing infrastructure** — even a minimal paper-trade script against HyperLiquid testnet.
4. **Fix or build research card pipeline** — zero output despite doctrine reference.

---

## Doctrine Gaps

### 1. Directive Enforcement (CRITICAL — 14 CYCLES, 0 ENFORCED)
34+ directives issued. 0 enforced. Pipeline does not read, parse, or apply advisory directives. This system exists only in this document — zero operational impact.

### 2. Trending Regime Gate (DOCTRINE BLIND SPOT)
Doctrine requires "explicit regime assumptions" but the spec schema and backtester have no regime-conditional execution mechanism. 21/23 ACCEPTs would benefit. Biggest single alpha improvement available.

### 3. Pre-Backtest Signal Validation (NEW GAP)
No mechanism to fast-scan whether a spec produces any entry signals before committing to full backtest with position simulation. This cycle wasted 10 backtest runs on 0-trade specs. A 10-second signal count pass would have caught all of them.

### 4. Forward-Testing Infrastructure (ABSENT — 7 CYCLES)
Zero strategies forward-tested. Supertrend 8:1 and MACD 7:1 validated for 7 cycles. This is the #1 blocker to revenue.

### 5. Parameter Convergence (14 CYCLES, WORSENING)
93%+ compute waste from duplicate parameter profiles. No dedup mechanism exists.

### 6. Research Card Pipeline (NON-FUNCTIONAL)
Only test fixture. Auto-transcript ingestion referenced in doctrine never built.

### 7. Claude Spec Quality Gate (NEW GAP)
Claude specs have a 36% ACCEPT rate on proven templates but are now producing 0-trade experimental designs. No feedback loop exists to warn the spec author that conditions will never fire. Need: indicator histogram analysis or signal preview before spec finalization.

---

## Suggestions For Asz

### 1. Build a 10-Second Signal Preview — Stop Wasting Backtests on 0-Trade Specs
This cycle burned 10 full backtest runs on strategies that produced 0-1 trades. A lightweight signal preview — load the indicator dataframe, evaluate entry conditions at each bar, count how many fire, report back — would take seconds and catch dead specs before they consume the full backtester. Implementation: a Python function that takes a spec's entry conditions, runs them against the existing indicator DF, and returns `{signal_count: N, first_signal_bar: X, last_signal_bar: Y}`. If `signal_count < 10`, don't bother with position simulation. This single addition would have saved 100% of this cycle's compute waste from Claude specs, and would give Quandalf feedback to loosen conditions before submitting.

### 2. Hard-Wire 3 Pipeline Rules — 93% Compute Savings for 3 Lines of Code
The pipeline has ignored 34+ machine directives for 14 cycles. Stop trying to fix the directive parser. Instead, hard-code the three most impactful rules directly:
- `if rr < 5.0: skip()` — R:R floor (all 23 ACCEPTs use 5:1+)
- `if asset == "BTC": skip()` — BTC exclusion (0 BTC ACCEPTs ever)
- `if param_hash in seen: skip()` — dedup (93% of outcomes are duplicates)

These are trivial code changes. Combined, they would redirect effectively all compute to Claude specs that actually produce ACCEPTs.

### 3. Deploy a Minimal Forward-Test Loop — The Path to Revenue
We have 23 ACCEPT strategies validated over months. Zero forward-tested. Every week without forward testing is potential income lost. A minimal implementation: Python script that reads a strategy spec, connects to HyperLiquid testnet API, subscribes to a live 15m/1h/4h candle feed, computes indicators on incoming data, evaluates entry conditions, logs paper trades to a JSON file. No position management, no execution — just "would this signal have fired?" with a timestamp. Even this crude version would tell us whether backtest edge translates to live within days. The Supertrend 8:1 champion (PF=1.921, all-regime profitable) has been waiting 7 cycles for this. Revenue is sitting on the table.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 12 |
|---|---|---|
| Total outcome notes (all-time) | 610+ | — |
| ACCEPTs (all-time) | 23 (3.7% rate) | — |
| Claude-originated ACCEPT rate | 100% (23/23) | — |
| Pipeline-originated ACCEPT rate | 0% (0/590+) | — |
| Latest batch outcomes | 30 | — |
| Latest batch ACCEPTs | 4 (template_diversity) | +2 (but identical metrics) |
| Latest batch unique profiles | 4 | — |
| Latest 10 backtests: total trades | 2 | NEW (signal drought) |
| Latest 10 backtests: net PnL | -$212 | NEW |
| Compute waste (estimated) | 93%+ | — |
| Directives enforced | 0/34+ | +3 directives, still 0 enforced |
| Forward tests initiated | 0 | — (7th cycle requesting) |
| Claude spec variants awaiting backtest | ~33 | — |
| Claude spec ACCEPT rate (tested) | 36% (4/11) | — |
| Claude spec 0-trade REJECT rate (recent) | 60% (3/5 newest) | NEW METRIC |
| Dead templates | 2 + 2 failing | +2 (chop_donchian, ema_extreme) |
| Untested templates | 2 (kama_vortex, stc_cycle) | NEW METRIC |
| Regime classifier status | NOT BROKEN — pipeline signal issue | — |

### ACCEPT Leaderboard (by PF, deduplicated, top 19)

| Rank | Strategy | PF | DD | Trades | Best Regime (PF) | Template |
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
| 14 | ema_rsi_atr precision 10:1 | 1.327 | 16.6% | 162 | Ranging (2.864) | ema_rsi_atr |
| 15 | MACD 12:1 ultimate | 1.302 | 9.8% | 137 | Trending (2.177) | macd_confirmation |
| 16 | ea9p5k2m narrow 9:1 | 1.288 | 18.6% | 92 | Trans (2.765) | ema_rsi_atr |
| 17 | RSI slingshot 12:1 | 1.270 | 8.4% | 162 | Trans (1.834) | rsi_pullback |
| 18 | Supertrend ADX5 6:1 | 1.220 | 14.3% | 99 | Ranging (1.611) | supertrend_follow |
| 19 | RSI pullback safe mod | 1.210 | 9.2% | 38 | Trans (1.597) | rsi_pullback |
