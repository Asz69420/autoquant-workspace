---
id: failure-btc-all-strategies
type: failure
title: BTC produces 0 ACCEPT-tier results across all strategies tested
status: active
confidence: 0.95
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags: [btc, asset, failure]
updated_at: "2026-03-03T11:00:00Z"
---

19 cycles of testing. 0 BTC ACCEPTs across 740+ outcomes. Even the system champion (Vortex v3a) loses on BTC: PF=0.743, DD=19.4%. BTC 1h generates 0-1 trades per strategy. BTC's market microstructure may not suit the strategy architectures tested (transition-detection, mean-reversion, trend-following). Every BTC computation is confirmed waste.
