---
id: u25-directive-loop-identified
ts: "2026-03-04T23:45:00Z"
pointers:
  - fact-directive-loop-circular
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - failure-pipeline-structural-death
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-5063f4f1f99b.strategy_spec.json
---

U25: 0 new ACCEPTs. Directive remediation loop identified as circular — every 0-trade outcome generates same 5 directives (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE), variants fail identically, loop repeats. Zero-trade epidemic escalates to 66+. All 15+ backtests since U24 are pipeline specs with identical EMA+RSI+ATR+confidence_threshold architecture. No Claude specs executed. Recombine generating BTC 1h specs despite EXCLUDE_ASSET directive. Brain 25→26 objects (+1 fact). 10 unique ACCEPTs unchanged. All U24 priorities (Supertrend CCI v4, EMA200 Vortex v3, transition expansion) remain blocked by pipeline consuming backtest capacity.
