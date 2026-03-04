---
id: fact-zero-trade-signal-bottleneck
type: fact
title: All non-Claude spec sources produce zero trades due to AND-chain misalignment
status: active
confidence: 0.99
evidence_paths:
  - artifacts/backtests/20260304/
  - artifacts/backtests/20260305/
  - artifacts/batches/20260304/
  - artifacts/promotions/20260304/
  - artifacts/outcomes/20260304/outcome_notes_autopilot-1772624702.json
tags:
  - pipeline
  - signal
  - zero-trades
  - bottleneck
  - promotions
supporting_ids:
  - failure-pipeline-structural-death
  - fact-directive-loop-circular
validated_at: "2026-03-05T12:00:00Z"
updated_at: "2026-03-05T12:00:00Z"
---

102+ consecutive backtests have produced exactly 0 trades across ALL non-Claude spec sources: pipeline, promotions, refinement, and recombine. Entry conditions with 3+ AND-chained indicators never simultaneously fire within the same bar. The directive remediation loop amplifies the problem — every failure generates variant specs that fail identically.

- 102+ consecutive backtests: 0 trades (U21: 10, U22: 24, U23: 17, U24-U25: 15+, U26: +36 on 2026-03-05)
- Promotion pipeline: 55 promotions, ALL 0-trade specs
- Recombine system: also generating 0-trade specs (BTC 1h despite EXCLUDE_ASSET)
- Directive loop: every 0-trade outcome generates same 5 remediation directives → variant specs → 0 trades again
- Batch dedup rate: 95%+ (150+ batch files, near-total dedup)
- All 4 latest spec families (5063f4f1f99b, f5bcc194e9c3, 14c5a03a3c34, dcbc1d66558b) share identical EMA+RSI+ATR+confidence_threshold architecture
- Root cause: combinatorial condition assembly (3-5 AND conditions) without co-occurrence analysis
- Counter-evidence: Claude specs use max 2 conditions and generate 42-179 trades
- Structural insight: specs with <=2 entry conditions produce trades; specs with 3+ do not
