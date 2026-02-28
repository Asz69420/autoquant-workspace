# Analyser Doctrine — Proposed v2
**Synthesized:** 2026-02-28 | **Author:** claude-advisor (DOCTRINE_SYNTHESIZER mode)
**Sources:** analyser-doctrine.md (v1, 43 entries), 30 outcome notes (20260226–27), 15 backtest results, STRATEGY_ADVISORY.md (20260228)

---

## Changelog from v1
- **Removed 8 entries:** 6 opaque YouTube video IDs with no extractable content (20260226-26, -31, -32, -34, -36, -37), plus 2 derivatives referencing those IDs (20260226-28, -30)
- **Consolidated 12 entries → 5:** Merged overlapping risk-gating, session-gating, and system-improvement rules
- **Rewrote 7 entries:** Clarified vague "promote recurring concept signal" entries into actionable rules
- **Added 7 entries:** New principles derived from 60+ pipeline cycles with zero ACCEPT outcomes

---

## 1) Research Heuristics

- [20260226-01|conf:0.74] Prioritize process-level concepts that can be tested independently of market direction claims. Reject ideas that require directional conviction to validate.

- [20260226-02|conf:0.72] Treat transcript-derived ideas as hypotheses until supported by repeatable backtest evidence. Require at least 2 independent positive results before promoting to doctrine.

- [20260226-03|conf:0.71] Promote ideas that improve observability, auditability, and operator decision quality. Telemetry and attribution come before new signal complexity.

- [20260226-04|conf:0.70] Prefer concepts that map cleanly into schema-valid ResearchCards and deterministic pipelines. If an idea cannot be expressed as a testable spec, it is not ready.

- [20260226-05|conf:0.69] Down-rank vague advice lacking constraints, failure modes, or measurable outcomes. Every rule must specify what it looks like when violated.

- [20260228-01|conf:0.72] Require evidence pointers (backtest hash, outcome file, or metric citation) for every proposed doctrine change. Unsourced rules decay to noise. *(Consolidated from 20260226-25, -30)*

---

## 2) Strategy Hypothesis Heuristics

- [20260226-06|conf:0.76] Every hypothesis must include explicit regime assumptions and invalidation conditions. A strategy without a stated regime context is untestable. **Evidence:** 0/30 strategy specs carry regime assumptions despite this rule existing; the 3 REVISE verdicts were the only outcomes using regime data (from post-hoc classification, not design).

- [20260226-07|conf:0.74] Separate signal logic from execution logic to reduce confounded performance attribution. Variants that resolve to identical execution paths despite different names must be caught before compute is spent. **Evidence:** `library_augmented` and `entry_tighten` produced byte-identical results across BTC/4h and ETH/1h.

- [20260226-08|conf:0.76] Require risk gating (drawdown limits, position sizing, loss circuit-breakers) before adding entry/exit complexity. Do not scale variant count until at least one variant achieves positive expectancy. **Evidence:** Pipeline generates 4–5 simultaneous variants per cycle with zero achieving PF > 1.0; 5 dimensions of change make attribution impossible. *(Consolidated from 20260226-08, -16, -21)*

- [20260226-09|conf:0.71] Favor mutation candidates that preserve non-repainting behavior and bar-close determinism. Reject any variant that uses intra-bar data or forward-looking indicators.

- [20260226-10|conf:0.70] Reject strategy framing that implies guaranteed outcomes or non-falsifiable claims. Every strategy must state conditions under which it would be abandoned.

- [20260228-02|conf:0.78] When PF is approximately 1.00 on large samples (>300 trades), prioritize drawdown compression and trade-quality filtering before any further signal complexity changes. Apply: time-of-day filters, consecutive-loss circuit breaker, minimum ATR threshold. **Evidence:** PF=1.033 on 389 trades (family 6167b17afa4f exit_change) — the only profitable outcome in 60+ cycles — is exactly this trigger condition. *(Upgraded from 20260227-0343)*

- [20260228-03|conf:0.80] If a directive type has been applied >= 3 consecutive times to a strategy family with avg delta PF <= 0.0, auto-blacklist that directive type for that family. Stop iterating on provably failed mutations. **Evidence:** ENTRY_TIGHTEN tried 4+ times with 0 improvement, actively degrades PF from 0.920 to 0.872. GATE_ADJUST tried 4 times, 0 improvement (identical to baseline — bug suspected). DIRECTIVE_EXPLORATION produced PF 0.510–0.682, worst in 15 backtests.

- [20260228-04|conf:0.75] Require regime-gated variants for any strategy showing regime-specific edge. If a variant achieves PF > 1.0 in one regime but < 0.95 overall, create a regime-filtered variant that only trades in the profitable regime before trying other modifications. **Evidence:** `remove_component` variant showed trending PF=1.14 but overall PF=0.949 due to ranging/transitional drag. `exit_change` showed balanced profile: trending=1.054, transitional=1.048, ranging=0.982.

---

## 3) Automation & System Heuristics

- [20260226-11|conf:0.78] Keep human approval checkpoints for high-impact automation: deployment transitions, live-capital enablement, and doctrine changes to the canonical file. Automated agents propose; humans approve.

- [20260226-12|conf:0.78] Enforce deterministic session gating before any live-capable execution pathway is enabled. No strategy reaches live without passing session-start checks (data freshness, exchange connectivity, risk limits loaded). *(Consolidated from 20260226-12, -20, -24)*

