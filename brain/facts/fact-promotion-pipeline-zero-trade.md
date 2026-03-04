---
id: fact-promotion-pipeline-zero-trade
type: fact
title: Research-to-spec promotion pipeline generates specs that produce zero trades
status: active
confidence: 0.90
evidence_paths:
  - artifacts/promotions/20260304/
  - artifacts/strategy_specs/20260304/
  - artifacts/batches/20260304/
tags:
  - promotions
  - zero-trades
  - research-pipeline
supporting_ids:
  - fact-zero-trade-signal-bottleneck
  - failure-pipeline-structural-death
validated_at: "2026-03-04T22:00:00Z"
updated_at: "2026-03-04T22:00:00Z"
---

The promotion pipeline (research card → thesis → strategy spec) is now operational and active — 55 promotions ran on 2026-03-04. However, all promotion-generated specs share the same AND-chain signal design flaw as the autopilot pipeline: entry conditions never co-fire within the same bar.

- 55 promotions ran on 2026-03-04 (all status: OK)
- All promotion-generated specs produced 0 trades when backtested
- Promotions successfully generate valid spec files with thesis artifacts
- Promotion sources: research linkmaps from YouTube/TradingView ingestion
- The promotion pipeline generates VOLUME (spec files) but not QUALITY (tradeable specs)
- Same root cause as pipeline: combinatorial condition assembly, 3+ AND conditions
- Promotion pipeline is NOT hypothesis-driven — it translates research concepts mechanically
