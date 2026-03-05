---
id: fact-kama-vortex-template-untested
type: fact
title: kama_vortex_divergence tested U33 — 0/9 WR, edge inconclusive at low sample. Needs parameter tuning for more trades.
status: active
confidence: 0.60
evidence_paths:
  - scripts/backtester/signal_templates.py
  - docs/shared/LAST_CYCLE_RESULTS.md
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/backtests/20260305/hl_20260305_018f5de6.backtest_result.json
  - artifacts/backtests/20260305/hl_20260305_960a48c2.backtest_result.json
tags:
  - template
  - kama
  - vortex
  - inconclusive
  - exhaustion-detection
  - parameter-tuning
supporting_ids:
  - fact-kama-adaptive-edge
  - fact-vortex-transition-edge
  - fact-transition-detection-general-edge
validated_at: "2026-03-06T06:30:00Z"
updated_at: "2026-03-06T06:30:00Z"
---

The `kama_vortex_divergence` template was tested in U33 after 5 cycles of requesting. Results are INCONCLUSIVE — not near-miss, not dead.

- U33: kama_vortex_div_v1 ETH 4h = 9 trades, 0 wins, PF=0.000, DD=9.5% — FAIL (INSUFFICIENT_TRADES + 0% WR)
- U33: kama_vortex_div_v1_10to1 ETH 4h = same 9 trades, same result (TP doesn't affect entries)
- U34 reassessment: 0/9 WR is statistically inconclusive at these R:R ratios. At 10:1 R:R, breakeven WR = 9.1%. P(0/9 | true WR = 11%) = 0.35 — can't reject edge hypothesis from 9 trades alone.
- However, 0% WR is not encouraging. The U33 "near-miss" label was premature.
- Template mechanism: KAMA flattening + Vortex crossover + ATR volatility gate = detects trend EXHAUSTION
- Signal rarity root cause: triple-gate too restrictive (same pattern as choppiness_donchian_fade in Entry 002)
- DD=9.51% is very low — template selects conservative, quiet entry zones
- Priority: increase trade count to 20+ via parameter tuning FIRST (relax KAMA flattening threshold, lower ATR gate), THEN evaluate edge
- Exhaustion-detection remains the LAST untested mechanism family with strong theoretical support from 5+ independent research frameworks
- Combines two proven ACCEPT families (KAMA PF=1.857 + Vortex PF=2.034)
- Confidence lowered from 0.80 to 0.60: mechanism functional but edge quality unknown
