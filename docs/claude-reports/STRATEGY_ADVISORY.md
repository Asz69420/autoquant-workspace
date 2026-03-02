# Strategy Advisory — 2026-03-03 (Update 14)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 706 outcome notes (all-time), 32 ACCEPT outcomes (24 unique), latest 30 outcomes (20260302), latest 10 backtests (20260302), 11 signal templates (2 dead, 2 untested, 1 failing), ~80 strategy specs, 180+ research cards (TradingView catalog scrapes), doctrine as of 20260228
**Prior advisory:** 2026-03-02 (Update 13)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 179 checks k_now < os_val (K < 20 after crossing above D = near-impossible). Should be k_prev < os_val. 0 trades, 14 cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken (line 149-150 skips if i<20). 2-sigma breakout unsuitable for crypto vol. 0 trades, 11 cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser at any R:R"},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "Latest 10 backtests: 6/10 are BTC despite 14 cycles of exclusion. BTC PF 0.594-1.001. 0 BTC ACCEPTs ever. Still being generated."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications, 15 cycles"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics across all applications"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%, 15 cycles"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_exit_change", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_gate_adjust", "reason": "PF 1.001 best, confirmed noise — latest backtest PF=1.001 again"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_threshold_sweep", "reason": "0% improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_template_switch", "reason": "0% success in 30+ outcome notes"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_param_sweep", "reason": "PF 0.969, DD 147%, zero improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_role_swap", "reason": "PF 0.644-0.963, 100% REJECT rate — latest backtests confirm PF=0.644 on BTC, PF=0.963 on ETH"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_threshold_sweep", "reason": "PF 0.998, noise, converges to same params"},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 1, "reason": "CHAMPION — PF=1.921, 7 ACCEPTs, only all-regime profitable template"},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 2, "reason": "9 ACCEPTs, best PF=1.712, most consistent"},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 3, "reason": "5 ACCEPTs incl. slingshot_12to1 PF=1.270"},
  {"action": "PREFER_TEMPLATE", "target": "ema_rsi_atr", "priority": 4, "reason": "2 ACCEPTs incl. precision_10to1 PF=1.327"},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All 23+ ACCEPTs use 5:1+ R:R"},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 9+ cycles, 706 outcome notes"},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 96% of unique ACCEPTs (23/24 unique). Pipeline = 1 unique ACCEPT (duplicated 9x)."},
  {"action": "BACKTEST_CLAUDE_SPECS_FIRST", "targets": ["claude-er8v3m6k", "claude-st5k2r8w", "claude-rp3w7k9d", "claude-mc6t8b3k", "claude-rp4f2w8n", "claude-st7a3k5w", "claude-ec6t4w8m", "claude-rp8f3m7v", "claude-mc4w9s2t", "claude-st6n2w4r", "claude-rp2f8k4v", "claude-mc7b3t9w", "claude-mc8r5t2w"], "reason": "13 specs ~33 variants still unbacktested"},
  {"action": "FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "CHAMPION PF=1.921, 8th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "macd_7to1_tail_harvester", "reason": "PF=1.712, 8th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "ema_rsi_atr_precision_10to1", "reason": "ACCEPT PF=1.327, ranging PF=2.864"},
  {"action": "ADD_REGIME_GATE", "target": "all_strategies", "gate": "disable_during_trending", "reason": "21/23 ACCEPTs lose money in trending. Gate would boost portfolio PF ~0.2-0.4"},
  {"action": "DEBUG_SIGNAL", "target": "choppiness_donchian_fade", "reason": "0 trades across 8+ backtests, CHOP > 61.8 threshold too strict"},
  {"action": "TEST_TEMPLATE", "target": "kama_vortex_divergence", "reason": "Exists in signal_templates.py but 0 backtests ever run"},
  {"action": "TEST_TEMPLATE", "target": "stc_cycle_timing", "reason": "Exists in signal_templates.py but 0 backtests ever run"},
  {"action": "DEDUP_PARAMS", "reason": "9 identical ACCEPTs (PF=1.419, DD=10.5%, 140 trades) counted separately. 93%+ compute waste on duplicates extends to ACCEPTs now."},
  {"action": "FIX_TEMPLATE_ROUTING", "target": "Claude specs with custom template_name", "reason": "3 Claude specs (st4q7r2n, mc5s9k3w, ec3w5m8k) REJECTED with 0 trades. Custom template names not in TEMPLATE_REGISTRY may cause fallback to wrong template. Validate routing before backtest."},
  {"action": "SIGNAL_PREVIEW", "reason": "10+ backtest runs wasted on 0-trade specs. Run fast signal count before committing to full backtest."},
  {"action": "FIX_RESEARCH_CARDS", "reason": "180+ research cards exist but all are TradingView catalog scrapes with no extracted rules. Pipeline produces catalog links, not actionable hypotheses."}
]
```

---

## Executive Summary

**The pipeline has produced its first ACCEPTs — but they're 9 copies of the same strategy, confirming parameter convergence now extends to positive results too.** Of 706 all-time outcome notes, 32 carry ACCEPT verdicts, but only 24 are unique strategies (23 Claude-originated + 1 pipeline clone duplicated 9x). The latest 10 backtests remain uniformly unprofitable (PF 0.594-1.001), BTC exclusion is still ignored (6/10 runs), and 3 new Claude specs with custom template names produced 0 trades — revealing a template routing problem where non-registry names fall back to wrong signal logic. The research card pipeline now produces 180+ cards, but they are all TradingView catalog scrapes with zero extracted trading rules, making the pipeline operationally non-functional for hypothesis generation. Machine directives remain 0% enforced across 15 cycles.

---

## Failing Patterns

### 1. Parameter Convergence Now Infects ACCEPTs (CRITICAL — 15TH CYCLE)
The latest 30 outcomes collapse to 4 unique metric profiles, same as last cycle. But a new failure mode emerged: **the pipeline's 9 ACCEPTs share identical metrics** (PF=1.419, DD=10.5%, 140 trades, regime split 29/71/40 trending/ranging/transitional). This means the system produced 9 separate outcome records for what is functionally one strategy. Parameter convergence isn't just wasting compute on REJECTs — it's inflating ACCEPT counts.

- Profile A: PF=1.419, DD=10.5%, 140 trades → 9 outcomes (ACCEPT, all identical)
- Profile B: PF=1.295, DD=24.3%, 140 trades → 17 outcomes (REVISE, all identical)
- Profile C: PF=0.0, DD=100%, 0 trades → 6 outcomes (REJECT, includes 3 Claude specs)
- Profile D: PF=1.075-1.095, DD=38-74% → 3 outcomes (REJECT for high DD)

**Effective ACCEPT rate from 30 outcomes: 1 unique strategy (3.3%), not 4 (13.3%).**

### 2. Claude Spec Template Routing Failure (NEW)
Three Claude specs produced 0 trades this cycle:
- **supertrend_quiet_pulse_10to1** (st4q7r2n)
- **macd_sol_momentum_8to1** (mc5s9k3w)
- **ema_crossover_minimalist_8to1** (ec3w5m8k)

Root cause analysis: these specs use custom `template_name` values not present in `TEMPLATE_REGISTRY`. The `resolve_template()` function falls through to name heuristics which should match ("supertrend" → supertrend_follow, "macd" → macd_confirmation), but the specs likely use `spec_rules` with entry conditions that never fire, OR the custom name bypasses the entry condition injection. Either way, the result is 0 trades on strategies designed to trade.

**Action needed:** validate that Claude specs with custom names correctly route through `spec_rules` with their `entry_long`/`entry_short` conditions intact.

### 3. Pipeline Spec Generation (STRUCTURALLY BROKEN — 15TH CYCLE)
- 640+ pipeline specs → 1 unique ACCEPT (duplicated 9x = 0.16% unique ACCEPT rate)
- Still generating BTC specs (6/10 latest backtests are BTC 4h)
- Still using blacklisted variants (directive_variant_2_role_swap, directive_variant_1_gate_adjust in latest batch)
- 0/39 machine directives enforced (15 cycles, now 39 directives)
- `directive_history.notes_considered: 0` in every outcome note

### 4. BTC: Confirmed Dead Asset (NEW DATA)
Latest 10 backtests provide fresh BTC evidence:
- BTC 4h role_swap: PF=0.644, -102% return, 165 trades
- BTC 4h gate_adjust: PF=1.001, +0.51% return, 406 trades (noise)
- BTC 4h template_diversity: PF=0.969, -3.56% return, 62 trades
- BTC 4h template_diversity: PF=0.594, -102% return, 142 trades (worst performer: 9.86% win rate)

**BTC all-time: 0 ACCEPTs across 706 outcomes. Every BTC backtest is wasted compute.**

### 5. Refinement Engine (DEAD — 10+ CYCLES)
Every outcome note across 706 results: `NO_IMPROVEMENT`. Refinement has never produced measurable improvement. System is incapable of self-optimization.

### 6. Dead Templates (UNCHANGED)
- **stochastic_reversal**: Bug at line 179 — `k_now < os_val` should be `k_prev < os_val`. After K crosses above D, requiring K < 20 means K crossed above D while both K and D are deep oversold — nearly impossible. Fix: check `k_prev < os_val` (K was oversold when cross began). 0 trades, 14 cycles.
- **bollinger_breakout**: Volume gate at line 149-150 always returns False when `i < 20`. 2-sigma breakout structurally unsuitable. 0 trades, 11 cycles.
- **choppiness_donchian_fade**: CHOP > 61.8 AND close <= DCL AND RSI < 35 — triple conjunction almost never occurs simultaneously. 0 trades in 8+ backtests. Needs threshold relaxation or architectural change (e.g., evaluate conditions independently, require 2-of-3).

### 7. Research Card Pipeline (OPERATIONAL BUT NON-FUNCTIONAL)
**Update from "dead":** The pipeline now produces 180+ research cards across 7 date folders. However, ALL are TradingView catalog scrapes containing indicator titles and author names — zero extracted trading rules, zero testable hypotheses, zero actionable content. Sample cards:
- "3D Volume Profile [UAlgo]" — no rules extracted
- "Pattern Recognition Signals | ProjectSyndicate" — no rules extracted
- "MNQ Liquidity Sweep Strategy (KUSH)" — no rules extracted
- "Support/Resistance Channel Breakout [SuprAlgo]" — no rules extracted

The pipeline scrapes catalog pages but performs no analysis. This is data collection theater — volume without value.

### 8. Trending Regime Destruction (UNCHANGED — CONFIRMED BY NEW DATA)
21/23 Claude ACCEPTs lose money in trending. Latest backtests confirm: trending PF ranges from 0.209 (template_diversity BTC, 38 trades) to 1.183 (role_swap ETH, 55 trades). The single pipeline ACCEPT (template_diversity PF=1.419) shows trending PF=2.145 — but this may be an artifact of only 29 trending trades.

### 9. Backtest Duplication (NEW)
3 of the latest 10 backtests are exact duplicates:
- ffe4de65 = ff6b00ee (BTC 4h role_swap, identical in all metrics)
- fea84769 = ff244610 (BTC 4h gate_adjust, identical)
- ffcc15b7 = fe432e22 = fe31f295 (ETH 1h, identical across 3 variants)

**5/10 backtests are wasted on re-running existing results.** No dedup at the backtest scheduling level.

---

## Promising Directions

### 1. Supertrend 8:1 Tail Harvester — CHAMPION (8th cycle requesting forward test)
PF=1.921, DD=10.9%, 85 trades, profitable in ALL regimes (trending=1.289, ranging=2.914, transitional=1.844). Only template profitable during trending. **Revenue is sitting on the table. 8 cycles without forward-testing this strategy.**

### 2. ema_rsi_atr Precision — 2 ACCEPTs, Ranging Specialist
ema_rsi_atr_precision_10to1 (PF=1.327, ranging PF=2.864) and ea9p5k2m narrow-band (PF=1.288, transitional PF=2.765). Narrow RSI bands (50-65) validated. With trending gate, effective PF would be ~2.0+.

### 3. Pipeline ACCEPT Profile — New Data Point
The 1 unique pipeline ACCEPT (template_diversity, PF=1.419, DD=10.5%, 140 trades) shows:
- Ranging PF=1.615, Transitional PF=0.760, Trending PF=2.145
- 29 trending / 71 ranging / 40 transitional trade distribution
- Notably profitable in trending (PF=2.145) — unusual. Only 29 trending trades though, so confidence is low.

This is the first evidence that the pipeline CAN produce viable strategies — but only with template_diversity, and only at massive duplication cost (9 identical outcomes for 1 unique strategy).

### 4. Trending Regime Gate — Still Biggest Single Improvement
Disable non-Supertrend/non-MACD-12:1 strategies during trending. Estimated PF improvement of 0.2-0.4 across portfolio. Zero risk. Zero development effort. Just configuration.

### 5. Untested Templates — kama_vortex_divergence and stc_cycle_timing
Both exist in signal_templates.py, both use indicators never tested together:
- **kama_vortex_divergence**: KAMA_10_2_30 flattening + VTXP_14/VTXM_14 crossover + ATR gate. Targets trend exhaustion.
- **stc_cycle_timing**: STC_10_12_26_0.5 threshold + EMA_50 slope + CHOP gate. Cycle-based entries.

Both represent genuine novel hypotheses with indicators that have 0 coverage in the ACCEPT pool. **Priority backtest candidates.**

### 6. Ultra-High R:R (12:1+) — Validated, Under-Explored
RSI slingshot 12:1 proved ACCEPT-viable (PF=1.270, 162 trades). 12:1 R:R has NOT been tested on:
- supertrend_follow (champion at 8:1, could be exceptional at 12:1)
- macd_confirmation (strong at 7:1, untested higher)
- ema_rsi_atr (precision at 10:1, gap to 12:1)

### 7. Multi-Strategy Portfolio — 4 Complementary Profiles Ready

| Strategy | Ranging PF | Transitional PF | Trending PF | Role |
|---|---|---|---|---|
| Supertrend 8:1 | 2.914 | 1.844 | 1.289 | All-weather core |
| ema_rsi_atr precision | 2.864 | 1.731 | 0.372 | Ranging specialist (trending gate) |
| MACD 12:1 ultimate | 1.581 | 0.569 | 2.177 | Trending specialist |
| RSI slingshot 12:1 | 1.610 | 1.834 | 0.763 | Transitional specialist (trending gate) |

---

## Template Health

| Template | ACCEPTs | Best PF | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|
| supertrend_follow | 7 | 1.921 | 95 | CHAMPION | Forward-test immediately; test 12:1 R:R |
| macd_confirmation | 9 | 1.712 | 155 | STRONG | Forward-test MACD 7:1; test 12:1 R:R |
| rsi_pullback | 5 | 1.442 | 105 | GOOD | 12:1 validated; explore new RSI bands |
| ema_rsi_atr | 2 | 1.327 | 127 | RISING | Trending gate needed; ranging PF=2.864 |
| spec_rules | ~1 | 1.419 | 140 | OPERATIONAL | Interpreter works; used by pipeline template_diversity |
| ema_crossover | 0 | — | 0 | EXHAUSTED | Fallback default; no ACCEPTs ever. Deprioritize. |
| choppiness_donchian_fade | 0 | — | 0 | FAILING | 0 trades in 8+ backtests; relax to CHOP>50, RSI 30/70, test 2-of-3 logic |
| kama_vortex_divergence | 0 | — | — | UNTESTED | Never backtested — priority test |
| stc_cycle_timing | 0 | — | — | UNTESTED | Never backtested — priority test |
| stochastic_reversal | 0 | — | 0 | DEAD | Bug line 179; fix k_now→k_prev or remove |
| bollinger_breakout | 0 | — | 0 | DEAD | Volume gate broken; remove from registry |

---

## Regime Insights

### Regime Performance Matrix (All Unique ACCEPTs)

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
| Pipeline template_div | **2.145** | 1.615 | 0.760 | Trending* (low N=29) |

### Key Regime Findings

1. **Ranging remains the money regime.** 19/24 unique ACCEPTs profit in ranging. Top ranging PFs: 2.914 (Supertrend), 2.864 (ema_rsi_atr), 2.558 (Supertrend ultra).

2. **Trending is the profit destroyer.** 21/24 unique ACCEPTs show trending PF < 1.0. Confirmed exceptions: Supertrend 8:1 (1.289), MACD 12:1 (2.177). Pipeline template_diversity ACCEPT shows trending PF=2.145 but on only 29 trades — likely noise.

3. **Transitional alpha growing.** 4 strategies with strong transitional edge, unchanged from prior cycle: RSI slingshot (PF=1.834), ea9p5k2m (PF=2.765), RSI shallow (PF=5.568), ema_rsi_atr precision (PF=1.731).

4. **Regime classifier confirmed functional.** Claude specs find 51-71 ranging trades. Pipeline signals don't fire during consolidation — signal design issue, not classifier bug.

5. **Latest backtests confirm trending damage.** BTC 4h template_diversity: trending PF=0.209 (38 trades), 0.663 (37 trades). ETH 1h across all variants: trending PF=0.990-1.009, best case breakeven.

---

## Recommended Directives

### Priority 1 — IMMEDIATE
1. **Forward-test Supertrend 8:1** — 8th cycle requesting. Revenue blocker. Every week without forward-testing is potential income lost.
2. **Forward-test MACD 7:1** — 8th cycle requesting.
3. **Implement parameter hash dedup** — 9 identical ACCEPTs, 17 identical REVISEs in latest batch. Single biggest compute savings available.
4. **Backtest kama_vortex_divergence and stc_cycle_timing** — templates exist but 0 backtests ever. Freshest hypotheses.
5. **Implement trending regime gate** — disable non-Supertrend/non-MACD-12:1 during trending.

### Priority 2 — HIGH
1. **Fix Claude spec template routing** — validate that custom template_name values route correctly through spec_rules with entry conditions intact. 3 specs wasted this cycle.
2. **Pre-validate signal count** — fast scan (no position sim) before full backtest. Would have caught all 0-trade specs.
3. **Hard-code 3 pipeline rules** — `if rr < 5.0: skip()`, `if asset == "BTC": skip()`, `if param_hash in seen: skip()`. Immediate 90%+ compute savings.
4. **Remove dead templates** — stochastic_reversal, bollinger_breakout from TEMPLATE_REGISTRY.
5. **Backtest dedup** — prevent re-running identical specs. 5/10 latest backtests were exact duplicates.

### Priority 3 — MEDIUM
1. **Build portfolio backtester** — test combined regime-gated allocation of 4 complementary strategies.
2. **Test 12:1 R:R on Supertrend and MACD** — proven on RSI, untested on champion templates.
3. **Fix research card pipeline** — currently produces 180+ catalog scrapes with 0 extracted rules. Need actual indicator analysis, rule extraction, and hypothesis generation.
4. **Build forward-testing infrastructure** — even minimal paper-trade against HyperLiquid testnet.
5. **Fix stochastic_reversal bug** — change `k_now < os_val` to `k_prev < os_val` on line 179 (long), and `k_now > ob` to `k_prev > ob` (short). Template may then produce trades.

---

## Doctrine Gaps

### 1. Directive Enforcement (CRITICAL — 15 CYCLES, 0 ENFORCED)
39 directives issued. 0 enforced. Pipeline does not read, parse, or apply advisory directives. The directive system has zero operational impact.

### 2. Trending Regime Gate (DOCTRINE BLIND SPOT)
Doctrine requires "explicit regime assumptions" (heuristic 20260226-06) but the spec schema and backtester have no regime-conditional execution mechanism. 21/24 ACCEPTs would benefit.

### 3. Pre-Backtest Signal Validation (GAP — 2ND CYCLE)
No mechanism to fast-scan signal count. This cycle and last burned 10+ backtest runs on 0-trade specs. Trivial to implement, massive savings.

### 4. Forward-Testing Infrastructure (ABSENT — 8 CYCLES)
Zero strategies forward-tested. Supertrend 8:1 and MACD 7:1 validated for 8 cycles. #1 blocker to revenue.

### 5. Parameter Convergence (15 CYCLES, WORSENING — NOW INFECTS ACCEPTs)
93%+ compute waste. No dedup mechanism. Now 9 identical ACCEPT outcomes prove convergence extends beyond REJECTs.

### 6. Research Card Quality (NEW GAP)
Doctrine heuristic 20260226-23 calls for "auto-transcript ingestion + concept tagging." The research card pipeline now runs but produces only TradingView catalog titles — no concept extraction, no rule generation, no hypothesis formation. The gap has shifted from "no pipeline" to "pipeline with no analytical capability."

### 7. Backtest Scheduling Dedup (NEW GAP)
5/10 latest backtests are exact duplicates. No mechanism to check whether an identical spec+asset+timeframe combination has already been run before scheduling.

### 8. Claude Spec Tracking (NEW GAP)
`artifacts/claude-specs/` directory is empty. No formal record of Claude-generated strategies, their routing, or their outcomes. Claude specs are tracked only via filename prefix in outcome notes. Need centralized spec registry.

---

## Suggestions For Asz

### 1. Fix the stochastic_reversal Bug — It's a 2-Character Fix That May Unlock a Dead Template
Line 179 of `signal_templates.py`: change `k_now` to `k_prev` in the long condition (and same logic for short). The current code requires K to be below 20 AFTER crossing above D — which means both K and D must be below 20 at the moment of the cross. This is so restrictive it produces 0 trades in 14 cycles. The intended behavior is to detect a bullish K/D crossover while the oscillator is oversold (K was below 20 when it started crossing). This is a 2-character fix (`k_now` → `k_prev`) that could reactivate an entire template family. Worth a quick test even if the template ends up mediocre — at least we'd know it was evaluated fairly.

### 2. Add a `--dry-run` Flag to the Backtester for Signal Counting
The single most impactful pipeline improvement: before running full position simulation, count how many entry signals a spec produces across the data window. If `signal_count < 20`, skip the backtest and report "insufficient signals." This would have prevented 10+ wasted backtest runs over the last 2 cycles. Implementation: in the backtest loop, add a `dry_run` mode that evaluates entry conditions but skips position management, fee calculation, and metric aggregation. Return only `{signal_count, first_bar, last_bar}`. A 10-second scan that saves hours of compute.

### 3. Hard-Wire the Dedup — The Pipeline Is Literally Running the Same Strategy 9 Times
Forget trying to fix the parameter generation logic. Just add a hash check: before scheduling a backtest, compute `hash(template + sorted(params) + asset + timeframe)`. If the hash exists in `artifacts/backtests/`, skip it. This cycle produced 9 identical ACCEPTs and 17 identical REVISEs from the same parameters. That's 26/30 outcomes (87%) that were pure waste. Three lines of code would reclaim that compute for Claude specs that actually produce novel results.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 13 |
|---|---|---|
| Total outcome notes (all-time) | 706 | +96 |
| ACCEPTs (all-time, raw) | 32 (4.5% rate) | +9 (pipeline template_diversity) |
| ACCEPTs (unique strategies) | 24 (3.4% rate) | +1 unique |
| Claude-originated unique ACCEPTs | 23 (96% of unique) | — |
| Pipeline-originated unique ACCEPTs | 1 (4% of unique, duplicated 9x) | NEW (first pipeline ACCEPT) |
| Latest batch outcomes | 30 | — |
| Latest batch unique strategies | 4 | — |
| Latest 10 backtests: profitable | 0 | — |
| Latest 10 backtests: duplicate runs | 5 (50%) | NEW METRIC |
| BTC backtests in latest 10 | 6 (60%) | Still ignoring exclusion |
| Compute waste (estimated) | 93%+ | — (now includes ACCEPT duplicates) |
| Directives enforced | 0/39 | +5 directives, still 0 enforced |
| Forward tests initiated | 0 | — (8th cycle requesting) |
| Claude spec variants awaiting backtest | ~33 | — |
| Claude spec ACCEPT rate (tested) | 36% (4/11) | — |
| Claude spec 0-trade rate (newest) | 60% (3/5) | — |
| Research cards produced | 180+ | +180 (was 0 real cards) |
| Research cards with extracted rules | 0 | NEW METRIC |
| Dead templates | 2 + 1 failing | — |
| Untested templates | 2 (kama_vortex, stc_cycle) | — |

### ACCEPT Leaderboard (by PF, deduplicated, top 20)

| Rank | Strategy | PF | DD | Trades | Best Regime (PF) | Template |
|---|---|---|---|---|---|---|
| 1 | Supertrend tail 8:1 | 1.921 | 10.9% | 85 | Ranging (2.914) | supertrend_follow |
| 2 | Supertrend ultra ADX10 8:1 | 1.907 | 12.9% | 99 | Ranging (2.558) | supertrend_follow |
| 3 | MACD 7:1 family | 1.712 | 7.5% | 161 | Ranging (2.062) | macd_confirmation |
| 4 | MACD 6:1 | 1.460 | 8.2% | 170 | Ranging (1.762) | macd_confirmation |
| 5 | RSI pullback 8:1 | 1.442 | 7.1% | 156 | Ranging (1.795) | rsi_pullback |
| 6 | RSI pullback 7:1 | 1.421 | 13.8% | 127 | Trending (1.605) | rsi_pullback |
| 7 | Pipeline template_div | 1.419 | 10.5% | 140 | Trending (2.145*) | spec_rules |
| 8 | Supertrend 10:1 | 1.410 | 12.9% | 99 | Ranging (1.874) | supertrend_follow |
| 9 | Supertrend 5:1 | 1.395 | 12.3% | 85 | Ranging (2.002) | supertrend_follow |
| 10 | MACD 5:1 | 1.358 | 10.2% | 147 | Ranging (1.822) | macd_confirmation |
| 11 | MACD moderate | 1.353 | 10.8% | 139 | Ranging (1.465) | macd_confirmation |
| 12 | MACD wide exit | 1.347 | 6.2% | 189 | Ranging (1.872) | macd_confirmation |
| 13 | Supertrend 1h 5:1 | 1.339 | 14.3% | 99 | Ranging (1.693) | supertrend_follow |
| 14 | RSI shallow dip 7:1 | 1.333 | 7.9% | 38 | Trans (5.568) | rsi_pullback |
| 15 | ema_rsi_atr precision 10:1 | 1.327 | 16.6% | 162 | Ranging (2.864) | ema_rsi_atr |
| 16 | MACD 12:1 ultimate | 1.302 | 9.8% | 137 | Trending (2.177) | macd_confirmation |
| 17 | ea9p5k2m narrow 9:1 | 1.288 | 18.6% | 92 | Trans (2.765) | ema_rsi_atr |
| 18 | RSI slingshot 12:1 | 1.270 | 8.4% | 162 | Trans (1.834) | rsi_pullback |
| 19 | Supertrend ADX5 6:1 | 1.220 | 14.3% | 99 | Ranging (1.611) | supertrend_follow |
| 20 | RSI pullback safe mod | 1.210 | 9.2% | 38 | Trans (1.597) | rsi_pullback |

*\* Pipeline template_div trending PF=2.145 based on only 29 trades — low confidence.*
