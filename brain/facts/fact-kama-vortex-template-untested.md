---
id: fact-kama-vortex-template-untested
type: fact
title: kama_vortex_divergence template exists in signal_templates.py but has never been backtested — combines two proven ACCEPT families
status: active
confidence: 0.85
evidence_paths:
  - scripts/backtester/signal_templates.py
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - template
  - kama
  - vortex
  - untested
  - exhaustion-detection
supporting_ids:
  - fact-kama-adaptive-edge
  - fact-vortex-transition-edge
  - fact-transition-detection-general-edge
validated_at: "2026-03-05T22:00:00Z"
updated_at: "2026-03-05T22:00:00Z"
---

The `kama_vortex_divergence` template is built into signal_templates.py but has ZERO backtests. It detects exhaustion via KAMA flattening + Vortex crossover + ATR volatility gate. This combines the two indicator families with highest ACCEPT rates: KAMA adaptive (KAMA Stoch v1 PF=1.857) and Vortex transition-detection (v3a PF=2.034).

- Template mechanism: detects trend EXHAUSTION (ending) vs transition-detection (beginning) — distinct market phase
- KAMA flattening = adaptive MA stops moving = trend losing momentum
- Vortex crossover = directional change confirmed
- ATR gate = volatility sufficient for profitable execution
- Both KAMA and Vortex are proven all-regime profitable families (2 of 3 all-regime architectures)
- Exhaustion-detection is an UNTESTED mechanism distinct from transition-detection (6/10 ACCEPTs) and mean-reversion
- Zero spec-writing effort required — template is ready to run
- No system exists to flag untested templates, allowing this to sit idle for weeks
- Confidence 0.85: high prior from proven component families, but unknown interaction and no backtest data
