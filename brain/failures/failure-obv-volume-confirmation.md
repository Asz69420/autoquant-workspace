---
id: failure-obv-volume-confirmation
type: failure
title: OBV as volume confirmation adds noise not edge to trend strategies
status: active
confidence: 0.75
evidence_paths:
  - artifacts/backtests/20260304/hl_20260304_f57eba08.backtest_result.json
tags:
  - volume
  - obv
  - confirmation
  - supertrend
validated_at: "2026-03-04T23:30:00Z"
updated_at: "2026-03-04T23:30:00Z"
---

OBV (On-Balance Volume) as a confirmation filter for Supertrend produces marginal results on ETH 4h.

- Supertrend OBV Confirm v1 (ETH 4h): PF=1.094, DD=26.78%, 284 trades, WR=17.61%
- Compare Supertrend without OBV: PF=1.921 (8:1), DD=10.9%, 85 trades
- OBV confirmation TRIPLED trade count (284 vs 85) while HALVING PF (1.094 vs 1.921)

OBV's cumulative nature makes it a poor bar-by-bar filter — it trends with price rather than providing independent confirmation. The excess trades suggest OBV rarely disagrees with Supertrend direction, so it's not filtering noise, just allowing more entries.

Low confidence (0.75) because only 1 test. May warrant revisit with OBV slope/divergence rather than level comparison.
