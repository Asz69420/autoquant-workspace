---
id: failure-pipeline-structural-death
type: failure
title: Pipeline killed U31 but residual persists — 12 more BTC 1h tests post-kill, Claude specs still blocked
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
  - artifacts/feasibility/20260305/
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772681322.json
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772710202.json
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772711102.json
  - artifacts/research/20260305/recombine-20260305033042-840e0f14.research_card.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-dd7abf6f002b.strategy_spec.json
  - artifacts/library/PROMOTED_INDEX.json
tags:
  - pipeline
  - starvation
  - automation
  - promotions
  - directive-loop
  - self-regenerating
  - research-collapse
  - industrial-scale
  - pipeline-kill
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - fact-directive-loop-circular
  - fact-research-pipeline-homogeneous
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-05T23:45:00Z"
updated_at: "2026-03-05T23:45:00Z"
---

The automated pipeline scaled to industrial-level waste before being killed in U31. Post-kill residual specs continue executing.

- U32: Pipeline kill ordered U31, but 12 more BTC 1h directive backtests ran post-kill (11:31-11:47 UTC). All 0-trade. Residual queue not fully drained.
- U32: 2 new outcome notes (autopilot-1772710202, autopilot-1772711102), both REJECT, both 0-trade, both directive_baseline_retest
- U32: 6 new pipeline promotions in artifacts/promotions/20260305/ — all from dead pipeline
- U32: Zero Claude spec results visible despite 12 specs + kama_vortex_div ordered. Execution confirmation needed.
- U31: Pipeline kill ordered. Claude-only execution confirmed. 12 Claude specs ordered.
- U30: 1826 backtests on 2026-03-05 (3652 files / 2), ALL 0-trade — 10x escalation
- U30: 2028 feasibility reports, 134 promotion runs, 96 recombine bundles, 140 experiments — ALL waste
- U30: 5 new REVIEW_REQUIRED promotions from pipeline await rejection
- U30: PPR scoring independently confirms only Claude specs merit PROMOTE (>3.0)
- U29: Research card pipeline collapsed — 10/10 identical "Adaptive Flag Patterns" clones on BTC 1h
- U29: Directive specs reference confidence_threshold (not a real column) — formally invalid
- U28: 100+ strategy specs generated in strategy_specs/20260305/ — generation accelerating
- Directive loop crosses day boundary with no circuit-breaker
- Self-regenerating: pipeline generates specs from its own failures → more failures → more specs
- 0/29+ machine directives read or applied by pipeline
- Three-layer collapse: specs → 0 trades → directives loop → research cards clone → more bad specs
