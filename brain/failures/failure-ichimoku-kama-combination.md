---
id: failure-ichimoku-kama-combination
type: failure
title: Ichimoku + KAMA combination fails across all configurations
status: active
confidence: 0.88
tags:
  - indicator-combo
  - ichimoku
  - kama
  - dead
evidence_paths:
  - artifacts/backtests/20260304/hl_20260304_ec85c520.backtest_result.json
  - artifacts/backtests/20260304/hl_20260304_a95b75f6.backtest_result.json
  - artifacts/backtests/20260304/hl_20260304_43292b85.backtest_result.json
  - artifacts/backtests/20260304/hl_20260304_3c59b0fa.backtest_result.json
supporting_ids:
  - fact-eth-4h-dominance
  - fact-kama-adaptive-edge
contradictory_ids: []
updated_at: "2026-03-04T23:00:00Z"
validated_at: "2026-03-04T23:00:00Z"
---

Ichimoku (ITS_9/IKS_26/ISA_9/ISB_26) combined with KAMA produces no ACCEPT-tier results across 4 configurations.

- ETH 4h: PF=0.908, 233 trades, DD=102.82% — catastrophic
- SOL 4h: PF=0.962, 209 trades — loss
- ETH 1h: PF=0.851, 268 trades — loss
- SOL 1h: PF=1.090, 241 trades — marginal, not ACCEPT

Root cause: Ichimoku's median-price signals use 9/26 period lookback creating slow, lagging entries. KAMA's adaptive smoothing adjusts speed dynamically. These indicator families have incompatible time horizons — Ichimoku is structurally slow while KAMA is structurally adaptive. The combination produces frequent entries (200-268 trades) that lack directional conviction.

Note: This does NOT invalidate Ichimoku alone or KAMA alone. KAMA Stoch v1 (PF=1.857) and Ichimoku TK cross (untested standalone) may still have value. The failure is specifically in combining both families.
