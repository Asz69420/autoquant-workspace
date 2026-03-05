---
id: failure-pipeline-structural-death
type: failure
title: Automated pipeline at industrial-scale waste — 1826 backtests/day at 0%, 7 cycles blocking Claude specs
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
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - fact-directive-loop-circular
  - fact-research-pipeline-homogeneous
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-05T23:30:00Z"
updated_at: "2026-03-05T23:30:00Z"
---

The automated pipeline has scaled to industrial-level waste. On 2026-03-05 alone: 1826 backtests, 2028 feasibility reports, 134 promotions, 96 bundles, 140 experiments — ALL producing zero-trade results. This is a 10x escalation from U29's "130+" estimate. The pipeline is the single largest blocker to research progress.

- U30: 1826 backtests on 2026-03-05 (3652 files / 2), ALL 0-trade — 10x escalation
- U30: 2028 feasibility reports, 134 promotion runs, 96 recombine bundles, 140 experiments — ALL waste
- U30: 5 new REVIEW_REQUIRED promotions from pipeline await rejection
- U30: PPR scoring independently confirms only Claude specs merit PROMOTE (>3.0). PROMOTED_INDEX = 10 entries, all Claude specs
- U29: Research card pipeline collapsed — 10/10 identical "Adaptive Flag Patterns" clones on BTC 1h
- U29: Directive specs reference confidence_threshold (not a real column) — formally invalid
- U28: 100+ strategy specs generated in strategy_specs/20260305/ — generation accelerating
- U28: spec-5df8f61c0c71 tested 10x, 0 trades every time
- Directive loop crosses day boundary with no circuit-breaker
- Self-regenerating: pipeline generates specs from its own failures → more failures → more specs
- 0/29+ machine directives read or applied by pipeline
- 9 Claude specs blocked 7 consecutive cycles (U24→U30) — ~14 cumulative ACCEPTs delayed
- Three-layer collapse: specs → 0 trades → directives loop → research cards clone → more bad specs
