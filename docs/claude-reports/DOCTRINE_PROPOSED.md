# Analyser Doctrine — Proposed v6

**Synthesized:** 2026-03-05 | **Author:** claude-advisor (DOCTRINE_SYNTHESIZER mode)
**Sources:** analyser-doctrine.md (41 entries), DOCTRINE_PROPOSED v5 (40 entries), ~830+ outcome notes (20260226–20260305), Strategy Advisory U26, 10 unique ACCEPTs
**Prior proposed:** v5 (20260304, 740+ outcomes)

---

## Changelog from v5

### Updated (4 entries — evidence base expanded 740→830+ outcomes, advisory U25–U26)
| Entry | Change |
|---|---|
| A-05 | Strengthened: Claude spec ACCEPT rate ~25% (2/9 specs → ACCEPT) vs pipeline ~0% (0 ACCEPTs from 640+ pipeline backtests). 102+ consecutive pipeline zero-trade backtests crossing day boundary (03-04 → 03-05). 3 Claude specs blocked 3 consecutive cycles. |
| A-07 | Updated: 102+ zero-trade backtests now (was 93%+ dedup rate). 36 new zero-trade runs on 2026-03-05 alone — all directive-generated, all sharing EMA+RSI+ATR+confidence_threshold architecture. |
| A-12 | Updated: Directive loop now confirmed CIRCULAR — same 5 remediation actions recycled on every zero-trade failure (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE). Loop crossed day boundary with no self-correction. ENTRY_RELAX and ENTRY_TIGHTEN issued simultaneously = self-contradictory. |
| AT-01 | Updated: 0 BTC ACCEPTs across 800+ outcomes (was 740+). Even champion Vortex v3a loses on BTC (PF=0.743). |

### Added (5 new entries from 830+ outcome evidence base)
| Entry | Evidence |
|---|---|
| S-11 | Max 2 entry conditions per spec. Triple conjunctions produce zero trades. All 10 ACCEPTs use ≤2 entry conditions. |
| S-12 | Transition-detection is a general edge mechanism. Vortex + Ichimoku TK = different math, same thesis, both ACCEPT. |
| A-14 | Zero-trade circuit breaker: halt spec family after 5 consecutive zero-trade backtests. 102+ epidemic would have been caught at 5–10. |
| A-15 | Pipeline halt when zero-trade rate exceeds 50% of a batch window. Not circuit-break — full halt. Reallocate capacity to Claude specs. |
| AT-06 | Transition-detection indicators (Vortex, Ichimoku TK) produce highest-alpha strategies. Expand to TRIX, TREX, TASC DM. |

### Removed from v5 (0 entries)
All v5 entries retain evidence support.

---

## 1) Research Heuristics

- [20260302-R01|conf:0.74] Treat all externally-derived ideas (transcripts, videos, articles) as hypotheses. Promote to doctrine only when supported by at least one backtest with PF > 1.1 and 30+ trades. Require 2 independent positive results before conferring conf > 0.80.

- [20260226-04|conf:0.70] Prefer concepts that map cleanly into schema-valid ResearchCards and deterministic backtester pipelines. If an idea cannot be expressed as a testable spec with entry/exit rules and measurable thresholds, it is not ready for doctrine.

- [20260302-R03|conf:0.72] Down-rank advice that lacks: (a) explicit failure conditions, (b) measurable outcome thresholds, or (c) constraints on when NOT to apply. Promote ideas that improve observability, auditability, and operator decision quality.

- [20260302-R04|conf:0.70] When recurring concept signals emerge from research (risk controls, data quality, workflow patterns), formalize them into testable doctrine entries with specific thresholds and evidence pointers — not vague concept tags. Require evidence citations (backtest hash, outcome file, metric) for every proposed doctrine change.

- [20260303-T01|conf:0.80] **Research cards must contain extracted rules, not catalog metadata.** A research card with only an indicator title and author name has zero doctrine value. Minimum viable card: at least one testable condition (e.g., "RSI_14 crosses_above 30 when ADX_14 > 25"). Evidence: 180+ cards produced, 0 with extracted rules, 0 hypotheses generated from the entire pipeline.

---

## 2) Strategy Hypothesis Heuristics

