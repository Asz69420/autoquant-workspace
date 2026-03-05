---
id: fact-research-pipeline-homogeneous
type: fact
title: Research card pipeline collapsed into homogeneous output — all cards are identical recombine clones of single indicator
status: active
confidence: 0.90
evidence_paths:
  - artifacts/research/20260305/recombine-20260305033042-840e0f14.research_card.json
  - artifacts/research/20260305/recombine-20260305035619-fccfb42a.research_card.json
  - artifacts/research/20260305/recombine-20260305034514-833f0d38.research_card.json
tags:
  - pipeline
  - research-cards
  - homogeneity
  - recombine
  - waste
supporting_ids:
  - failure-pipeline-structural-death
  - fact-directive-loop-circular
validated_at: "2026-03-05T23:00:00Z"
updated_at: "2026-03-05T23:00:00Z"
---

The research card pipeline has collapsed into producing identical output. All 10 latest research cards (2026-03-05) are structurally identical recombine clones:

- Same indicator: "Adaptive Flag Patterns [The_lurker]" from TradingView
- Same template: EMA_TREND_ATR_EXITS
- Same asset/timeframe: BTC 1h (violates EXCLUDE_ASSET:BTC directive)
- Same source_type: library_recombine
- Identical summary bullets across all 10 cards

This represents a second mode of pipeline collapse alongside the directive loop. While the directive loop produces identical SPEC remediation, the research pipeline produces identical RESEARCH input. Both feed into each other: homogeneous research cards → homogeneous specs → 0 trades → identical directives → more homogeneous specs.

No new external market ideas (YouTube, TradingView) are entering the system. Belief evolution is blocked from both internal (no backtests produce trade data) and external (no novel research cards) channels.
