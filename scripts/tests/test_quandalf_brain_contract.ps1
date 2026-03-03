$ErrorActionPreference = 'Stop'

$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location $ROOT

$tmpRoot = Join-Path $ROOT 'artifacts\tmp\quandalf_brain_smoke'
if (Test-Path $tmpRoot) {
  Remove-Item -LiteralPath $tmpRoot -Recurse -Force
}

$dirs = @(
  'brain\evidence',
  'brain\facts',
  'brain\rules',
  'brain\constraints',
  'brain\failures',
  'brain\journal',
  'brain\index',
  'brain\working_sets'
)
foreach ($d in $dirs) {
  New-Item -ItemType Directory -Path (Join-Path $tmpRoot $d) -Force | Out-Null
}

$evidencePath = Join-Path $tmpRoot 'brain\evidence\smoke-note.txt'
'Smoke evidence' | Set-Content -Path $evidencePath -Encoding UTF8

$fact = @'
---
id: fact.smoke.eth-range
type: fact
title: ETH range mean reversion outperformed in sample
status: active
confidence: 0.7
evidence_paths:
  - brain/evidence/smoke-note.txt
tags:
  - ETH
  - 4h
supporting_ids:
  - rule.smoke.bias
contradictory_ids: []
supersedes: []
superseded_by: []
updated_at: 2026-03-03T00:00:00Z
validated_at: 2026-03-03T00:05:00Z
---
Smoke fact body.
'@
$fact | Set-Content -Path (Join-Path $tmpRoot 'brain\facts\fact.smoke.eth-range.md') -Encoding UTF8

$rule = @'
---
id: rule.smoke.bias
type: rule
title: Prefer ranging setup when CHOP high
status: active
confidence: 0.6
evidence_paths:
  - brain/evidence/smoke-note.txt
tags:
  - ETH
  - 4h
supporting_ids:
  - fact.smoke.eth-range
contradictory_ids: []
supersedes: []
superseded_by: []
updated_at: 2026-03-03T00:01:00Z
validated_at: 2026-03-03T00:06:00Z
---
Smoke rule body.
'@
$rule | Set-Content -Path (Join-Path $tmpRoot 'brain\rules\rule.smoke.bias.md') -Encoding UTF8

$constraint = @'
---
id: constraint.smoke.risk
type: constraint
title: Keep risk per trade <= 1%
status: active
confidence: 1.0
evidence_paths:
  - brain/evidence/smoke-note.txt
tags:
  - ETH
  - 4h
applies_to_types:
  - rule
supersedes: []
superseded_by: []
updated_at: 2026-03-03T00:02:00Z
validated_at: 2026-03-03T00:07:00Z
---
Smoke constraint body.
'@
$constraint | Set-Content -Path (Join-Path $tmpRoot 'brain\constraints\constraint.smoke.risk.md') -Encoding UTF8

$failure = @'
---
id: failure.smoke.breakout-fake
type: failure
title: Breakout fakeouts in chop regime
status: active
confidence: 0.8
evidence_paths:
  - brain/evidence/smoke-note.txt
tags:
  - ETH
  - 4h
impact: drawdown
mitigation: require volatility expansion confirmation
supersedes: []
superseded_by: []
updated_at: 2026-03-03T00:03:00Z
validated_at: 2026-03-03T00:08:00Z
---
Smoke failure body.
'@
$failure | Set-Content -Path (Join-Path $tmpRoot 'brain\failures\failure.smoke.breakout-fake.md') -Encoding UTF8

$journal = @'
---
id: journal.smoke.2026-03-03
ts: 2026-03-03T00:09:00Z
pointers:
  - fact.smoke.eth-range
  - brain/evidence/smoke-note.txt
---
Validated smoke references.
'@
$journal | Set-Content -Path (Join-Path $tmpRoot 'brain\journal\journal.smoke.2026-03-03.md') -Encoding UTF8

$validateOut = & python scripts/quandalf/validate_brain.py --root $tmpRoot
if ($LASTEXITCODE -ne 0) { throw "validate_brain failed: $validateOut" }
if (($validateOut | Out-String) -notmatch 'BRAIN_VALIDATE \[OK\]') {
  throw "Expected validator OK summary, got: $validateOut"
}

$indexOut = & python scripts/quandalf/build_index.py --root $tmpRoot
if ($LASTEXITCODE -ne 0) { throw "build_index failed: $indexOut" }

$objectsPath = Join-Path $tmpRoot 'brain\index\objects.jsonl'
if (-not (Test-Path $objectsPath)) { throw 'objects.jsonl not created' }

$lineCount = (Get-Content $objectsPath | Measure-Object).Count
if ($lineCount -lt 4) { throw "Expected at least 4 indexed objects, got $lineCount" }

Write-Output 'PASS: quandalf brain contract smoke test'