- [20260226-13|conf:0.75] Invest first in telemetry for risk, latency, and execution drift before adding new automation features. Execution quality tracking (slippage, latency, fill rates) should be a continuous signal, not a post-mortem exercise. *(Consolidated from 20260226-13, -22)*

- [20260226-14|conf:0.73] Use prompt/version control and rollback pathways for agentic research components. Every LLM-generated artifact must be traceable to its prompt version and input data.

- [20260226-15|conf:0.72] Build error taxonomies and incident summaries so failures become reusable operational knowledge. Directive failure histories should feed back into directive selection, not be ignored. **Evidence:** Pipeline continues issuing ENTRY_TIGHTEN and GATE_ADJUST despite zero success rate across 4+ attempts.

- [20260228-05|conf:0.76] Require variant fingerprinting (hash of resolved signal parameters + execution config) before submitting to the backtester. Do not spend compute on variants that resolve to identical execution paths. **Evidence:** `library_augmented` collapses to identical results as `entry_tighten` — wasted 2x compute per cycle. *(Derived from 20260226-07, -23)*

- [20260228-06|conf:0.74] Ensure all gate comparisons use consistent units. Thresholds expressed as percentages must be compared to percentage values; absolute dollar values must be compared to absolute thresholds. **Evidence:** Drawdown gate compares $981 (absolute) to 0.30 (percentage), causing every strategy to fail for the wrong reason.

---

## 4) Asset & Template Heuristics (NEW SECTION)

- [20260228-07|conf:0.77] Route all new template and signal experiments through ETH (1h and 4h) first. Only promote to BTC after achieving PF > 1.10 on ETH. BTC amplifies losses 10–20x without proportional upside due to higher notional size. **Evidence:** ETH DD range $981–$3,662 vs BTC DD range $33,793–$40,184 with comparable trade counts.

- [20260228-08|conf:0.78] Mandate template diversification: no single signal template may consume more than 60% of backtest compute in any rolling 5-cycle window. If a template has been tested 10+ times without reaching PF > 1.05, force-rotate to untested templates. **Evidence:** 30/30 outcomes use `ema_rsi_atr` exclusively. 5 of 7 available templates (`supertrend_follow`, `macd_confirmation`, `bollinger_breakout`, `stochastic_reversal`, `ema_crossover`) remain completely untested after 60+ pipeline cycles.

- [20260228-09|conf:0.72] When combining variant types, test only the two highest-performing individual types together. Do not combine more than 2 mutation axes simultaneously. **Evidence:** `threshold_mutation` (PF=0.945) and `exit_change` (PF=1.033) are the only two variant types that moved PF meaningfully — these are the combination candidates, not arbitrary pairings.

---

## Removed Entries (Audit Trail)

The following entries from v1 were removed or absorbed. They are listed here for traceability, not for re-inclusion.

| Removed ID | Reason |
|---|---|
| 20260226-26 | Opaque YouTube ID `qbyQ8322m-M` — no extractable actionable content |
| 20260226-28 | Derivative of -26 — "convert concept to testable hypothesis" with no concept specified |
| 20260226-30 | Derivative of -26 — "record ingestion evidence pointer" with no ingestion target |
| 20260226-31 | Opaque YouTube ID `CEJ_R5226xE` — no extractable actionable content |
| 20260226-32 | Opaque YouTube ID `qMHd7NMu_Gc` — no extractable actionable content |
| 20260226-34 | Opaque YouTube ID `D4_rO7qK2rY` — no extractable actionable content |
| 20260226-36 | Opaque YouTube ID `NPxmHIGq-yY` — no extractable actionable content |
| 20260226-37 | Opaque YouTube ID `R-4uCkGMBag` — no extractable actionable content |

The following entries were consolidated into other rules (parent rule noted):

| Absorbed ID | Absorbed Into | Reason |
|---|---|---|
| 20260226-16 | 20260226-08 | "risk controls/gating" concept signal → merged into risk gating rule |
| 20260226-17 | *(deferred)* | "community/distribution" — not actionable for strategy pipeline; revisit if distribution tooling is built |
| 20260226-18 | 20260226-13 | "workflow automation" concept signal → merged into telemetry-first rule |
| 20260226-19 | 20260228-01 | "data ingestion quality" concept signal → merged into evidence pointer requirement |
| 20260226-20 | 20260226-12 | "session gating" hypothesis hook → merged into session gating rule |
| 20260226-21 | 20260226-08 | "risk limit enforcement" hypothesis hook → merged into risk gating rule |
| 20260226-22 | 20260226-13 | "execution quality tracking" hypothesis hook → merged into telemetry rule |
| 20260226-23 | 20260228-05 | "auto-transcript ingestion pipeline" → absorbed into variant fingerprinting rule |
| 20260226-24 | 20260226-12 | "session gating checklist" → merged into session gating rule |
| 20260226-25 | 20260228-01 | "agent quality gate with evidence links" → merged into evidence pointer requirement |
| 20260227-0343 | 20260228-02 | Upgraded with specific evidence and action items |

---

*This is a PROPOSED revision. The canonical doctrine file (`docs/DOCTRINE/analyser-doctrine.md`) should only be updated by the pipeline `update_analyser_doctrine.py` script after human review.*
