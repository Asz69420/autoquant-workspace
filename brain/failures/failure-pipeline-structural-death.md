---
id: failure-pipeline-structural-death
type: failure
title: Automated pipeline structurally dead and self-regenerating — 0 ACCEPTs, circular directive loop, 130+ zero-trade runs, research cards homogeneous
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
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772681322.json
  - artifacts/research/20260305/recombine-20260305033042-840e0f14.research_card.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-dd7abf6f002b.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-5df8f61c0c71.strategy_spec.json
tags:
  - pipeline
  - starvation
  - automation
  - promotions
  - directive-loop
  - self-regenerating
  - research-collapse
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - fact-directive-loop-circular
  - fact-research-pipeline-homogeneous
validated_at: "2026-03-05T23:00:00Z"
updated_at: "2026-03-05T23:00:00Z"
---

The automated pipeline (thesis → spec → refinement → backtest) has structurally failed AND is self-regenerating waste. All 10 unique ACCEPT-tier strategies came from Claude-specified specs. The pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419) and has been in drought for 130+ consecutive zero-trade runs.

- Drought cycles: 130+ (escalating from 66+ at U25, +36 on 2026-03-05, +10 same-spec retests U28, +30 new outcomes U29)
- Loop crosses day boundary (2026-03-04 → 2026-03-05) with no circuit-breaker
- U27: Pipeline self-regenerating — 3 new specs + 2 promotions generated AFTER 102+ epidemic documented
- U28: 100+ NEW strategy specs generated in strategy_specs/20260305/ directory — generation ACCELERATING
- U28: spec-5df8f61c0c71 tested 10x (3 variants × 2 assets × 2 timeframes), 0 trades every time — classic loop
- U29: Directive specs reference abstract pseudo-parameters (confidence_threshold) not actual dataframe columns — specs formally invalid
- U29: Research card pipeline collapsed — 10/10 latest cards are identical "Adaptive Flag Patterns" recombine clones on BTC 1h
- U29: All 30 latest outcome notes = REJECTED, 0 trades, identical remediation directives
- U28: Recent specs STILL target BTC 1h despite EXCLUDE_ASSET:BTC — directive enforcement completely absent
- Directive stall cycles: 44+ (refinement unable to improve any baseline)
- Directive loop: circular — same 5 remediation directives generated for every failure, variants fail identically
- Deduplication: 95%+ of batch runs are duplicates (150+ batch files on 2026-03-04)
- Directive enforcement: 0/29 machine directives read or applied by pipeline
- All refinement variants (ENTRY_TIGHTEN, PARAM_SWEEP, etc.) have 0% improvement rate
- Pipeline consumes 100% of backtest capacity, blocking Claude specs from executing
- 9 Claude specs blocked 6 consecutive cycles (U24→U29) — largest spec portfolio ever (27+ variants) sitting idle
- Estimated ~12 cumulative ACCEPTs delayed at 22% rate across 6 blocked cycles
- Three-layer collapse: specs produce 0 trades → directives loop → research cards clone → more bad specs
