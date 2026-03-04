---
id: failure-1h-degradation
type: failure
title: 1h timeframe degrades PF but CAN produce profitable signals (DD is the bottleneck)
status: active
confidence: 0.85
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/backtests/20260304/hl_20260304_dfdae944.backtest_result.json
tags:
  - timeframe
  - 1h
  - degradation
supporting_ids:
  - fact-eth-4h-dominance
  - rule-4h-only
contradictory_ids:
  - fact-supertrend-cci-1h-allregime
validated_at: "2026-03-04T23:00:00Z"
updated_at: "2026-03-04T23:00:00Z"
---

Most strategies tested on both 1h and 4h are worse on 1h:
- Vortex v3a: 1h PF=0.753 vs 4h PF=2.034 (delta -1.28)
- Vortex v3b: 1h PF=0.841 vs 4h PF=1.885 (delta -1.04)
- Vortex v2c: 1h PF=0.856 vs 4h PF=1.892 (delta -1.04)
- KAMA v2 SOL: 1h DD=36% vs Vortex SOL 4h DD=23.4%
- T3 Vortex SOL 1h: DD=81.3% (worst in system history)
- EMA200 Vortex v1: ETH 1h PF=0.796 vs SOL 4h PF=1.185

Average PF degradation: 0.94 points. 1h is typically a losing timeframe.

EXCEPTION (U23): Supertrend CCI v3 Wide ETH 1h achieved PF=1.480 with all-regime profitability (T:1.638, R:1.470, Tr:1.283). This is the FIRST 1h strategy profitable across all regimes. However, DD=36.43% exceeds the 20% constraint.

Revised conclusion: 1h degradation is primarily a RISK problem (DD accumulation) rather than a SIGNAL problem. Certain indicator architectures (Supertrend+CCI) can produce profitable 1h signals, but the higher trade frequency amplifies drawdown. Confidence reduced from 0.93 to 0.85 pending 4h port comparison.
