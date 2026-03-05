---
id: fact-zero-trade-signal-bottleneck
type: fact
title: All non-Claude spec sources produce zero trades due to AND-chain misalignment — 1826/day at industrial scale
status: active
confidence: 0.99
evidence_paths:
  - artifacts/backtests/20260304/
  - artifacts/backtests/20260305/
  - artifacts/batches/20260304/
  - artifacts/promotions/20260304/
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/outcomes/20260305/
tags:
  - pipeline
  - signal
  - zero-trades
  - bottleneck
  - promotions
  - industrial-scale
supporting_ids:
  - failure-pipeline-structural-death
  - fact-directive-loop-circular
  - fact-ppr-validates-claude-monopoly
validated_at: "2026-03-05T23:30:00Z"
updated_at: "2026-03-05T23:30:00Z"
---

1826 backtests on 2026-03-05 alone — ALL zero trades. Pipeline has scaled to industrial-level waste, an order of magnitude beyond U29's "130+" estimate. Entry conditions with 3+ AND-chained indicators never simultaneously fire within the same bar.

- U30: 1826 backtests on 2026-03-05 (3652 files), ALL 0-trade — 10x escalation from U29 estimate of 130+
- U30: 2028 feasibility reports, 134 promotion runs, 96 bundles, 140 experiments — ALL waste
- U30: 5 new REVIEW_REQUIRED promotions from dead pipeline await rejection
- U29: 30 outcome notes ALL 0-trade REJECTED with identical remediation directives
- U28: spec-5df8f61c0c71 tested 10x, 0 trades every time
- Promotion pipeline: 55+ promotions from 2026-03-04, ALL 0-trade specs
- Recombine system: generating BTC 1h specs despite EXCLUDE_ASSET
- Directive loop: every 0-trade outcome generates same 5 remediation directives → variant specs → 0 trades
- Directive specs reference confidence_threshold (not a real dataframe column) — formally invalid
- Root cause: combinatorial condition assembly (3-5 AND conditions) without co-occurrence analysis
- Counter-evidence: Claude specs use max 2 conditions and generate 42-179 trades
- PPR scoring independently confirms: pipeline specs score near-zero, only Claude specs score >3.0 (PROMOTE)
