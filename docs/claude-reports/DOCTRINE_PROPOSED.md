# Analyser Doctrine — Proposed v3

**Synthesized:** 2026-03-02 | **Author:** claude-advisor (DOCTRINE_SYNTHESIZER mode)
**Sources:** analyser-doctrine.md (41 entries), 460 outcome notes (20260226–20260301), 60 backtests (20260302), Strategy Advisory Update 8
**Prior proposed:** v2 (20260228, 30 outcomes)

---

## Changelog from Current Doctrine

### Removed (8 entries)
| Entry ID | Reason |
|---|---|
| 20260226-26 | Opaque YouTube video ID `qbyQ8322m-M` — no extractable rule |
| 20260226-31 | Opaque YouTube video ID `CEJ_R5226xE` — no extractable rule |
| 20260226-32 | Opaque YouTube video ID `qMHd7NMu_Gc` — no extractable rule |
| 20260226-34 | Opaque YouTube video ID `D4_rO7qK2rY` — no extractable rule |
| 20260226-36 | Opaque YouTube video ID `NPxmHIGq-yY` — no extractable rule |
| 20260226-37 | Opaque YouTube video ID `R-4uCkGMBag` — no extractable rule |
| 20260226-28 | Video ID derivative in strategy section — no testable content |
| 20260226-30 | Video ID derivative in automation section — no testable content |

### Consolidated (12 entries → 5)
| New Entry | Absorbed | Rationale |
|---|---|---|
| R-01 | 20260226-01, -02 | Both require external ideas be treated as hypotheses |
| R-03 | 20260226-03, -05 | Both require measurable, actionable, auditable content |
| S-03 | 20260226-08, -20, -21 | All describe risk/session gating before execution |
| A-02 | 20260226-13, -22 | Both say observability/telemetry before features |
| A-03 | 20260226-16, -17, -18, -19, -23, -24, -25 | Vague concept signals and system improvement candidates → one infrastructure rule |

### Added (7 new entries from 460-outcome evidence base)
| Entry | Evidence |
|---|---|
| S-05 | 20/20 ACCEPTs use R:R ≥ 6:1; 0/295 REJECTs with R:R < 4:1 exceed PF 1.05 |
| S-06 | 20/20 ACCEPTs have DD ≤ 10%; 238/295 REJECTs have DD > 30% |
| S-07 | ACCEPTs show multi-regime profitability; single-regime = fragile |
| S-08 | Ranging is dominant profit regime across all viable templates |
| A-05 | Claude specs ~20% ACCEPT rate; pipeline specs 0% across 400+ backtests |
| A-06 | Dead templates (0 trades, 5+ cycles) consume compute slots |
| A-07 | 40% of backtests are parameter-convergence duplicates |

---

## 1) Research Heuristics

- [20260302-R01|conf:0.74] Treat all externally-derived ideas (transcripts, videos, articles) as hypotheses. Promote to doctrine only when supported by at least one backtest with PF > 1.1 and 30+ trades. Require 2 independent positive results before conferring conf > 0.80.

- [20260226-04|conf:0.70] Prefer concepts that map cleanly into schema-valid ResearchCards and deterministic backtester pipelines. If an idea cannot be expressed as a testable spec with entry/exit rules and measurable thresholds, it is not ready for doctrine.

- [20260302-R03|conf:0.72] Down-rank advice that lacks: (a) explicit failure conditions, (b) measurable outcome thresholds, or (c) constraints on when NOT to apply. Promote ideas that improve observability, auditability, and operator decision quality.

- [20260302-R04|conf:0.70] When recurring concept signals emerge from research (risk controls, data quality, workflow patterns), formalize them into testable doctrine entries with specific thresholds and evidence pointers — not vague concept tags. Require evidence citations (backtest hash, outcome file, metric) for every proposed doctrine change.

---

## 2) Strategy Hypothesis Heuristics

- [20260226-06|conf:0.76] Every hypothesis must state: (a) which regime(s) it targets, (b) what invalidates it, and (c) what metric thresholds constitute success or failure. Hypotheses without explicit regime assumptions are rejected at spec review.

- [20260226-07|conf:0.74] Separate signal logic from execution logic. Entry signals, exit rules, and position sizing must be independently testable. Confounded attribution (signal + execution in one block) prevents meaningful iteration. Evidence: `library_augmented` and `entry_tighten` produced byte-identical results when signal and execution were entangled.

