---
id: constraint-min-trades-40
type: constraint
title: Minimum 40 trades required for statistical validity
status: active
confidence: 0.85
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags: [statistics, trade-count, acceptance-criteria]
updated_at: "2026-03-03T11:00:00Z"
---

Strategies with fewer than 40 trades lack statistical significance. The lowest trade-count ACCEPT is KAMA Stoch v1 with 42 trades. Most ACCEPTs have 79-179 trades. Strategies generating 0 trades (WILLR+STIFFNESS, dead templates) are auto-rejected. Strategies with 1-20 trades provide insufficient data for regime analysis.
