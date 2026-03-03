# Analyser Doctrine — Proposed v5

**Synthesized:** 2026-03-04 | **Author:** claude-advisor (DOCTRINE_SYNTHESIZER mode)
**Sources:** analyser-doctrine.md (41 entries), DOCTRINE_PROPOSED v4 (35 entries), ~740 outcome notes (20260226–20260304), Strategy Advisory Update 20, 49 batch runs, 8 unique ACCEPTs
**Prior proposed:** v4 (20260303, 706 outcomes)

---

## Changelog from v4

### Updated (3 entries — evidence base expanded 706→740+ outcomes, advisory U20)
| Entry | Change |
|---|---|
| S-09 | Strengthened: T3 Vortex Hybrid v2 REJECT specifically because 48% of trades in trending at PF=0.570 while ranging PF=1.756 and transitional PF=1.357. Adds concrete evidence that trending-regime gating would have salvaged an otherwise profitable strategy. |
| A-05 | Updated: 8/8 unique ACCEPTs in recent cycles are Claude-specified. Pipeline drought=53 cycles, 0 backtests executed this cycle due to BALROG block. |
| A-07 | Updated: 9 identical REJECT clones (PF=0.920, DD=981%, 226 trades) across 6 directive variants in latest outcomes — confirms waste now infects REJECTs too, not just ACCEPTs. |

### Added (5 new entries from 740+ outcome evidence base)
| Entry | Evidence |
|---|---|
| S-10 | Adaptive indicators > static for all-regime edge. KAMA+Vortex produce all 6 all-regime ACCEPTs. |
| A-11 | YAML serialization: multi-line arrays only. Inline `[a, b]` blocked ALL backtests for 36+ attempts. |
| A-12 | Directive system is non-functional. 49 directives issued, 0 enforced. 0% variant improvement rate. |
| A-13 | Forward-test graduation criteria needed. 2 live lanes, 0 defined milestones. |
| AT-05 | 4h is the only validated timeframe. 0 ACCEPTs on 15m or 1h ever. |

### Removed from v4 (0 entries)
All v4 entries retain evidence support.

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

- [20260303-S05|conf:0.93] **Minimum reward:risk ratio of 5:1 for all new strategy specs.** Across 740+ outcomes: all 8 unique ACCEPTs use R:R ≥ 5:1. 8:1 is the validated sweet spot (4/8 ACCEPTs). Every strategy with R:R < 4:1 produces PF < 1.05 after fees (4.5 bps taker + 1 bps slippage = 5.5 bps round-trip). Do not generate, backtest, or promote specs with TP/SL < 5.0.

- [20260303-S06|conf:0.90] **Maximum drawdown of 17% for ACCEPT consideration; ≤10% preferred.** 8/8 unique ACCEPTs have DD ≤ 16.4% (champion Supertrend 8:1 = 10.9%). DD > 30% = automatic REJECT without further analysis. The 10–17% band is REVISE territory. Stop multiplier floor of 1.5 ATR to prevent micro-stop noise.

- [20260302-S07|conf:0.85] **Multi-regime profitability required for ACCEPT.** A strategy must show PF > 1.0 in at least 2 of 3 regimes (trending, ranging, transitional). Single-regime strategies are REVISE at best. Evidence: 6/8 unique ACCEPTs are all-regime profitable (PF > 1.0 in all 3 regimes).

- [20260303-S08|conf:0.85] **Ranging is the dominant profit regime.** All 8 unique ACCEPTs profit in ranging (PF 1.12–4.87). Top ranging PFs: KAMA Stoch v1 (4.87), Supertrend 8:1 (2.914), Supertrend ultra (2.558), MACD 7:1 (2.062). Design strategies to capture momentum mean-reversion within established ranges.

- [20260304-S09|conf:0.90] **Gate non-resilient strategies during trending regime.** Most ACCEPTs lose money in trending. Only adaptive indicators (Vortex, KAMA, Supertrend) survive trending. Evidence (latest): T3 Vortex Hybrid v2 REJECTED — 48% of 277 trades in trending at PF=0.570 dragged overall PF to 0.980, while ranging PF=1.756 and transitional PF=1.357 were profitable. Filtering out trending trades would have salvaged this strategy. Add ADX < 25 or CHOP > 50 as a trending-regime gate for non-adaptive templates.

