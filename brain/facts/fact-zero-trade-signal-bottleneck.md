---
id: fact-zero-trade-signal-bottleneck
type: fact
title: All non-Claude spec sources produce zero trades due to AND-chain misalignment
status: active
confidence: 0.97
evidence_paths:
  - artifacts/backtests/20260304/
  - artifacts/batches/20260304/
  - artifacts/promotions/20260304/
tags:
  - pipeline
  - signal
  - zero-trades
  - bottleneck
  - promotions
supporting_ids:
  - failure-pipeline-structural-death
validated_at: "2026-03-04T23:00:00Z"
updated_at: "2026-03-04T23:00:00Z"
---

51+ consecutive backtests have produced exactly 0 trades across ALL non-Claude spec sources: pipeline, promotions, and refinement. Entry conditions with 3+ AND-chained indicators never simultaneously fire within the same bar. The problem now extends beyond the pipeline to the promotion system (research → thesis → spec).

- 51/51+ consecutive backtests: 0 trades (U21: 10, U22: 24, U23: 17 more)
- Promotion pipeline: 55 promotions today, ALL 0-trade specs
- Batch dedup rate: 95%+ (150+ batch files, near-total dedup)
- Refinement: refine-8d9a5d5c and refine-d89fb280 both 0 trades across all variants
- Signal clustering flagged: ETH 1h, SOL 1h, SOL 4h
- Pipeline ignores EXCLUDE_ASSET:BTC and EXCLUDE_TIMEFRAME:1h directives
- Root cause: combinatorial condition assembly (3-5 AND conditions) without co-occurrence analysis
- Counter-evidence: Claude specs use max 2 conditions and generate 42-179 trades
- Structural insight: specs with <=2 entry conditions produce trades; specs with 3+ do not
