# Analyser Doctrine — Proposed v7

**Synthesized:** 2026-03-06 | **Author:** claude-advisor (DOCTRINE_SYNTHESIZER mode)
**Sources:** analyser-doctrine.md (41 entries), DOCTRINE_PROPOSED v6 (45 entries), ~860+ outcome notes (20260226–20260306), Strategy Advisory U33, 11 unique ACCEPTs
**Prior proposed:** v6 (20260305, 830+ outcomes)

---

## Changelog from v6

### Updated (5 entries — evidence base expanded 830→860+, advisory U31–U33, 10→11 ACCEPTs)
| Entry | Change |
|---|---|
| A-05 | Updated: 11 unique ACCEPTs (was 10). Claude spec ACCEPT rate ~25% unchanged. Pipeline still at 0 ACCEPTs from 700+ backtests (was 640+). 170+ consecutive pipeline zero-trade backtests (was 102+). |
| A-12 | Strengthened: Directive loop confirmed STILL ACTIVE post-kill-order. 30 more REJECT outcomes on 2026-03-06 — all 0-trade, all identical 5-directive remediation. Pipeline kill order issued U31 but residual specs execute. conf 0.95→0.97. |
| A-14 | Updated: 170+ consecutive zero-trade backtests (was 102+). Evidence now spans 4+ days across 33 advisory cycles. |
| S-05 | Updated: R:R evidence expanded — 11 ACCEPTs (was 10). 6→7 ACCEPTs use 8:1 R:R. Supertrend CCI 8:1 variant shows PF improvement (1.358 vs 1.290) but DD blowout (25.36% vs 11.63%) — R:R alone cannot fix DD. |
| AT-01 | Updated: 0 BTC ACCEPTs across 860+ outcomes (was 800+). |

### Added (3 new entries from U33 evidence)
| Entry | Evidence |
|---|---|
| S-13 | EMA200 filtering amplifies transitional alpha but is structurally high-DD (25–40%). Three generations failed. Blacklist EMA200 as primary entry filter. |
| S-14 | R:R escalation does not reduce drawdown. Supertrend CCI 8:1 vs default: PF up (1.358 vs 1.290), DD up (25.36% vs 11.63%). Higher R:R shifts alpha toward transitional but degrades ranging. Do not use R:R tuning as DD fix. |
| A-16 | Template parameter tuning protocol: when a template generates 5-9 trades (near-miss), relax the most restrictive gate by one step before rejecting. Evidence: kama_vortex_div generated 9 trades (1 short of 10-trade minimum). |

### Removed (0 entries)
All v6 entries retain evidence support.

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

- [20260303-S05|conf:0.93] **Minimum reward:risk ratio of 5:1 for all new strategy specs.** Across 860+ outcomes: all 11 unique ACCEPTs use R:R >= 5:1. 8:1 is the validated sweet spot (7/11 ACCEPTs). Every strategy with R:R < 4:1 produces PF < 1.05 after fees (4.5 bps taker + 1 bps slippage = 5.5 bps round-trip). Do not generate, backtest, or promote specs with TP/SL < 5.0. Note: Supertrend CCI 8:1 variant shows PF improvement (1.358 vs 1.290) but DD blowout (25.36% vs 11.63%) — R:R escalation is for PF, not DD.

- [20260303-S06|conf:0.90] **Maximum drawdown of 20% for ACCEPT consideration; <=15% preferred.** 9/11 unique ACCEPTs have DD <= 16.4% (champion Supertrend 8:1 = 10.9%). DD > 30% = automatic REJECT without further analysis. The 15–20% band is REVISE territory. Stop multiplier floor of 1.5 ATR to prevent micro-stop noise. Note: EMA200 Vortex v2 (PF=1.969, DD=30%) is CONDITIONAL — DD exceeds cap despite record trans PF=4.321. Family now CLOSED (see S-13).

- [20260302-S07|conf:0.85] **Multi-regime profitability required for ACCEPT.** A strategy must show PF > 1.0 in at least 2 of 3 regimes (trending, ranging, transitional). Single-regime strategies are REVISE at best. Evidence: 9/11 unique ACCEPTs are all-regime profitable (PF > 1.0 in all 3 regimes).

- [20260303-S08|conf:0.85] **Ranging is the dominant profit regime.** All 11 unique ACCEPTs profit in ranging (PF 1.12–4.87). Top ranging PFs: KAMA Stoch v1 (4.87), Supertrend 8:1 (2.914), Supertrend ultra (2.558), MACD 7:1 (2.062). Design strategies to capture momentum mean-reversion within established ranges.