- [20260226-06|conf:0.76] Every hypothesis must state: (a) which regime(s) it targets, (b) what invalidates it, and (c) what metric thresholds constitute success or failure. Hypotheses without explicit regime assumptions are rejected at spec review.

- [20260226-07|conf:0.74] Separate signal logic from execution logic. Entry signals, exit rules, and position sizing must be independently testable. Confounded attribution (signal + execution in one block) prevents meaningful iteration. Evidence: `library_augmented` and `entry_tighten` produced byte-identical results when signal and execution were entangled.

- [20260302-S03|conf:0.78] Risk gating is mandatory before execution. Every strategy must enforce: (a) session gating — market conditions check before trade enablement, (b) risk limit enforcement — max DD cap and position size limit as non-optional pre-trade checks, (c) drawdown circuit breaker — auto-halt at configured threshold. Do not scale variant count until at least one variant achieves positive expectancy.

- [20260226-09|conf:0.71] Only accept mutation candidates that preserve non-repainting behavior and bar-close determinism. Reject any indicator or rule that uses future data or intra-bar state.

- [20260303-S05|conf:0.93] **Minimum reward:risk ratio of 5:1 for all new strategy specs.** Across 830+ outcomes: all 10 unique ACCEPTs use R:R >= 5:1. 8:1 is the validated sweet spot (6/10 ACCEPTs). Every strategy with R:R < 4:1 produces PF < 1.05 after fees (4.5 bps taker + 1 bps slippage = 5.5 bps round-trip). Do not generate, backtest, or promote specs with TP/SL < 5.0.

- [20260303-S06|conf:0.90] **Maximum drawdown of 20% for ACCEPT consideration; <=15% preferred.** 8/10 unique ACCEPTs have DD <= 16.4% (champion Supertrend 8:1 = 10.9%). DD > 30% = automatic REJECT without further analysis. The 15–20% band is REVISE territory. Stop multiplier floor of 1.5 ATR to prevent micro-stop noise. Note: EMA200 Vortex v2 (PF=1.969, DD=30%) is CONDITIONAL — DD exceeds cap despite record trans PF=4.321.

- [20260302-S07|conf:0.85] **Multi-regime profitability required for ACCEPT.** A strategy must show PF > 1.0 in at least 2 of 3 regimes (trending, ranging, transitional). Single-regime strategies are REVISE at best. Evidence: 8/10 unique ACCEPTs are all-regime profitable (PF > 1.0 in all 3 regimes).

- [20260303-S08|conf:0.85] **Ranging is the dominant profit regime.** All 10 unique ACCEPTs profit in ranging (PF 1.12–4.87). Top ranging PFs: KAMA Stoch v1 (4.87), Supertrend 8:1 (2.914), Supertrend ultra (2.558), MACD 7:1 (2.062). Design strategies to capture momentum mean-reversion within established ranges.

- [20260304-S09|conf:0.90] **Gate non-resilient strategies during trending regime.** Most ACCEPTs lose money in trending. Only adaptive indicators (Vortex, KAMA, Supertrend) survive trending. Evidence: T3 Vortex Hybrid v2 REJECTED — 48% of 277 trades in trending at PF=0.570 dragged overall PF to 0.980, while ranging PF=1.756 and transitional PF=1.357 were profitable. Filtering out trending trades would have salvaged this strategy. Add ADX < 25 or CHOP > 50 as a trending-regime gate for non-adaptive templates.

- [20260304-S10|conf:0.85] **Adaptive indicators produce all-regime edge; static indicators do not.** Adaptive indicators (KAMA, Vortex, Supertrend) adjust behavior to market conditions. All 8 all-regime ACCEPTs use at least one adaptive indicator. Static indicators (EMA, SMA, fixed-period RSI) fail in trending without regime gating. Prefer adaptive indicator families as primary signal source; static indicators acceptable as secondary filters only.

- [20260305-S11|conf:0.90] **Maximum 2 entry conditions per strategy spec.** All 10 unique ACCEPTs use <= 2 entry conditions. Triple conjunctions (3+ simultaneous AND conditions) produce zero trades — the intersection is too narrow to trigger on real market data. Evidence: 102+ consecutive zero-trade backtests used 3–4 entry conditions (EMA+RSI+ATR+confidence_threshold). Reduce complexity, not threshold parameters, to restore signal generation.

