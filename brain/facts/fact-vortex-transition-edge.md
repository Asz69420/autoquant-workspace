---
id: fact-vortex-transition-edge
type: fact
title: Vortex crossover captures regime transitions, enabling all-regime profitability on ETH
status: active
confidence: 0.92
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/outcomes/
tags:
  - vortex
  - regime
  - transition
  - eth
  - 4h
supporting_ids:
  - fact-transition-detection-general-edge
validated_at: "2026-03-04T23:30:00Z"
updated_at: "2026-03-04T23:30:00Z"
---

Vortex crossover (VTXP/VTXM) detects regime transitions, not regime states. This is why it works across all regimes on ETH — transitions happen at the boundaries of every regime. 7 variants tested on ETH 4h, 6 are all-regime profitable.

- EMA200 Vortex v2 12:1: PF=1.969, transitional PF=4.321 (NEW RECORD — U24). DD=30% borderline.
- v3a: PF=2.034, transitional PF=3.886
- v2c: PF=1.892, transitional PF=2.986
- v3b: PF=1.885, transitional PF=2.250
- v2b: PF=1.436, all-regime
- v1: PF=1.385, all-regime
- BTC vortex consistently fails (PF=0.743), proving the all-regime property is ETH-specific
- EMA200 price filter improves transitional alpha significantly (4.321 vs 3.886 without)
- 1h Vortex confirmed dead: v2c PF=0.816, v3b PF=0.803 (U24)
