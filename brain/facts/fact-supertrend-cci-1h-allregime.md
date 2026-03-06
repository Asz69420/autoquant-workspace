---
id: fact-supertrend-cci-1h-allregime
type: fact
title: Supertrend CCI architecture — default 12:1 ACCEPT, all variants CLOSED. R:R is architecture-dependent.
status: active
confidence: 0.90
tags:
  - supertrend
  - cci
  - 1h
  - 4h
  - all-regime
  - regime-tradeoff
  - rr-architecture
  - variants-closed
evidence_paths:
  - artifacts/backtests/20260304/hl_20260304_dfdae944.backtest_result.json
  - docs/shared/LAST_CYCLE_RESULTS.md
supporting_ids:
  - fact-eth-4h-dominance
  - rule-4h-only
contradictory_ids:
  - failure-1h-degradation
updated_at: "2026-03-06T08:00:00Z"
validated_at: "2026-03-06T08:00:00Z"
---

Supertrend CCI architecture tested across multiple configurations:

**ETH 1h (U23):** PF=1.480, 63 trades, DD=36.43%. All-regime: trending 1.638, ranging 1.470, transitional 1.283. FIRST 1h all-regime but DD prevents ACCEPT.

**ETH 4h default (U31 ACCEPT):** PF=1.290, 112 trades, DD=11.63%. Ranging/transitional specialist: trending 0.562, ranging 1.989, transitional 2.777.

**ETH 4h 8:1 variant (U33):** PF=1.358, 193 trades, DD=25.36%. Regime shift: trending 0.742, ranging 1.548, transitional 3.291.
- PF improvement (+0.068) but DD blowout (11.63% → 25.36%)
- 8:1 R:R shifts alpha toward transitional (bigger wins) while degrading ranging (more frequent smaller losses)
- Trade count nearly doubles (112 → 193) — narrower TP catches more entries before reversal

**ETH 4h tight variant (U33):** PF=1.179, 202 trades, DD=26.86%. Worse on all metrics.

Key insights:
1. CCI as trend-CONFIRMATION outperforms CCI as mean-reversion fade (CCI Chop Fade PF=1.255)
2. Default 4h variant (PF=1.290, DD=11.63%) is optimal — wider R:R doesn't improve risk-adjusted returns
3. 8:1 R:R regime shift pattern: more transitional alpha but more ranging bleed
4. Confidence raised to 0.90: 4 variants tested across 2 timeframes, consistent architecture behavior
5. **VARIANTS CLOSED (U35):** Only default 12:1 viable. 8:1 and tight both REJECT on DD. No further variant testing warranted.
6. **R:R architecture insight:** Confirmation strategies (late-entry) need wider TP than transition-detection strategies (early-entry). Supertrend CCI enters AFTER momentum confirmed → needs more room to run. This is the first evidence that the "8:1 sweet spot" rule is architecture-dependent, not universal.