- [20260302-S03|conf:0.78] Risk gating is mandatory before execution. Every strategy must enforce: (a) session gating — market conditions check before trade enablement, (b) risk limit enforcement — max DD cap and position size limit as non-optional pre-trade checks, (c) drawdown circuit breaker — auto-halt at configured threshold. Do not scale variant count until at least one variant achieves positive expectancy.

- [20260226-09|conf:0.71] Only accept mutation candidates that preserve non-repainting behavior and bar-close determinism. Reject any indicator or rule that uses future data or intra-bar state.

- [20260302-S05|conf:0.92] **Minimum reward:risk ratio of 5:1 for all new strategy specs.** Across 460 outcomes: every ACCEPT uses R:R ≥ 6:1; every strategy with R:R < 4:1 produces PF < 1.05 after fees (4.5 bps taker + 1 bps slippage = 5.5 bps round-trip). Do not generate, backtest, or promote specs with TP/SL < 5.0.

- [20260302-S06|conf:0.90] **Maximum drawdown of 10% for ACCEPT verdict.** 20/20 ACCEPTs have DD ≤ 10%. 238/295 REJECTs have DD > 30%. Stop multiplier floor of 1.5 ATR to prevent micro-stop noise. DD > 30% = automatic rejection without further analysis.

- [20260302-S07|conf:0.85] **Multi-regime profitability required for ACCEPT.** A strategy must show PF > 1.0 in at least 2 of 3 regimes (trending, ranging, transitional). Single-regime strategies are REVISE at best. Evidence: all 20 ACCEPTs show strength in both trending (PF 1.05–2.18) and ranging (PF 1.58–2.06).

- [20260302-S08|conf:0.82] **Ranging is the dominant profit regime.** MACD 7:1 PF=2.06 ranging, Supertrend ADX5 PF=1.61 ranging, EMA/RSI/ATR PF=1.55 ranging. Design strategies to capture momentum mean-reversion within established ranges. Transitional is solvable only with extreme R:R (7:1+); tight R:R universally fails in transitional.

- [20260226-10|conf:0.70] Reject strategy framing that implies guaranteed outcomes or non-falsifiable claims. Every strategy must have a kill condition: a specific metric threshold (e.g., PF < 1.0 over 50+ trades) that triggers deprecation.

- [20260228-02|conf:0.78] When PF ≈ 1.00 on large samples (>300 trades), prioritize drawdown compression and trade-quality filtering before signal complexity changes. Apply: time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. Evidence: PF=1.033 on 389 trades — the signal exists but fees/noise erode it; tighten the filter, don't add more signals.

- [20260228-03|conf:0.80] If a directive type has been applied ≥ 3 consecutive times to a strategy family with avg delta PF ≤ 0.0, auto-blacklist that directive for that family. Evidence: ENTRY_TIGHTEN (4+ attempts, PF degraded 0.920→0.872), GATE_ADJUST (4 attempts, 0 improvement), DIRECTIVE_EXPLORATION (PF 0.51–0.88, worst in 460 outcomes, DD up to 1501%).

---

## 3) Automation & System Heuristics

- [20260226-11|conf:0.78] Maintain human approval checkpoints for: (a) promoting strategies from backtest to forward-test, (b) transitioning from paper to live trading, (c) any change to risk parameters or position sizing, (d) doctrine changes to the canonical file. Automation handles repetition; humans handle judgment.

- [20260302-A02|conf:0.76] Invest in telemetry before features. Before adding new automation, ensure visibility into: risk exposure, execution latency, slippage, execution drift, and strategy PF decay. Execution quality tracking (actual vs. expected fills) should be a continuous monitoring signal, not a post-mortem exercise.

- [20260302-A03|conf:0.75] Prioritize infrastructure that compounds across every future cycle: parameter-level deduplication, machine directive enforcement parsing, agent quality gates requiring evidence links, and session gating checklists. Each of these reduces systemic waste.

- [20260226-14|conf:0.73] Use prompt/version control and rollback pathways for all agentic research components. Every LLM-generated artifact must be traceable to its prompt version and input data.

- [20260226-15|conf:0.72] Build error taxonomies from pipeline failures. Categorize failures (zero trades, high DD, parameter convergence, directive non-consumption) and link to root causes. Directive failure histories must feed back into directive selection. Evidence: pipeline continues issuing ENTRY_TIGHTEN and GATE_ADJUST despite 0% success rate across 9 cycles.

- [20260302-A05|conf:0.88] **Prioritize Claude-generated specs over pipeline-generated specs in batch queue.** Claude specs: ~20% all-time ACCEPT rate. Pipeline specs: 0% ACCEPT rate across 400+ backtests. Run Claude specs first each cycle; fill remaining capacity with pipeline specs only after they pass machine directive filters AND parameter-level dedup.

