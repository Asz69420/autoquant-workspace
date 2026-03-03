---
id: failure-1h-degradation
type: failure
title: 1h timeframe consistently degrades strategy PF by 0.94 points vs 4h
status: active
confidence: 0.93
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags:
  - timeframe
  - 1h
  - degradation
supporting_ids:
  - fact-eth-4h-dominance
  - rule-4h-only
validated_at: "2026-03-04T12:00:00Z"
updated_at: "2026-03-04T12:00:00Z"
---

Every strategy tested on both 1h and 4h is worse on 1h:
- Vortex v3a: 1h PF=0.753 vs 4h PF=2.034 (delta -1.28)
- Vortex v3b: 1h PF=0.841 vs 4h PF=1.885 (delta -1.04)
- Vortex v2c: 1h PF=0.856 vs 4h PF=1.892 (delta -1.04)
- KAMA v2 SOL: 1h DD=36% vs Vortex SOL 4h DD=23.4%
- T3 Vortex SOL 1h: DD=81.3% (worst in system history)

Average PF degradation: 0.94 points. 1h is typically a losing timeframe. Signal noise at 1h frequency overwhelms edge.
