---
id: fact-ppr-validates-claude-monopoly
type: fact
title: PPR scoring independently confirms only Claude-specified strategies merit promotion
status: active
confidence: 0.92
evidence_paths:
  - artifacts/library/PROMOTED_INDEX.json
  - artifacts/library/PROMOTED_INDEX_SUMMARY.json
  - artifacts/library/PASSED_INDEX.json
tags:
  - ppr
  - claude-specs
  - scoring
  - promoted-library
  - validation
supporting_ids:
  - fact-claude-specs-sole-progress
  - failure-pipeline-structural-death
validated_at: "2026-03-05T23:30:00Z"
updated_at: "2026-03-05T23:30:00Z"
---

The PPR (Post-backtest Performance Rating) scoring system, deployed independently of brain analysis, confirms that only Claude-specified strategies merit promotion. This is a third independent validation source alongside brain analysis and historical ACCEPT rates.

- PROMOTED_INDEX contains exactly 10 entries — ALL from Claude specs (every strategy_spec_path is claude-*)
- PPR scores for promoted strategies range from 3.1 to 4.5 (PROMOTE threshold is 3.0)
- Top PPR score: Supertrend tail harvester 8:1 at 4.47 (claude-st9k3m5x)
- Second: KAMA Stoch Pullback v1 at 4.27 (claude-d2f9b7e3)
- Pipeline specs score near-zero PPR (0 trades = PF 0.0, DD 100%)
- Top families in PROMOTED_INDEX: claude-d2f9b7e3 (2 entries), claude-st9k3m5x (2 entries)
- Templates in promoted library: supertrend variants (3), MACD variants (3), KAMA (2), RSI (1), supertrend_strong_trend (1)
- Zero pipeline-generated specs appear in PROMOTED_INDEX
- PPR provides objective, automated confirmation of brain beliefs about Claude spec superiority