- [20260304-S10|conf:0.85] **Adaptive indicators produce all-regime edge; static indicators do not.** Adaptive indicators (KAMA, Vortex, Supertrend) adjust their behavior to market conditions. All 6 all-regime ACCEPTs use at least one adaptive indicator. Static indicators (EMA, SMA, fixed-period RSI) fail in trending without regime gating. When designing new strategies, prefer adaptive indicator families (KAMA, Vortex, Supertrend) as the primary signal source. Static indicators are acceptable as secondary filters only.

- [20260226-10|conf:0.70] Reject strategy framing that implies guaranteed outcomes or non-falsifiable claims. Every strategy must have a kill condition: a specific metric threshold (e.g., PF < 1.0 over 50+ trades) that triggers deprecation.

- [20260228-02|conf:0.78] When PF ≈ 1.00 on large samples (>300 trades), prioritize drawdown compression and trade-quality filtering before signal complexity changes. Apply: time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. Evidence: PF=1.033 on 389 trades — the signal exists but fees/noise erode it; tighten the filter, don't add more signals.

- [20260228-03|conf:0.80] If a directive type has been applied ≥ 3 consecutive times to a strategy family with avg delta PF ≤ 0.0, auto-blacklist that directive for that family. Evidence: ENTRY_TIGHTEN (4+ attempts, PF degraded 0.920→0.872), GATE_ADJUST (4 attempts, 0 improvement), DIRECTIVE_EXPLORATION (PF 0.51–0.88, worst in 740+ outcomes, DD up to 1501%).

---

## 3) Automation & System Heuristics

- [20260226-11|conf:0.78] Maintain human approval checkpoints for: (a) promoting strategies from backtest to forward-test, (b) transitioning from paper to live trading, (c) any change to risk parameters or position sizing, (d) doctrine changes to the canonical file. Automation handles repetition; humans handle judgment.

- [20260302-A02|conf:0.76] Invest in telemetry before features. Before adding new automation, ensure visibility into: risk exposure, execution latency, slippage, execution drift, and strategy PF decay. Execution quality tracking (actual vs. expected fills) should be a continuous monitoring signal, not a post-mortem exercise.

- [20260302-A03|conf:0.75] Prioritize infrastructure that compounds across every future cycle: parameter-level deduplication, machine directive enforcement parsing, agent quality gates requiring evidence links, and session gating checklists. Each of these reduces systemic waste.

- [20260226-14|conf:0.73] Use prompt/version control and rollback pathways for all agentic research components. Every LLM-generated artifact must be traceable to its prompt version and input data.

- [20260226-15|conf:0.72] Build error taxonomies from pipeline failures. Categorize failures (zero trades, high DD, parameter convergence, directive non-consumption) and link to root causes. Directive failure histories must feed back into directive selection. Evidence: pipeline continues issuing ENTRY_TIGHTEN and GATE_ADJUST despite 0% success rate across 20+ cycles.

- [20260304-A05|conf:0.95] **Prioritize Claude-generated specs over pipeline-generated specs in batch queue.** Claude specs: 100% of ACCEPTs in recent cycles (8/8 unique). Pipeline specs: 1 unique ACCEPT ever from 640+ backtests. Pipeline drought = 53 cycles, directive stalls = 44. Run Claude specs first each cycle; fill remaining capacity with pipeline specs only after they pass machine directive filters AND parameter-level dedup.

- [20260303-A06|conf:0.85] **Prune dead templates after 3 consecutive cycles of zero trades.** Remove from TEMPLATE_REGISTRY: stochastic_reversal (0 trades, 18+ cycles, confirmed bug line 174), bollinger_breakout (0 trades, 14+ cycles, volume gate broken), choppiness_donchian_fade (0 trades, 8+ cycles, CHOP>61.8 AND close≤DCL AND RSI<35 triple conjunction near-impossible). If fixed, re-add after producing ≥1 trade in isolated test.

