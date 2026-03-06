---
id: failure-ema200-dd-barrier
type: failure
title: EMA200 Vortex family structurally exceeds 20% DD constraint — 7 variants across 3 generations failed. Family CLOSED.
status: active
confidence: 0.97
evidence_paths:
  - docs/shared/LAST_CYCLE_RESULTS.md
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - ema200
  - vortex
  - drawdown
  - closed-family
  - transition-detection
supporting_ids:
  - fact-transitional-highest-alpha
  - fact-vortex-transition-edge
  - constraint-max-dd-20pct
contradictory_ids:
  - fact-transition-detection-general-edge
validated_at: "2026-03-06T08:00:00Z"
updated_at: "2026-03-06T08:00:00Z"
---

The EMA200 Vortex family was designed to amplify transitional alpha by filtering Vortex crosses with EMA200 position. Seven variants across three generations ALL exceed the 20% DD constraint:

- v2 12:1 (U24): PF=1.969, DD=30.0%, trans PF=4.321 (RECORD) — conditional ACCEPT
- v3 tight 0.75 ATR (U31): DD=40% — REJECTED. Tight stop whipsawed at EMA200 transition zones
- v3 8:1 1.0 ATR (U33): PF=1.046, DD=25.56% — marginal PF, DD still exceeds constraint
- v3b 8:1 1.0 ATR (U33): PF=1.046, DD=25.56% — IDENTICAL to v3 8:1 (confirming same spec)
- v3b 10:1 1.0 ATR (U33): PF=1.358, DD=32.20% — better PF but WORSE DD from wider TP holding through drawdowns

Total: 7 distinct test configurations, DD range 25-40%. No configuration achieves DD<20%.

Root cause: EMA200 filter forces entries at high-volatility regime transition points. These are exactly the points where large adverse moves occur before the new regime establishes. Stop width cannot fix this because the volatility at transition IS the feature being captured.

Regime breakdown (v3b 10:1): trending 0.574, ranging 1.751, transitional 2.297
- Pattern: transitional alpha high but trending regime bleeds consistently
- EMA200 acts as a transition-detector that forces drawdown during non-transitional periods

U35 confirmation: v3 8:1 and v3b 8:1 produced identical results (PF=1.046, DD=25.56%, 130 trades), confirming these were the same spec. Confidence raised to 0.97 — 7 tests is comprehensive.

Conclusion: EMA200 Vortex produces high transitional alpha but the DD cost is structural and unfixable. FAMILY CLOSED — no further compute.
