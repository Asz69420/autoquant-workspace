---
id: fact-vortex-transition-edge
type: fact
title: Vortex crossover captures regime transitions, enabling all-regime profitability on ETH
status: active
confidence: 0.92
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/outcomes/
tags: [vortex, regime, transition, eth, 4h]
updated_at: "2026-03-03T11:00:00Z"
---

Vortex crossover (VTXP/VTXM) detects regime transitions, not regime states. This is why it works across all regimes on ETH — transitions happen at the boundaries of every regime. 6 variants tested on ETH 4h, 5 are all-regime profitable.

- v3a: PF=2.034, transitional PF=3.886 (highest single-regime PF ever)
- v2c: PF=1.892, transitional PF=2.986
- v3b: PF=1.885, transitional PF=2.250
- v2b: PF=1.436, all-regime
- v1: PF=1.385, all-regime
- BTC vortex consistently fails (PF=0.743), proving the all-regime property is ETH-specific