- [20260304-S09|conf:0.90] **Gate non-resilient strategies during trending regime.** Most ACCEPTs lose money in trending. Only adaptive indicators (Vortex, KAMA, Supertrend) survive trending. Evidence: T3 Vortex Hybrid v2 REJECTED — 48% of 277 trades in trending at PF=0.570 dragged overall PF to 0.980, while ranging PF=1.756 and transitional PF=1.357 were profitable. Add ADX < 25 or CHOP > 50 as a trending-regime gate for non-adaptive templates.

- [20260304-S10|conf:0.85] **Adaptive indicators produce all-regime edge; static indicators do not.** Adaptive indicators (KAMA, Vortex, Supertrend) adjust behavior to market conditions. All 9 all-regime ACCEPTs use at least one adaptive indicator. Static indicators (EMA, SMA, fixed-period RSI) fail in trending without regime gating. Prefer adaptive indicator families as primary signal source; static indicators acceptable as secondary filters only.

- [20260305-S11|conf:0.90] **Maximum 2 entry conditions per strategy spec.** All 11 unique ACCEPTs use <= 2 entry conditions. Triple conjunctions (3+ simultaneous AND conditions) produce zero trades — the intersection is too narrow to trigger on real market data. Evidence: 170+ consecutive zero-trade backtests used 3–4 entry conditions (EMA+RSI+ATR+confidence_threshold). Reduce complexity, not threshold parameters, to restore signal generation.

- [20260305-S12|conf:0.88] **Transition-detection is a general edge mechanism, not indicator-specific.** Both Vortex (directional momentum crossover) and Ichimoku TK (median price crossover) detect regime transitions using entirely different mathematical foundations — yet both produce all-regime profitable strategies. Any indicator that detects direction-change moments is a candidate for new ACCEPT-tier strategies. Priority candidates: TRIX zero-cross, TREX histogram zero-cross, TASC DM (Hilbert transform phase detection), SMC CHoCH/BOS. This extends transition-detection from a single-indicator finding to a thesis-level insight.

- [20260306-S13|conf:0.88] **EMA200 as entry filter is structurally high-DD — blacklist as primary entry gate.** Three generations of EMA200 Vortex tested (v2: DD=30%, v3 tight: DD=40%, v3b 8:1: DD=25%, v3b 10:1: DD=32%). EMA200 entries cluster at high-volatility transition points where stops get hit regardless of width (0.75–1.5 ATR all fail). The mechanism amplifies transitional alpha (trans PF=2.297–4.321) but the DD cost is structural and unfixable by stop tuning. Close the EMA200 Vortex family. EMA200 acceptable only as a secondary regime filter (e.g., "above EMA200 for long bias"), never as a primary entry gate.

- [20260306-S14|conf:0.82] **R:R escalation does not reduce drawdown; it shifts regime alpha.** Supertrend CCI 8:1 vs default 4h: PF rose (1.358 vs 1.290) but DD blew out (25.36% vs 11.63%). Regime breakdown: 8:1 shifted alpha from ranging (1.989→1.548) toward transitional (2.777→3.291), with fewer but larger wins. Do not use R:R escalation as a drawdown fix. Higher R:R improves PF per-trade but concentrates returns in fewer trades, increasing path-dependent DD. When DD exceeds target, address stop logic or signal selectivity — not reward target.

- [20260226-10|conf:0.70] Reject strategy framing that implies guaranteed outcomes or non-falsifiable claims. Every strategy must have a kill condition: a specific metric threshold (e.g., PF < 1.0 over 50+ trades) that triggers deprecation.

- [20260228-02|conf:0.78] When PF ~ 1.00 on large samples (>300 trades), prioritize drawdown compression and trade-quality filtering before signal complexity changes. Apply: time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. Evidence: PF=1.033 on 389 trades — the signal exists but fees/noise erode it; tighten the filter, don't add more signals.

- [20260228-03|conf:0.80] If a directive type has been applied >= 3 consecutive times to a strategy family with avg delta PF <= 0.0, auto-blacklist that directive for that family. Evidence: ENTRY_TIGHTEN (4+ attempts, PF degraded 0.920→0.872), GATE_ADJUST (4 attempts, 0 improvement), DIRECTIVE_EXPLORATION (PF 0.51–0.88, worst in 860+ outcomes, DD up to 1501%).

---

## 3) Automation & System Heuristics