- [20260304-A07|conf:0.95] **Deduplicate at the resolved parameter level, not the spec level.** 93%+ of compute is wasted on duplicates. Latest evidence: 9 REJECT clones (PF=0.920, DD=981%, 226 trades) produced across 6 directive variants with byte-identical metrics — different family IDs, same resolved parameters. Hash the tuple `(template_name, indicator_params, stop_mult, tp_mult, timeframe, asset)` and skip duplicates before backtesting. Single biggest efficiency gain available.

- [20260303-A08|conf:0.82] **Pre-validate signal count before full backtest.** Run a fast signal scan (evaluate entry conditions only, skip position simulation) before committing to a full backtest run. If `signal_count < 10` across the data window, skip the backtest and log "insufficient signals." Evidence: 2 zero-trade outcomes in 20260303 (empty spec, remove_component template). Would have prevented 10+ wasted runs over 3 cycles.

- [20260303-A09|conf:0.78] **Validate Claude spec template routing before backtest.** Claude specs with custom `template_name` values must be confirmed to route correctly through `spec_rules` with `entry_long`/`entry_short` conditions intact. Add a pre-flight check: does template resolve? Do entry conditions reference valid dataframe columns?

- [20260303-A10|conf:0.85] **Deduplicate at backtest scheduling level.** Before scheduling a backtest, check if an identical `(spec_hash, asset, timeframe)` combination has already been run. This is distinct from A-07 (parameter dedup catches differently-named specs that resolve identically); this catches the same spec run twice.

- [20260304-A11|conf:0.95] **YAML serialization must use multi-line array syntax.** Brain objects and all YAML frontmatter MUST use `- item` per line for arrays. Never use inline `[a, b, c]` syntax. The BALROG validator's `json.loads()` parser cannot parse unquoted inline arrays, causing schema validation to reject the object as "expected array, got string." Evidence: this single bug blocked ALL backtests for 36+ attempts across 6+ autopilot cycles (U18–U20). Impact: 53 drought cycles, 44 directive stalls. Fix: converted all 14 brain objects to multi-line syntax + `validated_at` timestamps.

- [20260304-A12|conf:0.92] **Directive system is non-functional — do not rely on automated refinement.** 49 machine directives issued across advisory cycles, 0 enforced by the pipeline. Directive variants (ENTRY_TIGHTEN, ENTRY_RELAX, GATE_ADJUST, THRESHOLD_SWEEP, EXIT_CHANGE, PARAM_SWEEP) produce byte-identical backtest metrics. The directive system also self-contradicts: zero-trade outcomes receive simultaneous ENTRY_RELAX + ENTRY_TIGHTEN suggestions. Refinement stage reports NO_IMPROVEMENT on 100% of outcomes. Do not allocate compute to directive-based refinement until the enforcement mechanism is rebuilt.

- [20260304-A13|conf:0.78] **Define forward-test graduation criteria.** Two strategies are live in forward-test (Vortex v3a, Supertrend 8:1) with KAMA Stoch v1 as a candidate for a third lane. No criteria exist for when a forward-tested strategy graduates to live trading. Define: minimum forward-test duration, minimum trade count, maximum PF degradation from backtest, maximum DD, and human approval gate.

- [20260228-06|conf:0.74] Ensure all gate comparisons use consistent units. Thresholds expressed as percentages must be compared to percentage values; absolute values to absolute thresholds. Evidence: drawdown gate compared $981 (absolute) to 0.30 (percentage), causing false rejections.

---

## 4) Asset & Timeframe Heuristics

- [20260303-AT01|conf:0.82] **ETH-first routing for all new experiments.** 0 BTC ACCEPTs across 740+ outcomes. BTC PF range: 0.594–1.001 (all-time). Route all new experiments through ETH first. Only expand to BTC after achieving PF > 1.10 on ETH with 50+ trades. BTC amplifies losses without proportional upside.

- [20260228-08|conf:0.78] No single template may consume more than 60% of backtest compute in any 5-cycle window. If a template has been tested 10+ times without PF > 1.05, force-rotate to untested templates. Evidence: monopoly patterns on ema_rsi_atr (30/30 outcomes on 20260227) while 5 templates remained untested.

- [20260228-09|conf:0.72] When combining variant types, test only the two highest-performing individual types together. Do not combine more than 2 mutation axes simultaneously.

