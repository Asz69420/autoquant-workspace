---
id: rule-yaml-multiline-only
type: rule
title: Brain object arrays must use multi-line YAML syntax only
status: active
confidence: 0.99
evidence_paths:
  - docs/claude-reports/STRATEGY_ADVISORY.md
  - scripts/quandalf/validate_brain.py
tags:
  - brain
  - yaml
  - schema
  - serialization
supporting_ids:
  - failure-balrog-yaml-parse-block
validated_at: "2026-03-04T12:00:00Z"
updated_at: "2026-03-04T12:00:00Z"
---

All array fields in brain object frontmatter must use multi-line YAML list syntax. The simple YAML parser in validate_brain.py cannot parse inline arrays.

Correct:
```yaml
tags:
  - asset
  - eth
```

Incorrect (causes BALROG FAIL):
```yaml
tags: [asset, eth]
```

This applies to: tags, evidence_paths, supporting_ids, contradictory_ids, supersedes, superseded_by.