- [20260226-11|conf:0.78] Maintain human approval checkpoints for: (a) promoting strategies from backtest to forward-test, (b) transitioning from paper to live trading, (c) any change to risk parameters or position sizing, (d) doctrine changes to the canonical file. Automation handles repetition; humans handle judgment.

- [20260302-A02|conf:0.76] Invest in telemetry before features. Before adding new automation, ensure visibility into: risk exposure, execution latency, slippage, execution drift, and strategy PF decay. Execution quality tracking (actual vs. expected fills) should be a continuous monitoring signal, not a post-mortem exercise.

- [20260302-A03|conf:0.75] Prioritize infrastructure that compounds across every future cycle: parameter-level deduplication, machine directive enforcement parsing, agent quality gates requiring evidence links, and session gating checklists. Each of these reduces systemic waste.

- [20260226-14|conf:0.73] Use prompt/version control and rollback pathways for all agentic research components. Every LLM-generated artifact must be traceable to its prompt version and input data.

- [20260226-15|conf:0.72] Build error taxonomies from pipeline failures. Categorize failures (zero trades, high DD, parameter convergence, directive non-consumption) and link to root causes. Directive failure histories must feed back into directive selection. Evidence: pipeline continues issuing ENTRY_TIGHTEN and GATE_ADJUST despite 0% success rate across 30+ cycles.

- [20260305-A05|conf:0.95] **Prioritize Claude-generated specs over pipeline-generated specs in batch queue.** Claude specs: 11/11 unique ACCEPTs (~25% ACCEPT rate per spec). Pipeline specs: 0 ACCEPTs from 700+ pipeline backtests (drought = 60+ cycles). 170+ consecutive pipeline zero-trade backtests spanning 4+ days. Claude specs blocked multiple cycles while pipeline consumed all capacity. Run Claude specs FIRST each cycle; fill remaining capacity with pipeline specs only after they pass machine directive filters AND parameter-level dedup.

- [20260303-A06|conf:0.85] **Prune dead templates after 3 consecutive cycles of zero trades.** Remove from TEMPLATE_REGISTRY: stochastic_reversal (0 trades, 18+ cycles, confirmed bug line 174), bollinger_breakout (0 trades, 14+ cycles, volume gate broken), choppiness_donchian_fade (0 trades, 8+ cycles, CHOP>61.8 AND close<=DCL AND RSI<35 triple conjunction near-impossible). If fixed, re-add after producing >= 1 trade in isolated test.

- [20260305-A07|conf:0.95] **Deduplicate at the resolved parameter level, not the spec level.** 95%+ of compute is wasted on duplicates. Evidence: 170+ zero-trade directive variants share identical EMA+RSI+ATR+confidence_threshold architecture — different family IDs, same resolved parameters. Hash the tuple `(template_name, indicator_params, stop_mult, tp_mult, timeframe, asset)` and skip duplicates before backtesting. Single biggest efficiency gain available.

- [20260303-A08|conf:0.82] **Pre-validate signal count before full backtest.** Run a fast signal scan (evaluate entry conditions only, skip position simulation) before committing to a full backtest run. If `signal_count < 10` across the data window, skip the backtest and log "insufficient signals." Evidence: 170+ zero-trade outcomes. Would have prevented 165+ wasted runs.

- [20260303-A09|conf:0.78] **Validate Claude spec template routing before backtest.** Claude specs with custom `template_name` values must be confirmed to route correctly through `spec_rules` with `entry_long`/`entry_short` conditions intact. Add a pre-flight check: does template resolve? Do entry conditions reference valid dataframe columns?

- [20260303-A10|conf:0.85] **Deduplicate at backtest scheduling level.** Before scheduling a backtest, check if an identical `(spec_hash, asset, timeframe)` combination has already been run. This is distinct from A-07 (parameter dedup catches differently-named specs that resolve identically); this catches the same spec run twice.

- [20260304-A11|conf:0.95] **YAML serialization must use multi-line array syntax.** Brain objects and all YAML frontmatter MUST use `- item` per line for arrays. Never use inline `[a, b, c]` syntax. The BALROG validator's `json.loads()` parser cannot parse unquoted inline arrays. Evidence: this single bug blocked ALL backtests for 36+ attempts across 6+ autopilot cycles (U18–U20).

