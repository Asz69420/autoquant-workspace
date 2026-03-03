---
id: fact-zero-trade-signal-bottleneck
type: fact
title: Pipeline-generated specs produce zero trades due to signal condition misalignment
status: active
confidence: 0.92
evidence_paths:
  - artifacts/backtests/20260304/
  - artifacts/batches/20260304/
tags:
  - pipeline
  - signal
  - zero-trades
  - bottleneck
supporting_ids:
  - failure-pipeline-structural-death
validated_at: "2026-03-04T18:00:00Z"
updated_at: "2026-03-04T18:00:00Z"
---

The latest 10 backtests ALL produced exactly 0 trades. Pipeline-generated entry conditions (AND-chains of 3-5 indicators) never simultaneously fire within the same bar. Signal clustering detected on 1h timeframe (conditions fire on adjacent bars but not the same bar). Post-BALROG-fix, backtests execute without schema errors but produce no trading signals.

- 10/10 latest backtests: 0 trades (gate reason: INSUFFICIENT_TRADES)
- Batch dedup rate: 87%+ (27-run full-grid batches 100% deduplicated)
- Signal clustering flagged: ETH 1h, SOL 1h (SIGNAL_CLUSTERED feasibility failure)
- Pipeline targets BTC 1h despite EXCLUDE_ASSET:BTC directives
- Root cause: combinatorial condition assembly without hypothesis-driven co-occurrence analysis
- Counter-evidence: Claude-designed specs on same indicators generate 42-179 trades (sufficient)
