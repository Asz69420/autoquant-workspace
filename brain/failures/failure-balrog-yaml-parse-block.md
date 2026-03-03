---
id: failure-balrog-yaml-parse-block
type: failure
title: BALROG pre-backtest gate blocked all backtests due to inline YAML array parsing bug
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - data/logs/outbox/20260303T153200Z___autopilot-1772551811-BATCH_BACKTEST_SUMMARY___Backtester___FAIL.json
tags:
  - balrog
  - yaml
  - pipeline
  - schema
  - blocker
validated_at: "2026-03-04T12:00:00Z"
updated_at: "2026-03-04T12:00:00Z"
---

The validate_brain.py simple YAML parser uses json.loads() to parse inline arrays like `tags: [a, b, c]`. JSON requires quoted strings, so unquoted values fail parsing and return the raw string instead of an array. The schema then rejects it as "expected array". This blocked all 14 brain objects, producing 17 FAILs and 14 WARNs across 36+ backtest attempts over 6+ autopilot cycles.

- Root cause: parse_scalar() in validate_brain.py line 27-30 tries json.loads on inline arrays, fails silently
- Impact: 0 backtests executed since brain init (U18), drought surged 31 → 53
- Fix: Convert all inline arrays to multi-line YAML (`- item` per line), add validated_at timestamps
- Prevention: All future brain objects must use multi-line YAML list syntax only