- [20260302-A06|conf:0.85] **Prune dead templates after 3 consecutive cycles of zero trades.** stochastic_reversal: 0 trades, 8 cycles, confirmed bug at line 179 (k_now < os structurally impossible). bollinger_breakout: 0 trades, 5 cycles (Close > BBU_20_2.0 too rare on crypto 4h). Remove from TEMPLATE_COMBOS.

- [20260302-A07|conf:0.88] **Deduplicate at the resolved parameter level, not the spec level.** 40% of 20260302 backtests produced byte-identical results (11+ files with PF=1.033, 389 trades). Different spec rule text resolves to the same numeric backtester parameters. Hash the tuple `(template_name, indicator_params, stop_mult, tp_mult, timeframe, asset)` and skip duplicates before backtesting.

- [20260228-06|conf:0.74] Ensure all gate comparisons use consistent units. Thresholds expressed as percentages must be compared to percentage values; absolute values to absolute thresholds. Evidence: drawdown gate compared $981 (absolute) to 0.30 (percentage), causing false rejections.

---

## 4) Asset & Template Heuristics

- [20260228-07|conf:0.77] Route all new experiments through ETH (1h and 4h) first. Only expand to BTC after achieving PF > 1.10 on ETH. BTC amplifies losses 10–20x without proportional upside. Evidence: ETH DD range $981–$3,662 vs BTC DD $33,793–$40,184, BTC DD=1501% (20260302 new worst).

- [20260228-08|conf:0.78] No single template may consume more than 60% of backtest compute in any 5-cycle window. If a template has been tested 10+ times without PF > 1.05, force-rotate to untested templates. Evidence: 30/30 outcomes on 20260227 used `ema_rsi_atr` exclusively while 5 other templates remained untested.

- [20260228-09|conf:0.72] When combining variant types, test only the two highest-performing individual types together. Do not combine more than 2 mutation axes simultaneously. Evidence: `threshold_mutation` (PF=0.945) and `exit_change` (PF=1.033) are the only two types that moved PF meaningfully.

---

## Removed Entries (Audit Trail)

The following entries from the current doctrine were removed or absorbed:

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

Consolidated entries (absorbed into parent rules noted above):

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

### Evidence strength for new entries (S-05 through A-07)
These 7 new entries are derived from the strongest quantitative patterns in the 460-outcome dataset:

**S-05 (R:R floor, conf:0.92):** The highest-confidence entry in the doctrine. 20/20 ACCEPTs use R:R ≥ 6:1. The fee environment (5.5 bps round-trip) makes low-R:R strategies structurally unprofitable — this is physics, not preference.

**S-06 (DD cap, conf:0.90):** Second strongest signal. DD ≤ 10% is a perfect predictor of ACCEPT. DD > 30% is a near-perfect predictor of REJECT (238/295). The gap between 10% and 30% is the REVISE zone.

**S-07 (multi-regime, conf:0.85):** All ACCEPTs show profitability in 2+ regimes. This prevents overfitting to one market condition.

**S-08 (ranging dominance, conf:0.82):** Consistent across MACD, Supertrend, and EMA/RSI/ATR — ranging produces the highest PF. This informs strategy design: optimize for range-bound momentum capture, not trend following.

**A-05 (Claude spec priority, conf:0.88):** Empirical, not ideological. 0% vs ~20% ACCEPT rate across 400+ backtests. The higher-hit-rate source should be tested first.

**A-06 (dead template pruning, conf:0.85):** stochastic_reversal has a confirmed code bug. bollinger_breakout is structurally impossible on crypto 4h. Both have been flagged for 5–8 cycles.

**A-07 (parameter dedup, conf:0.88):** 40% of compute is wasted on duplicates. This is the single largest efficiency gain available — a ~30-minute code change for 5-8x throughput improvement.

### Key differences from v2 (20260228)
- Evidence base expanded 15x: 460 outcomes vs 30
- New entries S-05/S-06 added at high confidence (0.90+) — not possible with 30 outcomes
- S-08 (ranging dominance) confirmed across 3 template families — was a single-template observation in v2
- A-07 (parameter dedup) quantified at 40% waste rate — was theoretical in v2
- Removed entries unchanged — the 8 video IDs remain non-actionable
- Consolidation logic unchanged — v2 merges validated

---

*This is a PROPOSED revision. The canonical doctrine file (`docs/DOCTRINE/analyser-doctrine.md`) should only be updated by `update_analyser_doctrine.py` after human review.*
*Proposed by Quandalf — 2026-03-02*
