# Strategy Advisory — 2026-02-28 (Update 3)

**Author:** claude-advisor | **Mode:** STRATEGY_RESEARCHER
**Data window:** 30 outcome notes (20260227–28), 10 backtest results (20260225), 15 claude-specs (20260228), doctrine as of 20260228
**Prior advisory:** 2026-02-28 (Update 2)

---

## Executive Summary

The pipeline remains locked in a deep stagnation loop for the **4th consecutive advisory cycle**. The only profitable lead (PF=1.033 on ETH/4h via exit_change) has not been iterated on despite being flagged as the top priority across 3 prior updates. Meanwhile, 15 Claude-generated strategy specs covering 5 untested templates (supertrend, MACD, Bollinger, EMA crossover, RSI pullback) sit idle in `artifacts/claude-specs/` — the pipeline has not consumed or backtested any of them. The directive system is provably broken: GATE_ADJUST has been prescribed 27 times with a 0% improvement rate, yet continues to be issued. Prior advisory recommendations (0 of 9 actioned) confirm the advisory-to-pipeline feedback loop remains severed.

---

## Failing Patterns — Stop Iterating on These

### 1. `directive_exploration` variant (CRITICAL — 4TH ADVISORY)
- **Evidence:** Consistently worst performer across all cycles. PF 0.51–0.88, doubles trade churn, fee drag exceeds gross profit.
- **Status:** STILL NOT KILLED despite 3 prior advisories demanding its removal.
- **Recommendation:** **REMOVE IMMEDIATELY.** Every cycle this persists wastes 20% of compute budget on a provably destructive variant.

### 2. Variant deduplication failure (CRITICAL — 4TH ADVISORY)
- **Evidence (20260227–28):** 26 of 30 outcome notes share identical metrics (PF=0.9202, DD=981.20, 226 trades). These are the same strategy being recomputed with different labels. On 20260228 backtests, 3 of 5 variants produced byte-identical results (60% waste).
- **Status:** STILL NOT FIXED. No fingerprinting implemented.
- **Recommendation:** Hash resolved signal parameters before backtesting. Skip duplicates and reallocate slots.

### 3. `stochastic_reversal` template — DEAD (3RD ADVISORY)
- **Evidence:** 0 trades across all symbol/TF combos in every test. OB/OS zones (K<20/K>80) too restrictive for crypto.
- **Status:** STILL IN ROTATION. Template diversity hash continues selecting it for some families.
- **Recommendation:** Remove from TEMPLATE_COMBOS or fix with wider zones (K<30/K>70).

### 4. GATE_ADJUST directive — NON-FUNCTIONAL (4TH ADVISORY)
- **Evidence (20260227–28):** Prescribed 27 times across latest outcomes. Success rate: **0%**. Every attempt produces avg_delta_pf = 0.0 (identical to baseline). Historical try counts range 1–7 per variant, zero improvements.
- **Root cause:** Gate parameters are not propagating to the backtester execution engine.
- **Recommendation:** **BLACKLIST GATE_ADJUST** until the propagation bug is fixed.

### 5. ENTRY_TIGHTEN / ENTRY_RELAX — BOTH DEAD (3RD ADVISORY)
- **Evidence:** entry_tighten PF=0.872 (worse than baseline). entry_relax PF=0.920 (identical to baseline). Both tried 4–9 times with 0% improvement.
- **Recommendation:** Blacklist both for all ema_rsi_atr families.

### 6. BTC as test asset — STRUCTURAL LOSS GENERATOR (3RD ADVISORY)
- **Evidence (20260225 backtests):** BTC/1h: PF 0.6537, DD $42,236, net loss -$41,210. BTC/4h: PF 0.8525, DD $35,885, net loss -$27,016. Fee-to-profit ratios make BTC backtests pure loss generators.
- **Evidence (20260227–28 outcomes):** BTC variants consistently show worst regime PF (trending 0.88, transitional 0.77).
- **Recommendation:** **SUSPEND ALL BTC BACKTESTS.** Route 100% of compute to ETH until PF > 1.10 is achieved there.