- [20260305-A12|conf:0.97] **Directive system is non-functional and circular — do not rely on automated refinement.** 49+ machine directives issued across advisory cycles, 0 enforced by the pipeline. Directive loop confirmed CIRCULAR and PERSISTENT: same 5 remediation actions (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE) recycled on every zero-trade failure. ENTRY_RELAX and ENTRY_TIGHTEN issued simultaneously = self-contradictory. Loop survived kill order (U31) — 30 more REJECT outcomes on 2026-03-06 post-kill. 170+ consecutive zero-trade backtests spanning 4+ days and 33 advisory cycles = conclusive systemic failure. Do not allocate compute to directive-based refinement until the enforcement mechanism is rebuilt from scratch.

- [20260304-A13|conf:0.78] **Define forward-test graduation criteria.** Two strategies are live in forward-test (Vortex v3a, Supertrend 8:1) with KAMA Stoch v1, Ichimoku TK v1, and Supertrend CCI v4 as candidates for lanes 3–5. No criteria exist for graduation. Proposed minimum: 30 days live, PF > 1.2, DD < 15%, human approval gate. PF < 0.8 or DD > 25% = demote. **15th cycle requesting.**

- [20260305-A14|conf:0.92] **Zero-trade circuit breaker: halt spec family after 5 consecutive zero-trade backtests.** When any single spec family produces 5+ consecutive zero-trade backtest results, halt ALL further backtests from that family. Escalate to Claude spec review for root cause diagnosis. Evidence: 170+ consecutive zero-trade backtests all from the same pipeline spec families. A circuit breaker at 5 would have saved 165+ wasted runs (4+ days of compute).

- [20260305-A15|conf:0.90] **Pipeline full halt when zero-trade rate exceeds 50% of a batch window.** When more than half the backtests in any 10-run window produce zero trades, the pipeline must halt entirely — not circuit-break a single family. Reallocate ALL backtest capacity to Claude-specified specs until the pipeline produces at least 1 trade per run on a validation set. This is a system-level safety valve, not a per-family control.

- [20260306-A16|conf:0.75] **Template parameter tuning protocol for near-miss specs.** When a template generates 5–9 trades (above signal-exists threshold, below 10-trade minimum gate), do not reject as dead. Instead: (a) identify the most restrictive gate parameter, (b) relax it by one step (e.g., ATR gate ×0.8, flattening threshold ×1.2, proximity window ×1.5), (c) re-run ONE variant. If still <10 trades after 2 relaxation steps, classify as "too selective for current data window." Evidence: kama_vortex_div generated 9 trades — combines two proven ACCEPT families (KAMA PF=1.857 + Vortex PF=2.034) — but signals are too rare at default parameters. This is a near-miss, not a failure.

- [20260228-06|conf:0.74] Ensure all gate comparisons use consistent units. Thresholds expressed as percentages must be compared to percentage values; absolute values to absolute thresholds. Evidence: drawdown gate compared $981 (absolute) to 0.30 (percentage), causing false rejections.

---

## 4) Asset & Timeframe Heuristics

- [20260305-AT01|conf:0.85] **ETH-first routing for all new experiments.** 0 BTC ACCEPTs across 860+ outcomes over 33 cycles. BTC PF range: 0.594–1.001 (all-time). Even champion Vortex v3a produces PF=0.743 on BTC. Route all new experiments through ETH first. Only expand to BTC after achieving PF > 1.10 on ETH with 50+ trades.

- [20260228-08|conf:0.78] No single template may consume more than 60% of backtest compute in any 5-cycle window. If a template has been tested 10+ times without PF > 1.05, force-rotate to untested templates.

- [20260228-09|conf:0.72] When combining variant types, test only the two highest-performing individual types together. Do not combine more than 2 mutation axes simultaneously.

- [20260303-AT04|conf:0.76] **Untested templates are priority backtest candidates.** kama_vortex_divergence exists in `signal_templates.py` and produced 9 trades — confirmed functional but parameter-restricted (see A-16). ALMA, T3, and MACDh indicator families have low coverage. Novel hypotheses with unused indicators should be tested before further refinement of exhausted templates.

- [20260304-AT05|conf:0.90] **4h is the only validated timeframe.** 0 ACCEPTs on 15m or 1h across 11 unique ACCEPTs and 50+ backtests. 1h degrades PF by 0.94 avg compared to 4h on the same strategy (Supertrend CCI: trend PF 1.638→0.562 on 1h→4h shift). Route all new experiments to 4h primary. Only test 1h after a strategy achieves ACCEPT on 4h.