- [20260305-S12|conf:0.88] **Transition-detection is a general edge mechanism, not indicator-specific.** Both Vortex (directional momentum crossover) and Ichimoku TK (median price crossover) detect regime transitions using entirely different mathematical foundations — yet both produce all-regime profitable strategies. Any indicator that detects direction-change moments is a candidate for new ACCEPT-tier strategies. Priority candidates: TRIX zero-cross, TREX histogram zero-cross, TASC DM (Hilbert transform phase detection). This extends transition-detection from a single-indicator finding to a thesis-level insight.

- [20260226-10|conf:0.70] Reject strategy framing that implies guaranteed outcomes or non-falsifiable claims. Every strategy must have a kill condition: a specific metric threshold (e.g., PF < 1.0 over 50+ trades) that triggers deprecation.

- [20260228-02|conf:0.78] When PF ~ 1.00 on large samples (>300 trades), prioritize drawdown compression and trade-quality filtering before signal complexity changes. Apply: time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. Evidence: PF=1.033 on 389 trades — the signal exists but fees/noise erode it; tighten the filter, don't add more signals.

- [20260228-03|conf:0.80] If a directive type has been applied >= 3 consecutive times to a strategy family with avg delta PF <= 0.0, auto-blacklist that directive for that family. Evidence: ENTRY_TIGHTEN (4+ attempts, PF degraded 0.920→0.872), GATE_ADJUST (4 attempts, 0 improvement), DIRECTIVE_EXPLORATION (PF 0.51–0.88, worst in 830+ outcomes, DD up to 1501%).

---

## 3) Automation & System Heuristics

- [20260226-11|conf:0.78] Maintain human approval checkpoints for: (a) promoting strategies from backtest to forward-test, (b) transitioning from paper to live trading, (c) any change to risk parameters or position sizing, (d) doctrine changes to the canonical file. Automation handles repetition; humans handle judgment.

- [20260302-A02|conf:0.76] Invest in telemetry before features. Before adding new automation, ensure visibility into: risk exposure, execution latency, slippage, execution drift, and strategy PF decay. Execution quality tracking (actual vs. expected fills) should be a continuous monitoring signal, not a post-mortem exercise.

- [20260302-A03|conf:0.75] Prioritize infrastructure that compounds across every future cycle: parameter-level deduplication, machine directive enforcement parsing, agent quality gates requiring evidence links, and session gating checklists. Each of these reduces systemic waste.

- [20260226-14|conf:0.73] Use prompt/version control and rollback pathways for all agentic research components. Every LLM-generated artifact must be traceable to its prompt version and input data.

- [20260226-15|conf:0.72] Build error taxonomies from pipeline failures. Categorize failures (zero trades, high DD, parameter convergence, directive non-consumption) and link to root causes. Directive failure histories must feed back into directive selection. Evidence: pipeline continues issuing ENTRY_TIGHTEN and GATE_ADJUST despite 0% success rate across 20+ cycles.

- [20260305-A05|conf:0.95] **Prioritize Claude-generated specs over pipeline-generated specs in batch queue.** Claude specs: 10/10 unique ACCEPTs (~25% ACCEPT rate per spec). Pipeline specs: 0 ACCEPTs from 640+ pipeline backtests (drought = 53+ cycles). 102+ consecutive pipeline zero-trade backtests crossing day boundary. 3 Claude specs (ALMA Vortex, T3 EMA200, CCI KAMA — 9 variants) blocked 3 consecutive cycles while pipeline consumed all capacity. Run Claude specs FIRST each cycle; fill remaining capacity with pipeline specs only after they pass machine directive filters AND parameter-level dedup.

- [20260303-A06|conf:0.85] **Prune dead templates after 3 consecutive cycles of zero trades.** Remove from TEMPLATE_REGISTRY: stochastic_reversal (0 trades, 18+ cycles, confirmed bug line 174), bollinger_breakout (0 trades, 14+ cycles, volume gate broken), choppiness_donchian_fade (0 trades, 8+ cycles, CHOP>61.8 AND close<=DCL AND RSI<35 triple conjunction near-impossible). If fixed, re-add after producing >= 1 trade in isolated test.

