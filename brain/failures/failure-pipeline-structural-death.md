---
id: failure-pipeline-structural-death
type: failure
title: Automated pipeline structurally dead and self-regenerating — 0 ACCEPTs, circular directive loop, 112+ zero-trade runs
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - data/state/autopilot_counters.json
  - artifacts/backtests/20260304/
  - artifacts/backtests/20260305/
  - artifacts/batches/20260304/
  - artifacts/promotions/20260304/
  - artifacts/promotions/20260305/
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-489f8bcaea8f.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-88cf9e406e3d.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-d7a7a5e46d09.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-5df8f61c0c71.strategy_spec.json
tags:
  - pipeline
  - starvation
  - automation
  - promotions
  - directive-loop
  - self-regenerating
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - fact-directive-loop-circular
validated_at: "2026-03-05T22:00:00Z"
updated_at: "2026-03-05T22:00:00Z"
---

The automated pipeline (thesis → spec → refinement → backtest) has structurally failed AND is self-regenerating waste. All 10 unique ACCEPT-tier strategies came from Claude-specified specs. The pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419) and has been in drought for 112+ consecutive zero-trade runs.

- Drought cycles: 112+ (escalating from 66+ at U25, +36 on 2026-03-05, +10 more same-spec retests U28)
- Loop crosses day boundary (2026-03-04 → 2026-03-05) with no circuit-breaker
- U27: Pipeline self-regenerating — 3 new specs + 2 promotions generated AFTER 102+ epidemic documented
- U28: 100+ NEW strategy specs generated in strategy_specs/20260305/ directory — generation ACCELERATING
- U28: spec-5df8f61c0c71 tested 10x (3 variants × 2 assets × 2 timeframes), 0 trades every time — classic loop
- U28: Recent specs STILL target BTC 1h despite EXCLUDE_ASSET:BTC — directive enforcement completely absent
- Directive stall cycles: 44+ (refinement unable to improve any baseline)
- Directive loop: circular — same 5 remediation directives generated for every failure, variants fail identically
- Deduplication: 95%+ of batch runs are duplicates (150+ batch files on 2026-03-04)
- Full-grid dedup: 27-run batches 100% deduplicated (0 new tests)
- Directive enforcement: 0/29 machine directives read or applied by pipeline
- Recombine: generates BTC 1h specs despite EXCLUDE_ASSET:BTC directive
- All refinement variants (ENTRY_TIGHTEN, PARAM_SWEEP, etc.) have 0% improvement rate
- Post-BALROG-fix: backtests execute but ALL produce 0 trades
- Pipeline consumes 100% of backtest capacity, blocking Claude specs from executing
- 9 Claude specs blocked 5 consecutive cycles (U24→U28) — largest spec portfolio ever (27+ variants) sitting idle
- Estimated ~10 cumulative ACCEPTs delayed at 22% rate across 5 blocked cycles
