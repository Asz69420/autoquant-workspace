---
id: failure-willr-stiffness
type: failure
title: WILLR + STIFFNESS combination never generates trading signals
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/outcomes/
tags:
  - willr
  - stiffness
  - dead-indicator
  - zero-trades
validated_at: "2026-03-04T12:00:00Z"
updated_at: "2026-03-04T12:00:00Z"
---

9 backtests across 3 assets (BTC, ETH, SOL) and 3 timeframes (15m, 1h, 4h). Zero trades in every single run. The STIFFNESS indicator never drops below 50 simultaneously with WILLR at extremes (<-80 or >-20). STIFFNESS_20_3_100 is dead as any signal or filter component. WILLR alone may have value with a different regime gate (CHOP), but the STIFFNESS pairing is permanently blacklisted.