- [20260305-A07|conf:0.95] **Deduplicate at the resolved parameter level, not the spec level.** 95%+ of compute is wasted on duplicates. Latest evidence: 102+ zero-trade directive variants share identical EMA+RSI+ATR+confidence_threshold architecture — different family IDs, same resolved parameters. Hash the tuple `(template_name, indicator_params, stop_mult, tp_mult, timeframe, asset)` and skip duplicates before backtesting. Single biggest efficiency gain available.

- [20260303-A08|conf:0.82] **Pre-validate signal count before full backtest.** Run a fast signal scan (evaluate entry conditions only, skip position simulation) before committing to a full backtest run. If `signal_count < 10` across the data window, skip the backtest and log "insufficient signals." Evidence: 102+ zero-trade outcomes. Would have prevented 97+ wasted runs.

- [20260303-A09|conf:0.78] **Validate Claude spec template routing before backtest.** Claude specs with custom `template_name` values must be confirmed to route correctly through `spec_rules` with `entry_long`/`entry_short` conditions intact. Add a pre-flight check: does template resolve? Do entry conditions reference valid dataframe columns?

- [20260303-A10|conf:0.85] **Deduplicate at backtest scheduling level.** Before scheduling a backtest, check if an identical `(spec_hash, asset, timeframe)` combination has already been run. This is distinct from A-07 (parameter dedup catches differently-named specs that resolve identically); this catches the same spec run twice.

- [20260304-A11|conf:0.95] **YAML serialization must use multi-line array syntax.** Brain objects and all YAML frontmatter MUST use `- item` per line for arrays. Never use inline `[a, b, c]` syntax. The BALROG validator's `json.loads()` parser cannot parse unquoted inline arrays. Evidence: this single bug blocked ALL backtests for 36+ attempts across 6+ autopilot cycles (U18–U20).

- [20260305-A12|conf:0.95] **Directive system is non-functional and circular — do not rely on automated refinement.** 49+ machine directives issued across advisory cycles, 0 enforced by the pipeline. Directive loop confirmed CIRCULAR: same 5 remediation actions (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE) recycled on every zero-trade failure. ENTRY_RELAX and ENTRY_TIGHTEN issued simultaneously = self-contradictory. Loop crossed day boundary (03-04 → 03-05) with no self-correction. 102+ consecutive zero-trade backtests = conclusive. Do not allocate compute to directive-based refinement until the enforcement mechanism is rebuilt from scratch.

- [20260304-A13|conf:0.78] **Define forward-test graduation criteria.** Two strategies are live in forward-test (Vortex v3a, Supertrend 8:1) with KAMA Stoch v1 and Ichimoku TK v1 as candidates for lanes 3–4. No criteria exist for graduation. Proposed minimum: 30 days live, PF > 1.2, DD < 15%, human approval gate. PF < 0.8 or DD > 25% = demote.

- [20260305-A14|conf:0.92] **Zero-trade circuit breaker: halt spec family after 5 consecutive zero-trade backtests.** When any single spec family produces 5+ consecutive zero-trade backtest results, halt ALL further backtests from that family. Escalate to Claude spec review for root cause diagnosis. Evidence: 102+ consecutive zero-trade backtests all from the same EMA+RSI+ATR+confidence_threshold pipeline spec family. A circuit breaker at 5 would have saved 97+ wasted runs (2+ days of compute). The current system has no mechanism to detect and halt repeated zero-trade failures.

- [20260305-A15|conf:0.90] **Pipeline full halt when zero-trade rate exceeds 50% of a batch window.** When more than half the backtests in any 10-run window produce zero trades, the pipeline must halt entirely — not circuit-break a single family. Reallocate ALL backtest capacity to Claude-specified specs until the pipeline produces at least 1 trade per run on a validation set. This is a system-level safety valve, not a per-family control. Evidence: 102+ consecutive zero-trade across ALL pipeline specs is a systemic failure, not a single-spec issue.

- [20260228-06|conf:0.74] Ensure all gate comparisons use consistent units. Thresholds expressed as percentages must be compared to percentage values; absolute values to absolute thresholds. Evidence: drawdown gate compared $981 (absolute) to 0.30 (percentage), causing false rejections.

---

## 4) Asset & Timeframe Heuristics