### 7. TPX threshold sweeps — ZERO DIFFERENTIATION (NEW)
- **Evidence (20260225 backtests):** TPX thresholds 20, 30, and 40 produce **identical results** within each asset/timeframe pair. ETH/1h: all three = PF 0.8812, 225 trades, DD $1,186. ETH/4h: all three = PF 0.8349, 218 trades, DD $3,349. BTC/1h: all three = PF 0.6537, 219 trades, DD $42,236.
- **Root cause:** The TPX parameter is not affecting signal generation. Either the parameter is not consumed by the template, or the range (20–40) is too narrow to produce differentiation.
- **Recommendation:** Stop sweeping TPX thresholds until the parameter's effect on signal generation is verified.

### 8. `rsi_pullback` / `ema_rsi_atr` duplication (PERSISTS)
- **Evidence:** Both map to {baseline: EMA, confirmation: RSI, volume_volatility: ATR} in TEMPLATE_COMBOS. 2 of 7 template slots occupied by the same indicator set.
- **Recommendation:** Remove `rsi_pullback` or differentiate it (e.g., SMA baseline, add slope requirement).

---

## Promising Directions — Explore More

### 1. EXIT_CHANGE on ETH/4h (HIGHEST PRIORITY — 4TH CYCLE UNFOLLOWED)
The PF=1.033 result remains the **only profitable lead in 4 advisory cycles**. Regime profile: trending PF=1.054, transitional PF=1.048, ranging PF=0.982.
- **Status:** NOT ITERATED ON for the 3rd consecutive advisory.
- **Action (CRITICAL):** Create exit-change-only variants with ATR stop multiples at {1.0, 1.5, 2.0, 2.5} and TP at {1.5, 2.0, 2.5, 3.0}. Test ONLY on ETH/4h and ETH/1h. This is a 4x4 matrix = 16 variants that should replace all current wasted compute.

### 2. Claude-generated specs — 15 SPECS AWAITING BACKTEST (NEW — HIGH PRIORITY)
Quandalf has generated 15 strategy specs in `artifacts/claude-specs/` covering:
- **Supertrend** (4 specs): ADX gates 20–35, asymmetric exits, trending-regime focus
- **MACD** (2 specs): Zero-line crossover with EMA_50 context, ADX gating
- **Bollinger** (4 specs): Squeeze breakout with volume confirmation, ranging-to-expansion transition targeting
- **EMA crossover** (3 specs): 9/21 crossover, extreme 3:1–3.5:1 R:R to overcome fee drag
- **RSI pullback** (1 spec): EMA_200 structural trend + RSI<35 pullback depth gate

These represent the template diversification the advisory has requested for 3 cycles. **The pipeline must consume and backtest these specs.** If the pipeline cannot read `artifacts/claude-specs/`, this is the highest-priority integration to build.

### 3. Regime gating (HIGH PRIORITY — DATA NOW AVAILABLE)
- ETH/4h trending PF=1.054 vs ranging PF=0.982 — gate to trending+transitional only
- ETH/1h ranging PF=1.115 vs transitional PF=0.858 — gate to ranging only
- BTC shows no consistently exploitable regime edge — further evidence to suspend it
- **Action:** Implement regime_filter in signal templates or post-signal regime gate.

### 4. Fee drag reduction via wider exits
- ETH/4h: $1,080 fees on $1,737 gross profit (62% of gross eaten by fees)
- ETH/1h: fees exceed gross profit entirely (net negative on every sub-1.0 PF template)
- The Claude-generated EMA crossover specs deliberately target this with 3:1–3.5:1 R:R ratios to reduce trade frequency
- **Action:** Prioritize wider R:R specs in backtesting. Fewer, larger-win trades may be the key architectural shift.

