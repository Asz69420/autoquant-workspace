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
validated_at: "2026-03-04T23:45:00Z"
updated_at: "2026-03-04T23:45:00Z"
---

The outcome→directive→variant→outcome loop generates identical remediation actions for every 0-trade failure. Every 0-trade outcome note produces the same 5 directives: GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE. These create variant specs (gate_adjust, entry_relax, exploration) that fail identically with 0 trades. The variant failures generate the same 5 directives again. Zero information gain per iteration.

- 66+ consecutive 0-trade backtests, each generating same 5 remediation directives
- All 4 latest strategy spec families (5063f4f1f99b, f5bcc194e9c3, 14c5a03a3c34, dcbc1d66558b) show identical directive loop behavior
- Each spec generates 3-4 variants (gate_adjust, entry_relax, exploration, template_diversity) — ALL 0 trades
- Variant failures re-enter the loop and generate the same directives
- All specs share same broken architecture: EMA baseline + RSI confirmation + ATR gate + confidence_threshold
- Confidence threshold sweeps (0.55-0.60) have no effect when entry conditions never co-fire
- Recombine system also feeds into this loop (BTC 1h specs despite EXCLUDE_ASSET directive)
- Net effect: pipeline consumes 100% of backtest capacity running circular remediation on unfixable specs
