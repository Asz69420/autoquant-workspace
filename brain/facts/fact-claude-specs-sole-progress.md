---
id: fact-claude-specs-sole-progress
type: fact
title: Claude-specified strategies are the only source of ACCEPT-tier results — U33 first execution since U31, 3 new specs written
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - docs/shared/LAST_CYCLE_RESULTS.md
  - artifacts/library/PROMOTED_INDEX.json
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-t3vtx01.strategy_spec.json
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-mchtrn01.strategy_spec.json
  - artifacts/strategy_specs/20260306/strategy-spec-20260306-claude-almcci01.strategy_spec.json
tags:
  - claude-specs
  - pipeline
  - accept-rate
  - spec-portfolio
  - ppr-validated
supporting_ids:
  - failure-pipeline-structural-death
  - fact-zero-trade-signal-bottleneck
  - fact-research-pipeline-homogeneous
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-06T01:00:00Z"
updated_at: "2026-03-06T01:00:00Z"
---

All 11 unique ACCEPT-tier strategies were designed by Claude advisory cycles using the spec_rules template. The ACCEPT rate for Claude specs is ~24% (11/~47). The automated pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419, which may have been partially Claude-influenced).

- U33: 7 Claude-ordered specs executed (first results since U31). kama_vortex_div near-miss (9 trades). EMA200 family CLOSED (DD 25-32%). 3 new Claude specs written (T3 Vortex, MACDh CHOP, ALMA CCI).
- U33: Claude spec ACCEPT rate maintained ~24%. Pipeline ACCEPT rate maintained ~0%.
- U32: Pipeline killed U31 but residual persisted.
- U31: Supertrend CCI v4 NEW ACCEPT (PF=1.290). EMA200 Vortex v3 tight REJECT (DD=40%).
- U30: PPR scoring independently validates — PROMOTED_INDEX ALL Claude specs. PPR 3.1-4.5 vs pipeline near-zero.
- Key differentiator: Claude specs use thesis-driven design with 2-condition rules. Pipeline uses 3-5 condition combinatorial mutations.
- Research velocity bounded by Claude advisory cycle frequency, not compute
- NEW U33 specs awaiting execution:
  - T3 Vortex Transition (claude-t3vtx01): T3 smooth filter + Vortex cross, 2 variants
  - MACDh CHOP Transition (claude-mchtrn01): MACD histogram zero-cross + CHOP gate, 3 variants
  - ALMA CCI Exhaustion (claude-almcci01): ALMA trend + CCI -100 exhaustion, 3 variants
- 8 total new variants ready to run, ALL following brain rules (2 conditions, 8:1 R:R, ETH 4h)