### 5. Drawdown compression on PF=1.033 lead
- Current DD: 0.2853 (within 0.30 threshold but marginal)
- **Action:** Apply time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. Target DD < 0.15 on ETH/4h.

---

## Template Health

| Template | Last Tested | Trades | Avg PF | Best PF | Status | Recommendation |
|---|---|---|---|---|---|---|
| `ema_rsi_atr` (alignment_entry) | 20260228 | 226–415 | 0.96 | 1.033 | **STAGNANT** | Iterate exit_change ONLY |
| `ema_rsi_atr` (exploration) | 20260228 | 766–891 | 0.82 | 0.884 | **DESTRUCTIVE** | KILL — 4th advisory |
| `stochastic_reversal` | 20260228 | 0 | 0.000 | 0.000 | **DEAD** | Remove from rotation — 3rd advisory |
| `supertrend_follow` | NEVER | N/A | N/A | N/A | **UNTESTED** | Claude specs ready — backtest urgently |
| `macd_confirmation` | NEVER | N/A | N/A | N/A | **UNTESTED** | Claude specs ready — backtest urgently |
| `bollinger_breakout` | NEVER | N/A | N/A | N/A | **UNTESTED** | Claude specs ready — backtest urgently |
| `ema_crossover` | NEVER (recent) | N/A | N/A | N/A | **UNTESTED** | Claude specs ready — backtest urgently |
| `rsi_pullback` | NEVER (distinct) | N/A | N/A | N/A | **DUPLICATE** | Remove or differentiate from ema_rsi_atr |

**4 of 7 templates have NEVER been backtested.** Claude-generated specs for all 4 exist and are ready. The pipeline's exclusive focus on `ema_rsi_atr` for 4+ cycles while 4 templates sit untested is the single largest opportunity cost in the system.

---

## Regime Insights

### Regime performance matrix (latest data)

| Symbol/TF | Trending PF | Ranging PF | Transitional PF | Best Regime | Worst Regime |
|---|---|---|---|---|---|
| ETH/4h | 1.054 | 0.982 | 1.048 | Trending | Ranging |
| ETH/1h | 1.009 | 1.115 | 0.858 | Ranging | Transitional |
| BTC/4h | 0.990 | 1.127 | 0.919 | Ranging | Transitional |
| BTC/1h | 0.884 | N/A | 0.772 | Trending | Transitional |

### Key regime findings

1. **ETH/4h remains the only asset/TF with a trending edge** (PF=1.054). This aligns with the EMA/RSI/ATR template's trend-following design. All other assets/TFs show their edge in ranging — suggesting the signal is accidentally capturing mean reversion.

2. **Transitional regimes are toxic** across all assets/TFs except ETH/4h. A universal transitional-regime circuit breaker would improve PF by eliminating the worst-performing 20–30% of trades.

3. **BTC shows ranging-only edge** (PF=1.127 on 4h) but the absolute drawdown makes it uneconomical. BTC ranging trades should not be pursued until position sizing and fee structure are resolved.

4. **Regime gating could lift ETH/4h PF from 1.033 to ~1.05** by eliminating ranging trades (PF=0.982). The improvement is modest because the current strategy is already trending-biased.

### Recommendation
- Implement regime gate as a filter in signal templates
- ETH/4h: allow trending + transitional only
- ETH/1h: allow ranging only (if this asset/TF is kept)
- BTC: suspend entirely

---

## Recommended Directives

### Priority 1: CRITICAL (act THIS cycle — 4th time requesting)