- [20260305-AT06|conf:0.85] **Transition-detection indicators are the highest-alpha research frontier.** Indicators that detect direction-change moments produce the highest-PF strategies: Vortex (trans PF=3.886), Ichimoku TK (trans PF=2.44), EMA200 Vortex (trans PF=4.321 RECORD — family CLOSED due to DD, see S-13). Validated across 3 independent frameworks (Vortex = directional momentum, Ichimoku = median price, SMC CHoCH/BOS = structural). Priority expansion: TRIX zero-cross, TREX histogram zero-cross, TASC DM (Hilbert transform). Once indicators are added, design 2-condition specs (brain rules: ETH 4h, 8:1 R:R).

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

### Key changes from v6 → v7

1. **Evidence base expanded 4%**: 860+ outcomes (was 830+). Key new signals: 170+ consecutive zero-trade (was 102+), EMA200 family closure (3 generations all DD>20%), kama_vortex_div near-miss (9/10 trades), R:R escalation proven not to fix DD (Supertrend CCI 8:1), 11 unique ACCEPTs (was 10).

2. **3 new entries**: S-13 (EMA200 blacklist), S-14 (R:R ≠ DD fix), A-16 (template parameter tuning protocol).

3. **5 entries updated**: A-05 (11 ACCEPTs, 700+ pipeline backtests), A-12 (directive loop survives kill order, conf 0.97), A-14 (170+ zero-trade), S-05 (R:R evidence — 8:1 PF up but DD up), AT-01 (860+ outcomes).

4. **S-13 codifies the EMA200 family closure**: Three generations (v2, v3, v3b) tested across 4 stop widths (0.75–1.5 ATR) and 3 R:R ratios (8:1, 10:1, 12:1). All fail DD constraint (25–40%). The mechanism (EMA200 entries cluster at high-volatility transition points) is now understood and blacklisted. Transitional alpha is real (PF=2.297–4.321) but the DD cost is structural.

5. **S-14 captures a counter-intuitive finding**: Higher R:R improves per-trade PF but concentrates returns in fewer trades, increasing path-dependent DD. This prevents future wasted cycles chasing DD fixes through R:R tuning.

6. **A-16 creates a path for near-miss templates**: kama_vortex_div at 9 trades is the closest a template has come to ACCEPT without crossing the 10-trade gate. The tuning protocol (relax most restrictive gate by one step, max 2 relaxation attempts) prevents premature template abandonment while bounding effort.

### Entry count summary
| Section | v6 Entries | v7 Entries | Change |
|---|---|---|---|
| Research Heuristics | 5 | 5 | 0 |
| Strategy Hypothesis | 15 | 17 | +2 (S-13 EMA200 blacklist, S-14 R:R ≠ DD) |
| Automation & System | 19 | 20 | +1 (A-16 template tuning protocol) |
| Asset & Timeframe | 6 | 6 | 0 |
| **Total** | **45** | **48** | **+3 net** |

### Confidence distribution
| Range | Count | Examples |
|---|---|---|
| 0.90+ | 10 | S-05, S-06, S-09, S-11, A-05, A-07, A-11, A-12 (0.97), A-14, AT-05 |
| 0.80–0.89 | 12 | S-07, S-08, S-10, S-12, S-13, S-14, A-06, A-08, A-10, AT-01, AT-06, T-01 |
| 0.70–0.79 | 14 | R-01 through R-04, S-03, S-04, A-02, A-03, A-09, A-13, A-16, AT-04, etc. |
| <0.70 | 0 | — |

All entries meet the minimum confidence threshold of 0.70. A-12 (directive loop) elevated to 0.97 — highest single-entry confidence — based on 170+ zero-trade outcomes surviving an explicit kill order.

### Priority actions for next cycle
1. **Verify pipeline kill** — 30 more REJECT outcomes post-kill-order. Residual specs still executing.
2. **Tune kama_vortex_div** — 9 trades is 1 short. Relax KAMA flattening or ATR gate. Highest-potential new mechanism family.
3. **Execute 3 new Claude specs** — T3 Vortex, MACDh CHOP, ALMA CCI (7 variants). Novel transition-detection candidates.
4. **Add TRIX_14 to dataframe** — 11th cycle requesting. Last untapped transition-detection indicator.
5. **Define forward-test graduation** (A-13) — 15th cycle requesting. 3 candidates waiting.
6. **Enroll KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4 in forward-test** — decorrelated ACCEPTs ready.

---

*This is a PROPOSED revision. The canonical doctrine file (`docs/DOCTRINE/analyser-doctrine.md`) should only be updated by `update_analyser_doctrine.py` after human review.*
*Proposed by Quandalf — 2026-03-06*
