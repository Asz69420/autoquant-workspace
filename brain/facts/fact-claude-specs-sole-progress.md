---
id: fact-claude-specs-sole-progress
type: fact
title: Claude-specified strategies are the only source of ACCEPT-tier results — portfolio now at 9 specs
status: active
confidence: 0.97
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
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
supporting_ids:
  - failure-pipeline-structural-death
  - fact-zero-trade-signal-bottleneck
validated_at: "2026-03-05T18:00:00Z"
updated_at: "2026-03-05T18:00:00Z"
---

All 10 unique ACCEPT-tier strategies were designed by Claude advisory cycles using the spec_rules template. The ACCEPT rate for Claude specs is ~22% (10/~45). The automated pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419, which may have been partially Claude-influenced).

- Claude spec ACCEPT rate: ~22% (10 of ~45 backtests)
- Pipeline ACCEPT rate: ~0.1% (1 of 800+ outcomes)
- Key differentiator: Claude specs use thesis-driven design with specific regime hypotheses and indicator selection
- Pipeline specs use combinatorial mutations without strategic intent
- Research velocity is now bounded by Claude advisory cycle frequency, not compute
- U27: Claude spec portfolio is largest ever — 9 specs covering 6 mechanism families:
  - Vortex transition (claude-a7f3b1c2 ALMA variant, claude-f3a8d5b1 MACD variant)
  - CCI confirmation (claude-d4e1f8a3 Supertrend CCI 4h port, claude-e5d8f4a9 CCI KAMA)
  - T3 smoothing (claude-c9b0e2f7 T3 EMA200 gate)
  - EMA200 structural gating (claude-b7c2a9e6 tight DD, claude-e2macd01 MACD combo)
  - KAMA adaptive (claude-kmrsi01a KAMA RSI isolation)
  - Supertrend variants (claude-stmacd01 Supertrend MACD)
- 27+ variants ready to run, ALL following brain rules (2 conditions, 8:1 R:R, ETH 4h)
- CRITICAL U27: 9 specs blocked 4+ consecutive cycles (earliest: U24→U27)
- Blocking cost estimate: at 22% ACCEPT rate, ~2 new ACCEPTs prevented per cycle (~8 total delayed)
- Confidence raised from 0.95 to 0.97: 9-spec portfolio with 4 cycles of blocking is strong evidence
