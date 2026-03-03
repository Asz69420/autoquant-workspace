---
id: constraint-max-dd-20pct
type: constraint
title: Maximum drawdown cap of 20% for ACCEPT verdict
status: active
confidence: 0.90
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - risk
  - drawdown
  - acceptance-criteria
validated_at: "2026-03-04T12:00:00Z"
updated_at: "2026-03-04T12:00:00Z"
---

Strategies exceeding 20% max drawdown are rejected regardless of PF. All 8 ACCEPT-tier strategies have DD between 7.1% and 16.4%. The highest-DD ACCEPT is CCI Chop Fade v2 at 16.4%. KAMA Stoch v1 at 10.1% represents the ideal DD range. SOL strategies failing this gate: T3 Vortex SOL 1h DD=81.3%, KAMA v2 SOL 1h DD=36%.
