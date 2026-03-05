---
id: fact-kama-vortex-template-untested
type: fact
title: kama_vortex_divergence template tested U33 — generated 9 trades (1 short of 10 minimum). Near-miss, needs parameter tuning.
status: active
confidence: 0.80
evidence_paths:
  - scripts/backtester/signal_templates.py
  - docs/shared/LAST_CYCLE_RESULTS.md
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - template
  - kama
  - vortex
  - near-miss
  - exhaustion-detection
  - parameter-tuning
supporting_ids:
  - fact-kama-adaptive-edge
  - fact-vortex-transition-edge
  - fact-transition-detection-general-edge
validated_at: "2026-03-06T01:00:00Z"
updated_at: "2026-03-06T01:00:00Z"
---

The `kama_vortex_divergence` template was FINALLY backtested in U33 after 5 cycles of requesting. Result: 9 trades on ETH 4h (1 short of 10-trade minimum gate). The exhaustion-detection mechanism IS FUNCTIONAL but signals are too rare.

- U33: kama_vortex_div_v1 ETH 4h = 9 trades, PF=0.000, DD=9.5% — FAIL (INSUFFICIENT_TRADES, min 10)
- U33: kama_vortex_div_v1_10to1 ETH 4h = same 9 trades (TP doesn't affect entry count)
- Template mechanism: KAMA flattening + Vortex crossover + ATR volatility gate = detects trend EXHAUSTION
- Signal rarity root cause: triple-gate too restrictive (same pattern as choppiness_donchian_fade in Entry 002)
- Tuning options: relax KAMA flattening threshold (wider slope window), lower ATR gate, or widen Vortex crossover proximity
- Exhaustion-detection remains the LAST untested mechanism family with highest theoretical potential
- Combines two proven ACCEPT families (KAMA PF=1.857 + Vortex PF=2.034)
- Confidence lowered from 0.85 to 0.80: template works mechanically but requires parameter changes to be viable