- [20260305-AT01|conf:0.85] **ETH-first routing for all new experiments.** 0 BTC ACCEPTs across 800+ outcomes over 26 cycles. BTC PF range: 0.594–1.001 (all-time). Even champion Vortex v3a produces PF=0.743 on BTC. Route all new experiments through ETH first. Only expand to BTC after achieving PF > 1.10 on ETH with 50+ trades.

- [20260228-08|conf:0.78] No single template may consume more than 60% of backtest compute in any 5-cycle window. If a template has been tested 10+ times without PF > 1.05, force-rotate to untested templates. Evidence: monopoly patterns on ema_rsi_atr (30/30 outcomes on 20260227) while 5 templates remained untested.

- [20260228-09|conf:0.72] When combining variant types, test only the two highest-performing individual types together. Do not combine more than 2 mutation axes simultaneously.

- [20260303-AT04|conf:0.76] **Untested templates are priority backtest candidates.** kama_vortex_divergence exists in `signal_templates.py` with 0 backtests ever. ALMA, Ichimoku, and T3 indicator families have low coverage. Novel hypotheses with unused indicators should be tested before further refinement of exhausted templates.

- [20260304-AT05|conf:0.90] **4h is the only validated timeframe.** 0 ACCEPTs on 15m or 1h across 10 unique ACCEPTs and 50+ backtests. 1h degrades PF by 0.94 avg compared to 4h on the same strategy. Route all new experiments to 4h primary. Only test 1h after a strategy achieves ACCEPT on 4h, and only to assess timeframe robustness — not to discover edge.

- [20260305-AT06|conf:0.85] **Transition-detection indicators are the highest-alpha research frontier.** Indicators that detect direction-change moments produce the highest-PF strategies: Vortex (trans PF=3.886), Ichimoku TK (trans PF=2.44), EMA200 Vortex (trans PF=4.321 RECORD). This is validated across 2 independent indicator families (Vortex = directional momentum, Ichimoku = median price). Priority expansion: TRIX zero-cross, TREX histogram zero-cross, TASC DM (Hilbert transform phase detection). Once these indicators are added to the dataframe, design 2-condition specs following brain rules (ETH 4h, 8:1 R:R).

---

## Removed Entries (Audit Trail — cumulative)

### Removed from original doctrine (v3, unchanged)
| Removed ID | Reason |
|---|---|
| 20260226-26 | Opaque YouTube ID `qbyQ8322m-M` — no extractable content |
| 20260226-28 | Derivative of -26 — "convert concept" with no concept specified |
| 20260226-30 | Derivative of -26 — "record ingestion pointer" with no target |
| 20260226-31 | Opaque YouTube ID `CEJ_R5226xE` — no extractable content |
| 20260226-32 | Opaque YouTube ID `qMHd7NMu_Gc` — no extractable content |
| 20260226-34 | Opaque YouTube ID `D4_rO7qK2rY` — no extractable content |
| 20260226-36 | Opaque YouTube ID `NPxmHIGq-yY` — no extractable content |
| 20260226-37 | Opaque YouTube ID `R-4uCkGMBag` — no extractable content |

### Consolidated from original doctrine (v3, unchanged)
| Absorbed ID | Into | Reason |
|---|---|---|
| 20260226-01 | R-01 | Merged with -02: both require hypothesis treatment |
| 20260226-02 | R-01 | Merged with -01 |
| 20260226-03 | R-03 | Merged with -05: both require actionability |
| 20260226-05 | R-03 | Merged with -03 |
| 20260226-08 | S-03 | Merged with -20, -21: all require risk/session gating |
| 20260226-13 | A-02 | Merged with -22: both require telemetry investment |
| 20260226-16 | A-03 | "risk controls" signal → infrastructure rule |
| 20260226-17 | A-03 | "community/distribution" signal → infrastructure rule |
| 20260226-18 | A-03 | "workflow automation" signal → infrastructure rule |
| 20260226-19 | R-04 | "data ingestion quality" → evidence pointer rule |
| 20260226-20 | S-03 | "session gating" hook → risk gating rule |
| 20260226-21 | S-03 | "risk limit enforcement" hook → risk gating rule |
| 20260226-22 | A-02 | "execution quality tracking" → telemetry rule |
| 20260226-23 | A-03 | "auto-transcript ingestion" → infrastructure rule |
| 20260226-24 | S-03 | "session gating checklist" → risk gating rule |
| 20260226-25 | A-03 | "agent quality gate" → infrastructure rule |

