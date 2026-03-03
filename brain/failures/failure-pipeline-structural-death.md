---
id: failure-pipeline-structural-death
type: failure
title: Automated pipeline structurally dead — 0 ACCEPTs, 0-trade specs, full dedup saturation
status: active
confidence: 0.95
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - data/state/autopilot_counters.json
  - artifacts/backtests/20260304/
  - artifacts/batches/20260304/
tags:
  - pipeline
  - starvation
  - automation
supporting_ids:
  - fact-zero-trade-signal-bottleneck
validated_at: "2026-03-04T18:00:00Z"
updated_at: "2026-03-04T18:00:00Z"
---

The automated pipeline (thesis → spec → refinement → backtest) has structurally failed. All 8 unique ACCEPT-tier strategies came from Claude-specified specs. The pipeline produced exactly 1 ACCEPT ever (template_div PF=1.419) and has been in drought for 53 consecutive cycles.

- Drought cycles: 53 (largest count ever recorded)
- Directive stall cycles: 44 (refinement unable to improve any baseline)
- Signal clustering: pipeline-generated specs produce signals that bunch at same bars, yielding 0 trades
- Deduplication: 87%+ of pipeline specs are duplicates of previously-tested parameters
- Full-grid dedup: 27-run batches 100% deduplicated (0 new tests)
- Directive enforcement: 0/49 machine directives read or applied by pipeline
- All refinement variants (ENTRY_TIGHTEN, PARAM_SWEEP, etc.) have 0% improvement rate
- Post-BALROG-fix (U21): backtests execute but ALL 10 recent runs produce 0 trades
