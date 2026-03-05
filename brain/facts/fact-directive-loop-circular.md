---
id: fact-directive-loop-circular
type: fact
title: Directive remediation loop is circular and self-amplifying — generates identical actions for every 0-trade failure, specs reference non-existent columns
status: active
confidence: 0.99
evidence_paths:
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624018-backfill-strategy-spec-20260304-5063f4f1f99b.strategy_spec.json
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772623802.json
  - artifacts/strategy_specs/20260304/strategy-spec-20260304-5063f4f1f99b.strategy_spec.json
  - artifacts/backtests/20260305/
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-489f8bcaea8f.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-88cf9e406e3d.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-5df8f61c0c71.strategy_spec.json
  - artifacts/strategy_specs/20260305/strategy-spec-20260305-dd7abf6f002b.strategy_spec.json
  - artifacts/outcomes/20260305/outcome_notes_autopilot-1772682858.json
tags:
  - pipeline
  - directives
  - circular-loop
  - zero-trades
  - compute-waste
  - self-amplifying
  - pseudo-signals
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - failure-pipeline-structural-death
  - fact-promotion-pipeline-zero-trade
  - fact-research-pipeline-homogeneous
validated_at: "2026-03-05T23:00:00Z"
updated_at: "2026-03-05T23:00:00Z"
---

The outcome→directive→variant→outcome loop generates identical remediation actions for every 0-trade failure. Every 0-trade outcome note produces the same 5 directives: GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE. These create variant specs (gate_adjust, entry_relax, exploration) that fail identically with 0 trades. The variant failures generate the same 5 directives again. Zero information gain per iteration.

- 130+ consecutive 0-trade backtests (U21: 10, U22: 24, U23: 17, U24-U25: 15+, U26: +36, U28: +10 same-spec retests, U29: +30 new outcomes), each generating same 5 remediation directives
- Loop crosses day boundary (2026-03-04 → 2026-03-05) with no circuit-breaker intervention
- All 4 U24 strategy spec families (5063f4f1f99b, f5bcc194e9c3, 14c5a03a3c34, dcbc1d66558b) show identical directive loop behavior
- 2026-03-05 specs (13a80050d94c, 5df8f61c0c71, 12c5d8d913ad, dd7abf6f002b) continue the same pattern
- U28: spec-5df8f61c0c71 tested 10x with 3 directive variants — all 0 trades. Classic single-spec loop.
- U29: NEW — directive specs contain abstract pseudo-parameters (confidence_threshold sweeps 0.55-0.60) that don't map to any dataframe column. These specs are FORMALLY INVALID — they could never produce trades even in perfect market conditions. The loop is generating syntactically broken specs.
- U29: All 30 latest outcome notes produce identical remediation directives with identical failure reasons (LOW_TRADE_COUNT, HIGH_DRAWDOWN, PF_BELOW_1)
- U28: 100+ new specs generated in strategy_specs/20260305/ — generation rate still accelerating despite total failure
- Each spec generates 3-4 variants (gate_adjust, entry_relax, exploration, template_diversity) — ALL 0 trades
- Variant failures re-enter the loop and generate the same directives
- All specs share same broken architecture: EMA baseline + RSI confirmation + ATR gate + confidence_threshold
- Recombine system also feeds into this loop (BTC 1h specs despite EXCLUDE_ASSET directive)
- Net effect: pipeline consumes 100% of backtest capacity running circular remediation on unfixable specs
- 9 Claude specs (27+ variants) blocked 6 consecutive cycles due to capacity starvation
- Confidence raised from 0.98 to 0.99: pseudo-signal discovery proves specs are structurally impossible, not just poorly tuned
