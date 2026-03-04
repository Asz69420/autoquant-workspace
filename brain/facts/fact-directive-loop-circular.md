---
id: fact-directive-loop-circular
type: fact
title: Directive remediation loop is circular — generates identical actions for every 0-trade failure with zero information gain
status: active
confidence: 0.95
evidence_paths:
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624018-backfill-strategy-spec-20260304-5063f4f1f99b.strategy_spec.json
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772623802.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-5063f4f1f99b.strategy_spec.json
  - artifacts/backtests/20260305/
tags:
  - pipeline
  - directives
  - circular-loop
  - zero-trades
  - compute-waste
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - failure-pipeline-structural-death
  - fact-promotion-pipeline-zero-trade
validated_at: "2026-03-05T12:00:00Z"
updated_at: "2026-03-05T12:00:00Z"
---

The outcome→directive→variant→outcome loop generates identical remediation actions for every 0-trade failure. Every 0-trade outcome note produces the same 5 directives: GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE. These create variant specs (gate_adjust, entry_relax, exploration) that fail identically with 0 trades. The variant failures generate the same 5 directives again. Zero information gain per iteration.

- 102+ consecutive 0-trade backtests (U25: 66+, U26: +36 on 2026-03-05), each generating same 5 remediation directives
- Loop crosses day boundary (2026-03-04 → 2026-03-05) with no circuit-breaker intervention
- All 4 latest strategy spec families (5063f4f1f99b, f5bcc194e9c3, 14c5a03a3c34, dcbc1d66558b) show identical directive loop behavior
- 2026-03-05 specs (13a80050d94c, 5df8f61c0c71, 12c5d8d913ad) continue the same pattern across ETH and SOL, 1h and 4h
- Each spec generates 3-4 variants (gate_adjust, entry_relax, exploration, template_diversity) — ALL 0 trades
- Variant failures re-enter the loop and generate the same directives
- All specs share same broken architecture: EMA baseline + RSI confirmation + ATR gate + confidence_threshold
- Confidence threshold sweeps (0.55-0.60) have no effect when entry conditions never co-fire
- Recombine system also feeds into this loop (BTC 1h specs despite EXCLUDE_ASSET directive)
- Net effect: pipeline consumes 100% of backtest capacity running circular remediation on unfixable specs
- 3 Claude specs (ALMA Vortex, T3 EMA200, CCI KAMA) blocked for 3 consecutive cycles (U24→U26) due to capacity starvation
