---
id: rule-max-2-entry-conditions
type: rule
title: Limit entry conditions to max 2 AND-chained indicators per side
status: active
confidence: 0.92
evidence_paths:
  - artifacts/backtests/20260304/
  - artifacts/backtests/20260303/
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - signal-design
  - entry-conditions
  - trade-frequency
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - fact-claude-specs-sole-progress
contradictory_ids: []
validated_at: "2026-03-04T22:00:00Z"
updated_at: "2026-03-04T22:00:00Z"
---

Specs with more than 2 AND-chained entry conditions per side (long/short) consistently produce zero trades. All 8 ACCEPT-tier strategies use exactly 2 entry conditions. Pipeline and promotion specs with 3-5 conditions have a 0% trade generation rate across 34+ consecutive backtests.

- All 8 ACCEPT-tier strategies: 2 entry conditions per side
- Pipeline specs with 3-5 conditions: 34/34 backtests = 0 trades
- Claude specs (2 conditions): generate 42-179 trades on same data
- Mechanism: indicator correlations mean 3+ conditions cluster but rarely align on exact same bar
- Recommendation: reject any spec with >2 entry conditions before backtesting
- Exception: could allow 3 conditions if one is a regime gate (CHOP, ADX) with wide threshold
