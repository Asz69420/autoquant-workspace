---
id: rule-adaptive-over-static
type: rule
title: Prefer adaptive indicators over static indicators for all-regime strategies
status: active
confidence: 0.91
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - artifacts/outcomes/
tags: [indicator-selection, adaptive, all-regime, design-principle]
supporting_ids: [fact-kama-adaptive-edge, fact-vortex-transition-edge, fact-ranging-reliable-base]
contradictory_ids: []
updated_at: "2026-03-03T12:00:00Z"
---

Adaptive indicators (self-adjusting parameters or transition-detecting mechanics) are the only indicator families that produce all-regime ACCEPT-tier strategies. Static indicators max out at PF=1.712 (MACD) and require regime gates to avoid trending losses.

Evidence hierarchy from 46 backtests:
- **Adaptive** (KAMA_10_2_30): PF=1.857, all-regime. Self-adjusts smoothing speed. Ranging PF=4.87.
- **Transition-detecting** (VTXP/VTXM): PF=2.034, all-regime. Detects regime shifts via directional movement crossover.
- **Trend-following** (Supertrend): PF=1.921, all-regime BUT relies on fixed ATR multiple. Success may come from exit mechanics (direction flip) rather than adaptivity.
- **Static oscillators** (CCI, RSI, MACD): Max PF=1.712. Need CHOP gate for ranging. Trending losses without gates.
- **Dead** (STC, QQE, STIFFNESS): Structural misfits. 0 ACCEPTs.

Design rule: when creating new specs, start with adaptive indicators (KAMA, T3, ALMA, Vortex) before testing static oscillators. Static oscillators should only be used with mandatory regime gates.

Counter-evidence to monitor: If a static oscillator achieves all-regime ACCEPT without gates, this rule weakens.