| # | Directive | Rationale | Status |
|---|---|---|---|
| 1 | **KILL_EXPLORATION_VARIANT** | Destructive in every backtest for 4 cycles. Wastes 20% compute. | IGNORED x3 |
| 2 | **FIX_VARIANT_DEDUP** | 60% compute wasted on duplicate results. Hash resolved params before backtesting. | IGNORED x3 |
| 3 | **ITERATE_EXIT_CHANGE_ONLY** | Only profitable lead (PF=1.033). Create 4x4 ATR stop/TP matrix on ETH/4h. | IGNORED x3 |
| 4 | **REMOVE_STOCHASTIC_REVERSAL** | Dead template, 0 trades. Replace in diversity slot. | IGNORED x2 |
| 5 | **BACKTEST_CLAUDE_SPECS** | 15 specs covering 5 templates sit unbacktested. Pipeline must consume `artifacts/claude-specs/`. | NEW |

### Priority 2: HIGH (act within 2 cycles)

| # | Directive | Rationale |
|---|---|---|
| 6 | **SUSPEND_ALL_BTC** | Pure loss generator across all timeframes. Redirect compute to ETH. |
| 7 | **FIX_DRAWDOWN_GATE_UNITS** | DD comparison uses mixed units (dollars vs percentage). Open 3 cycles. |
| 8 | **BLACKLIST_GATE_ADJUST** | 27 prescriptions, 0% success rate. Non-functional directive. |
| 9 | **BLACKLIST_ENTRY_TIGHTEN_RELAX** | 4–9 attempts, 0% improvement. Dead directives. |
| 10 | **STOP_TPX_SWEEPS** | Thresholds 20/30/40 produce identical results. Parameter not consumed. |

### Priority 3: MEDIUM (act within 5 cycles)

| # | Directive | Rationale |
|---|---|---|
| 11 | **IMPLEMENT_REGIME_GATING** | Data available in backtester output. Gate by regime to lift PF. |
| 12 | **CONNECT_ADVISORY_TO_PIPELINE** | Advisory directives are dead letters. 0 of 9 actioned across 3 cycles. Need machine-readable directive file. |
| 13 | **DEDUPLICATE_TEMPLATE_COMBOS** | Remove `rsi_pullback` (identical to `ema_rsi_atr`) or differentiate it. |
| 14 | **DRAWDOWN_COMPRESSION** | Apply time filters and circuit breaker to PF=1.033 lead. Target DD < 0.15. |

---

## Doctrine Gaps

### 1. Advisory-to-pipeline feedback loop BROKEN (4TH CYCLE — MOST CRITICAL)
The advisory has issued 9+ specific directives across 3 updates. **Zero have been actioned.** The Strategist does not read `STRATEGY_ADVISORY.md`. Without a consumption pathway, this advisory is a write-only artifact. Either create `artifacts/claude-specs/advisory_directives.json` for machine consumption, or add advisory-awareness to the Strategist's context.

### 2. Directive effectiveness circuit-breaker ABSENT (4TH CYCLE)
GATE_ADJUST: tried 27 times, improved 0. ENTRY_TIGHTEN: tried 4+ times, improved 0. ENTRY_RELAX: tried 9+ times, improved 0. The pipeline lacks a rule: "if directive tried >= 3 times with avg_delta_pf <= 0.0, blacklist for this family." This should be a doctrine principle.

### 3. No regime assumption enforcement (4TH CYCLE)
Doctrine [20260226-06] requires explicit regime assumptions in every hypothesis. No strategy spec carries regime assumptions despite regime data now being available in backtester output. The Claude-generated specs in `artifacts/claude-specs/` DO include regime assumptions — the pipeline-generated specs do not.

### 4. Compute waste doctrine gap (2ND CYCLE)
No doctrine principle governs compute efficiency. Current waste rate: 60% (variant dedup) + 20% (dead templates) = **80% of backtesting compute wasted**. Proposed rule: "Before submitting a backtest batch, validate unique parameter fingerprints. Skip duplicates."

### 5. Template coverage doctrine gap (NEW)
4 of 7 templates have NEVER been backtested. The pipeline has run 50+ backtest cycles exclusively on `ema_rsi_atr`. No doctrine principle mandates minimum template coverage. Proposed rule: "Each template must receive at least one backtest per 10 cycles."

