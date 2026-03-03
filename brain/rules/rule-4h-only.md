---
id: rule-4h-only
type: rule
title: Only deploy and test strategies on 4h timeframe
status: active
confidence: 0.95
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
tags: [timeframe, 4h, deployment]
supporting_ids: [fact-eth-4h-dominance]
updated_at: "2026-03-03T11:00:00Z"
---

All ACCEPT-tier results are 4h. 1h consistently degrades PF by 0.94 points on average. 15m has 0 ACCEPTs ever. New strategy designs and backtests should target 4h exclusively unless explicitly testing a timeframe hypothesis.
