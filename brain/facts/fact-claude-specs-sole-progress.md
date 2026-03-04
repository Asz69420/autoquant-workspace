---
id: fact-claude-specs-sole-progress
type: fact
title: Claude-specified strategies are the only source of ACCEPT-tier results
status: active
confidence: 0.95
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/claude-specs/
tags:
  - claude-specs
  - pipeline
  - accept-rate
supporting_ids:
  - failure-pipeline-structural-death
validated_at: "2026-03-05T12:00:00Z"
updated_at: "2026-03-05T12:00:00Z"
---

All 10 unique ACCEPT-tier strategies were designed by Claude advisory cycles using the spec_rules template. The ACCEPT rate for Claude specs is ~22% (10/~45). The automated pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419, which may have been partially Claude-influenced).

- Claude spec ACCEPT rate: ~22% (10 of ~45 backtests)
- Pipeline ACCEPT rate: ~0.1% (1 of 800+ outcomes)
- Key differentiator: Claude specs use thesis-driven design with specific regime hypotheses and indicator selection
- Pipeline specs use combinatorial mutations without strategic intent
- Research velocity is now bounded by Claude advisory cycle frequency, not compute
- CRITICAL U26: 3 Claude specs (ALMA Vortex, T3 EMA200, CCI KAMA — 9 variants) blocked for 3 consecutive cycles (U24→U26) by pipeline capacity starvation
- Blocking cost estimate: at 22% ACCEPT rate, ~2 new ACCEPTs are being prevented per cycle of delay
