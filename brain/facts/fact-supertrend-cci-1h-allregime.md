---
id: fact-supertrend-cci-1h-allregime
type: fact
title: Supertrend CCI v3 Wide achieves all-regime profitability on ETH 1h (first 1h success)
status: active
confidence: 0.82
tags:
  - supertrend
  - cci
  - 1h
  - all-regime
  - near-miss
evidence_paths:
  - artifacts/backtests/20260304/hl_20260304_dfdae944.backtest_result.json
supporting_ids:
  - fact-eth-4h-dominance
  - rule-4h-only
contradictory_ids:
  - failure-1h-degradation
updated_at: "2026-03-04T23:00:00Z"
validated_at: "2026-03-04T23:00:00Z"
---

Supertrend CCI v3 Wide on ETH 1h achieved PF=1.480, 63 trades, +62.5% return with all-regime profitability:
- Trending PF=1.638 (30 trades)
- Ranging PF=1.470 (13 trades)
- Transitional PF=1.283 (20 trades)

This is the FIRST 1h strategy to show profitable signals across all three regimes. However, DD=36.43% exceeds the 20% constraint, preventing ACCEPT status.

Key implications:
1. The 4h-only rule (rule-4h-only) needs nuance: 1h CAN produce profitable all-regime signals. The issue is DD accumulation, not signal quality.
2. CCI as trend-CONFIRMATION (with Supertrend direction) outperforms CCI as mean-reversion fade (CCI Chop Fade PF=1.255).
3. A 4h port of this architecture should reduce DD while maintaining PF (per 4h-dominance pattern).
4. If 4h port succeeds with DD<20%, this becomes a new ACCEPT and validates CCI-confirmation as a new signal paradigm.

Confidence set at 0.82 (single backtest, 63 trades — needs 4h validation).