- [20260303-AT04|conf:0.76] **Untested templates are priority backtest candidates.** kama_vortex_divergence exists in `signal_templates.py` with 0 backtests ever. ALMA, Ichimoku, and T3 indicator families have 0 coverage. Novel hypotheses with unused indicators should be tested before further refinement of exhausted templates. 3 pending Claude specs (ALMA MACDh, Ichimoku TK, T3 Vortex Pullback) are queued.

- [20260304-AT05|conf:0.90] **4h is the only validated timeframe.** 0 ACCEPTs on 15m or 1h across 8 unique ACCEPTs and 46+ backtests. 1h degrades PF by 0.94 avg compared to 4h on the same strategy. Route all new experiments to 4h primary. Only test 1h after a strategy achieves ACCEPT on 4h, and only to assess timeframe robustness — not to discover edge.

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

### Key changes from v4 → v5

1. **Evidence base expanded 5%**: 740+ outcomes (was 706). Key new signal: BALROG YAML bug root cause identified and fixed; KAMA Stoch v1 ACCEPT confirmed; T3 Vortex Hybrid trending-regime failure provides strongest S-09 evidence yet.

2. **5 new entries**: S-10 (adaptive > static), A-11 (YAML multi-line mandatory), A-12 (directive system dead), A-13 (forward-test graduation), AT-05 (4h only timeframe).

3. **Directive system officially declared dead**: A-12 consolidates 20 cycles of evidence: 0/49 directive enforcement, byte-identical metrics across directive variants, self-contradicting suggestions, 0% refinement improvement rate. This is the most significant structural finding — the entire refinement pipeline is inert.

4. **YAML serialization standard codified**: A-11 at conf:0.95 — a single formatting bug (inline arrays) blocked ALL backtests for 36+ attempts across 6 autopilot cycles. This is the highest-impact system-level learning since inception.

5. **Adaptive indicator thesis formalized**: S-10 codifies the meta-observation that all 6 all-regime ACCEPTs use adaptive indicators (KAMA, Vortex, Supertrend). This guides future spec design: start with adaptive indicators, use static as secondary filters.

6. **4h timeframe exclusivity**: AT-05 makes explicit what was implicit — 0 ACCEPTs on any timeframe other than 4h, with measured 0.94 PF degradation on 1h. This prevents wasted backtest runs on inferior timeframes.

### Entry count summary
| Section | v4 Entries | v5 Entries | Change |
|---|---|---|---|
| Research Heuristics | 5 | 5 | 0 |
| Strategy Hypothesis | 12 | 13 | +1 (S-10 adaptive indicators) |
| Automation & System | 14 | 17 | +3 (A-11 YAML, A-12 directives dead, A-13 fwd-test) |
| Asset & Timeframe | 4 | 5 | +1 (AT-05 4h only) |
| **Total** | **35** | **40** | **+5 net** |

### Confidence distribution
| Range | Count | Examples |
|---|---|---|
| 0.90+ | 6 | S-05 (R:R floor), S-06 (DD cap), S-09 (trending gate), A-05 (Claude priority), A-07 (dedup), A-11 (YAML), AT-05 (4h) |
| 0.80–0.89 | 9 | S-07, S-08, S-10, A-06, A-08, A-10, A-12, AT-01, T-01 |
| 0.70–0.79 | 14 | R-01 through R-04, S-03, S-04, etc. |
| <0.70 | 0 | — |

All entries meet the minimum confidence threshold of 0.70. Three entries elevated to 0.95 (A-05, A-07, A-11) based on overwhelming evidence.

### Priority actions for next cycle
1. Verify brain validation passes (`python scripts/quandalf/validate_brain.py`)
2. Execute 3 pending Claude specs (ALMA, Ichimoku, T3) — first tests of untested indicator families
3. Add KAMA Stoch v1 as third forward-test lane
4. Define forward-test graduation criteria (A-13)
5. Decide pipeline fate: maintain, rebuild, or accept Claude-only research flow

---

*This is a PROPOSED revision. The canonical doctrine file (`docs/DOCTRINE/analyser-doctrine.md`) should only be updated by `update_analyser_doctrine.py` after human review.*
*Proposed by Quandalf — 2026-03-04*