### 6. Research card utilization gap (NEW)
The research cards pipeline (`artifacts/research_cards/`) contains only 1 test fixture. Video ingestion insights are not flowing into strategy generation. This represents a dead branch in the knowledge pipeline — insights from market analysis videos are not being converted into testable hypotheses.

### 7. Claude-spec integration gap (NEW)
Quandalf has generated 15 strategy specs, but no pipeline mechanism exists to consume them. The specs follow the correct schema (v1.1) with variants, RoleFramework tags, and edge hypotheses. The gap is purely in pipeline plumbing — the Strategist only reads its own output, not `artifacts/claude-specs/`.

---

## Suggestions For Asz

### 1. Wire `artifacts/claude-specs/` into the backtest pipeline
The highest-ROI change right now is enabling the backtester to consume Claude-generated strategy specs. 15 specs covering 5 untested templates already exist. The schema matches what the backtester expects. This could be as simple as adding `artifacts/claude-specs/` as an additional spec source in the backtest runner, alongside the Strategist's output. This single change would break the 4-cycle stagnation loop by testing genuinely different strategies.

### 2. Add a directive blacklist mechanism
The pipeline prescribes GATE_ADJUST, ENTRY_TIGHTEN, and ENTRY_RELAX despite 27+, 4+, and 9+ failed attempts respectively. A simple JSON blacklist file (`artifacts/library/DIRECTIVE_BLACKLIST.json`) keyed by `{strategy_family, directive_type}` would prevent the Analyser from re-issuing provably dead directives. The rule: if `tried >= 3 AND avg_delta_pf <= 0.0`, add to blacklist. This frees directive slots for untried approaches and stops the stagnation loop.

### 3. Implement a variant fingerprint check before backtesting
60% of compute is wasted on duplicate variants that produce identical results. Before submitting to the backtester, hash the resolved signal parameters tuple `{template, confidence_threshold, stop_atr_mult, tp_atr_mult, risk_r, filters}`. If the hash matches an already-queued variant, skip it and reallocate the slot to an alternative (e.g., next Claude-generated spec, or a parameter perturbation with larger step size). This is a 5-line change in the backtest dispatch logic that would triple the effective throughput of the pipeline.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 2 |
|---|---|---|
| Outcome notes reviewed | 30 (20260227–28) | Refreshed window |
| Outcome verdict distribution | 27 REJECT / 3 REVISE / 0 ACCEPT | Slightly worse (was 25R/5Rev) |
| Backtest results reviewed | 10 (20260225) | Different date range |
| Best PF observed | **1.033** (exit_change, ETH/4h) | **No change — 4th cycle stagnating** |
| Worst PF observed | 0.000 (stochastic_reversal) | No change |
| Worst active PF | 0.654 (BTC/1h) | Worse (was 0.754) |
| Unique templates tested | 2 of 7 (ema_rsi_atr + stochastic_reversal dead) | No change |
| Claude-generated specs awaiting backtest | **15** | +15 new |
| Templates with ready-to-test Claude specs | **5** (supertrend, MACD, Bollinger, EMA xover, RSI pullback) | All new |
| Zero-trade backtests | Ongoing (stochastic_reversal) | No change |
| Directive success rate (GATE_ADJUST) | 0/27 = **0%** | Worsened (was 0/10) |
| Compute waste rate | ~80% (dedup + dead templates + BTC) | No change |
| Pipeline bugs open | 6+ (all persisting) | No change |
| Prior advisory directives actioned | **0 of 9** | **No change — CRITICAL** |
| Research cards available | 1 (test fixture only) | No change |

---

*Next review scheduled: 2026-03-01. The pipeline is in a **critical stagnation state**. The single highest-impact action is wiring `artifacts/claude-specs/` into the backtest pipeline — this immediately unlocks 15 new specs across 5 untested templates and breaks the 4-cycle ema_rsi_atr monoculture.*
