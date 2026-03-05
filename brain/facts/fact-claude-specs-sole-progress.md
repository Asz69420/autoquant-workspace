---
id: fact-claude-specs-sole-progress
type: fact
title: Claude-specified strategies are the only source of ACCEPT-tier results — 9 specs blocked 7 cycles, ~14 ACCEPTs delayed, PPR validated
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/library/PROMOTED_INDEX.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-a7f3b1c2.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-c9b0e2f7.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-e5d8f4a9.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-d4e1f8a3.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-b7c2a9e6.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-claude-f3a8d5b1.strategy_spec.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-claude-stmacd01.strategy_spec.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-claude-kmrsi01a.strategy_spec.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-claude-e2macd01.strategy_spec.json
tags:
  - claude-specs
  - pipeline
  - accept-rate
  - spec-portfolio
  - blocking
  - ppr-validated
supporting_ids:
  - failure-pipeline-structural-death
  - fact-zero-trade-signal-bottleneck
  - fact-research-pipeline-homogeneous
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-05T23:30:00Z"
updated_at: "2026-03-05T23:30:00Z"
---

All 10 unique ACCEPT-tier strategies were designed by Claude advisory cycles using the spec_rules template. The ACCEPT rate for Claude specs is ~22% (10/~45). The automated pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419, which may have been partially Claude-influenced).

- Claude spec ACCEPT rate: ~22% (10 of ~45 backtests)
- Pipeline ACCEPT rate: ~0% (0 of 1826+ backtests on 2026-03-05 alone)
- U30: PPR scoring independently validates — PROMOTED_INDEX contains 10 entries, ALL Claude specs. PPR scores 3.1-4.5 vs pipeline near-zero. Third independent confirmation source.
- U30: Confidence raised 0.98→0.99 on PPR validation + 7th blocked cycle
- Key differentiator: Claude specs use thesis-driven design with specific regime hypotheses and indicator selection
- Pipeline specs use combinatorial mutations without strategic intent
- Research velocity bounded by Claude advisory cycle frequency, not compute
- Claude spec portfolio: 9 specs covering 6 mechanism families:
  - Vortex transition (claude-a7f3b1c2 ALMA variant, claude-f3a8d5b1 MACD variant)
  - CCI confirmation (claude-d4e1f8a3 Supertrend CCI 4h port, claude-e5d8f4a9 CCI KAMA)
  - T3 smoothing (claude-c9b0e2f7 T3 EMA200 gate)
  - EMA200 structural gating (claude-b7c2a9e6 tight DD, claude-e2macd01 MACD combo)
  - KAMA adaptive (claude-kmrsi01a KAMA RSI isolation)
  - Supertrend variants (claude-stmacd01 Supertrend MACD)
- 27+ variants ready to run, ALL following brain rules (2 conditions, 8:1 R:R, ETH 4h)
- 9 specs blocked 7 consecutive cycles (U24→U30). ~14 cumulative ACCEPTs delayed at 22% rate
