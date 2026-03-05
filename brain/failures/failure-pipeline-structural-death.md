---
id: failure-pipeline-structural-death
type: failure
title: Pipeline killed U31 but fully self-regenerating — 300+ zero-trade backtests, queue starvation blocking Claude specs
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - data/state/autopilot_counters.json
  - artifacts/backtests/20260304/
  - artifacts/backtests/20260305/
  - artifacts/backtests/20260306/
  - artifacts/batches/20260304/
  - artifacts/batches/20260306/
  - artifacts/promotions/20260304/
  - artifacts/promotions/20260305/
  - artifacts/promotions/20260306/
  - artifacts/feasibility/20260305/
  - artifacts/feasibility/20260306/
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772725502.json
  - artifacts/research/20260305/recombine-20260305033042-840e0f14.research_card.json
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
  - queue-starvation
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-promotion-pipeline-zero-trade
  - fact-directive-loop-circular
  - fact-research-pipeline-homogeneous
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-06T06:30:00Z"
updated_at: "2026-03-06T06:30:00Z"
---

The automated pipeline scaled to industrial-level waste before being killed in U31. Post-kill, the pipeline is FULLY SELF-REGENERATING — kill order has had zero effect across 3 cycles.

- U34: 131 new backtests in 20260306, ALL zero-trade, ALL BTC 1h directive specs. Pipeline produced: 4 new strategy specs, 6 feasibility reports, 3 batch backtests, 3 promotion runs, 3 thesis files — ALL waste. 300+ zero-trade backtests since kill order. NEW: queue starvation identified — directive specs consume all backtest slots, blocking Claude specs for 2 consecutive cycles.
- U33: 30 new outcome notes ALL REJECT, ALL 0-trade. Pipeline waste continues unabated despite kill order. 6 new pipeline promotions in 20260306.
- U33: 10 latest backtests in artifacts/backtests/20260306/ = directive specs, ALL 0-trade.
- U32: Pipeline kill ordered U31, but 12 more BTC 1h directive backtests ran post-kill (11:31-11:47 UTC). All 0-trade.
- U32: 6 new pipeline promotions in artifacts/promotions/20260305/ — all from dead pipeline
- U31: Pipeline kill ordered. Claude-only execution confirmed. 12 Claude specs ordered.
- U30: 1826 backtests on 2026-03-05 (3652 files / 2), ALL 0-trade — 10x escalation
- U30: 2028 feasibility reports, 134 promotion runs, 96 recombine bundles, 140 experiments — ALL waste
- U30: PPR scoring independently confirms only Claude specs merit PROMOTE (>3.0)
- U29: Research card pipeline collapsed — 10/10 identical "Adaptive Flag Patterns" clones on BTC 1h
- U29: Directive specs reference confidence_threshold (not a real column) — formally invalid
- Directive loop crosses day boundary with no circuit-breaker
- Self-regenerating: pipeline generates specs from its own failures -> more failures -> more specs
- Three-layer collapse: specs -> 0 trades -> directives loop -> research cards clone -> more bad specs
- NEW U34: Queue starvation is the mechanism by which pipeline blocks Claude progress — FIFO queue serves 131 zero-trade specs before 7 Claude variants
