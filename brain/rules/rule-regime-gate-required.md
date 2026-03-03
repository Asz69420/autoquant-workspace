---
id: rule-regime-gate-required
type: rule
title: All non-adaptive strategies require trending regime gate
status: active
confidence: 0.88
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags: [regime, gate, trending, risk]
supporting_ids: [fact-ranging-reliable-base]
updated_at: "2026-03-03T11:00:00Z"
---

21/24 legacy ACCEPTs lose money during trending regime. Only Vortex (transition-detecting) and KAMA (adaptive) strategies survive trending without a gate. All other strategy families (MACD, RSI, EMA, CCI) need a CHOP > 50 or equivalent gate to disable trading during strong trends. ADX-as-filter destroys mean-reversion (PF drops 1.43 → 0.84). CHOP alone is the preferred regime gate.