---

## Synthesis Notes

### Key changes from v5 → v6

1. **Evidence base expanded 12%**: 830+ outcomes (was 740+). Key new signal: 102+ consecutive zero-trade backtests crossing day boundary (03-04 → 03-05), directive loop confirmed circular (same 5 actions recycled), 10 unique ACCEPTs (was 8), transition-detection validated as general mechanism across 2 independent indicator families.

2. **5 new entries**: S-11 (max 2 entry conditions), S-12 (transition-detection thesis), A-14 (zero-trade circuit breaker), A-15 (pipeline full halt), AT-06 (transition-detection frontier).

3. **4 entries updated**: A-05 (Claude priority — 3 specs blocked 3 cycles), A-07 (dedup — 102+ zero-trade), A-12 (directive loop circular — confirmed self-contradictory), AT-01 (800+ outcomes).

4. **S-11 codifies the 2-condition rule**: 102+ zero-trade backtests all used 3–4 entry conditions. All 10 ACCEPTs use <= 2. This is the single strongest signal for why pipeline specs fail: entry logic too complex for real market data.

5. **Circuit-breaker doctrine fills critical gap**: A-14 and A-15 are the most actionable new entries. Without them, the system has no mechanism to detect or halt repeated failures. The 102+ epidemic proves this gap is catastrophic — 97+ wasted backtests, 2+ days of compute, all producing identical zero-trade results.

6. **Transition-detection elevated from finding to thesis**: S-12 + AT-06 formalize the observation that regime-transition detection is indicator-agnostic. Vortex and Ichimoku TK use completely different math but both produce all-regime ACCEPTs. This opens the door to TRIX, TREX, and TASC DM as next-generation candidates.

### Entry count summary
| Section | v5 Entries | v6 Entries | Change |
|---|---|---|---|
| Research Heuristics | 5 | 5 | 0 |
| Strategy Hypothesis | 13 | 15 | +2 (S-11 max 2 conditions, S-12 transition-detection) |
| Automation & System | 17 | 19 | +2 (A-14 circuit breaker, A-15 pipeline halt) |
| Asset & Timeframe | 5 | 6 | +1 (AT-06 transition-detection frontier) |
| **Total** | **40** | **45** | **+5 net** |

### Confidence distribution
| Range | Count | Examples |
|---|---|---|
| 0.90+ | 9 | S-05 (R:R floor), S-06 (DD cap), S-09 (trending gate), S-11 (2 conditions), A-05 (Claude priority), A-07 (dedup), A-11 (YAML), A-12 (directives dead), A-14 (circuit breaker), A-15 (pipeline halt), AT-05 (4h) |
| 0.80–0.89 | 10 | S-07, S-08, S-10, S-12, A-06, A-08, A-10, AT-01, AT-06, T-01 |
| 0.70–0.79 | 15 | R-01 through R-04, S-03, S-04, etc. |
| <0.70 | 0 | — |

All entries meet the minimum confidence threshold of 0.70. Nine entries at 0.90+ (was six in v5) — evidence base now strong enough to justify high-confidence rules on entry complexity, dedup, and pipeline safety.

### Priority actions for next cycle
1. **HALT PIPELINE** — 102+ zero-trade is conclusive. Every additional run is confirmed waste.
2. **Execute 3 blocked Claude specs** (ALMA Vortex, T3 EMA200, CCI KAMA) — 9 variants, ETH 4h. At 25% ACCEPT rate, ~2 should produce tradeable results.
3. **Add TRIX_14, TREX, TASC DM to dataframe** — transition-detection expansion candidates.
4. **Define forward-test graduation criteria** (A-13) — 7th cycle requesting.
5. **Promote KAMA Stoch v1 + Ichimoku TK v1 to forward-test** — decorrelated ACCEPTs.
6. **Implement circuit breaker** (A-14) — zero-code: `if consecutive_zero_trade >= 5: skip_family()`.

---

*This is a PROPOSED revision. The canonical doctrine file (`docs/DOCTRINE/analyser-doctrine.md`) should only be updated by `update_analyser_doctrine.py` after human review.*
*Proposed by Quandalf — 2026-03-05*
