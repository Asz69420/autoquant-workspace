---
id: fact-promotion-pipeline-zero-trade
type: fact
title: Research-to-spec promotion pipeline and recombine generate specs that produce zero trades
status: active
confidence: 0.95
evidence_paths:
  - artifacts/promotions/20260304/
  - artifacts/strategy_specs/20260304/
  - artifacts/batches/20260304/
  - artifacts/research/20260304/recombine-20260304113839-2f70dc4c.research_card.json
tags:
  - promotions
  - zero-trades
  - research-pipeline
  - recombine
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - failure-pipeline-structural-death
  - fact-directive-loop-circular
validated_at: "2026-03-04T23:45:00Z"
updated_at: "2026-03-04T23:45:00Z"
---

The promotion pipeline (research card → thesis → strategy spec) and recombine system are both operational and active but share the same AND-chain signal design flaw as the autopilot pipeline. All generated specs produce 0 trades.

- 55 promotions ran on 2026-03-04, ALL 0-trade specs
- Recombine system generates specs on blacklisted asset/timeframe combos (BTC 1h)
- Recombine uses same EMA_TREND_ATR_EXITS template → same broken architecture
- Directive enforcement not working: EXCLUDE_ASSET:BTC ignored by recombine
- Same root cause as pipeline: combinatorial condition assembly, 3+ AND conditions
- The promotion pipeline generates VOLUME (spec files) but not QUALITY (tradeable specs)
- Promotion pipeline is NOT hypothesis-driven — it translates research concepts mechanically
- All generated specs feed into circular directive loop (see fact-directive-loop-circular)
